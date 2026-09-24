# Extraction benchmark — the whole corpus, end to end

**Run of 2026-09-23.** 300 synthetic lab reports through the real product path —
`POST /documents`, the OCR worker, `lab.fn_ingest_lab_document` — scored against the
sealed answer key. First time the full corpus has been read by OpenParser.

```powershell
.\bench\run.ps1
```

Roughly 8 seconds a document, about 40 minutes and ₹27 for the 300. Outputs land in
`bench/reports/<timestamp>.txt` and `.json`; the per-document dumps in `bench/results/`
are what make every subsequent measurement free (see [Reproducing](#reproducing-it-for-nothing)).

---

## 1. Headline

| Metric | Value | |
|---|---|---|
| Reports | 300 | every PDF in the corpus |
| Rows printed | 4,177 | what the answer key says is on the pages |
| Rows found | 3,651 | |
| **Recall** | **87.4%** | of the rows printed, how many we found |
| **Precision** | **86.1%** | of the rows we produced, how many are real |
| **Code accuracy** | **99.7%** | given a row we found, the right canonical code — 7 wrong |
| **Value accuracy** | **85.2%** | given a row we found, the right number |
| Reports yielding nothing | 26 | |

Precision looks low by construction: rows printed with no readable value are kept
deliberately, and the answer key does not contain them. That is a design decision from
CLAUDE.md §2 — an honest blank beats an invented number — not a defect to tune away.

### The one number that matters most

**Value accuracy, not recall.** 3,651 rows were found and about **541 carry the wrong
number**. A missed row is a hole a reviewer can see; a wrong value is a false reading on
the right chart, which nobody sees. `scripts/score_corpus.py` says so in its own legend,
and the data agrees: we lose more clinical truth to misread values than to missed rows.

---

## 2. Was it tuned to what we looked at?

Patients 1–4 are the reports that were opened and inspected while building the pipeline.
The rest were never looked at.

| Split | Reports | Rows | Recall | Precision | Code | Value | Wrong | Empty |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Developed against (P01–P04) | 60 | 881 | 90.1% | 92.0% | 99.6% | 84.8% | 0 | 2 |
| **Never inspected (P05–P20)** | **240** | **3,296** | **86.7%** | 84.6% | 99.7% | **85.3%** | 7 | 24 |

A 3.4-point recall gap and **value accuracy that is fractionally better on the held-out
set** (85.3% vs 84.8%). The pipeline is not fitted to the documents that were read. That
was an explicit constraint on this work and it holds.

---

## 3. By layout — the view worth reading

A single recall number hides which pages actually fail.

| Layout | Reports | Rows | Found | Recall | Precision | Code | Value | Empty |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `handwritten_full` | 1 | 1 | 0 | **0.0%** | — | — | — | 1 |
| `register_page` | 2 | 5 | 0 | **0.0%** | 0.0% | — | — | 0 |
| `chat_screenshot` | 3 | 9 | 0 | **0.0%** | — | — | — | 3 |
| `cut_sheet` | 4 | 19 | 1 | **5.3%** | 5.3% | 100.0% | 100.0% | 0 |
| `thermal_slip` | 18 | 24 | 5 | **20.8%** | 35.7% | 100.0% | **0.0%** | **17** |
| `glossy_marketing` | 6 | 84 | 35 | 41.7% | 45.5% | 100.0% | 97.1% | 0 |
| `boxed_panels` | 17 | 233 | 130 | 55.8% | 53.7% | 100.0% | 71.5% | 1 |
| `ledger_ruled` | 13 | 164 | 99 | 60.4% | 58.9% | 96.9% | 81.8% | 0 |
| `two_column` | 15 | 186 | 125 | 67.2% | 81.7% | 100.0% | 72.8% | 0 |
| `mixed_print_hand` | 19 | 227 | 169 | 74.4% | 88.0% | 100.0% | 87.0% | 0 |
| `kv_header_table` | 25 | 261 | 216 | 82.8% | 75.5% | 99.5% | 98.1% | 0 |
| `handwritten_values` | 20 | 25 | 22 | 88.0% | 84.6% | 100.0% | **50.0%** | 3 |
| `range_bar` | 2 | 21 | 19 | 90.5% | 86.4% | 100.0% | 89.5% | 0 |
| `landscape_wide` | 10 | 99 | 92 | 92.9% | 90.2% | 100.0% | 100.0% | 0 |
| `dense_multipanel` | 23 | 799 | 744 | 93.1% | 97.0% | 99.9% | **70.7%** | 1 |
| `minimal_lines` | 13 | 94 | 89 | 94.7% | 89.9% | 98.9% | **31.5%** | 0 |
| `mobile_photo` | 3 | 38 | 36 | 94.7% | 94.7% | 97.1% | 100.0% | 0 |
| `duplicate_watermark` | 5 | 41 | 39 | 95.1% | 88.6% | 100.0% | 97.4% | 0 |
| `typewriter_manual` | 9 | 59 | 57 | 96.6% | 90.5% | 100.0% | **24.6%** | 0 |
| `carbon_copy` | 6 | 65 | 64 | 98.5% | 95.5% | 98.4% | 62.5% | 0 |
| `clean_table` | 42 | 572 | 566 | 99.0% | 86.3% | 99.8% | 91.9% | 0 |
| `continuation` | 20 | 928 | 920 | 99.1% | 99.1% | 99.9% | 99.3% | 0 |
| `poor_scan` | 11 | 139 | 139 | **100.0%** | 88.5% | 99.3% | 97.1% | 0 |
| `fax_header` | 8 | 51 | 51 | **100.0%** | 72.9% | 100.0% | 98.0% | 0 |
| `dot_matrix_pinfeed` | 3 | 16 | 16 | **100.0%** | 80.0% | 100.0% | 75.0% | 0 |
| `discharge_summary` | 2 | 17 | 17 | **100.0%** | 100.0% | 100.0% | 100.0% | 0 |

Worth noting up front: **`poor_scan`, `fax_header` and `mobile_photo` are at or near 100%
recall.** Those are the layouts with no text layer at all — pure OCR cases. The engine
handles degraded images better than it handles unusual *table geometry*, which is the
opposite of what you would guess and it reframes where the remaining work is.

---

## 4. Three findings

### 4.1 Value accuracy is the problem, and it is concentrated

Recall is respectable almost everywhere. Reading the right number off a found row is not.

| Layout | Rows found | Value right | ≈ wrong values |
|---|---:|---:|---:|
| `dense_multipanel` | 744 | 70.7% | **~218** |
| `minimal_lines` | 89 | 31.5% | ~61 |
| `typewriter_manual` | 57 | 24.6% | ~43 |
| `boxed_panels` | 130 | 71.5% | ~37 |
| `two_column` | 125 | 72.8% | ~34 |
| `carbon_copy` | 64 | 62.5% | ~24 |
| `handwritten_values` | 22 | 50.0% | ~11 |

**`dense_multipanel` alone is about 40% of every wrong value in the corpus**, because it
carries 799 rows — a fifth of the entire key — at 70.7%. High recall on a high-volume
layout hides a large absolute error. It is the single highest-value thing to look at, and
its 93.1% recall is exactly why it has not looked like a problem until now.

The pattern across `minimal_lines`, `typewriter_manual` and `carbon_copy` — high recall,
collapsed value accuracy — says the row is located correctly and the wrong *column* is
being read from it. That is column-role inference, not OCR. `columns.py` is where to look.

### 4.2 The recall cliffs are narrow and mostly deliberate

Three layouts return nothing at all: `handwritten_full`, `register_page`,
`chat_screenshot` — 6 reports, 15 rows. These are the pages CLAUDE.md §9 describes as
deliberately hostile, including the three a clinic would send back. Low priority.

**`thermal_slip` is the exception and the one real recall target**: 18 reports, **17 of
them empty**, 20.8% recall, 0% value on the five rows it does find. That is 17 of the 26
empty reports in the whole corpus — the single largest recoverable block. A till-roll is
narrow and very long, so the likely cause is page geometry rather than legibility, which
would make it a contained fix.

Empty reports break down as: `thermal_slip` 17, `chat_screenshot` 3, `handwritten_values`
3, and one each in `handwritten_full`, `boxed_panels`, `dense_multipanel`.

### 4.3 All 7 wrong codes are one known bug

```
P05-R10  'ALB'      key=UR_PROT  stored=ALB
P08-R03  'ALBUMIN'  key=UR_PROT  stored=ALB
P11-R03  'ALBUMIN'  key=UR_PROT  stored=ALB
P11-R12  'ALB'      key=UR_PROT  stored=ALB
P14-R03  'ALBUMIN'  key=UR_PROT  stored=ALB
P15-R03  'ALBUMIN'  key=UR_PROT  stored=ALB
P17-R03  'ALBUMIN'  key=UR_PROT  stored=ALB
```

`ALBUMIN` printed under a urine heading means urine protein, not serum albumin. This is
precisely what `requires_panel_id` in migration `007` exists to prevent (CLAUDE.md §5),
so the alias table is not at fault — **the section is not resolving to the urine panel**,
and a panel-scoped alias that never sees a panel never gets its chance. Smallest of the
three fixes, and the one with a patient-safety edge: it puts a urine result on a serum
albumin trend line.

### 4.4 Labels most often missed

```
15x  VITAMIN D3 (25-OH)        7x  Epith. Cells        6x  S.G.P.T.
14x  HAEMOGLOBIN               7x  TSH                 6x  Sr.Creat
12x  Ferritin, Serum           7x  Free T4             5x  CHOLESTEROL - TOTAL
 8x  Vitamin D (25-OH)         7x  S. T.S.H.           5x  Total Leucocyte Count
                               7x  TLC                 5x  S.G.O.T.
```

These are ordinary, central analytes in ordinary spellings — not exotic ones. They are
missed because of where they sit on certain pages, not because the vocabulary lacks them.
Consistent with §4.1 and §4.2: a geometry problem, not a vocabulary problem.

---

## 5. Reproducing it for nothing

The run wrote **300 `.raw.json` + 300 `.extraction.json`** into `bench/results/`, one pair
per PDF, named after it:

```
P01-R09.pdf  →  P01-R09.OPENPARSER.raw.json          engine blocks, before interpretation
             →  P01-R09.OPENPARSER.extraction.json   what the pipeline made of them
```

This is the convention from `src/idp/outputs.py` in the idp workspace, and it is what
turns the next measurement from ₹27 and forty minutes into a few seconds and nothing:

```bash
docker compose exec -T api python /work/scripts/replay.py --by-layout
```

`replay.py` rebuilds every extraction from the saved blocks and re-scores — **no
OpenParser calls**. Change the pipeline, run it, see whether recall moved. Try three
ideas and throw two away, which is not something you do when each measurement is billed
per page.

The round trip was verified rather than assumed: `read_raw` → `build_extraction`
reproduces a recorded extraction byte-identical, so replay measures the pipeline and not
a lossy dump.

### What replay cannot tell you

**Recall and value only.** An analyte code comes from `fn_resolve_analyte` against the
alias table, so code accuracy needs the database and a real ingest — `score_corpus.py`
after a real run. Replay answers *did the change find more rows and read them right*; the
scorer answers *did the right codes land on them*. Neither substitutes for the other.

The worker writes the dumps and never sees `corpus/data/answers/`; `api` holds the key
and does the scoring. That separation is deliberate — CLAUDE.md §7, a parser that can
read the answers measures nothing.

---

## 6. Bugs this run found

**`results_flag_check` was killing whole documents.** `lab.results.flag` is `VARCHAR(4)`
with a CHECK allowing exactly H, L, HH, LL, A, N. The payload builder clipped whatever sat
in the flag column to four characters to make it fit, so a column misread as the flag
column turned `Interpretation` into `Inte` — short enough to pass the length, not a flag,
CHECK violation, INSERT aborted, **document lost after three OpenParser calls**. About 10%
of documents were dying this way before it was caught mid-run. `split_flag_suffix` can
also emit `*`, `**`, `↑` and `↓`, none of which the CHECK allows, so `Inte` was only the
first of several. Fixed by validating against the six rather than truncating; unrecognised
is NULL, the same rule as an unknown analyte code. Migration `015` fixes the same bug on
the review path, where a reviewer typing "High" got a 500 for being right.

A `BEFORE INSERT` trigger — the pattern `008` used for `ref_low`/`ref_high` — cannot fix
this. `VARCHAR(4)` is enforced when the tuple is built, before any BEFORE trigger runs.
Measured on a temp table, not assumed.

**`2>&1` on a native command threw away a completed run.** In PowerShell 5.1, redirecting
a native command's stderr wraps every line in an `ErrorRecord`; with
`$ErrorActionPreference = "Stop"` that terminates the script. `bench/run.ps1` did this
around the scoring step, so the first full run finished, computed every number, and died
before writing the report. Also: `score_corpus.py` exits non-zero when it finds a wrong
code, which is a finding and not a failure — its exit code is now recorded, not obeyed.

---

## 7. What to do next

In the order the numbers argue for:

1. **`dense_multipanel` values** — ~218 wrong numbers, about 40% of all value error, on a
   layout already at 93.1% recall. Highest return.
2. **`thermal_slip`** — 17 empty reports, the largest recoverable recall block, and
   probably page geometry rather than legibility.
3. **Urine albumin → `UR_PROT`** — 7 rows, smallest fix, and the only one of the three
   that can put a result on the wrong patient's trend line.

All three are now testable against the full corpus for free. Measure before and after,
in either direction — CLAUDE.md §5 records two changes that looked obviously right and
made things worse.
