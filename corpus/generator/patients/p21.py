"""Patient 21 - HELD OUT. Nephrology: diabetic nephropathy, creatinine climbing.

Male, 54 at the first report, Nagpur. Long-standing type 2 diabetes with proteinuria
already established when the record opens. Creatinine 1.4 to 3.2 over two years, eGFR
58 down to 21, anaemia and hyperkalaemia arriving on cue as the kidney fails. He is
being worked up for dialysis access by the last report.

This patient is NOT part of the training corpus. Every layout here is one the
extractor has never met, several printed labels are spellings that are deliberately
absent from catalog.py, and three tests have no code in the master at all. None of
those spellings may be added to the master afterwards - the whole point is to measure
what happens when a label is genuinely unknown, and a master quietly widened to fit
the test set measures nothing.
"""

from __future__ import annotations

HOLDOUT = True

PATIENT = {
    "number": 21,
    "name": "Prabhakar Deshmukh",
    "sex": "M",
    "dob": "1969-11-30",
    "uhid": "ORG/451207",
    "department": "Nephrology",
    "city": "Nagpur",
    "age_at_first": 54,
    "tracked": ["CREAT"],
    "brief": "Diabetic nephropathy progressing towards dialysis",
}


def check_arc(series):
    cr = [v for _, v in series["CREAT"]]
    fails = []
    if not cr[0] < 1.6:
        fails.append(f"should open in early CKD, creatinine {cr[0]}")
    if not cr == sorted(cr):
        fails.append(f"creatinine should not improve: {cr}")
    if not cr[-1] > 2.5:
        fails.append(f"should reach advanced CKD, final creatinine {cr[-1]}")
    return fails


NAIDU = "Dr. Sanjay Naidu"

LABS = {
    "orange": {
        "abbr": "ORG", "acc_style": 1,
        "name": "Orange City Renal Sciences Laboratory",
        "name_local": "ऑरेंज सिटी रीनल सायन्सेस प्रयोगशाळा",
        "addr": "Ramdaspeth, Nagpur 440010",
        "addr_local": "रामदासपेठ, नागपूर 440010",
        "city": "Nagpur",
        "phone": "0712 254 7719",
        "accred": "NABL MC-4471 | Dialysis and Transplant Services",
        "path": {"name": "Dr. Ashwini Kale", "qual": "MD (Pathology)",
                 "regn": "MMC 2007/04/28861", "scrawl": "A Kale"},
    },
    "vidarbha": {
        "abbr": "VDB", "acc_style": 0,
        "name": "Vidarbha Reference Laboratory",
        "name_local": "विदर्भ संदर्भ प्रयोगशाळा",
        "addr": "Dharampeth, Nagpur 440010",
        "addr_local": "धरमपेठ, नागपूर 440010",
        "city": "Nagpur",
        "phone": "0712 229 3304",
        "accred": "ISO 15189:2022 | ULR prefixed reports",
        "path": {"name": "Dr. Nitin Barapatre", "qual": "MD, DNB (Pathology)",
                 "regn": "MMC 2003/11/19274", "scrawl": "N Barapatre"},
    },
    "sadar": {
        "abbr": "SDR", "acc_style": 3,
        "name": "Sadar Collection Centre and Path Lab",
        "name_local": "सदर संकलन केंद्र आणि पॅथ लॅब",
        "addr": "Sadar Bazaar, Nagpur 440001",
        "addr_local": "सदर बाजार, नागपूर 440001",
        "city": "Nagpur",
        "phone": "0712 276 1180",
        "accred": "Collection centre. Samples processed at the Dharampeth hub.",
        "path": {"name": "Dr. Ujwala Thakre", "qual": "MBBS, DCP",
                 "regn": "MMC 2012/06/41190", "scrawl": "U Thakre"},
    },
}

CKD_LEGEND = [
    ("eGFR staging, CKD-EPI", "eGFR mL/min/1.73m2"),
    ("90 and above", "Stage 1, normal or high"),
    ("60 to 89", "Stage 2, mildly decreased"),
    ("45 to 59", "Stage 3a, mild to moderate"),
    ("30 to 44", "Stage 3b, moderate to severe"),
    ("15 to 29", "Stage 4, severely decreased"),
    ("Below 15", "Stage 5, kidney failure"),
]

# Fluid retention as the kidney fails: weight rises while he is not eating well,
# and the blood pressure stays high on three drugs.
HEIGHT_CM = 171.0

VITALS = {
    1: {"weight_kg": 78.4, "bp": "148/88", "spo2": 97, "temp_f": 98.2,
        "context": "Routine nephrology review. Proteinuria known for four years."},
    2: {"weight_kg": 79.6, "bp": "152/90", "spo2": 97, "temp_f": 98.4,
        "context": "Creatinine up. Ramipril dose reviewed, salt restriction reinforced."},
    3: {"weight_kg": 81.2, "bp": "156/92", "spo2": 96, "temp_f": 98.6,
        "context": "Ankle oedema. Frusemide added. Haemoglobin falling."},
    4: {"weight_kg": 82.8, "bp": "150/86", "spo2": 96, "temp_f": 98.0,
        "context": "Erythropoietin started. Potassium restriction counselling."},
    5: {"weight_kg": 80.4, "bp": "146/84", "spo2": 95, "temp_f": 98.4,
        "context": "Referred for AV fistula. Transplant workup discussed with family."},
}

REPORTS = [
    # ---- R01 -- early CKD, the accredited house format -----------------------
    {
        "collected": "2024-02-06 08:40", "reported": "2024-02-06 16:10",
        "lab": "orange", "layout_style": "nabl_ulr",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": NAIDU, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 0, "traps": ["legend_lines", "abnormal_shaded", "method_sub_line"],
        "interpretation": "Stage 3a chronic kidney disease with significant "
                          "albuminuria. Continue the ACE inhibitor, tighten blood "
                          "pressure control and repeat in six months.",
        "sections": [
            {"panel": "KFT", "title": 0, "legend": CKD_LEGEND, "methods": True,
             "labels": {"CREAT": "SR. CREATININE (ENZYMATIC)",
                        "UREA": "UREA, SERUM (UV-GLDH)",
                        "EGFR": "eGFR (CKD-EPI 2021)"},
             "values": {"CREAT": 1.42, "UREA": 46, "UA": 7.2}},
            {"heading": "Urine",
             "row_traps": {"UR_PROT": "text_result", "UR_COLOUR": "text_result",
                           "UR_GLU": "text_result"},
             "rows": [{"code": "UR_COLOUR", "value": "Pale yellow"},
                      {"code": "UR_PROT", "value": "2+", "flag": "H"},
                      {"code": "UR_GLU", "value": "Trace"},
                      {"code": "ACR", "value": 386, "flag": "H"},
                      {"label": "Serum Cystatin C", "value": "1.62", "unit": "mg/L",
                       "reference": "0.53 - 0.95", "flag": "H"}]},
        ],
    },
    # ---- R02 -- columns the other way round ----------------------------------
    {
        "collected": "2024-08-14 09:05", "reported": "2024-08-14 18:25",
        "lab": "vidarbha", "layout_style": "rtl_columns",
        "header_style": "two_line_ribbon", "uhid_label": "Registration No",
        "doctor": NAIDU, "specimen": "Serum",
        "alias": 1, "traps": ["sno_column", "abnormal_shaded"],
        "damage": ["fold"],
        "sections": [
            {"panel": "KFT", "title": 1,
             "labels": {"CREAT": "Creatinine - Serum", "UREA": "Blood Urea",
                        "UA": "Uric Acid, Serum"},
             "values": {"CREAT": 1.74, "UREA": 58, "UA": 7.9}},
            {"panel": "ELECTROLYTES", "title": 0, "drop": ["CA_ION", "MG"],
             "labels": {"NA": "SODIUM (Na+)", "K": "POTASSIUM (K+)",
                        "CL": "CHLORIDE (Cl-)"},
             "values": {"NA": 138, "K": 5.2, "CL": 104, "CA": 8.9, "PHOS": 4.6}},
        ],
    },
    # ---- R03 -- line-printer stationery from the collection centre -----------
    {
        "collected": "2025-03-19 07:55", "reported": "2025-03-19 15:40",
        "lab": "sadar", "layout_style": "green_bar",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": NAIDU, "specimen": "Whole blood (EDTA), Serum",
        "alias": 2, "traps": ["no_reference_column", "footnote_marker"],
        "footnotes": [("1", "Haemoglobin below 10 g/dL in CKD. Iron studies and "
                            "erythropoietin assessment advised."),
                      ("2", "Sample haemolysed. Potassium may read falsely high.")],
        "sections": [
            {"panel": "CBC", "title": 1, "drop": ["MPV", "BASO_PCT"],
             "labels": {"HGB": "HAEMOGLOBIN (Hb%)", "PLT": "Thrombocyte Count",
                        "PCV": "PACKED CELL VOLUME / HCT"},
             "values": {"HGB": 9.6, "RBC": 3.44, "PCV": 29.8, "MCV": 86.6, "MCH": 27.9,
                        "MCHC": 32.2, "RDW": 15.8, "WBC": 7400, "NEUT_PCT": 64,
                        "LYMPH_PCT": 26, "MONO_PCT": 7, "EOS_PCT": 3,
                        "PLT": 214000}},
            {"heading": "RENAL",
             "rows": [{"code": "CREAT", "value": 2.08, "flag": "H", "marker": "2"},
                      {"code": "UREA", "value": 74, "flag": "H"},
                      {"label": "Beta-2 Microglobulin", "value": "4.81", "unit": "mg/L",
                       "reference": "0.8 - 2.2", "flag": "H"}]},
        ],
    },
    # ---- R04 -- district-hospital requisition form, filled in ----------------
    {
        "collected": "2025-10-02 08:20", "reported": "2025-10-02 17:05",
        "lab": "orange", "layout_style": "form_boxes",
        "header_style": "centred_classic", "uhid_label": "OPD No",
        "doctor": NAIDU, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 0, "traps": ["unit_in_label", "method_sub_line"],
        "damage": ["aged", "crop-right"],
        "note": "Form returned by the renal clinic. Values entered by the duty "
                "technician and countersigned.",
        "sections": [
            {"panel": "KFT", "title": 0, "methods": True,
             "labels": {"CREAT": "Creatinine (Sr.)", "EGFR": "Estimated GFR"},
             "values": {"CREAT": 2.61, "UREA": 96, "UA": 8.4}},
            {"heading": "Anaemia and bone profile",
             "rows": [{"code": "HGB", "value": 8.9, "flag": "L"},
                      {"code": "FERRITIN", "value": 84},
                      {"code": "CA", "value": 8.2, "flag": "L"},
                      {"code": "PHOS", "value": 5.8, "flag": "H"},
                      {"label": "Parathyroid Hormone (Intact)", "value": "218",
                       "unit": "pg/mL", "reference": "15 - 65", "flag": "H"}]},
        ],
    },
    # ---- R05 -- this visit beside the last one, both in bold -----------------
    {
        "collected": "2026-04-21 08:10", "reported": "2026-04-21 16:50",
        "lab": "vidarbha", "layout_style": "dual_period",
        "header_style": "logo_left_banner", "uhid_label": "UHID",
        "doctor": NAIDU, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 1, "traps": ["prev_value_column", "abnormal_shaded",
                              "interpretation_block"],
        "interpretation": "Stage 4 chronic kidney disease. Vascular access should be "
                          "created now rather than at the point of need. Dietary "
                          "potassium and phosphate restriction reinforced.",
        "sections": [
            {"panel": "KFT", "title": 1,
             "sub": "Current column is 21/04/2026. Previous column is 02/10/2025.",
             "prev": {"CREAT": "2.61", "UREA": "96", "UA": "8.4", "EGFR": "25",
                      "BUN": "45"},
             "labels": {"CREAT": "S. CREATININE", "EGFR": "eGFR (CKD-EPI 2021)"},
             "values": {"CREAT": 3.24, "UREA": 118, "UA": 8.8}},
            {"panel": "ELECTROLYTES", "title": 1, "drop": ["CA_ION"],
             "prev": {"NA": "138", "K": "5.2", "CL": "104", "CA": "8.2",
                      "PHOS": "5.8", "MG": "2.1"},
             "values": {"NA": 136, "K": 5.7, "CL": 107, "CA": 8.0, "PHOS": 6.2,
                        "MG": 2.3}},
        ],
    },
]
