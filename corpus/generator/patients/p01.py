"""Patient 1 of 20 - Endocrinology. Type 2 diabetes: poor control improving, then a relapse year.

Male, 52 at the first report. Diagnosed late 2021 with HbA1c 9.6, brought down over two
years to 6.9, then loses control through 2025 (HbA1c back to 8.7) after stopping
medication; an infected foot ulcer in June 2025 is the acute episode, and early diabetic
nephropathy shows as microalbuminuria and a creatinine drifting 0.95 -> 1.34 with eGFR
falling behind it. 2026 is partial recovery, not a cure.

Only the independent values are written here. VLDL, LDL, non-HDL, the lipid ratios, BUN,
globulin, A:G, indirect bilirubin, eAG, UIBC, transferrin saturation, ANC, ALC and eGFR
are all computed by ``catalog.derive`` from these, so they cannot disagree with them.
"""

from __future__ import annotations

PATIENT = {
    "number": 1,
    "name": "Mahesh V. Deshpande",
    "sex": "M",
    "dob": "1969-04-12",
    "uhid": "SRV/207431",
    "department": "Endocrinology",
    "city": "Pune",
    "age_at_first": 52,
    "tracked": ["HBA1C"],
    "brief": "Type 2 diabetes, poor control improving, then a relapse year",
}


def check_arc(series):
    """The five-year story, asserted rather than assumed: bad, better, relapse, partly back."""
    a1c = [v for _, v in series["HBA1C"]]
    fails = []
    if not a1c[0] > 9.0:
        fails.append(f"HbA1c should start above 9.0, got {a1c[0]}")
    if not min(a1c) < 7.0:
        fails.append(f"HbA1c should reach target at some point, best was {min(a1c)}")
    if not max(a1c[5:]) > 8.0:
        fails.append("no relapse above 8.0 in the later years")
    if not a1c[-1] < a1c[0]:
        fails.append("patient ends worse than they started")
    return fails

LABS = {
    "sanjeevani": {
        "abbr": "SD", "acc_style": 0,
        "name": "Sanjeevani Diagnostics",
        "addr": "Plot 14, Karve Nagar, Pune 411052",
        "city": "Pune",
        "phone": "020 2544 8190",
        "accred": "NABL Accredited (MC-2187) | ISO 15189:2012",
        "path": {"name": "Dr. Shilpa M. Ranade", "qual": "MD (Pathology)",
                 "regn": "MMC 2004/03/1187", "scrawl": "S. Ranade"},
    },
    "kaveri": {
        "abbr": "KPL", "acc_style": 1,
        "name": "Kaveri Path Labs",
        "addr": "2nd Floor, Shivaji Chowk, Kothrud, Pune 411038",
        "city": "Pune",
        "phone": "020 2546 7712",
        "accred": "NABL Accredited (M-3312)",
        "path": {"name": "Dr. Prasad V. Kulkarni", "qual": "MD, DNB (Pathology)",
                 "regn": "MMC 2007/11/4420", "scrawl": "P Kulkarni"},
    },
    "ashwini": {
        "abbr": "AHL", "acc_style": 2,
        "name": "Ashwini Hospital Laboratory",
        "addr": "Ashwini Multispeciality Hospital, Dhankawadi, Pune 411043",
        "city": "Pune",
        "phone": "020 2437 6600",
        "accred": "Department of Laboratory Medicine",
        "path": {"name": "Dr. Neelam A. Bhagwat", "qual": "MBBS, MD (Clinical Pathology)",
                 "regn": "MMC 1999/07/0912", "scrawl": "N Bhagwat"},
    },
    "trimurti": {
        "abbr": "TDC", "acc_style": 3,
        "name": "Trimurti Diagnostic Centre",
        "addr": "Shop 3, Sinhagad Road, Pune 411030",
        "city": "Pune",
        "phone": "020 2425 3388",
        "accred": "Clinical Laboratory, Reg. No. PMC/DL/2019/4471",
        "path": {"name": "Dr. Kiran S. Pathak", "qual": "MD (Pathology)",
                 "regn": "MMC 2011/05/6633", "scrawl": "K Pathak"},
    },
}

KARVE = "Dr. Anil S. Karve, MBBS, MD (Medicine)"
NENE = "Dr. Vrushali Nene, MBBS, DNB (Endocrinology)"
JOGLEKAR = "Dr. Sameer Joglekar, MBBS, MD, DM (Endocrinology)"
BHOSALE = "Dr. R. R. Bhosale, MBBS (Surgery Unit II)"

HBA1C_LEGEND = [
    ("HbA1c - interpretation (ADA 2024)", "HbA1c"),
    ("Below 5.7 %", "Normal"),
    ("5.7 - 6.4 %", "Prediabetes"),
    ("6.5 % and above", "Diabetes mellitus"),
    ("Below 7.0 %", "Glycaemic target for most non-pregnant adults"),
]

LIPID_LEGEND = [
    ("Cholesterol - risk categories (NCEP ATP III)", "Total Cholesterol"),
    ("Below 200 mg/dL", "Desirable"),
    ("200 - 239 mg/dL", "Borderline high"),
    ("240 mg/dL and above", "High"),
]

# Vitals recorded at the visit that produced each lab report, keyed by report number.
# Companion EMR data, written to generated/vitals/ - the parser never sees this.
# Height is constant; BMI and the Celsius temperature are computed in build.py so they
# cannot drift from the weight and Fahrenheit readings authored here.
#
# The weight tracks the glycaemic story: 88.4 kg at diagnosis, down to 78.6 at best
# control in mid-2024, back up through the 2025 relapse, partly lost again by 2026.
# BP follows it. June 2025 is the acute episode - febrile, infected foot ulcer with an
# E. coli UTI - and is the only visit with a fever and a dip in saturation.
HEIGHT_CM = 172.0

VITALS = {
    1: {"weight_kg": 88.4, "bp": "148/94", "spo2": 98, "temp_f": 98.4,
        "context": "First visit after incidental hyperglycaemia. Overweight, hypertensive."},
    2: {"weight_kg": 87.6, "bp": "144/92", "spo2": 98, "temp_f": 98.2,
        "context": "Metformin started; diet and walking advised."},
    3: {"weight_kg": 85.2, "bp": "138/88", "spo2": 97, "temp_f": 98.6,
        "context": "Losing weight steadily. Thyroid checked as part of workup."},
    4: {"weight_kg": 83.9, "bp": "136/86", "spo2": 98, "temp_f": 98.4,
        "context": "Amlodipine added for blood pressure."},
    5: {"weight_kg": 82.1, "bp": "134/84", "spo2": 98, "temp_f": 98.2,
        "context": "Transaminases mildly raised; fatty liver suspected."},
    6: {"weight_kg": 79.8, "bp": "128/82", "spo2": 99, "temp_f": 98.4,
        "context": "Annual health check. Best weight and BP so far."},
    7: {"weight_kg": 79.2, "bp": "126/80", "spo2": 98, "temp_f": 98.6,
        "context": "Stable. Early microalbuminuria noted on urine testing."},
    8: {"weight_kg": 78.6, "bp": "124/78", "spo2": 98, "temp_f": 98.2,
        "context": "Best glycaemic control of the five years."},
    9: {"weight_kg": 80.4, "bp": "130/84", "spo2": 97, "temp_f": 98.8,
        "context": "Weight creeping up; reports medication adherence slipping."},
    10: {"weight_kg": 86.2, "bp": "146/92", "spo2": 97, "temp_f": 98.4,
         "context": "Relapse. Off medication for several months, weight regained."},
    11: {"weight_kg": 87.1, "bp": "148/94", "spo2": 98, "temp_f": 98.2,
         "context": "Therapy restarted; HbA1c rechecked."},
    12: {"weight_kg": 86.4, "bp": "132/84", "spo2": 96, "temp_f": 101.2,
         "context": "Febrile with an infected foot ulcer and E. coli UTI. Pre-operative "
                    "assessment for debridement."},
    13: {"weight_kg": 85.9, "bp": "134/84", "spo2": 97, "temp_f": 99.1,
         "context": "Third post-operative day. Fever settling on antibiotics."},
    14: {"weight_kg": 84.6, "bp": "136/86", "spo2": 98, "temp_f": 98.4,
         "context": "Annual health check. Recovering control on reinstituted therapy."},
    15: {"weight_kg": 82.7, "bp": "130/82", "spo2": 98, "temp_f": 98.6,
         "context": "Improved but not back to the 2024 baseline."},
}

REPORTS = [
    # ---- R01 -- new diagnosis workup ---------------------------------------
    {
        "collected": "2021-10-05 08:40", "reported": "2021-10-05 18:20",
        "lab": "sanjeevani", "layout_style": "clean_table",
        "header_style": "letterhead_logo_left", "uhid_label": "UHID",
        "doctor": KARVE, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 0, "traps": ["legend_lines"],
        "note": "Fasting sample. Newly detected hyperglycaemia - suggest clinical correlation "
                "and repeat HbA1c after 3 months.",
        "sections": [
            {"panel": "DIABETES", "title": 0, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 214, "GLU_PP": 298, "HBA1C": 9.6}},
            {"panel": "LIPID", "title": 0, "legend": LIPID_LEGEND,
             "values": {"CHOL": 226, "TRIG": 268, "HDL": 34}},
            {"panel": "KFT", "title": 0,
             "values": {"CREAT": 0.95, "UREA": 32, "UA": 6.8}},
        ],
    },
    # ---- R02 -- urine screen plus a standalone HbA1c ------------------------
    {
        "collected": "2022-01-18 09:15", "reported": "2022-01-18 16:05",
        "lab": "kaveri", "layout_style": "minimal_lines",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": KARVE, "specimen": "Urine (midstream), Whole blood (EDTA)",
        "alias": 1, "traps": ["unit_in_value_cell", "sample_type_row"],
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 1, "sample_row": "Urine, Midstream Clean Catch",
             "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.0, "UR_SPGR": 1.020,
                        "UR_PROT": "Trace", "UR_GLU": "++", "UR_KET": "Absent",
                        "UR_PUS": 3, "UR_RBC": 0, "UR_EPITH": 2}},
            {"heading": "Glycated Haemoglobin",
             "rows": [{"code": "HBA1C", "value": 9.1}, {"code": "EAG"}]},
        ],
    },
    # ---- R03 -- handwritten values, short thyroid check ---------------------
    {
        "collected": "2022-06-22 10:05", "reported": "2022-06-22 19:40",
        "lab": "trimurti", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": KARVE, "specimen": "Serum",
        "alias": 2, "traps": ["no_header_row", "sparse_panel"],
        "sections": [
            {"panel": "THYROID", "title": 2, "drop": ["FT3", "FT4", "ANTI_TPO"],
             "trap": "sparse_panel",
             "values": {"TSH": 3.12, "T3_TOTAL": 118, "T4_TOTAL": 8.4}},
            {"heading": "Blood Sugar", "rows": [{"code": "GLU_F", "value": 148}]},
        ],
    },
    # ---- R04 -- electrolytes, HbA1c, an uncoded homocysteine ---------------
    {
        "collected": "2022-11-09 08:20", "reported": "2022-11-09 17:30",
        "lab": "ashwini", "layout_style": "kv_header_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": NENE, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["footnote_marker"],
        "footnotes": [("1", "Homocysteine is not part of the ordered profile; assayed on "
                            "clinician request. Correlate with vitamin B12 and folate status.")],
        "sections": [
            {"panel": "ELECTROLYTES", "title": 0, "drop": ["CA_ION"],
             "values": {"NA": 139, "K": 4.3, "CL": 103, "CA": 9.2, "PHOS": 3.4, "MG": 2.0}},
            {"heading": "Biochemistry - Additional",
             "rows": [
                 {"code": "HBA1C", "value": 8.3},
                 {"code": "EAG"},
                 {"label": "Homocysteine, Serum", "value": "16.4", "unit": "umol/L",
                  "reference": "5.0 - 15.0", "flag": "H", "marker": "1"},
             ]},
        ],
    },
    # ---- R05 -- carbon copy LFT --------------------------------------------
    {
        "collected": "2023-03-14 08:55", "reported": "2023-03-14 15:10",
        "lab": "sanjeevani", "layout_style": "carbon_copy",
        "header_style": "minimal_text_top", "uhid_label": "UHID",
        "doctor": NENE, "specimen": "Serum",
        "alias": 3, "traps": ["range_with_unit", "method_sub_line"],
        "sections": [
            {"panel": "LFT", "title": 1, "methods": True,
             "values": {"BILI_T": 0.9, "BILI_D": 0.25, "ALT": 58, "AST": 44, "ALP": 96,
                        "GGT": 62, "PROT_T": 7.4, "ALB": 4.4}},
            {"heading": "Additional Tests", "methods": True,
             "rows": [
                 {"code": "HBA1C", "value": 7.8},
                 {"code": "EAG"},
                 {"label": "LDH (Lactate Dehydrogenase)", "value": "214", "unit": "U/L",
                  "reference": "140 - 280"},
             ]},
        ],
    },
    # ---- R06 -- annual health check, six panels -----------------------------
    {
        "collected": "2023-08-02 07:50", "reported": "2023-08-02 20:15",
        "lab": "kaveri", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "MRN",
        "doctor": JOGLEKAR, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 0, "traps": ["merged_panel_heading", "text_result", "method_sub_line"],
        "note": "Annual health check package. Vitamin D deficient - supplementation advised.",
        "sections": [
            {"panel": "CBC", "title": 1, "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "values": {"HGB": 14.2, "RBC": 4.78, "PCV": 43.1, "MCV": 90.2, "MCH": 29.7,
                        "WBC": 7400, "NEUT_PCT": 61, "LYMPH_PCT": 29, "MONO_PCT": 6,
                        "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 268000}},
            {"panel": "LIPID", "title": 3, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 184, "TRIG": 168, "HDL": 41}},
            {"panels": ["LFT", "ELECTROLYTES"], "heading": "Biochemistry - Liver and Minerals",
             "trap": "merged_panel_heading",
             "drop": ["GGT", "AG_RATIO", "GLOB", "CA_ION", "MG", "PHOS"],
             "values": {"BILI_T": 0.8, "BILI_D": 0.2, "ALT": 44, "AST": 36, "ALP": 88,
                        "PROT_T": 7.2, "ALB": 4.3,
                        "NA": 141, "K": 4.1, "CL": 104, "CA": 9.4}},
            {"panel": "IRON", "title": 1, "drop": ["UIBC"], "methods": True,
             "values": {"FERRITIN": 96, "IRON": 88, "TIBC": 342}},
            {"panel": "VITAMIN", "title": 0, "methods": True,
             "values": {"VIT_D": 18.4, "VIT_B12": 264, "FOLATE": 6.8}},
            {"heading": "Other Investigations",
             "rows": [
                 {"code": "BLOOD_GROUP", "value": "B Positive", "trap": "text_result"},
                 {"code": "HBA1C", "value": 7.2},
                 {"code": "EAG"},
                 {"label": "Apolipoprotein B", "value": "104", "unit": "mg/dL",
                  "reference": "< 100", "flag": "H"},
             ]},
        ],
    },
    # ---- R07 -- two panels side by side -------------------------------------
    {
        "collected": "2023-12-19 09:30", "reported": "2023-12-19 18:00",
        "lab": "ashwini", "layout_style": "two_column",
        "header_style": "stamp_and_signature", "uhid_label": "Hospital No",
        "doctor": JOGLEKAR, "specimen": "Serum, Urine (midstream)",
        "alias": 1, "traps": ["sno_column"], "stamp": "VERIFIED<br>LAB MEDICINE",
        "sections": [
            {"panel": "THYROID", "title": 0,
             "values": {"TSH": 2.84, "T3_TOTAL": 124, "T4_TOTAL": 8.9, "FT3": 3.1,
                        "FT4": 1.24, "ANTI_TPO": 12.4}},
            {"panel": "URINE_ROUTINE", "title": 2,
             "values": {"UR_COLOUR": "Straw", "UR_PH": 5.5, "UR_SPGR": 1.015,
                        "UR_PROT": "Trace", "UR_GLU": "+", "UR_KET": "Absent",
                        "UR_PUS": 4, "UR_RBC": 1, "UR_EPITH": 3, "MICROALB": 26,
                        "ACR": 34}},
        ],
    },
    # ---- R08 -- best control, and a test not reported -----------------------
    {
        "collected": "2024-05-07 08:10", "reported": "2024-05-07 16:45",
        "lab": "sanjeevani", "layout_style": "clean_table",
        "header_style": "letterhead_logo_left", "uhid_label": "UHID",
        "doctor": JOGLEKAR, "specimen": "Fluoride plasma, Whole blood (EDTA), Serum",
        "alias": 1, "traps": ["not_reported", "sparse_panel"],
        "sections": [
            {"panel": "DIABETES", "title": 4, "drop": ["GLU_R"],
             "values": {"GLU_F": 118, "GLU_PP": 162, "HBA1C": 6.9,
                        "INSULIN_F": "Not Reported"},
             "row_traps": {"INSULIN_F": "not_reported"}},
            {"panel": "THYROID", "title": 4, "drop": ["T3_TOTAL", "T4_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel", "values": {"TSH": 2.96, "FT4": 1.19}},
        ],
    },
    # ---- R09 -- printed haematology with a handwritten addendum -------------
    {
        "collected": "2024-09-21 10:40", "reported": "2024-09-21 17:55",
        "lab": "trimurti", "layout_style": "mixed_print_hand",
        "header_style": "centred_title_only", "uhid_label": "Reg. No",
        "doctor": KARVE, "specimen": "Whole blood (EDTA)",
        "alias": 2, "traps": ["text_result"],
        "sections": [
            {"heading": "Haematology",
             "rows": [
                 {"code": "ESR", "value": 22, "flag": "H"},
                 {"code": "PERIPH_SMEAR",
                  "value": "Normocytic normochromic red cells. No abnormal cells seen. "
                           "Platelets adequate on smear.",
                  "trap": "text_result"},
             ]},
            {"heading": "Added on clinician request (verbal)", "hand_addendum": True,
             "rows": [{"code": "HBA1C", "value": 7.0}, {"code": "GLU_PP", "value": 154}]},
        ],
    },
    # ---- R10 -- the relapse, on a bad photocopy ----------------------------
    {
        "collected": "2025-02-11 08:05", "reported": "2025-02-11 19:20",
        "lab": "kaveri", "layout_style": "poor_scan",
        "header_style": "banner_with_qr", "uhid_label": "Patient ID",
        "doctor": JOGLEKAR, "specimen": "Serum, Urine (midstream)",
        "alias": 3, "traps": ["ambiguous_abbreviation", "text_result"],
        "stamp": "URGENT<br>CLINICAL REVIEW",
        "note": "Microalbuminuria with rising creatinine - suggest nephrology referral and "
                "review of glycaemic control.",
        "sections": [
            {"panel": "KFT", "title": 4,
             "values": {"CREAT": 1.28, "UREA": 44, "UA": 7.6}},
            {"panel": "URINE_ROUTINE", "title": 3,
             "labels": {"UR_PROT": "ALBUMIN"},
             "row_traps": {"UR_PROT": "ambiguous_abbreviation", "UR_GLU": "text_result"},
             "values": {"UR_COLOUR": "Yellow", "UR_PH": 5.5, "UR_SPGR": 1.025,
                        "UR_PROT": "++", "UR_GLU": "+++", "UR_KET": "Trace",
                        "UR_PUS": 6, "UR_RBC": 1, "UR_EPITH": 3, "MICROALB": 78,
                        "ACR": 112}},
            {"heading": "Glycaemic Status",
             "rows": [{"code": "HBA1C", "value": 8.4}, {"code": "EAG"}]},
        ],
    },
    # ---- R11 -- a single test on the page ----------------------------------
    {
        "collected": "2025-03-04 09:00", "reported": "2025-03-04 14:10",
        "lab": "sanjeevani", "layout_style": "minimal_lines",
        "header_style": "minimal_text_top", "uhid_label": "UHID",
        "doctor": JOGLEKAR, "specimen": "Whole blood (EDTA)",
        "alias": 0, "traps": ["legend_lines"],
        "sections": [
            {"heading": "Glycosylated Haemoglobin", "legend": HBA1C_LEGEND,
             "rows": [{"code": "HBA1C", "value": 8.7}]},
        ],
    },
    # ---- R12 -- acute episode: infected foot ulcer, pre-debridement --------
    {
        "collected": "2025-06-16 11:20", "reported": "2025-06-16 21:05",
        "lab": "ashwini", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": BHOSALE, "specimen": "Whole blood (EDTA), Citrate plasma, Urine",
        "alias": 0, "traps": ["sno_column", "repeat_test_same_day", "text_result"],
        "note": "Pre-operative screen for wound debridement. Leucocytosis with neutrophilia. "
                "PT repeated on the same sample after re-centrifugation.",
        "sections": [
            {"panel": "CBC", "title": 0,
             "values": {"HGB": 12.8, "RBC": 4.42, "PCV": 38.6, "MCV": 87.3, "MCH": 29.0,
                        "MCHC": 33.2, "RDW": 14.6, "WBC": 14200, "NEUT_PCT": 82,
                        "LYMPH_PCT": 12, "MONO_PCT": 4, "EOS_PCT": 2, "BASO_PCT": 0,
                        "PLT": 402000, "MPV": 10.4}},
            {"panel": "COAGULATION", "title": 2, "methods": True,
             "values": {"PT": 13.8, "INR": 1.12, "APTT": 32.4, "D_DIMER": 640},
             "extra_rows": [
                 {"code": "PT", "label": "Prothrombin Time (PT) - Repeat", "value": "13.2",
                  "unit": "sec", "reference": "11.0 - 14.0", "trap": "repeat_test_same_day"},
             ]},
            {"heading": "Microbiology",
             "rows": [
                 {"code": "URINE_CULTURE",
                  "value": "Escherichia coli, >100000 CFU/mL. Sensitive: Nitrofurantoin, "
                           "Fosfomycin, Meropenem. Resistant: Ciprofloxacin, Co-trimoxazole.",
                  "trap": "text_result", "flag": "H"},
                 {"code": "ESR", "value": 48, "flag": "H"},
             ]},
        ],
    },
    # ---- R13 -- three days later, one handwritten repeat --------------------
    {
        "collected": "2025-06-19 07:45", "reported": "2025-06-19 12:30",
        "lab": "ashwini", "layout_style": "handwritten_full",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": BHOSALE, "specimen": "Serum",
        "alias": 1, "traps": ["no_header_row"],
        "note": "Repeat post procedure. Hydration advised, recheck after one week.",
        "sections": [
            {"heading": "Serum Creatinine - Repeat",
             "rows": [{"code": "CREAT", "value": 1.34, "flag": "H"}]},
        ],
    },
    # ---- R14 -- health check two, running onto a second page ---------------
    {
        "collected": "2026-01-27 07:40", "reported": "2026-01-27 20:50",
        "lab": "kaveri", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "MRN",
        "doctor": JOGLEKAR, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 2, "traps": ["ambiguous_abbreviation", "ratio_no_code", "footnote_marker"],
        "page_break_after": 3,
        "footnotes": [("1", "Lp(a) is largely genetically determined; a single elevated "
                            "result need not be repeated.")],
        "note": "Glycaemic control improved on reinstituted therapy but remains above target. "
                "Renal function to be monitored three-monthly.",
        "sections": [
            {"panel": "CBC", "title": 3,
             "values": {"HGB": 13.1, "RBC": 4.51, "PCV": 39.8, "MCV": 88.2, "MCH": 29.0,
                        "MCHC": 32.9, "RDW": 14.1, "WBC": 8100, "NEUT_PCT": 64,
                        "LYMPH_PCT": 26, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 289000, "MPV": 9.9}},
            {"panel": "LIPID", "title": 5, "labels": {"CHOL": "TC"},
             "row_traps": {"CHOL": "ambiguous_abbreviation"},
             "values": {"CHOL": 198, "TRIG": 212, "HDL": 38}},
            {"panel": "DIABETES", "title": 2, "drop": ["GLU_R"],
             "values": {"GLU_F": 156, "GLU_PP": 224, "HBA1C": 7.9, "INSULIN_F": 14.2}},
            {"panel": "LFT", "title": 4,
             "values": {"BILI_T": 0.7, "BILI_D": 0.2, "ALT": 49, "AST": 38, "ALP": 92,
                        "GGT": 54, "PROT_T": 7.1, "ALB": 4.2}},
            {"panel": "KFT", "title": 5,
             "values": {"CREAT": 1.22, "UREA": 40, "UA": 7.2}},
            {"heading": "Additional Investigations",
             "rows": [
                 {"label": "Lipoprotein (a)", "value": "38", "unit": "mg/dL",
                  "reference": "< 30", "flag": "H", "marker": "1"},
                 {"label": "TG / HDL Ratio", "value": "5.6", "unit": "",
                  "reference": "< 3.5", "flag": "H", "trap": "ratio_no_code"},
                 {"label": "Neutrophil - Lymphocyte Ratio (NLR)", "value": "2.5",
                  "unit": "", "reference": "1.0 - 3.0", "trap": "ratio_no_code"},
             ]},
        ],
    },
    # ---- R15 -- partial recovery, iron and vitamins -------------------------
    {
        "collected": "2026-08-30 08:25", "reported": "2026-08-30 17:15",
        "lab": "trimurti", "layout_style": "kv_header_table",
        "header_style": "centred_title_only", "uhid_label": "Reg. No",
        "doctor": JOGLEKAR, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["not_reported", "method_sub_line"],
        "sections": [
            {"panel": "IRON", "title": 4, "methods": True,
             "values": {"FERRITIN": 62, "IRON": 74, "TIBC": 368}},
            {"panel": "VITAMIN", "title": 5, "methods": True,
             "values": {"VIT_D": 32.6, "VIT_B12": 318, "FOLATE": "Not Reported"},
             "row_traps": {"FOLATE": "not_reported"}},
            {"heading": "Glycaemic Control",
             "rows": [{"code": "HBA1C", "value": 7.2}, {"code": "EAG"}]},
        ],
    },
]
