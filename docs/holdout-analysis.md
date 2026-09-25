# Holdout analysis — 15 unseen documents

**25 September 2026.** First run of `corpus/data/holdout/` against the current build.
Raw dumps saved to `bench/holdout/` so re-scoring is free. Cost of the run: $0.015.

---

## 1. Headline

| Metric | Training corpus | **Holdout** | Gap |
|---|---:|---:|---:|
| Row recall | 87.5% | **52.7%** | −34.8 |
| Value accuracy | 96.3% | **84.7%** | −11.6 |
| Precision | 85.3% | **57.6%** | −27.7 |
| UHID found | 88.4% | **66.7%** (10/15) | −21.7 |

**This is the overfitting result.** Same code, unseen layouts, recall falls by more than a
third. The training numbers were not measuring generalisation — they were measuring fit.

Secondary accuracies on the rows we *did* find:

| | |
|---|---:|
| Value correct | 100/118 — 84.7% |
| Unit correct | 87/118 — 73.7% |
| Flag correct | 81/118 — 68.6% |
| Reference range correct | 60/118 — **50.8%** |

Reference ranges are close to a coin toss.

---

## 2. What the holdout is

15 documents, 3 patients (P21–P23), 224 printed result rows. Generated with **12 layout styles
that appear nowhere in the training corpus**:

`nabl_ulr` · `rtl_columns` · `green_bar` · `form_boxes` · `dual_period` · `card_grid` ·
`newsprint_cols` · `pastel_wellness` · `grid_lines` · `spine_barcode` · `sticker_sheet` ·
`ledger_landscape`

Zero overlap with the 26 training layouts. It also introduces traps that attack column-role
inference directly: `test_code_column`, `sno_column`, `prev_value_column`, `range_split_columns`,
`flag_as_words`, `unit_in_label`, `unit_in_value_cell`, `footnote_marker`, `legend_lines`,
`interpretation_block`.

This is a well-built holdout. It targets our weakest assumption — that the analyte name is in the
first column — and it finds it.

---

## 3. Per-document results

| Report | Layout | Rows found | Value ok | Unit ok | UHID | Name |
|---|---|---:|---:|---:|:--:|:--:|
| P21-R01 | nabl_ulr | 8/10 | 8 | 8 | ok | ok |
| P21-R02 | rtl_columns | **0/10** | 0 | 0 | MISS | MISS |
| P21-R03 | green_bar | 18/18 | 11 | 11 | ok | ok |
| P21-R04 | form_boxes | **0/10** | 0 | 0 | ok | ok |
| P21-R05 | dual_period | 11/11 | 11 | 5 | MISS | MISS |
| P22-R01 | card_grid | 4/19 | 0 | 0 | ok | ok |
| P22-R02 | newsprint_cols | 16/19 | 9 | 9 | MISS | MISS |
| P22-R03 | pastel_wellness | 6/16 | 6 | 0 | MISS | ok |
| P22-R04 | grid_lines | **0/20** | 0 | 0 | ok | ok |
| P22-R05 | spine_barcode | 15/16 | 15 | 15 | ok | ok |
| P23-R01 | sticker_sheet | **0/10** | 0 | 0 | MISS | MISS |
| P23-R02 | ledger_landscape | 15/26 | 15 | 14 | ok | ok |
| P23-R03 | nabl_ulr | 14/14 | 14 | 14 | ok | ok |
| P23-R04 | dual_period | 11/11 | 11 | 11 | ok | ok |
| P23-R05 | card_grid | **0/14** | 0 | 0 | ok | ok |

Four documents are perfect. Five produce nothing. The distribution is bimodal — this code either
understands a layout or it does not, with little in between.

---

## 4. Root causes

Every diagnosis below was verified against the sealed key, not inferred.

### 4.1 Wrong column chosen as the label — 30 rows

**P22-R04** (`test_code_column`). The grid is `TEST CODE | INVESTIGATION | RESULT | UNITS | RANGE`.
`infer_roles` assigned column 0 as the label:

```
roles = {0: 'label', 1: 'unknown', 2: 'value', 3: 'unit', 4: 'reference'}
produced:  'HAE-001' | '11.6' | 'g/dL' | '11.5 - 15.5'
expected:  'Haemoglobin' | '11.6' | 'g/dL' | '11.5 - 15.5'
```

The value, unit and range are **all correct**. Only the name is wrong — we labelled it with the
lab's internal test code. Rows whose code cell was blank were dropped entirely, which is why 20
expected rows produced 7.

**P21-R02** (`rtl_columns`). Columns are printed in reverse order:
`RANGE | UNITS | RESULT | INVESTIGATION | S.NO`. We picked column 1 — the units column — as the
label, so every analyte is called `mg/dL`.

Both are the same underlying fault: **we assume position instead of reading content.** We have 321
known analyte spellings in the alias table and never consult them when deciding which column holds
the analyte name.

### 4.2 Label not normalised — 20 rows

**P22-R03** (`unit_in_label`):
```
produced:  'Haemoglobin level (g/dL)'   expected: 'Haemoglobin level'  unit 'g/dL'
```
**P21-R04** (`unit_in_label` + `method_sub_line`):
```
produced:  'Creatinine (Sr.) (mg/dL)\nMethod: Modified Jaffe, kinetic'
expected:  'Creatinine (Sr.)'  unit 'mg/dL'  method 'Modified Jaffe, kinetic'
```

`Row.raw_method` exists precisely for this and did not fire. The unit is sitting in the label where
the alias lookup will never match it.

### 4.3 Transposed grids and glued cells — 29 rows

**P22-R01** (`card_grid`) is **transposed** — each analyte is a *column*, each attribute a *row*:

```
['HB (HAEMOGLOBIN)', 'RBC COUNT', 'HCT / PCV']
['7.8',              '3.96',      '26.4'     ]
['g/dL',             'mil/uL',    '%'        ]
['11.5 - 15.5',      '4.0 - 5.2', '35 - 45'  ]
```

Our pipeline assumes rows are records. Here columns are records. The same document's IRON STUDIES
table arrives with whole cards glued into single cells:
`'S. FERRITIN (CLIA)\n6\nng/mL\n7 - 140'`.

**P23-R05** (`card_grid`) is glued with no separator at all:
`'TOTAL BILIRUBIN0.78 mg/dL0.3 - 1.2'`.

### 4.4 Value, flag and unit fused in one cell — 7 value errors

**P21-R03**. We find all 18 labels but only 11 values are right:
```
produced value: '9.6 L g/dL'
expected:       value '9.6'  flag 'L'  unit 'g/dL'
```
`split_value_unit()` handles value+unit and `split_flag_suffix()` handles value+flag. Neither
handles all three at once.

### 4.5 No table, engine-side — 10 rows

**P23-R01** (`sticker_sheet`) is the important one, because it is **not our bug**. Everything
OpenParser returned:

```
[text]   Marine Drive Liver Institute Laboratory Kochi 0484 237 6600
[text]   Printed for the case file. Formal report issued separately.
[text]   Tested by: S. Pawar (B.Sc. MLT)
[text]   Dr. Sunitha Menon  ·  MD. DNB (Pathology)  ·  Regn. No. TCMC 2004/12/8817
[footer] P23-R01 · Marine Drive Liver Institute Laboratory
[number] Page 1 of 1
```

No patient name, no UHID, no analytes. Ten expected rows and the engine returned none of them.
**No downstream algorithm can recover data that was never read.** This is the honest ceiling.

### 4.6 UHID label vocabulary gaps — 5 documents

`Member ID`, `Registration No`, `OPD No` and `Patient ID` are all UHID labels we do not recognise.
Each miss sends a document to manual patient matching even when extraction succeeded.

---

## 5. Where the 106 missing rows went

| Cause | Rows | Share | Whose fault |
|---|---:|---:|---|
| Wrong column chosen as label | 30 | 28% | **ours** |
| Label not normalised (unit / method) | 20 | 19% | **ours** |
| Transposed grid or glued cells | 29 | 27% | engine, recoverable |
| Engine returned nothing | 10 | 9% | engine, **not recoverable** |
| Partial / mixed | 17 | 16% | mixed |

**Ours: 50 rows (47%).** Engine-side but readable: 29 (27%). Genuinely unrecoverable: 10 (9%).

A nuance the recall number hides: across the five zero-scoring documents we still **produced 32
rows**, most carrying correct values, units and ranges. They scored zero because the label was
wrong. The data quality underneath is better than 52.7% suggests — the naming is what failed.

---

## 6. What this changes

**I need to correct my own recommendation.** Two days ago I argued the table path should stay
deterministic because it measured 96.3% value accuracy. That figure came from the training corpus.
On unseen layouts the same code gives **84.7% value accuracy and 52.7% recall**. The table path is
not robust; it is fitted. Your overfitting objection applies to Pass A, not just the geometric pass
I proposed and withdrew.

Look at what fixing this deterministically would require:

1. A code-column detector (`^[A-Z]{2,4}-\d+$` is not general — some labs use numerics)
2. A reversed-column-order detector
3. A transposed-grid detector
4. A unit-in-label stripper
5. A method-subline splitter
6. A value+flag+unit tri-splitter
7. Glued-cell splitting with no separator
8. An expanded UHID label vocabulary

Eight rules, and the next holdout will need more. That is the treadmill.

Now look at what they have in common. Items 1–6 are all the same question — *which part of this
text is the analyte name, which is the number, which is the unit* — and that is a judgement a
language model makes well and a positional heuristic makes badly. A grounded pass would see
`TEST CODE | INVESTIGATION | RESULT` and pick `INVESTIGATION` without being told, because it knows
what a test code looks like.

**The holdout strengthens the case for the grounded LLM being primary, not a fallback.**

Two honest caveats against over-swinging:

- **It is not a universal fix.** §4.5 is 10 rows the engine never returned. No model recovers those.
- **We have not measured it.** Everything above argues an LLM *should* do better here. That is a
  hypothesis, and this document exists because our last set of numbers turned out to be measuring
  the wrong thing.

---

## 7. Recommendation

**Run the head-to-head on this holdout before changing any code.**

The 15 documents are now the right test set: unseen, adversarial, with a sealed key. Run a grounded
extraction pass over the same `bench/holdout/` dumps and score it with the same scorer.

- Cost: 15 × ~$0.002 = **$0.03**
- Time: minutes
- Answers: does the grounded pass beat 52.7% recall / 84.7% value accuracy on layouts nobody tuned
  for, and does it also hold up on the 282 training documents where we currently get 96.3%?

If it wins on both, the architecture collapses to one mechanism and the eight rules never get
written. If it loses, we have learned that cheaply and can go fix role inference knowing it is worth
the effort.

Regardless of that outcome, two fixes are worth making because they are small, general and not
format-specific:

- **Use the alias table when choosing the label column.** The column whose cells resolve against 321
  known analyte spellings is the analyte column. This alone addresses §4.1 — 30 rows, 28% of all
  misses — and it is not a heuristic, it is a lookup against data we already maintain.
- **Add the missing UHID labels.** `Member ID`, `Registration No`, `OPD No`, `Patient ID`. Five
  documents, trivial change.

---

## 8. Open questions

1. **Was this holdout generated from the same generator as the training corpus?** If so, real
   documents will be harder still, and 52.7% is an optimistic ceiling rather than a pessimistic one.
2. **Is `sticker_sheet` (§4.5) representative of anything real?** If small labs genuinely print
   sticker sheets, we should know that the engine cannot read them at all before it surprises us in
   production.
3. **Do you want the head-to-head run now?** $0.03, and it settles the architecture question with
   measurement instead of argument.
4. **Should reference ranges block a result?** At 50.8% accuracy they are unreliable, and a wrong
   range on a clinical value is arguably worse than no range. Currently we store whatever we find.
