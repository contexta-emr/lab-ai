# Reading any lab report — findings, options, costs

**25 September 2026.** Measured against the 303-document corpus, re-read the same day on the
current build. Companion to `docs/extraction-strategy.html`.

The question asked: *OpenParser returns raw JSON that may or may not contain a table. The
information we need is in there either way. How do we pull it out reliably, for patients in
tier-2 and tier-3 cities whose print quality and formats will vary?*

---

## 1. Summary

| | |
|---|---|
| Documents re-read | 303 — none failed |
| Results stored | 4,260 · 86.4% resolved to a canonical analyte |
| UHID detected | 268 / 303 (88.4%) |
| Documents yielding **zero** rows | 26 |
| Print styles at 100% extraction | **22 of 26** |

**The constraint is not print quality.** Poor scans, phone photos, carbon copies, fax headers,
dot-matrix pinfeed and typewriter output all extract at 100%. The failures cluster in four
*formats*, and 17 of the 26 total failures are one format: the thermal slip.

**The thermal slips fail because of our code, not the engine.** Every value is present in
OpenParser's response with coordinates. Our pipeline builds result rows only from `<table>` HTML,
and a receipt-shaped page produces no table.

**Changing vendor does not help.** Measured, not assumed — see §5.

---

## 2. Extraction by print style

Source: `lab.documents` joined to `corpus/data/answers/reports.csv`, 300 of 303 documents carry
corpus metadata.

| Print / layout style | Docs | UHID | Empty | Rows | OK |
|---|---:|---:|---:|---:|---:|
| handwritten_full | 1 | 100% | 1 | 0 | **0%** |
| chat_screenshot | 3 | 0% | 3 | 0 | **0%** |
| thermal_slip | 18 | 94% | 17 | 5 | **6%** |
| handwritten_values | 20 | 90% | 3 | 26 | 85% |
| boxed_panels | 17 | 94% | 1 | 242 | 94% |
| dense_multipanel | 23 | 57% | 1 | 767 | 96% |
| clean_table | 42 | 98% | 0 | 657 | 100% |
| kv_header_table | 25 | 92% | 0 | 287 | 100% |
| continuation | 20 | 100% | 0 | 928 | 100% |
| mixed_print_hand | 19 | 100% | 0 | 191 | 100% |
| two_column | 15 | 80% | 0 | 146 | 100% |
| ledger_ruled | 13 | 69% | 0 | 165 | 100% |
| minimal_lines | 13 | 100% | 0 | 100 | 100% |
| **poor_scan** | 11 | 100% | 0 | 157 | **100%** |
| landscape_wide | 10 | 90% | 0 | 102 | 100% |
| **typewriter_manual** | 9 | 89% | 0 | 64 | **100%** |
| **fax_header** | 8 | 50% | 0 | 70 | **100%** |
| **carbon_copy** | 6 | 100% | 0 | 67 | **100%** |
| glossy_marketing | 6 | 100% | 0 | 77 | 100% |
| duplicate_watermark | 5 | 100% | 0 | 44 | 100% |
| cut_sheet | 4 | 100% | 0 | 19 | 100% |
| **dot_matrix_pinfeed** | 3 | 100% | 0 | 20 | **100%** |
| **mobile_photo** | 3 | 100% | 0 | 38 | **100%** |
| range_bar / discharge_summary / register_page | 2 each | — | 0 | 54 | 100% |

Bold rows are the degraded-print styles — the ones expected to be the problem for tier-2/3 city
uploads. All at 100%.

**Caveat.** This corpus is synthetic. `poor_scan` and `mobile_photo` model degradation we invented.
A real photo taken in poor light may be worse than anything here. The table proves our handling of
*simulated* degradation; re-measure against real uploads before quoting these as production rates.

A second, separate gap: `dense_multipanel` (57%) and `fax_header` (50%) extract their rows fine but
often fail to identify the patient. That is a header-reading problem, not a table problem, and wants
its own pass.

---

## 3. Why thermal slips fail

`P07-R07`, as OpenParser returned it — page is 455pt wide, a receipt:

```
 15 paragraph_title x 153-299  y 381   THYROID PROFILE
 16 text            x  14-87   y 409   S. T.S.H.
 17 text            x 338-438  y 428   1.86 uIU/mL
 18 paragraph_title x  14-191  y 450   F.T.4 (Free Thyroxine)
 19 text            x 347-438  y 470   1.36 ng/dL
 20 text            x  14-96   y 493   T4 (TOTAL)
 21 text            x 355-438  y 511   9.2  $ \mu $g/dL
```

Three analytes, all present, none extracted. The structure is regular:

- **Labels** are left-aligned at `x0 = 14`.
- **Values** are right-aligned to `x1 = 438`, one block later, slightly lower.
- Values carry their unit inline, and sometimes LaTeX — which `_unmath` already handles.

Two traps:

1. **Block labels are unreliable.** `S. T.S.H.` came back as `text`; `F.T.4 (Free Thyroxine)` came
   back as `paragraph_title`. Same role, different label. Any rule must key on **x-position**.
2. **Header fields use a different geometry.** `Patient Name` at `y 88` with `Shalini Awasthi` at
   `y 106` — same x, stacked vertically. That is the single-column fold pattern `fold_single_column`
   already implements for grids.

### The test that said otherwise

`api/tests/test_thermal_slip_extraction.py` — docstring *"A thermal slip must yield a patient and
rows that carry values"* — has four assertions and passes. It tests `P05-R02`, the **one** thermal
slip of eighteen for which OpenParser returned a table (2 tables, 5 rows). The other seventeen
return zero tables, zero rows, and no test covers them.

This is the third green-but-vacuous test this session, after the `"\times"`-is-a-TAB fixture and the
3-row fixture that left the unit column UNKNOWN. It is also the most likely reason the corpus report
and the review console appeared to disagree: the suite asserted thermal slips worked.

---

## 4. What we already own

Everything Pass B needs exists and is already tested on the table path:

| Primitive | Location | Does |
|---|---|---|
| `split_value_unit()` | `services/ocr/numbers.py` | `"1.86 uIU/mL"` → `("1.86", "uIU/mL")`, rejecting H/L flags |
| `split_flag_suffix()` | `services/ocr/numbers.py` | strips a trailing `H` / `L` |
| `looks_like_flag()` | `services/ocr/numbers.py` | distinguishes a flag from a unit |
| `fold_single_column()` | `services/ocr/tables.py` | folds label-over-value stacks |
| `_unmath()` | `services/ocr/pipeline.py` | `$ \mu $g/dL` → `µg/dL` |
| `infer_roles()` | `services/ocr/columns.py` | assigns analyte / value / unit / range to columns |
| coverage check | panel templates | reports missing, unexpected, unresolved |

If loose blocks are folded into the **same grid shape a table produces**, all of the above runs
unchanged. Nothing downstream needs to know where the grid came from.

---

## 5. Alternatives tested

All measured on three real thermal slips (`P07-R07`, `P05-R08`, `P12-R04`), not assumed.

| Attempt | Result | Verdict |
|---|---|---|
| Lower `layout_threshold` (default 0.3; thermal blocks score 0.38–0.49 vs 0.95 on clean pages) | Hosted API returns `422 unsupported_ocr_option`. Only `image_block_ocr`, `chart_recognition`, `merge_layout_blocks` are exposed — all already set. | Blocked here; **available if self-hosted** |
| `aws-textract-tables-layout` + `forms` | Table on 1 of 3. 138 blocks vs our 24. | Marginal |
| `azure-di-layout` | Table on 1 of 3, 6 rows. | Marginal |
| `mistral-ocr-4` | No tables on any. | No gain |

**On the character counts.** Azure DI returned 1,966 characters against PaddleOCR-VL's 582, which
first looked like PaddleOCR losing 70% of the page. It is not. Azure returns the same text three
times — once as paragraphs, once as lines, once as words. Deduplicated, the content is identical:

```
paddleocr:  Patient Name | Devansh Choudhary | Hospital No | MCH/226104 | Plt Count | 96000 /uL L
azure-di:   Patient Name | Devansh Choudhary | Hospital No | MCH/226104 | Plt Count | 96000 /uL L
```

`P05-R08` genuinely has one analyte — it is a single platelet slip, not a badly-parsed panel.

**Conclusion.** No vendor change buys measurable information on these documents, and each would add
a processor, a contract and a residency question. The gap is ours.

### A client bug found on the way

`OCR_OPTIONS` in `services/ocr/openparser.py` is merged into every request regardless of model, so
any model other than `paddleocr-vl-1.6` fails with `422 unsupported_ocr_option: image_block_ocr`.
The client can only ever talk to one model. Worth fixing whether or not we switch.

---

## 6. Costs

OCR layer, per page. Self-hosted figures are Azure Central India list prices.

| Option | Per page | 10K/mo | 100K/mo | 500K/mo | Data in India |
|---|---:|---:|---:|---:|---|
| OpenParser hosted (today) | $0.0010 | $10 | $100 | $500 | **No — US** |
| Azure DI Layout | $0.0100 | $100 | $1,000 | $5,000 | Yes |
| Self-hosted PaddleOCR-VL, NC4as T4 v3 @ $0.594/hr | fixed | $433 | $433 | $433 | Yes |
| Self-hosted, NV12ads A10 v5 @ $1.117/hr | fixed | $815 | $815 | $815 | Yes |

**Breakeven: ~433,000 pages/month.** Below it the hosted API is cheaper, and at pilot volume it is
not close. A September 2026 study of VLM extraction economics independently puts the self-hosting
crossover at ~440K documents/month. One T4 at ~5s/page also saturates near 500K/month, so the cost
crossover and the capacity ceiling arrive together — convenient for planning.

### Pass C, if built

Measured, not estimated. An LMDX-style prompt built from our actual blocks (text + quantised
`XX|YY` coordinates) is **725 input tokens at the median**, 999 at p90, ~250 output.

Critically, Pass C runs **only on documents that fail the coverage check** — 26 of 303 today (8.6%),
and fewer once Pass B lands. Assume 3% escalation:

| Model | Per escalated doc | Amortised at 3% | 100K docs/mo | In India |
|---|---:|---:|---:|---|
| Haiku 4.5 | $0.0020 | $0.00006 | $6 | No |
| Sonnet 5 | $0.0059 | $0.00018 | $18 | No |
| Open-weight 7B on the same GPU | — | $0 | $0 | Yes |

Cost is not what decides Pass C. Residency is.

---

## 7. Recommendation

Three passes over the same block JSON. **The router already exists** — the coverage check that
reports missing / unexpected / unresolved analytes is precisely the signal for "this document did
not extract properly, escalate it".

### Pass A — tables (exists, unchanged)
`<table>` HTML → grid → `infer_roles` → analyte resolution. ~93% of documents. $0.

### Pass B — geometry (build now)
Loose blocks → lines (cluster by y-overlap) → columns (cluster by x) → **the same grid shape Pass A
produces** → existing downstream, unchanged.

Steps:

1. Make the lying test honest first — parametrise `test_thermal_slip_extraction.py` over all 18
   slips so it fails for the right reason. `xfail(strict=True)` on the 17 as the forcing signal.
2. Add `blocks_to_grid()` beside `fold_single_column()` in `tables.py`. Cluster blocks into rows by
   y-overlap; assign columns by x-band. Key on position, never on the engine's `label`.
3. In `pipeline.py`, call it when a page yields no table blocks, and on blocks left over outside a
   table's bbox on pages that do.
4. Re-run `scripts/replay.py` over the free cached corpus. Watch for regression on the 282 documents
   that already work — this must be additive.
5. Re-ingest and re-measure by print style.

No new dependency. No per-document cost. Every value traceable to a bounding box.

### Pass C — grounded LLM (design, do not build)

LMDX-style: suffix each block with quantised coordinates, require the model to name the block it
read each value from, **discard anything that fails to ground**. A fabricated potassium value cannot
survive, because an invented one points at no block. Reported localisation accuracy 88–94% zero-shot,
98–99% fine-tuned; 90.9% F1 at just 10 training documents.

**Do not use JSON mode for this.** Constrained decoding costs 3–9 points of accuracy across
open-weight models, and one benchmark saw output validity *fall* from 51% to 37% under structured
output. Generate freely; the grounding check is the guarantee, not the schema.

Build only if Pass B leaves a residue worth the governance conversation. It may be five documents.

### Not building

- `chat_screenshot` (3) and `handwritten_full` (1) — genuine engine limits. Manual entry is correct.
- `P18-R11` — deliberately `blurred_photo | finger_over_page | illegible_scan | poor_lighting`.
  Failing it *is* the correct behaviour.

---

## 8. Open questions

| Question | Why it matters | Status |
|---|---|---|
| Expected monthly volume | Single biggest driver of §6. Decides hosted vs self-hosted. | **Unknown — blocking the cost decision** |
| May patient data reach an LLM API? | Decides whether Pass C is hosted, self-hosted, or never built. | Open |
| Production OCR engine | If self-hosted, `layout_threshold` becomes tunable and may fix thermal slips at source too. Does **not** block Pass B, which is engine-independent. | Open |
| Hard cases ask for manual entry | Agreed. Makes Pass C non-urgent. | **Decided** |

---

## Sources

- [LMDX: Language Model-based Document Information Extraction and Localization](https://arxiv.org/pdf/2309.10952) — the grounding technique
- [Beyond Accuracy: Robustness, Cost and Governance Trade-offs for VLMs in Templated Document Extraction](https://arxiv.org/pdf/2609.15706) — the ~440K/month crossover
- [ExtractBench](https://arxiv.org/pdf/2602.12247) and [JSONSchemaBench](https://arxiv.org/pdf/2501.10868) — why not to use constrained decoding
- [ClusterTabNet](https://arxiv.org/html/2402.07502v2) — table reconstruction from coordinates
- [PaddleOCR-VL pipeline options](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PaddleOCR-VL.html) — `layout_threshold`, `layout_unclip_ratio`
- [Azure AI Document Intelligence pricing](https://azure.microsoft.com/en-in/pricing/details/document-intelligence/)
