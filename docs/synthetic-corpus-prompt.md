# Synthetic patient corpus — PDF generation prompt

**Deliverable: 300 PDFs and nothing else that the parser can see.** 20 invented patients, 15 lab
reports each, spread over the five years to 2026-09-18, in many different report styles. The parser
is given only the PDFs. A sealed answer key is written to a separate folder that the extraction path
never reads; the scorer opens it afterwards.

**Can Claude produce the PDFs directly?** Yes — with one mechanical step, because a PDF is a binary
file and no model emits binary as text. Claude writes each report as an HTML page and prints it to
PDF headlessly. Verified working on this machine:

```bash
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless=new --disable-gpu \
  --no-pdf-header-footer --print-to-pdf="out.pdf" "file:///C:/path/to/report.html"
```

A one-page A4 PDF comes out at ~26 KB, with script fonts and CSS scan effects preserved. HTML is the
right authoring format here: real layout variety, handwriting via script fonts, and scan artefacts
via CSS filters and SVG noise — none of which a table-drawing library gives cheaply.

**Where things go**

```
idp/code/generated/corpus/P01/P01-R01.pdf …          ← the only thing the parser sees
idp/code/generated/_answers/reports.csv, rows.csv    ← sealed key, scorer only
idp/code/generated/_html/P01/P01-R01.html            ← source pages, kept for re-rendering
idp/code/generated/vitals/P01-vitals.json            ← vitals per visit, companion EMR data
```

Run the prompt below once per patient. Fill in `PATIENT_NUMBER` and its row from the roster.

**How it is actually built (patient 1 done, 2026-09-18).** The eleven layouts are hand-authored
once as stylesheets and the per-patient clinical data is authored as Python, rather than writing 300
one-off HTML files:

```
tools/corpus/layouts/*.css     the eleven layout_style looks, hand-authored
tools/corpus/catalog.py        analyte vocabulary, label aliases, ranges, derived maths
tools/corpus/render.py         structure only - header styles, columns, where traps bend the table
tools/corpus/patients/p01.py   patient 1: identity, labs, doctors, 15 reports, 15 sets of vitals
tools/corpus/build.py          compose -> HTML -> Edge -> PDF -> sealed CSV key + vitals JSON

uv run python tools/corpus/build.py --patient 1 --fresh    # 15 PDFs + key, then self-checks
uv run python tools/corpus/build.py --patient 1 --only 6   # re-render one report while tuning
```

Every derived value (VLDL, LDL, non-HDL, both lipid ratios, BUN, globulin, A:G, indirect bilirubin,
eAG, UIBC, TSAT, ANC, ALC, eGFR — and BMI in the vitals file) is computed from the authored inputs
*after* rounding, so rule 8 cannot be violated by hand. A patient module carries `HEIGHT_CM` and a
`VITALS` dict of 15 entries alongside its `REPORTS`; the build refuses to write a partial vitals
file. `build.py` ends by asserting this section's coverage
rules - panel counts of 2 or 3, date window and order, layout/lab/trap/test minimums, the HbA1c arc,
page counts - and exits non-zero if any fail.

One property worth knowing: the `poor_scan` CSS filter makes the browser rasterise that page, so
**that PDF carries no text layer and only the OCR path can read it.** Realistic for a photocopy,
and deliberate.

---

## The prompt

````text
You are generating a synthetic lab-report corpus for testing a medical document extraction system in
India. Nothing you produce describes a real person. You have file and shell tools; use them.

# YOUR TASK

For **patient PATIENT_NUMBER of 20**, produce **15 lab report PDFs** covering five years, plus rows
appended to the sealed answer key, plus one vitals file for the same 15 visit dates.

For each report:
1. Write `generated/_html/P<nn>/P<nn>-R<mm>.html` — a complete, self-contained A4 page.
2. Print it to `generated/corpus/P<nn>/P<nn>-R<mm>.pdf` with the headless Edge command above.
3. Append the report's facts to `generated/_answers/reports.csv` and every printed test to
   `generated/_answers/rows.csv`.

Then, once per patient, write `generated/vitals/P<nn>-vitals.json` — the vitals recorded at each of
those 15 visits (see **VITALS AT EACH VISIT** below).

Then open two or three of the PDFs to confirm they render as intended, and report what you made.

**The PDFs are the test input. The answer key exists only to score the extraction afterwards, and
nothing in the parsing path may read it.** Do not write a data JSON beside the PDFs. The vitals file
is not extraction input either — it is companion EMR data and lives outside `generated/corpus/`.

# THE 20-PATIENT ROSTER (generate only your assigned one)

| # | Department | Case brief | Age at first report | Sex |
|---|---|---|---|---|
| 1 | Endocrinology | Type 2 diabetes, poor control improving, then a relapse year | 52 | M |
| 2 | Cardiology | Post-MI secondary prevention, statin titration | 61 | M |
| 3 | Nephrology | CKD stage 3a progressing to 3b, diabetic nephropathy | 58 | F |
| 4 | Paediatrics | Iron-deficiency anaemia in a child, treated and resolving | 6 | F |
| 5 | Paediatrics | Recurrent febrile illness, dengue episode, full recovery | 11 | M |
| 6 | Hepatology | Non-alcoholic fatty liver, weight loss improves enzymes | 45 | M |
| 7 | Endocrinology | Hypothyroidism, dose titration to euthyroid | 34 | F |
| 8 | Obstetrics | Two pregnancies: anaemia and gestational diabetes screening | 29 | F |
| 9 | Haematology | B12 deficiency anaemia, macrocytic, corrected | 66 | F |
| 10 | Cardiology | Hypertension with dyslipidaemia, stable on treatment | 48 | M |
| 11 | Nephrology | Recurrent UTI with stones, kidney function preserved | 37 | F |
| 12 | General medicine | Enteric fever episode, then annual health checks | 26 | M |
| 13 | Endocrinology | Prediabetes progressing to diabetes despite advice | 41 | M |
| 14 | Geriatrics | Multi-morbidity: CKD, anaemia, vitamin D deficiency | 78 | M |
| 15 | Rheumatology | Rheumatoid arthritis, inflammatory markers responding | 44 | F |
| 16 | Hepatology | Hepatitis B carrier under surveillance, stable | 39 | M |
| 17 | Paediatrics | Thalassaemia trait, monitored, no progression | 9 | M |
| 18 | Oncology follow-up | Post-treatment monitoring, counts recovering | 55 | F |
| 19 | Pulmonology | Recurrent chest infections in a smoker, inflammation | 63 | M |
| 20 | Endocrinology | Thyrotoxicosis treated to hypothyroid, then stable | 31 | F |

**On top of the ten panels, each patient also carries these**, so the rarer tests are spread across
the corpus rather than clustered on one case:

| Patient | Must also include |
|---|---|
| 1, 6, 11, 16 | COAGULATION (pre-procedure screen) and a MICROBIOLOGY culture |
| 2, 7, 12, 17 | CARDIAC markers (TROP_I, CPK_MB, NT_PROBNP) |
| 3, 8, 13, 18 | TUMOUR MARKERS (PSA) and SEROLOGY |
| 4, 9, 14, 19 | HORMONES (cortisol, prolactin, PTH, testosterone) |
| 5, 10, 15, 20 | INFLAMMATION (CRP, HS_CRP, RA_FACTOR, ASO) |

# HARD RULES

1. **Invented identities only.** Indian names, cities and doctors. Do not use Yash M. Patel, Yashvi
   M. Patel or Saubhik Bhaumik (already in our test corpus), and nothing resembling a real person.
2. **Invented labs and hospitals**, never a real brand: "Sanjeevani Diagnostics", "Kaveri Path Labs",
   "Ashwini Hospital Laboratory" and similar.
3. **One UHID per patient, printed on all 15 reports.** Format: 3-4 uppercase letters, a dot or
   slash, then 5-6 digits (`SNJ/104772`). Unique to this patient across the whole corpus. Labs label
   it differently — UHID, MRN, Patient ID, Reg. No, Hospital No — but the value never changes.
4. **India-specific:** DD/MM/YYYY dates, mg/dL and similar units, Indian reference ranges, Indian
   cities, "Dr." with MBBS/MD qualifications.
5. **Timeline:** all 15 reports between 2021-09-18 and 2026-09-18, chronological, 2-8 months apart,
   irregular. Two reports days apart around an acute episode is realistic.
6. **Age advances with the dates**, and children get **age-appropriate reference ranges**.
7. **The clinical story shows in the numbers** across the five years, with one realistic setback.
   No impossible values.
8. **Derived values must compute** (within rounding): VLDL = TRIG/5 · LDL = CHOL − HDL − VLDL ·
   NON_HDL = CHOL − HDL · CHOL/HDL and LDL/HDL ratios · BUN = UREA/2.14 · GLOB = PROT_T − ALB ·
   A:G = ALB/GLOB · eAG = 28.7 × HBA1C − 46.7 · eGFR consistent with creatinine, age and sex, and it
   must fall as creatinine rises · BILI_I = BILI_T − BILI_D · differential percentages sum to 100.
9. **Codes in the answer key come only from the vocabulary below**, or are blank for a test that has
   no code (see coverage).

# THE TEN PANELS — THE BACKBONE OF EVERY PATIENT'S HISTORY

**Every one of these ten panels must appear on 2 or 3 of this patient's 15 reports** - whatever their
diagnosis. A diabetic patient still gets a thyroid check, a urine routine and a vitamin screen. That
is 20-30 panel instances across 15 reports, so most reports carry more than one panel.

Codes are Contexta canonical codes. **Rotate the printed title through the aliases** - a different
one each time the panel appears, because matching those titles is exactly what we are testing.

| # | Panel code | Printed title - rotate these | Analytes |
|---|---|---|---|
| 1 | `CBC` | CBC · Complete Blood Count · Complete Hemogram · Haemogram · Hemogram · Complete Haemogram | HGB g/dL, RBC mil/uL, PCV %, MCV fL, MCH pg, MCHC g/dL, RDW %, WBC /uL, NEUT_PCT %, LYMPH_PCT %, MONO_PCT %, EOS_PCT %, BASO_PCT %, ANC /uL, ALC /uL, PLT /uL, MPV fL |
| 2 | `LIPID` | Lipid Profile · Lipid Panel · Lipidogram · Lipid Screen · Dyslipidemia Profile · Cholesterol Profile | CHOL, TRIG, HDL, LDL, VLDL, NON_HDL mg/dL, CHOL_HDL_RATIO, LDL_HDL_RATIO |
| 3 | `DIABETES` | Diabetes Profile · Diabetic Profile · Sugar Profile · Blood Sugar Profile · Glycemic Profile · Glucose Profile | GLU_F, GLU_PP, GLU_R mg/dL, HBA1C %, EAG mg/dL, INSULIN_F uIU/mL |
| 4 | `LFT` | LFT · Liver Function Test · Liver Function Profile · Liver Profile · Hepatic Function Panel · Liver Panel | BILI_T, BILI_D, BILI_I mg/dL, ALT, AST, ALP, GGT U/L, PROT_T, ALB, GLOB g/dL, AG_RATIO |
| 5 | `KFT` | RFT · Renal Function Test · Renal Profile · Kidney Function Test · KFT · Kidney Profile · Renal Panel | CREAT, UREA, BUN, UA mg/dL, EGFR mL/min/1.73m2 |
| 6 | `THYROID` | Thyroid Profile · Thyroid Function Test · TFT · Thyroid Panel · Thyroid Function Profile | TSH uIU/mL, T3_TOTAL ng/dL, T4_TOTAL ug/dL, FT3 pg/mL, FT4 ng/dL, ANTI_TPO IU/mL |
| 7 | `URINE_ROUTINE` | Urine Routine · Urine R/M · Urine Routine & Microscopy · CUE · Complete Urine Examination · Urinalysis · Routine Urine Examination | UR_COLOUR, UR_PH, UR_SPGR, UR_PROT, UR_GLU, UR_KET (text), UR_PUS, UR_RBC, UR_EPITH /hpf, MICROALB mg/L, ACR mg/g |
| 8 | `ELECTROLYTES` | Serum Electrolytes · Electrolyte Panel · Electrolytes · Electrolyte Profile · Mineral Profile | NA, K, CL mmol/L, CA, CA_ION, PHOS, MG mg/dL |
| 9 | `IRON` | Iron Profile · Iron Studies · Iron Panel · Iron Status · Anemia Profile · Anaemia Profile | FERRITIN ng/mL, IRON, TIBC, UIBC ug/dL, TSAT % |
| 10 | `VITAMIN` | Vitamin Profile · Vitamin Panel · Nutritional Profile · Nutrition Profile · Vitamin Screening · Bone Health Profile | VIT_D ng/mL, VIT_B12 pg/mL, FOLATE ng/mL |

**Panel membership is mostly complete, sometimes partial.** Usually print the whole list. Sometimes
a lab prints a short version - a thyroid profile with only TSH, T3 and T4; a urine routine without
microalbumin and ACR; iron studies without UIBC - or slips an extra test into the panel's table.
Roughly one panel instance in four should be partial. Never drop so much that under 60% of the
panel remains, unless you record it as the trap `sparse_panel`.

**Watch these:** in this vocabulary `UA` is Uric Acid, never urinalysis. VLDL, NON_HDL, the two lipid
ratios, EAG, BILI_I, GLOB, AG_RATIO and TSAT are usually calculated, so they must agree with the
values they derive from. MICROALB and ACR are often ordered separately from a urine routine.

**Other codes available** for the extras assigned to this patient - CARDIAC: TROP_I ng/mL, CPK_MB
U/L, NT_PROBNP pg/mL · INFLAMMATION: CRP, HS_CRP mg/L, RA_FACTOR, ASO IU/mL · COAGULATION: PT sec,
INR ratio, APTT sec, D_DIMER ng/mL · HORMONES: PTH pg/mL, TESTO_T ng/dL, PROLACTIN ng/mL,
CORTISOL_AM ug/dL · SEROLOGY (text): HBSAG, ANTI_HCV, HIV, WIDAL, DENGUE_NS1, DENGUE_IGM, MP, VDRL ·
HAEMATOLOGY extras: ESR mm/hr, RETIC %, PERIPH_SMEAR, BLOOD_GROUP (text) · PSA ng/mL ·
URINE_CULTURE (text).

# HOW THE 15 REPORTS ARE PACKED

Mix the shapes. Do not put the same number of panels on every report:
- **2 health-check reports** carrying 5-6 panels each, 25+ tests (this is where several of the ten
  get their second or third appearance)
- **several reports with 2-3 panels**, the ordinary follow-up visit
- **several single-panel reports**
- **at least 2 single-test reports** - one test on the page, a repeat creatinine or a TSH

Per patient, across the 15 reports, also produce:
- at least **45 distinct tests**
- at least **3 text results** (blood group, culture, smear comment, reactive / non-reactive)
- at least **4 tests with no code in the vocabulary** - print them, leave the key's code column
  blank: Lipoprotein(a), Homocysteine, Apolipoprotein A1/B, Amylase, Lipase, LDH, CPK total,
  Procalcitonin, HbA2/HbF, G6PD, Anti-CCP, ANA, Vitamin B6, urinary sodium, stool occult blood,
  TG/HDL ratio, urea/creatinine ratio, neutrophil-lymphocyte ratio. A wrong guess on these is worse
  than an honest blank, and that is precisely what we are measuring.
- the disease-tracking tests on **8+ of the 15 reports**, so a chart has a line to draw

# HOW THE REPORTS MUST VARY

**Printed test names must differ between labs.** The same test across this patient's reports should
appear under **at least three spellings** — `Creatinine, Serum` / `S. CREATININE` / `Sr.Creat` /
`CREATININE (SERUM)`. Vary capitals, punctuation, abbreviation, word order. The key still records
the correct code.

**Use at least 6 different layouts and at least 3 different labs per patient.** Across the corpus
every layout below must appear.

`layout_style`:
- `clean_table` — modern bordered grid
- `minimal_lines` — no borders, aligned columns only
- `two_column` — two panels side by side
- `kv_header_table` — demographics in a bordered key-value box
- `dense_multipanel` — 3+ panels with sub-headings on one page
- `handwritten_values` — printed form, values written by hand (script font, blue ink, slight
  rotation per value)
- `handwritten_full` — whole report handwritten on a letterhead
- `mixed_print_hand` — printed panel plus a handwritten addendum
- `poor_scan` — skew 0.4-1.2deg, grey speckle, faint text, a stamp overlapping the table
- `carbon_copy` — faint fixed-width dot-matrix look
- `continuation` — two pages, the table continues across the break

`header_style`: `letterhead_logo_left`, `centred_title_only`, `banner_with_qr`,
`stamp_and_signature`, `minimal_text_top`, `hospital_department_block`.

# DELIBERATE TRAPS

Use **at least 8 of these** across the 15 reports, each recorded in the key:
`legend_lines` (Desirable / Borderline / High table under the results) · `method_sub_line` ·
`unit_in_value_cell` (`12.4 g/dL`) · `range_with_unit` (`35-104 U/L`) · `no_header_row` ·
`sno_column` · `ratio_no_code` · `ambiguous_abbreviation` (`TC`) · `merged_panel_heading` ·
`sample_type_row` · `footnote_marker` · `repeat_test_same_day` · `text_result` ·
`paediatric_range` · `not_reported` (a test listed with no value).

# HTML AUTHORING RULES

- A4 page: `@page { size: A4; margin: 12-16mm }`. Everything self-contained — no external fonts,
  images or scripts; a logo is CSS shapes or an inline SVG.
- Fonts already on this machine: "Segoe UI", Calibri, Cambria, Georgia, "Times New Roman", Consolas
  and "Courier New" for print; **"Ink Free" and "Segoe Script" for handwriting**.
- Handwriting: script font, ink colour `#1a3a8f` or `#16233f`, 1-3 px vertical jitter and
  `rotate(-1.5deg to 1.5deg)` per value, so it does not sit perfectly on the baseline.
- Poor scan: wrap the page in a container with `filter: contrast(1.2) brightness(0.96) grayscale(1)`,
  a faint repeating-gradient speckle, `transform: rotate(0.6deg)`, and a semi-transparent rotated
  stamp over part of the table.
- Carbon copy: Courier New, letter-spacing 0.5px, colour `#4a4a4a`, no borders.
- The page must be plausible as a document a clinic would hand over: letterhead, address, phone,
  accession number, page footer, signature block with a pathologist's name and registration.

# VITALS AT EACH VISIT

One file per patient, `generated/vitals/P<nn>-vitals.json`: a flat JSON array of 15 objects, one per
lab-report date, in the same order as the reports.

```json
[
  {
    "report_id": "P01-R01",
    "date": "2021-10-05",
    "age_years": 52,
    "height_cm": 172.0,
    "weight_kg": 88.4,
    "bmi": 29.9,
    "blood_pressure": "148/94",
    "spo2_pct": 98,
    "temperature_f": 98.4,
    "context": "First visit after incidental hyperglycaemia. Overweight, hypertensive."
  }
]
```

Rules:

1. **One row per lab report**, `report_id` and `date` matching `reports.csv` exactly. No visits that
   have no report, no reports that have no vitals.
2. **Height is constant** for an adult across the five years. A child on the roster grows: patients
   4, 5 and 17 must gain height and weight year on year, on a plausible paediatric curve.
3. **BMI is computed**, never typed: `weight_kg / (height_cm/100)^2`, one decimal.
4. **Blood pressure is the text `"148/94"`**, matching the production column, which is TEXT and is
   split at query time. Not two integers.
5. **Temperature is Fahrenheit**, as Indian clinics record it. Normal is 98.0-98.8; only a genuinely
   febrile visit goes above 99.
6. **SpO2** is 97-99 in a well patient. Drop it only where the case justifies it — an infection, a
   chest case, an acute episode.
7. **The vitals must tell the same story as the labs.** Weight and BP track glycaemic or cardiac
   control across the five years; the acute episode in the clinical arc is the visit that carries
   the fever and any dip in saturation. A patient whose HbA1c collapses while their weight sits
   still is not a coherent record.
8. `context` is one short line saying what was happening at that visit.

# THE SEALED ANSWER KEY

`generated/_answers/reports.csv` — one line per report:
`report_id,pdf_path,patient_number,uhid,patient_name,sex,age_printed,collected_at,reported_at,lab_name,uhid_label,referring_doctor,department,expected_panels,layout_style,header_style,traps`

`generated/_answers/rows.csv` — one line per printed test:
`report_id,section_heading,printed_label,code,value,unit,reference,method,flag,trap`

Rules: `expected_panels` uses the panel codes above (`CBC`, `LIPID`, `DIABETES`, `LFT`, `KFT`, `THYROID`, `URINE_ROUTINE`, `ELECTROLYTES`, `IRON`, `VITAMIN`, plus `CARDIAC`, `COAGULATION`, `HORMONES`, `SEROLOGY`, `INFLAMMATION`, `TUMOUR_MARKERS`). It and `traps` are `|`-separated. `code` is blank for a test with no code.
`value` is exactly as printed (`03`, `<0.01`, `Not Detected`). Quote any field containing a comma.

# BEFORE YOU FINISH, CHECK

1. 15 PDFs exist for this patient and each opens as a valid A4 page.
2. Dates in order, inside the window, ages consistent; the same UHID on all 15.
3. **Each of the ten panels appears on 2 or 3 reports** - count them panel by panel before
   finishing, and vary the printed title each time.
4. 6+ layouts, 3+ labs, 8+ traps, 45+ distinct tests, 2 health checks, 2 single-test reports,
   3 text results, 4 tests with no code, plus the extra panels assigned to this patient.
5. Derived values compute; the trend across reports matches the case brief when read in date order.
6. Every PDF has a matching line in reports.csv, and every printed test a line in rows.csv.
7. `generated/vitals/P<nn>-vitals.json` has 15 rows whose ids and dates match the reports, BMI
   recomputes from height and weight, and the weight, BP and fever read like the same patient the
   labs describe.
8. No data JSON anywhere near the PDFs. The vitals file is not near the PDFs — it is in
   `generated/vitals/`, and nothing in the parsing path opens it.
````

---

## After the PDFs exist

1. **Validate** (`tools/validate_corpus.py`, to be written): UHIDs unique across patients, dates in
   window and in order, coverage counts met, every PDF has key lines, derived values compute.
2. **Run the parser blind** over `generated/corpus/` with the local engine, writing JSON to `out/`.
3. **Score** (`tools/score_corpus_pdf.py`, to be written) by joining the extraction output to
   `_answers/*.csv`: header fields, panel detection, per-test value and unit, and — separately —
   name resolution, where a wrong code on a no-code test counts as a failure.
4. **Charts** are built on the extracted data, so a charting bug and an extraction bug stay
   distinguishable.

## Open points

- **Handwriting is a script font, not real handwriting.** Convincing on screen, but genuinely
  scanned pen strokes would need photographed or image-model pages. Worth revisiting once the
  printed cases pass.
- **Cost and time:** 300 reports at roughly one page each. Generating one patient at a time keeps
  each run reviewable.
- **No "TEST DATA" watermark**, as you asked. `generated/` is the only marker of what these are.
