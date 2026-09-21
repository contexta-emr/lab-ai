"""Patient 14 of 20 - Geriatrics. Multi-morbidity: CKD, anaemia, vitamin D deficiency.

Male, 78 at the first report, Dehradun. Three problems running together and interacting:
stage 3b chronic kidney disease, the anaemia that comes with it, and a vitamin D level
that starts at 9.8 with a secondary rise in parathyroid hormone. Haemoglobin drifts 10.8
-> 9.4 over three years as the kidney function falls, and an erythropoietin agent lifts it
back to 10.6.

The setback is August 2024: an upper gastrointestinal bleed on the anti-inflammatory a
neighbour recommended for knee pain, haemoglobin 7.2 and two units transfused.
"""

from __future__ import annotations

PATIENT = {
    "number": 14,
    "name": "Brijmohan Lal Uniyal",
    "sex": "M",
    "dob": "1943-05-11",
    "uhid": "HVH/205718",
    "department": "Geriatrics",
    "city": "Dehradun",
    "age_at_first": 78,
    "tracked": ["HGB"],
    "brief": "Multi-morbidity: CKD, anaemia, vitamin D deficiency",
}


def check_arc(series):
    hgb = [v for _, v in series["HGB"]]
    fails = []
    if not 10.0 <= hgb[0] <= 11.5:
        fails.append(f"should open with mild CKD anaemia, got {hgb[0]}")
    if not min(hgb) < 8.0:
        fails.append(f"the bleed never shows, lowest {min(hgb)}")
    if not hgb[-1] > 10.0:
        fails.append(f"erythropoietin should lift it back, ends {hgb[-1]}")
    return fails


LABS = {
    "doon": {
        "abbr": "DDC", "acc_style": 0,
        "name": "Doon Valley Diagnostic Centre",
        "name_local": "दून वैली डायग्नोस्टिक सेंटर",
        "addr": "Rajpur Road, Dehradun 248001",
        "addr_local": "राजपुर रोड, देहरादून 248001",
        "city": "Dehradun",
        "phone": "0135 274 1120",
        "accred": "NABL Accredited (MC-6640) | ISO 15189:2012",
        "path": {"name": "Dr. Shobha Rawat", "qual": "MD (Pathology)",
                 "regn": "UKMC 2005/09/3312", "scrawl": "S Rawat"},
    },
    "himalaya": {
        "abbr": "HVH", "acc_style": 1,
        "name": "Himalaya Vishram Hospital Laboratory",
        "name_local": "हिमालय विश्राम हॉस्पिटल प्रयोगशाला",
        "addr": "Chakrata Road, Dehradun 248009",
        "addr_local": "चकराता रोड, देहरादून 248009",
        "city": "Dehradun",
        "phone": "0135 262 8800",
        "accred": "Department of Laboratory Medicine, Geriatric Services",
        "path": {"name": "Dr. Gopal Negi", "qual": "MD, DNB (Pathology)",
                 "regn": "UKMC 1998/04/0819", "scrawl": "G Negi"},
    },
    "mussoorie": {
        "abbr": "MPL", "acc_style": 3,
        "name": "Mussoorie Road Path Lab",
        "name_local": "मसूरी रोड पैथ लैब",
        "addr": "Jakhan, Dehradun 248001",
        "addr_local": "जाखन, देहरादून 248001",
        "city": "Dehradun",
        "phone": "0135 273 5567",
        "accred": "NABL Accredited (M-4409)",
        "path": {"name": "Dr. Preeti Bahuguna", "qual": "MBBS, MD (Path.)",
                 "regn": "UKMC 2013/06/7754", "scrawl": "P Bahuguna"},
    },
}

BISHT = "Dr. K. S. Bisht, MBBS, MD (Geriatric Medicine)"
THAPA = "Dr. Rekha Thapa, MBBS, MD (Medicine)"
SEMWAL = "Dr. Arun Semwal, MBBS, MD, DM (Nephrology)"

VITD_LEGEND = [
    ("Vitamin D (25-OH) - interpretation", "Vitamin D ng/mL"),
    ("Below 10", "Severe deficiency"),
    ("10 - 20", "Deficiency"),
    ("20 - 30", "Insufficiency"),
    ("30 - 100", "Sufficiency"),
]

# An 80 year old loses height and weight slowly. The August 2024 bleed takes
# four kilos off and drops his blood pressure; both recover over a year.
HEIGHT_CM = 166.0

VITALS = {
    1: {"weight_kg": 64.2, "bp": "148/82", "spo2": 96, "temp_f": 98.2,
        "context": "First geriatric clinic visit. Tired, poor appetite, aching bones."},
    2: {"weight_kg": 63.6, "bp": "146/80", "spo2": 96, "temp_f": 98.4,
        "context": "Vitamin D loading course started."},
    3: {"weight_kg": 63.0, "bp": "144/80", "spo2": 97, "temp_f": 98.2,
        "context": "Bone pain better. Renal function slowly declining."},
    4: {"weight_kg": 62.4, "bp": "142/78", "spo2": 96, "temp_f": 98.6,
        "context": "Annual review. Anaemia noted, iron studies requested."},
    5: {"weight_kg": 61.8, "bp": "140/78", "spo2": 96, "temp_f": 98.4,
        "context": "Oral iron started alongside the vitamin D."},
    6: {"weight_kg": 61.2, "bp": "138/76", "spo2": 96, "temp_f": 98.2,
        "context": "Haemoglobin still falling despite iron."},
    7: {"weight_kg": 60.6, "bp": "136/76", "spo2": 95, "temp_f": 98.4,
        "context": "Erythropoietin started under nephrology supervision."},
    8: {"weight_kg": 56.8, "bp": "104/62", "spo2": 94, "temp_f": 98.8,
        "context": "Melaena for two days after taking a neighbour's painkiller. Admitted."},
    9: {"weight_kg": 57.4, "bp": "118/70", "spo2": 96, "temp_f": 98.4,
        "context": "Third day after transfusion of two units. Bleeding stopped."},
    10: {"weight_kg": 58.6, "bp": "128/74", "spo2": 96, "temp_f": 98.2,
         "context": "Six weeks on. Endoscopy showed a healing gastric ulcer."},
    11: {"weight_kg": 59.8, "bp": "132/76", "spo2": 96, "temp_f": 98.6,
         "context": "Recovering. Erythropoietin dose increased."},
    12: {"weight_kg": 60.4, "bp": "134/76", "spo2": 96, "temp_f": 98.4,
         "context": "Haemoglobin back above 10."},
    13: {"weight_kg": 60.8, "bp": "136/78", "spo2": 96, "temp_f": 98.2,
         "context": "Single confirmatory haemoglobin before the annual review."},
    14: {"weight_kg": 61.2, "bp": "136/78", "spo2": 96, "temp_f": 98.4,
         "context": "Annual review. All three problems stable."},
    15: {"weight_kg": 61.6, "bp": "134/76", "spo2": 97, "temp_f": 98.2,
         "context": "Well for his age. Three-monthly nephrology follow-up continues."},
}

REPORTS = [
    # ---- R01 -- first geriatric clinic visit --------------------------------
    {
        "collected": "2021-10-07 09:30", "reported": "2021-10-07 18:20",
        "lab": "himalaya", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Hospital No",
        "doctor": BISHT, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["legend_lines", "text_result"],
        "interpretation": "Three findings that reinforce one another: stage 3b kidney "
                          "disease, a normocytic anaemia in keeping with it, and severe "
                          "vitamin D deficiency with a secondary rise in parathyroid "
                          "hormone. Treat the vitamin D first and review in three months.",
        "sections": [
            {"panel": "KFT", "title": 0,
             "values": {"CREAT": 1.62, "UREA": 58, "UA": 7.6}},
            {"panel": "VITAMIN", "title": 0, "legend": VITD_LEGEND,
             "values": {"VIT_D": 9.8, "VIT_B12": 268, "FOLATE": 6.4}},
            {"heading": "Haematology",
             "rows": [{"code": "HGB", "value": 10.8, "flag": "L"},
                      {"code": "MCV", "value": 88.4},
                      {"code": "BLOOD_GROUP", "value": "O Positive",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R02 -- vitamin D loading -------------------------------------------
    {
        "collected": "2022-01-20 08:50", "reported": "2022-01-20 16:10",
        "lab": "doon", "layout_style": "dot_matrix_pinfeed",
        "header_style": "minimal_text_top", "uhid_label": "Patient ID",
        "doctor": BISHT, "specimen": "Serum",
        "alias": 1, "traps": ["range_split_columns"],
        "sections": [
            {"panel": "HORMONES", "title": 0, "drop": ["PROLACTIN"],
             "values": {"CORTISOL_AM": 11.8, "PTH": 96.4, "TESTO_T": 286}},
            {"heading": "Bone Chemistry",
             "rows": [{"label": "Beta CrossLaps (CTX)", "value": "0.62", "unit": "ng/mL",
                       "reference": "0.10 - 0.70"},
                      {"code": "CA", "value": 8.6}, {"code": "PHOS", "value": 4.4},
                      {"code": "ALP", "value": 128, "flag": "H"},
                      {"code": "HGB", "value": 10.6, "flag": "L"}]},
        ],
    },
    # ---- R03 -- bone pain better --------------------------------------------
    {
        "collected": "2022-06-16 09:05", "reported": "2022-06-16 17:00",
        "lab": "mussoorie", "layout_style": "ledger_ruled",
        "header_style": "bilingual_header", "uhid_label": "Reg. No",
        "doctor": THAPA, "specimen": "Serum, Urine (midstream)",
        "alias": 2, "traps": ["unit_in_label", "sample_type_row"],
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 1, "sample_row": "Urine, Midstream",
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.0, "UR_SPGR": 1.012,
                        "UR_PROT": "Trace", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 4, "UR_RBC": 2, "UR_EPITH": 5, "MICROALB": 68,
                        "ACR": 84}},
            {"heading": "Renal and Haematology",
             "rows": [{"code": "CREAT", "value": 1.74, "flag": "H"},
                      {"code": "EGFR"},
                      {"code": "HGB", "value": 10.4, "flag": "L"}]},
        ],
    },
    # ---- R04 -- annual review ------------------------------------------------
    {
        "collected": "2022-11-24 07:55", "reported": "2022-11-24 19:10",
        "lab": "himalaya", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Hospital No",
        "doctor": BISHT, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 3, "traps": ["merged_panel_heading", "text_result", "method_sub_line"],
        "note": "Annual geriatric review package.",
        "sections": [
            {"panel": "CBC", "title": 1, "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "values": {"HGB": 10.2, "RBC": 3.54, "PCV": 31.2, "MCV": 88.1, "MCH": 28.8,
                        "WBC": 6400, "NEUT_PCT": 62, "LYMPH_PCT": 28, "MONO_PCT": 6,
                        "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 218000}},
            {"panel": "LIPID", "title": 1, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 168, "TRIG": 126, "HDL": 42}},
            {"panels": ["LFT", "ELECTROLYTES"], "heading": "Biochemistry Screen",
             "trap": "merged_panel_heading",
             "drop": ["GGT", "AG_RATIO", "GLOB", "BILI_I", "CA_ION", "MG"],
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 18, "AST": 22, "ALP": 118,
                        "PROT_T": 6.6, "ALB": 3.6,
                        "NA": 138, "K": 4.8, "CL": 105, "CA": 8.8, "PHOS": 4.6}},
            {"panel": "IRON", "title": 4, "drop": ["UIBC"], "methods": True,
             "values": {"FERRITIN": 48, "IRON": 52, "TIBC": 372}},
            {"panel": "THYROID", "title": 1, "drop": ["FT3", "ANTI_TPO"],
             "values": {"TSH": 4.26, "T3_TOTAL": 88, "T4_TOTAL": 7.4, "FT4": 1.02}},
            {"heading": "Other",
             "rows": [{"code": "HBA1C", "value": 5.6},
                      {"code": "PERIPH_SMEAR",
                       "value": "Normocytic normochromic anaemia. No abnormal cells.",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R05 -- oral iron started -------------------------------------------
    {
        "collected": "2023-05-12 09:15", "reported": "2023-05-12 16:30",
        "lab": "doon", "layout_style": "cut_sheet",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": THAPA, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 0, "traps": ["test_code_column"],
        "sections": [
            {"heading": "Anaemia Workup",
             "lab_codes": {"HGB": "H-01", "FERRITIN": "B-40", "IRON": "B-41",
                           "TIBC": "B-42", "VIT_B12": "B-55"},
             "rows": [{"code": "HGB", "value": 9.8, "flag": "L"},
                      {"code": "FERRITIN", "value": 36},
                      {"code": "IRON", "value": 46, "flag": "L"},
                      {"code": "TIBC", "value": 388},
                      {"code": "TSAT"},
                      {"code": "VIT_B12", "value": 284}]},
        ],
    },
    # ---- R06 -- still falling -------------------------------------------------
    {
        "collected": "2023-11-03 08:40", "reported": "2023-11-03 17:20",
        "lab": "himalaya", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": SEMWAL, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 1, "traps": ["abnormal_shaded", "footnote_marker"],
        "footnotes": [("1", "Erythropoietin considered once iron stores are adequate and "
                            "other causes of anaemia excluded.")],
        "sections": [
            {"panel": "KFT", "title": 3,
             "values": {"CREAT": 1.92, "UREA": 68, "UA": 8.0},
             "row_traps": {"CREAT": "footnote_marker"}},
            {"panel": "IRON", "title": 3, "drop": ["UIBC"],
             "values": {"FERRITIN": 128, "IRON": 68, "TIBC": 344}},
            {"panel": "THYROID", "title": 4, "drop": ["T3_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel",
             "values": {"TSH": 4.64, "T4_TOTAL": 7.2, "FT4": 0.98}},
            {"heading": "Haemoglobin",
             "rows": [{"code": "HGB", "value": 9.4, "flag": "L"}]},
        ],
    },
    # ---- R07 -- erythropoietin started ---------------------------------------
    {
        "collected": "2024-03-21 09:00", "reported": "2024-03-21 15:45",
        "lab": "mussoorie", "layout_style": "thermal_slip",
        "header_style": "centred_title_only", "uhid_label": "Reg. No",
        "doctor": SEMWAL, "specimen": "Whole blood (EDTA)",
        "alias": 2, "traps": ["no_reference_column"],
        "sections": [
            {"heading": "Haemoglobin",
             "rows": [{"code": "HGB", "value": 9.6, "flag": "L"}]},
        ],
    },
    # ---- R08 -- the bleed -----------------------------------------------------
    {
        "collected": "2024-08-17 02:40", "reported": "2024-08-17 05:20",
        "lab": "himalaya", "layout_style": "poor_scan",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": BISHT, "specimen": "Whole blood (EDTA), Serum, Citrate plasma",
        "alias": 3, "traps": ["sno_column", "text_result", "abnormal_shaded"],
        "stamp": "CRITICAL<br>PHONED 05:05",
        "note": "Haemoglobin 7.2 with melaena. Two units cross-matched and transfused. "
                "Nephrology and gastroenterology informed.",
        "sections": [
            {"panel": "CBC", "title": 4, "drop": ["ANC", "ALC", "MPV", "MCHC"],
             "values": {"HGB": 7.2, "RBC": 2.62, "PCV": 22.4, "MCV": 85.5, "MCH": 27.5,
                        "RDW": 16.8, "WBC": 11200, "NEUT_PCT": 76, "LYMPH_PCT": 18,
                        "MONO_PCT": 4, "EOS_PCT": 1, "BASO_PCT": 1, "PLT": 286000}},
            {"panel": "COAGULATION", "title": 0,
             "values": {"PT": 13.2, "INR": 1.06, "APTT": 30.8, "D_DIMER": 420}},
            {"heading": "Emergency Chemistry",
             "rows": [{"code": "UREA", "value": 96, "flag": "H"},
                      {"code": "CREAT", "value": 2.08, "flag": "H"},
                      {"code": "BLOOD_GROUP", "value": "O Positive, 2 units cross-matched",
                       "trap": "text_result"},
                      {"label": "Stool Occult Blood", "value": "Positive", "unit": "",
                       "reference": "Negative", "flag": "H", "trap": "text_result"}]},
        ],
    },
    # ---- R09 -- third day after transfusion ----------------------------------
    {
        "collected": "2024-08-20 06:20", "reported": "2024-08-20 09:40",
        "lab": "himalaya", "layout_style": "fax_header",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": BISHT, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["no_reference_column"],
        "note": "Faxed to the medical ward at 09:45 hrs.",
        "sections": [
            {"heading": "Post-transfusion Counts",
             "rows": [{"code": "HGB", "value": 9.8, "flag": "L"},
                      {"code": "PCV", "value": 30.2, "flag": "L"},
                      {"code": "UREA", "value": 54, "flag": "H"},
                      {"code": "CREAT", "value": 1.88, "flag": "H"}]},
        ],
    },
    # ---- R10 -- six weeks on --------------------------------------------------
    {
        "collected": "2024-10-02 09:25", "reported": "2024-10-02 16:50",
        "lab": "doon", "layout_style": "landscape_wide",
        "header_style": "barcode_header", "uhid_label": "Patient ID",
        "doctor": SEMWAL, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 1, "traps": ["prev_value_column", "method_sub_line"],
        "sections": [
            {"panel": "IRON", "title": 5, "methods": True,
             "prev": {"FERRITIN": "128 (03/11/2023)", "IRON": "68 (03/11/2023)"},
             "values": {"FERRITIN": 62, "IRON": 54, "TIBC": 380}},
            {"heading": "Renal and Haemoglobin",
             "prev": {"CREAT": "2.08 (17/08/2024)", "HGB": "7.2 (17/08/2024)"},
             "rows": [{"code": "CREAT", "value": 1.86, "flag": "H"},
                      {"code": "EGFR"},
                      {"code": "HGB", "value": 9.9, "flag": "L"}]},
        ],
    },
    # ---- R11 -- dose increased ------------------------------------------------
    {
        "collected": "2025-02-19 08:50", "reported": "2025-02-19 17:10",
        "lab": "mussoorie", "layout_style": "typewriter_manual",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": SEMWAL, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["no_reference_column", "not_reported"],
        "sections": [
            {"heading": "Renal, Bone and Counts",
             "rows": [{"code": "HGB", "value": 10.2, "flag": "L"},
                      {"code": "CREAT", "value": 1.90, "flag": "H"},
                      {"code": "PTH", "value": 132.6, "flag": "H"},
                      {"code": "VIT_D", "value": 24.8},
                      {"code": "TESTO_T", "value": "Not Reported",
                       "trap": "not_reported"},
                      {"label": "Serum Bicarbonate (HCO3)", "value": "20.6",
                       "unit": "mmol/L", "reference": "22 - 29", "flag": "L"}]},
        ],
    },
    # ---- R12 -- back above ten ------------------------------------------------
    {
        "collected": "2025-07-08 09:10", "reported": "2025-07-08 16:40",
        "lab": "doon", "layout_style": "glossy_marketing",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": THAPA, "specimen": "Whole blood (EDTA), Serum",
        "alias": 3, "traps": ["test_code_column", "flag_as_words"],
        "interpretation": "Haemoglobin has responded to erythropoietin and iron. Renal "
                          "function is stable at stage 3b and vitamin D is now sufficient.",
        "sections": [
            {"heading": "Haemogram",
             "lab_codes": {"HGB": "H-01", "RBC": "H-02", "PCV": "H-03", "WBC": "H-10",
                           "PLT": "H-20"},
             "rows": [{"code": "HGB", "value": 10.6, "flag": "L"},
                      {"code": "RBC", "value": 3.68, "flag": "L"},
                      {"code": "PCV", "value": 32.8, "flag": "L"},
                      {"code": "MCV", "value": 89.1},
                      {"code": "WBC", "value": 6600},
                      {"code": "PLT", "value": 232000}]},
            {"panel": "DIABETES", "title": 1, "drop": ["GLU_R", "INSULIN_F"],
             "lab_codes": {"GLU_F": "T-1042", "HBA1C": "T-2210"},
             "values": {"GLU_F": 96, "GLU_PP": 128, "HBA1C": 5.6}},
            {"panel": "VITAMIN", "title": 5,
             "lab_codes": {"VIT_D": "B-50", "VIT_B12": "B-55", "FOLATE": "B-56"},
             "values": {"VIT_D": 32.4, "VIT_B12": 342, "FOLATE": 8.2}},
            {"panel": "URINE_ROUTINE", "title": 5, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.0, "UR_SPGR": 1.010,
                        "UR_PROT": "Trace", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 5, "UR_RBC": 2, "UR_EPITH": 6}},
        ],
    },
    # ---- R13 -- one haemoglobin ----------------------------------------------
    {
        "collected": "2025-12-16 09:45", "reported": "2025-12-16 13:20",
        "lab": "mussoorie", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": THAPA, "specimen": "Whole blood (EDTA)",
        "alias": 0, "traps": ["no_header_row"],
        "sections": [
            {"heading": "Haemoglobin",
             "rows": [{"code": "HGB", "value": 10.4, "flag": "L"}]},
        ],
    },
    # ---- R14 -- annual review, two pages -------------------------------------
    {
        "collected": "2026-05-06 07:50", "reported": "2026-05-06 20:15",
        "lab": "himalaya", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "Hospital No",
        "doctor": BISHT, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["ratio_no_code", "footnote_marker"],
        "page_break_after": 3,
        "footnotes": [("1", "Anti-inflammatory drugs remain contraindicated. The patient "
                            "and family have been told again.")],
        "sections": [
            {"panel": "CBC", "title": 2,
             "values": {"HGB": 10.6, "RBC": 3.72, "PCV": 33.2, "MCV": 89.2, "MCH": 28.5,
                        "MCHC": 31.9, "RDW": 14.6, "WBC": 6200, "NEUT_PCT": 61,
                        "LYMPH_PCT": 29, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 226000, "MPV": 9.2}},
            {"panel": "LIPID", "title": 4,
             "values": {"CHOL": 162, "TRIG": 118, "HDL": 44}},
            {"panel": "DIABETES", "title": 4, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 98, "GLU_PP": 132, "HBA1C": 5.7}},
            {"panel": "LFT", "title": 4,
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 17, "AST": 21, "ALP": 106,
                        "GGT": 24, "PROT_T": 6.5, "ALB": 3.5}},
            {"panel": "KFT", "title": 4,
             "values": {"CREAT": 1.88, "UREA": 64, "UA": 7.8},
             "row_traps": {"UREA": "footnote_marker"}},
            {"heading": "Derived",
             "rows": [{"label": "Urea / Creatinine Ratio", "value": "34", "unit": "",
                       "reference": "20 - 35", "trap": "ratio_no_code"},
                      {"label": "Neutrophil - Lymphocyte Ratio", "value": "2.1",
                       "unit": "", "reference": "1.0 - 3.0", "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R15 -- stable --------------------------------------------------------
    {
        "collected": "2026-09-01 08:35", "reported": "2026-09-01 16:20",
        "lab": "doon", "layout_style": "mixed_print_hand",
        "header_style": "stamp_and_signature", "uhid_label": "Patient ID",
        "doctor": SEMWAL, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["method_sub_line"], "stamp": "GERIATRIC<br>CLINIC",
        "sections": [
            {"panel": "ELECTROLYTES", "title": 3, "methods": True,
             "values": {"NA": 139, "K": 4.6, "CL": 104, "CA": 8.9, "CA_ION": 4.6,
                        "PHOS": 4.2, "MG": 2.0}},
            {"panel": "HORMONES", "title": 2, "drop": ["PROLACTIN", "CORTISOL_AM"],
             "values": {"PTH": 108.4, "TESTO_T": 264}},
            {"heading": "Noted at the clinic", "hand_addendum": True,
             "rows": [{"code": "HGB", "value": 10.5}, {"code": "CREAT", "value": 1.86}]},
        ],
    },
]
