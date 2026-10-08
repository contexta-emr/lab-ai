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

## 0. Latest — the re-run of 8 October 2026, Pass B on

Fresh database, all 300 re-uploaded and re-read, the grounded LLM pass (Pass B, Claude
Haiku 4.5) on, firing on any page Pass A read **no value** from. `master` at `833756c`.
Reports: `bench/reports/2026-10-08-2321.txt` (corpus) and `2026-10-08-holdout.txt`.
**Sections 1–8 below are the 23 September run, kept as recorded.**

| Corpus, 300 reports, 4,177 rows | 23 Sep | **8 Oct** |
|---|---:|---:|
| Rows found | 3,651 | **3,920** |
| Recall | 87.4% | **93.8%** |
| Precision | 86.1% | **91.6%** |
| Right code, of rows with a code | 99.7% | 99.7% |
| **Right value**, of rows found | 85.2% | **97.1%** |
| Wrong codes | 7 | 7 — the same urine-albumin bug, §5.3 |
| Reports that yielded nothing | 26 | **5** |

| Holdout, 15 reports, 224 rows, layouts never seen | 25 Sep | **8 Oct** |
|---|---:|---:|
| Rows found | 180 | **191** |
| Recall · precision | 80.4% · 83.7% | **85.3% · 86.0%** |
| Right value | 92.2% | **92.7%** |
| Wrong codes · UHID read | — · 12/15 | **0** · 12/15 |

**Where it moved.** `thermal_slip` 20.8% → **87.5%** recall and 17 empty reports → 1, which is
Pass B. `boxed_panels` 55.8% → 96.1%, `glossy_marketing` 41.7% → 100%, `ledger_ruled` 60.4% →
93.3% and `cut_sheet` 5.3% → 52.6%, which is the Pass A work since September. Value accuracy
rose on nearly every layout — the micro sign (review B1) and the value/unit splitting.
`two_column` is still the hole at **67.7%**.

**Pass B, measured on the final state** (the 31 documents re-read on the fixed code, and the
holdout): 39 escalations — 25 pages with no rows, and **14 with rows but no value on any**,
which the old zero-rows rule would never have sent. 38 calls, 74 rows returned, **73
grounded, 1 discarded** by the grounding check. **$0.0301, about ₹0.07 a call**, logged by the
worker from the API's own usage figures.

**What the run found, and what was fixed during it:**

- `fn_purge_synthetic` predated `lab.document_lists`, so the first attempt's clearing failed —
  and `run.ps1` hid the error and scored the old data as new. Fixed: migration `031`, and
  `run.ps1` clears in one transaction and stops on failure.
- Pass B's `merge()` appended recovered rows beside Pass A's empty ones (every test twice), and
  stored values as quoted — `1.12 mg/dL $ H $`, no number. Fixed: a recovered value fills the
  empty row of the same label, cleaned the way Pass A cleans a cell.
- The model sometimes files the flag under UNIT; and `mL/min/1.73m²` matched no unit pattern,
  in either pass, so eGFR kept no number. Both fixed.
- The worker buffered its log in 8 KB blocks and showed nothing; now unbuffered.

The 31 documents those fixes change were re-read; the other 269 were checked by replaying
their saved engine output against the stored rows, and come out identical.

**Still open.** P03-R06 comes back from OpenParser as one block holding `Age / Sex`, on both
reads — the engine loses the page, and Pass B can only re-read what the engine returned. Which
documents Pass B wrote rows for is not recorded: `engine_key()` folds `openparser+grounded` back
to `openparser` (review B28).

**Cost.** OpenParser 469 pages across the day's runs — the stopped one, this one and the 31
re-reads — about ₹41 from its own logged figures. Claude about ₹5.9, against a ₹10 cap.
`2026-10-08-2312` is this run before the 31 re-reads: 93.9% recall and 97.0% value, so the
re-reads moved value accuracy and unit/flag placement rather than recall.

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

## 2. Single-column pairing rule — 2026-09-24 measurement

**Status: MISS.** All four recall/precision spec targets (§3.3) unmet. The rule lifts
thermal slip precision by 73.7 points (26.3% → 100.0%) and overall corpus precision by
3.5 points (81.8% → 85.3%) — both real gains, both short of the ≥93% target — at the
cost of leaving recall unchanged. Regression test on four wide tables passes; no corpus
regression.

**Correct measurement command** (corrects the printed brief):
```bash
cd api && python ../scripts/replay.py --raw ../bench/results --by-layout
```
*The docker form in the brief measures the master worktree, not the pairing branch.*

### Holdout set performance (other 14 thermal slips, all non-thermal layouts)

| Metric | Before | After | Target | Result |
|---|---|---|---|---|
| thermal_slip recall | 20.8% | 20.8% | ≥80% | **MISS** |
| register_page recall | 0.0% | 0.0% | ≥70% | **MISS** |
| cut_sheet recall | 5.3% | 5.3% | ≥70% | **MISS** |
| Corpus precision | 81.8% | 85.3% | ≥93% | **MISS** |
| Extracted-to-expected row ratio | 106.9% | ~102.5% | 98–104% | **MET** |
| clean_table recall | 99.0% | 99.0% | no regression | PASS |
| continuation recall | 99.1% | 99.1% | no regression | PASS |
| dense_multipanel recall | 93.1% | 93.1% | no regression | PASS |
| Code accuracy | 99.7% | unmeasurable without a database run | no regression | **N/A** — needs `score_corpus.py` after a real ingest, not `replay.py` |

### Why the targets were missed

The spec assumed folding alone would restore both header fields and result values. Two
pre-existing gates remain (discovered Task 3, documented as `xfail(strict=True)` in
`tests/test_thermal_slip_extraction.py`):

1. **`_header_rows` promotion fails:** The code promotes a table only when every filled
   row pairs with a header key. A folded 2-cell row yields exactly one pair; the len(pairs)
   >= 2 fallback never fires. Additionally, `'Report Released'` and `'Specimen'` are
   absent from `_HEADER_KEYS`, so even a properly paired row lacks these fields. Unblocked
   by Task 5 (header vocabulary).

2. **`infer_roles` types columns UNKNOWN:** The code types a value column UNKNOWN when
   the unit is glued to the value (e.g. `'12.9 g/dL'`), so no value column is recognized.
   Pre-existing, unrelated to folding, deferred to value-accuracy work in spec section 8.

### Regression test

Created `api/tests/test_no_regression.py` with four wide tables (`P01-R01`, `P02-R03`,
`P03-R05`, `P04-R02`). All four assert `fold_single_column(grid) is grid` (identity, not
equality). All pass; the transform leaves wide tables untouched.

```
tests/test_no_regression.py::test_wide_tables_are_untouched[P01-R01] PASSED
tests/test_no_regression.py::test_wide_tables_are_untouched[P02-R03] PASSED
tests/test_no_regression.py::test_wide_tables_are_untouched[P03-R05] PASSED
tests/test_no_regression.py::test_wide_tables_are_untouched[P04-R02] PASSED
```

**No regression anywhere in the corpus.** The fold's reach is narrow by design — it fires
on only 2 of 832 tables in the whole 300-document corpus, so the corpus-wide precision
gain (81.8% → 85.3% overall, 26.3% → 100.0% on `thermal_slip`) is not evidence that the
*fold* generalises; it comes from the header vocabulary added in a later task, not from
folding. The generalisation evidence for that vocabulary is UHID recovery on two holdout
documents never opened during development — `P07-R07` (Shalini Awasthi, `MLC/607318`)
and `P15-R07` (Anjali Bhattacharyya, `BRH/649238`) — alongside the dev-set document
`P05-R02`, across three different labs' UHID formats.

---

## 3. Was it tuned to what we looked at?

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

## 4. By layout — the view worth reading

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

## 5. Three findings

### 5.1 Value accuracy is the problem, and it is concentrated

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

### 5.2 The recall cliffs are narrow and mostly deliberate

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

### 5.3 All 7 wrong codes are one known bug

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

### 5.4 Labels most often missed

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

## 6. Reproducing it for nothing

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

## 7. Bugs this run found

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

## 8. What to do next

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
