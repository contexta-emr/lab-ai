# Contexta Lab IDP

Attachment Intelligence for lab reports. A doctor uploads a PDF or a photograph of a lab
report; the service reads it, works out which patient it belongs to from the UHID printed on
the page, resolves every printed test name to a canonical code, and stores the result so a
five-year trend can be charted.

A standalone service with its own database. It sits **beside** `contexta-emr`, not inside it.

| Latest benchmark, 8 October 2026 | Corpus, 300 reports | Holdout, 15 unseen layouts |
|---|---|---|
| Recall · precision | **93.8% · 91.6%** | **85.3% · 86.0%** |
| Right code · right value | 99.7% · **97.1%** | 94.6% · 92.7% |

Details in [`docs/extraction-benchmark.md`](docs/extraction-benchmark.md) §0.

---

## How it works

```
 upload (console or API)
   │   the file is stored; a placeholder document waits in 'received'
   ▼
 OCR worker ── OpenParser (hosted OCR) ── blocks: tables, text, positions
   │
   ├─ Pass A   tables → rows, by what each column contains
   ├─ Pass B   only when Pass A read no value: a language model re-reads the
   │           engine's own text, and every value must quote a block it was sent
   ▼
 lab.fn_complete_document ── patient matched by UHID, labels resolved to codes
   ▼
 review queue ── a person confirms the patient ──► 'verified' ──► trends
```

Four rules shape everything:

- **Nothing is clinical fact until a person verifies it.** Only `status = 'verified'` documents
  reach `lab.v_results_verified`, the view every clinical read uses.
- **A misfiled result is a patient-safety event.** A UHID that matches only approximately goes
  to the review queue; it is never attached on a maybe.
- **An unknown test gets no code, never a wrong one.** No alias match means `analyte_id` is NULL
  and the label lands in `lab.unmatched_labels` for a person to map.
- **The database is the product.** All writes go through `lab.fn_*` functions; the API never
  writes `lab.*` tables directly.

---

## What is in here

```
db/                numbered SQL migrations 000-031: schema, functions, seed   ← the product
api/               FastAPI service; app/services/ocr/ is the extraction pipeline
web/               Next.js review console: upload, queue, review, patients
scripts/           migrations, OCR worker, corpus upload, scoring, repairs
bench/             run.ps1 (the corpus benchmark), results/ (engine output), reports/
e2e/               browser tests (Playwright, in its own container)
corpus/generator/  the synthetic corpus generator; catalog.py is the vocabulary
corpus/data/       300 synthetic reports, the sealed answer key, the 15-report holdout
docs/              architecture, benchmark, holdout, review findings
```

---

## Getting started

### Prerequisites

- **Docker Desktop.** Everything runs in containers: Postgres 16, the API, the worker, the console.
- **Git**, and on Windows **PowerShell** for `bench/run.ps1`.
- **uv**, only for the lint commands (`uvx ruff`).
- An **OpenParser API key** to read documents. An **Anthropic API key** is optional (Pass B).

### 1. Configure

```bash
cp .env.example .env
```

Fill in `.env`. It is gitignored and must stay that way.

| Variable | Needed for | Notes |
|---|---|---|
| `IDP_OPENPARSER_KEY` | reading any document | the worker reads nothing without it |
| `ANTHROPIC_API_KEY` | Pass B | empty means Pass B is off; the worker says so at start |
| `LABIDP_DATABASE_URL` | running against Neon | leave unset for the local database — see below |
| `DATABASE_URL` | scripts run on the host | the local stack is `postgresql://labidp:labidp_local_only@localhost:15432/labidp` |
| `ENVIRONMENT` | — | `development` turns authentication off; anything else keeps it on |

### 2. Start the stack

```bash
docker compose up -d --build
docker compose exec api python /work/scripts/run_migrations.py
```

| Service | Address |
|---|---|
| Console | http://localhost:3000 — no sign-in in development |
| API | http://localhost:8000 — interactive docs at `/docs`, health at `/health` |
| Postgres | `localhost:15432`, user / database `labidp`, password `labidp_local_only` |
| pgAdmin | `docker compose --profile tools up -d pgadmin`, then http://localhost:5050 |

Stop with `docker compose stop`; your data stays in the Docker volume.

### 3. Read some documents

Upload through the console's **Upload** page, or the whole synthetic corpus at once:

```bash
docker compose exec api python /work/scripts/upload_corpus.py              # 300 reports
docker compose exec api python /work/scripts/upload_corpus.py --limit 10   # a quick look
docker compose logs -f worker                                              # watch them read
```

The worker reads each one with OpenParser, about 7 seconds a document. Documents then wait in
the **Queue** for a person to confirm the patient; only confirmed documents appear in a
patient's trends.

---

## Running against Neon

The API and worker use the local Postgres unless `LABIDP_DATABASE_URL` is set in `.env`.

1. **Create a database** for this service in your Neon project — `CREATE DATABASE labidp;` in
   any SQL client connected to the project, with auto-commit on.
2. **Add the line to `.env`**, using the **direct** endpoint (no `-pooler` in the host; the pooler
   runs in transaction mode and breaks some DDL), with no quotes:
   ```
   LABIDP_DATABASE_URL=postgresql://USER:PASSWORD@ep-xxxx.region.azure.neon.tech/labidp?sslmode=require
   ```
3. **Create the schema** — either run the migrations against it, or copy the local database:
   ```powershell
   $neon = ((Select-String -Path .env -Pattern '^LABIDP_DATABASE_URL=(.+)$').Matches[0].Groups[1].Value).Trim()
   docker compose exec -T db pg_dump -U labidp -d labidp --no-owner --no-privileges -n core -n lab -f /tmp/schemas.sql
   docker compose exec -T db pg_dump -U labidp -d labidp --no-owner --no-privileges -t public.schema_migrations -f /tmp/migrations.sql
   docker compose exec -T db psql $neon -c "CREATE EXTENSION IF NOT EXISTS pg_trgm"
   docker compose exec -T db psql $neon -q -v ON_ERROR_STOP=1 --single-transaction -f /tmp/schemas.sql > $null
   docker compose exec -T db psql $neon -q -v ON_ERROR_STOP=1 --single-transaction -f /tmp/migrations.sql > $null
   ```
4. **Switch:** `docker compose up -d api worker`. To come back, remove the line and run the same
   command.

Neon suspends when idle, so the first request after a pause takes a few seconds. Uploaded files
stay on the machine running the stack (`storage/`); Neon holds only the database.

---

## The database

Hand-written, numbered SQL in `db/`, applied in order by `scripts/run_migrations.py`, which
records each file and its checksum in `public.schema_migrations`.

```bash
docker compose exec api python /work/scripts/run_migrations.py --status   # applied and pending
docker compose exec api python /work/scripts/run_migrations.py --with-holdout   # also seed P21-P23
```

**Never edit an applied migration — write a new one.** The runner warns when a file no longer
matches what was applied. The holdout patients are seeded only when asked for, so evaluation
patients cannot end up in a database by accident.

```
core.patients ──────┐
                    │  matched by the UHID printed on the page
lab.documents ──────┘   one uploaded file, its extraction state, its patient
     │
     ├── lab.reports            one lab report inside that file
     │        ├── lab.report_sections    one panel block ("COMPLETE HEMOGRAM")
     │        │        └── lab.results   one printed test line
     │        └── lab.report_notes       interpretation, footnotes, remarks
     ├── lab.document_lists     the doctor's order and patient tags typed on review
     └── lab.document_events    append-only audit of every status change

lab.panels ── lab.panel_aliases ── lab.panel_analytes   panels, their titles, their members
lab.analytes ── lab.analyte_aliases                     tests and every spelling they arrive under
           └── lab.reference_ranges                     normal, by sex and age
lab.unmatched_labels                                    what the vocabulary still misses
```

The `core` tables are a compatibility subset of the EMR's own, with its table and column names,
so pointing this service at the EMR's database later changes no query.

**The alias table is the whole game.** One test arrives as `Creatinine, Serum`, `S. CREATININE`,
`Sr.Creat` and `CREATININE (SERUM)`. `lab.fn_resolve_analyte` tries an exact alias, then a
normalised one, then trigram similarity with the score stored — and an alias can be scoped to a
panel, so `ALBUMIN` under a urine heading is not serum albumin.

### Conventions

- **BigInt identity keys**, sent as strings. Validate with `/^\d+$/`; never `Number()` or
  `parseInt()`, which corrupt silently above 2^53.
- **`practice_id` on every tenant table**, taken from the verified token, never from the request.
- **Soft delete** (`is_deleted`, `deleted_at`, `deleted_by`) and audit columns everywhere.
- **No native enums**: `VARCHAR` plus `CHECK`, because changing a CHECK is a migration and
  changing an enum is an outage.

---

## Testing

All of these pass on `main` and must keep passing:

```bash
uvx ruff@0.16.10 check .                                        # lint, one rule set for the repo
uvx ruff@0.16.10 format --check .                               # formatting
docker compose exec -T -w /app api mypy                         # types
docker compose exec -T -w /app api python -m pytest tests -q    # API and database tests
docker compose exec -T web npx tsc --noEmit                     # console types
docker compose exec -T web npx next lint                        # console lint
docker compose --profile e2e run --rm e2e                       # browser tests
```

The database tests run inside transactions that are rolled back, so they leave nothing behind.
The extraction tests read the recorded engine output in `bench/results/`, so they need no OCR.

---

## The benchmark

```powershell
.\bench\run.ps1              # all 300: clear, upload, read, score
.\bench\run.ps1 -Limit 10    # a quick check first
.\bench\run.ps1 -KeepData    # rejoin an interrupted run, or re-score a finished one
```

It **clears the local database** before uploading — the corpus is synthetic, so nothing real is
lost — and refuses to run while `LABIDP_DATABASE_URL` is set. A full run costs about Rs 30 in
OpenParser and a few rupees in Pass B, and takes 40 minutes to 3 hours depending on how hard
OpenParser throttles. Reports land in `bench/reports/`; the per-document engine output in
`bench/results/` is what makes later measurements free:

```bash
docker compose exec api python /work/scripts/score_corpus.py --by-layout          # score what is stored
docker compose exec api python /work/scripts/upload_corpus.py --corpus holdout    # the 15 unseen reports
docker compose exec api python /work/scripts/score_corpus.py --corpus holdout --by-layout
```

**The answer key is for scoring only.** Nothing in the extraction path may read
`corpus/data/answers/`, or the score measures nothing.

---

## Where documents go

| Service | What is sent | Where | Cost |
|---|---|---|---|
| OpenParser | every uploaded document, whole | United States | about Rs 0.09 a page |
| Anthropic (Pass B) | only documents Pass A read no value from; table and text blocks with header lines — name, UHID, age, referring doctor — withheld | United States | about Rs 0.07 a document |

Production patient data belongs on Postgres in an Azure India region, which is the decision on
record; Neon has no India region.

---

## Troubleshooting

- **A code change does not show up.** Docker Desktop on Windows passes no file events into
  containers: `docker compose restart api` after editing `api/app/`, and
  `docker compose restart worker` for the worker.
- **`-w /app` fails with "Cwd must be an absolute path"** in Git Bash, which rewrites `/app` into
  a Windows path. Prefix the command with `MSYS_NO_PATHCONV=1`, or use PowerShell.
- **The first request to Neon times out.** It was asleep; try again.

---

## Documentation

| | |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | the system, every table and function, the passes — with diagrams |
| [`docs/grounded-pass.html`](docs/grounded-pass.html) | the whole system on one page, and exactly what Pass B sends |
| [`docs/extraction-benchmark.md`](docs/extraction-benchmark.md) | the corpus runs: 8 October with Pass B, 23 September before it |
| [`docs/holdout-testset.md`](docs/holdout-testset.md) | the 15 reports the extractor has never seen, and how to read their score |
| [`docs/review-2026-10-08.md`](docs/review-2026-10-08.md) | code review findings, what is fixed and what is open |
| [`docs/corpus-summary.md`](docs/corpus-summary.md) | the synthetic corpus: patients, layouts, damage |
| [`docs/schema.dbml`](docs/schema.dbml) | the schema, for dbdiagram.io |
