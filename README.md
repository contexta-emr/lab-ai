# Contexta Lab IDP

Attachment Intelligence for lab reports: a doctor uploads a PDF or a photograph
of a lab report, the service reads it, works out which patient it belongs to
from the UHID printed on the page, resolves every printed test name to a
canonical code, and stores the result so a five-year trend can be charted.

This is a standalone service. It owns its own database and does not touch the
EMR's. It sits **beside** `contexta-emr`, not inside it.

---

## What is in here

```
contexta-lab-idp/
├── db/          the database: schema, functions, seed          ← start here
├── api/         FastAPI service (Python)                       ← the middle layer
├── web/         Next.js review console (TypeScript)            ← the UI
├── corpus/      300 synthetic lab reports + the generator      ← test data
├── scripts/     migration runner, corpus loader
└── docs/        the corpus spec and the Top 10 Panels reference
```

Four things to understand before anything else:

**The database is the product.** The schema, the analyte master and the
Postgres functions are where the real thinking is. The API is a thin, careful
layer over them; the console is a thin layer over the API. If you read one
folder, read `db/`.

**Nothing is clinical fact until a human says so.** A parsed result sits at
`status = 'needs_review'` or `'parsed'` until somebody confirms the patient
match. Only then does it become `'verified'`, and only verified rows appear in
`lab.v_results_verified`, which is what any clinical read should use. A misfiled
lab result is a patient-safety event, so the pipeline is built to stop rather
than guess.

**An unknown test gets no code, never a wrong one.** If a printed label matches
no analyte, `lab.results.analyte_id` is NULL and the label goes into
`lab.unmatched_labels` for a human to map. A confident wrong code is worse than
an honest blank, because a wrong code silently corrupts a trend line.

**The corpus is synthetic and says so.** All 300 reports and 20 patients are
invented. Every document row carries `is_synthetic = true` and can be deleted in
one statement.

---

## Getting it running

### 1. A database

This service needs its own PostgreSQL 16 database — not the EMR's. A Neon
project is fine, so is a local Docker Postgres.

**Connecting DBeaver to Neon.** Neon gives you a string like
`postgresql://user:pwd@ep-xxx.region.aws.neon.tech/dbname?sslmode=require`.
In DBeaver: *New Connection → PostgreSQL*, host is the `ep-….neon.tech` part,
port 5432, then database, user and password. On the **SSL tab tick Use SSL and
set sslmode = require** — Neon refuses plaintext connections.

Two things that catch people out. Use the **direct endpoint, not the `-pooler`
one**, for migrations: the pooler runs in transaction mode and breaks `CREATE
TYPE`, advisory locks and some DDL. And Neon **autosuspends when idle**, so the
first connection after a break takes a few seconds and may time out once —
reconnect and it is awake.

### 2. Credentials

```bash
cp .env.example .env
# put your connection string in .env
```

`.env` is gitignored and must stay that way. The EMR repo already has a live
credential incident on record (`docs/GETTING_STARTED.md:83,85` and
`apps/api/.env.example:41-42` carry real passwords); do not add a second one.
`git rm` does not clear history.

### 3. Schema and seed data

```bash
pip install "psycopg[binary]"
python scripts/run_migrations.py --status     # what is pending
python scripts/run_migrations.py              # apply it
```

That applies, in order:

| file | what it creates |
|---|---|
| `000_core_compat.sql` | a minimal `core` schema — practices, users, patients, visit_attachments |
| `001_schema_and_master.sql` | the `lab` schema, panels, analytes, aliases, reference ranges |
| `002_documents_reports_results.sql` | documents, reports, sections, results, notes, audit |
| `003_functions.sql` | resolve, match, ingest, review, trend |
| `004_seed_analyte_master.sql` | 16 panels, 108 analytes, ~357 aliases, reference ranges |
| `005_seed_practice_and_patients.sql` | the demo practice and 20 synthetic patients |

**If you would rather create the tables from DBeaver than from the script.**
Open a SQL editor on the connection and run the six files **in order**, one at a
time, each as a whole script (Alt+X in DBeaver, not Ctrl+Enter — Ctrl+Enter
sends one statement). Order matters: `003` references tables `002` creates, and
`004`/`005` insert into them. The only thing you lose is `public.schema_
migrations`, so nothing records what has been applied and a re-run of `004` will
duplicate seed rows. Fine for a first look; use the script once anyone else
touches the database.

**About `000_core_compat.sql`.** The EMR's `core` schema is not in this database,
but `lab.*` needs a patient, a practice, a user and an uploaded file to point at.
So we create those four tables using the EMR's exact table names, column names
and types, copied from `apps/api/prisma/schema.prisma`. The day this service is
pointed at the real EMR database, you drop `000` from the run order and nothing
else changes — not a query, not a function, not a line of API code, because the
names already match.

### 4. Load the test corpus

```bash
python scripts/load_corpus.py
```

300 documents go in through `lab.fn_ingest_lab_document`, the same function the
real parser calls. Most come out verified; three marked illegible and one in
thirty with a deliberately OCR-mangled UHID land in the review queue, so the
queue has something real in it.

### 5. The API and the console

```bash
cd api && pip install -e . && uvicorn app.main:app --reload    # localhost:8000
cd web && npm install && npm run dev                           # localhost:3000
```

Or `docker compose up` to get Postgres, the API and the console together.

---

## The database, in one page

```
core.patients ──────┐
                    │  matched by UHID printed on the page
lab.documents ──────┘   one uploaded file, its extraction state, its patient
     │
     ├── lab.reports            one lab report inside that file
     │        │
     │        ├── lab.report_sections    one panel block ("COMPLETE HEMOGRAM")
     │        │        │
     │        │        └── lab.results   one printed test line
     │        │
     │        └── lab.report_notes       interpretation, footnotes, remarks
     │
     └── lab.document_events    append-only audit of every status change

lab.panels ── lab.panel_aliases        the titles a panel arrives under
lab.analytes ── lab.analyte_aliases    the spellings a test arrives under
           └── lab.reference_ranges    normal, by sex and age
lab.unmatched_labels                   what the vocabulary still misses
```

### The alias table is the whole game

The same test arrives as `Creatinine, Serum`, `S. CREATININE`, `Sr.Creat` and
`CREATININE (SERUM)`. Query the raw printed label and a trend line silently
plots three points where there should be seven. `lab.analyte_aliases` holds
every spelling; `lab.fn_resolve_analyte` tries them in three passes:

1. `exact_alias` — the spelling is in the master verbatim
2. `normalised_alias` — the same once case and punctuation stop mattering
3. `fuzzy_alias` — trigram similarity above a threshold, with the score stored

No match returns nothing, and the caller writes NULL.

### Reference ranges are not one number

A haemoglobin of 12.4 is normal for a woman, low for a man, and normal for a
six-year-old. `lab.reference_ranges` holds one row per applicable band, keyed by
sex and age, and the most specific match wins.

---

## The functions

Everything the API does goes through these. It never writes `lab.*` directly and
never builds SQL — matching the EMR's own functions-first rule. Every function
takes `p_practice_id` explicitly, and the API passes the value from the verified
token, never from the request body.

| function | does |
|---|---|
| `lab.fn_resolve_analyte` | printed label → canonical analyte, with method and confidence |
| `lab.fn_resolve_panel` | printed section heading → canonical panel |
| `lab.fn_match_patient_by_uhid` | the auto-detect step; fuzzy hits score below 1 so they quarantine |
| `lab.fn_ingest_lab_document` | writes the whole document tree in one transaction |
| `lab.fn_review_lab_document` | a human confirms or rejects; cascades the patient down |
| `lab.fn_get_analyte_trend` | every verified point for one analyte, in date order |

---

## The corpus

`corpus/` holds 300 synthetic lab reports for 20 patients across five years,
plus the generator that made them.

```
corpus/generator/     catalog.py, render.py, build.py, layouts/, patients/
corpus/data/pdfs/     P01/…P20/  — 300 PDFs, the only thing a parser should see
corpus/data/answers/  reports.csv, rows.csv — the sealed key, for scoring only
corpus/data/vitals/   20 JSON files — height, weight, BMI, BP, SpO2, temperature
corpus/data/html/     the source pages, so a layout tweak re-renders
```

It is deliberately hostile: 26 layouts including a thermal till roll, a
handwritten register page, a WhatsApp screenshot, a discharge summary with the
labs buried in a section, and a chain-lab format where values sit on range bars.
52 reports carry physical damage — yellowed paper, fold creases, tea rings, torn
corners, cropped edges, phone photographs in bad light — and three are
deliberately illegible.

Those 52 have no text layer and need OCR: `paddle_vl` (PaddleOCR-VL on our own
hardware, ~20 min a page, in boundary) or `openparser` (the same model hosted,
~6 seconds and ~₹0.09 a page, but the document leaves India). Being synthetic,
this corpus is one of the few things that may legitimately go to the hosted
engine — see `docs/architecture.md` §4a.

**The answer key is not input.** `corpus/data/answers/` is how you score an
extraction afterwards. Nothing in the parsing path may read it.

`catalog.py` is the single source of truth for the vocabulary: `db/seed/
export_master.py` generates the analyte master SQL from it, so the database and
the corpus cannot drift apart.

---

## Conventions

Carried over from the EMR so this ports cleanly:

- **BigInt identity primary keys.** Validate with `/^\d+$/` before casting;
  never `Number()` or `parseInt()`, which corrupt silently above 2^53.
- **`practice_id` on every tenant-scoped table**, taken from the verified token
  and never from client input. Sub-resources are checked by parent id *and*
  `practice_id`.
- **Soft delete** — `is_deleted`, `deleted_at`, `deleted_by` — and full audit
  columns on every table.
- **No native enums.** `VARCHAR` plus a `CHECK`, as the EMR does, because
  changing a CHECK is a migration and changing an enum is an outage.
- **Functions-first.** The API calls functions; it does not write tables.

## Open questions this work touches

- `lab.results` is the normalised child table the EMR has not yet decided to
  build. CLAUDE.md §6 records `lab_attachments` JSONB versus
  `core.consultation_labs` as undecided and blocking. This service settles the
  question for itself; the EMR still has to make its own call.
- Data residency. Neon has no India region. DPDPA does not name a separate
  health-data category today, but a production deployment holding real PHI
  should be on Azure Postgres in an India region, which is the decision already
  on record.
