"""Patient 6 of 20 - Hepatology. Non-alcoholic fatty liver, weight loss improves enzymes.

Male, 45 at the first report, Ahmedabad. Found on an insurance medical to have ALT 118
and a bright liver on ultrasound. Eighteen months of diet and walking take 11 kg off and
ALT down to 34. The setback is 2025: the weight comes back after a knee injury stops him
walking, and ALT climbs to 86 before a second effort brings it to 41.

Third wave of layouts starts here - a landscape follow-up sheet with a previous-result
column, a duplicate copy stamped across the page, and a report that arrived by fax.
"""

from __future__ import annotations

PATIENT = {
    "number": 6,
    "name": "Jigar H. Bhavsar",
    "sex": "M",
    "dob": "1976-07-08",
    "uhid": "SVH/513207",
    "department": "Hepatology",
    "city": "Ahmedabad",
    "age_at_first": 45,
    "tracked": ["ALT"],
    "brief": "Non-alcoholic fatty liver, weight loss improves enzymes",
}


def check_arc(series):
    alt = [v for _, v in series["ALT"]]
    fails = []
    if not alt[0] > 90:
        fails.append(f"should start with a clearly raised ALT, got {alt[0]}")
    if not min(alt) < 45:
        fails.append(f"weight loss never normalises ALT, best {min(alt)}")
    if not any(alt[j] > min(alt[:j]) + 35 for j in range(1, len(alt))):
        fails.append("no relapse after the best result")
    if not alt[-1] < alt[0]:
        fails.append("ends no better than it started")
    return fails


LABS = {
    "sabarmati": {
        "abbr": "SDL", "acc_style": 0,
        "name": "Sabarmati Diagnostics",
        "name_local": "સાબરમતી ડાયગ્નોસ્ટિક્સ",
        "addr": "Ashram Road, Ahmedabad 380009",
        "addr_local": "આશ્રમ રોડ, અમદાવાદ 380009",
        "city": "Ahmedabad",
        "phone": "079 2658 4120",
        "accred": "NABL Accredited (MC-6018) | ISO 15189:2012",
        "path": {"name": "Dr. Falguni R. Trivedi", "qual": "MD (Pathology)",
                 "regn": "GMC 2005/11/2276", "scrawl": "F Trivedi"},
    },
    "riverfront": {
        "abbr": "RPL", "acc_style": 2,
        "name": "Riverfront Path Lab",
        "name_local": "રિવરફ્રન્ટ પેથ લેબ",
        "addr": "CG Road, Navrangpura, Ahmedabad 380006",
        "addr_local": "સી.જી. રોડ, નવરંગપુરા, અમદાવાદ 380006",
        "city": "Ahmedabad",
        "phone": "079 2640 7733",
        "accred": "NABL Accredited (M-9042)",
        "path": {"name": "Dr. Nitin M. Vyas", "qual": "MBBS, MD (Path.)",
                 "regn": "GMC 2013/02/7719", "scrawl": "N Vyas"},
    },
    "swaminarayan": {
        "abbr": "SVH", "acc_style": 1,
        "name": "Swaminarayan Vidhya Hospital Laboratory",
        "name_local": "સ્વામિનારાયણ વિદ્યા હોસ્પિટલ પ્રયોગશાળા",
        "addr": "Maninagar, Ahmedabad 380008",
        "addr_local": "મણિનગર, અમદાવાદ 380008",
        "city": "Ahmedabad",
        "phone": "079 2546 9000",
        "accred": "Department of Laboratory Medicine",
        "path": {"name": "Dr. Hetal S. Panchal", "qual": "MD, DNB (Pathology)",
                 "regn": "GMC 2000/06/0884", "scrawl": "H Panchal"},
    },
}

DESAI = "Dr. Kalpesh Desai, MBBS, MD, DM (Hepatology)"
SHAH = "Dr. Rupal Shah, MBBS, MD (Medicine)"
PATEL_R = "Dr. Rohit N. Patel, MBBS, MS (General Surgery)"

LFT_LEGEND = [
    ("ALT - interpretation in fatty liver", "ALT (SGPT)"),
    ("Below 50 U/L", "Within reference interval"),
    ("50 - 100 U/L", "Mild elevation, common in steatosis"),
    ("Above 100 U/L", "Investigate other causes of hepatitis"),
]

# 11 kg off over eighteen months, back on after the knee injury in early 2025,
# then off again. Blood pressure follows the weight. No febrile visit except the
# post-operative one after the hernia repair.
HEIGHT_CM = 174.0

VITALS = {
    1: {"weight_kg": 96.4, "bp": "142/90", "spo2": 97, "temp_f": 98.4,
        "context": "Insurance medical. Raised enzymes and a bright liver on ultrasound."},
    2: {"weight_kg": 94.2, "bp": "138/88", "spo2": 98, "temp_f": 98.2,
        "context": "Dietician seen. Walking 30 minutes most days."},
    3: {"weight_kg": 91.0, "bp": "134/86", "spo2": 98, "temp_f": 98.6,
        "context": "Enzymes falling with the weight."},
    4: {"weight_kg": 88.6, "bp": "132/84", "spo2": 98, "temp_f": 98.4,
        "context": "Sustained effort, six kilos down."},
    5: {"weight_kg": 86.2, "bp": "128/82", "spo2": 99, "temp_f": 98.2,
        "context": "Pre-operative bloods for an elective hernia repair."},
    6: {"weight_kg": 85.8, "bp": "130/84", "spo2": 97, "temp_f": 100.2,
        "context": "Second post-operative day. Low-grade fever, wound clean."},
    7: {"weight_kg": 85.4, "bp": "126/80", "spo2": 98, "temp_f": 98.4,
        "context": "Annual review. Best liver enzymes so far."},
    8: {"weight_kg": 86.9, "bp": "128/82", "spo2": 98, "temp_f": 98.6,
        "context": "Knee injury; walking stopped six weeks ago."},
    9: {"weight_kg": 90.2, "bp": "136/86", "spo2": 97, "temp_f": 98.4,
        "context": "Weight climbing again, enzymes following it."},
    10: {"weight_kg": 93.6, "bp": "140/88", "spo2": 97, "temp_f": 98.2,
         "context": "Relapse confirmed. Restarted on a supervised programme."},
    11: {"weight_kg": 92.1, "bp": "138/88", "spo2": 98, "temp_f": 98.6,
         "context": "Swimming instead of walking while the knee settles."},
    12: {"weight_kg": 89.4, "bp": "134/84", "spo2": 98, "temp_f": 98.4,
         "context": "Responding to the second effort."},
    13: {"weight_kg": 87.8, "bp": "130/84", "spo2": 98, "temp_f": 98.2,
         "context": "Single repeat ALT to confirm the downward trend."},
    14: {"weight_kg": 86.0, "bp": "128/82", "spo2": 99, "temp_f": 98.4,
         "context": "Annual review. Fibroscan booked."},
    15: {"weight_kg": 84.6, "bp": "126/80", "spo2": 98, "temp_f": 98.6,
         "context": "Enzymes near normal, weight the lowest in five years."},
}

REPORTS = [
    # ---- R01 -- the insurance medical --------------------------------------
    {
        "collected": "2021-11-16 08:30", "reported": "2021-11-16 18:20",
        "lab": "sabarmati", "layout_style": "dense_multipanel",
        "header_style": "letterhead_logo_left", "uhid_label": "UHID",
        "doctor": SHAH, "specimen": "Serum, Fluoride plasma",
        "alias": 0, "traps": ["legend_lines"],
        "note": "Raised transaminases with an AST:ALT ratio below 1, in keeping with "
                "hepatic steatosis. Correlate with imaging.",
        "sections": [
            {"panel": "LFT", "title": 0, "legend": LFT_LEGEND,
             "values": {"BILI_T": 1.0, "BILI_D": 0.3, "ALT": 118, "AST": 74, "ALP": 112,
                        "GGT": 96, "PROT_T": 7.6, "ALB": 4.5}},
            {"panel": "LIPID", "title": 0,
             "values": {"CHOL": 232, "TRIG": 284, "HDL": 33}},
            {"panel": "DIABETES", "title": 0, "drop": ["GLU_R"],
             "values": {"GLU_F": 112, "GLU_PP": 168, "HBA1C": 6.2, "INSULIN_F": 22.4}},
        ],
    },
    # ---- R02 -- urine screen and a repeat ALT ------------------------------
    {
        "collected": "2022-03-22 09:00", "reported": "2022-03-22 15:40",
        "lab": "riverfront", "layout_style": "minimal_lines",
        "header_style": "bilingual_header", "uhid_label": "Patient ID",
        "doctor": SHAH, "specimen": "Urine (midstream), Serum",
        "alias": 1, "traps": ["unit_in_value_cell", "sample_type_row"],
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 1, "sample_row": "Urine, Midstream",
             "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Yellow", "UR_PH": 6.0, "UR_SPGR": 1.022,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 2, "UR_RBC": 0, "UR_EPITH": 2}},
            {"heading": "Liver Enzymes",
             "rows": [{"code": "ALT", "value": 96, "flag": "H"},
                      {"code": "AST", "value": 62, "flag": "H"},
                      {"code": "GGT", "value": 84, "flag": "H"}]},
        ],
    },
    # ---- R03 -- landscape follow-up with the previous column ---------------
    {
        "collected": "2022-08-30 08:45", "reported": "2022-08-30 17:10",
        "lab": "sabarmati", "layout_style": "landscape_wide",
        "header_style": "banner_with_qr", "uhid_label": "UHID",
        "doctor": DESAI, "specimen": "Serum",
        "alias": 2, "traps": ["prev_value_column", "method_sub_line"],
        "note": "Previous results shown for comparison, as requested by the clinician.",
        "sections": [
            {"heading": "Liver Function - Comparative", "methods": True,
             "prev": {"ALT": "96 (22/03/2022)", "AST": "62 (22/03/2022)",
                      "ALP": "108 (16/11/2021)", "GGT": "84 (22/03/2022)",
                      "BILI_T": "1.00 (16/11/2021)", "ALB": "4.5 (16/11/2021)"},
             "rows": [{"code": "BILI_T", "value": 0.9}, {"code": "BILI_D", "value": 0.2},
                      {"code": "ALT", "value": 74, "flag": "H"},
                      {"code": "AST", "value": 52, "flag": "H"},
                      {"code": "ALP", "value": 104}, {"code": "GGT", "value": 68},
                      {"code": "PROT_T", "value": 7.4}, {"code": "ALB", "value": 4.4}]},
            {"panel": "THYROID", "title": 1, "drop": ["FT3", "ANTI_TPO"],
             "prev": {"TSH": "2.86 (16/11/2021)"},
             "values": {"TSH": 2.64, "T3_TOTAL": 128, "T4_TOTAL": 8.6, "FT4": 1.22}},
        ],
    },
    # ---- R04 -- six kilos down ----------------------------------------------
    {
        "collected": "2023-01-11 08:20", "reported": "2023-01-11 16:35",
        "lab": "riverfront", "layout_style": "kv_header_table",
        "header_style": "barcode_header", "uhid_label": "Patient ID",
        "doctor": DESAI, "specimen": "Serum",
        "alias": 3, "traps": ["footnote_marker", "ratio_no_code"],
        "footnotes": [("1", "Fibrosis-4 index calculated from age, AST, ALT and platelet "
                            "count. Below 1.30 makes advanced fibrosis unlikely.")],
        "sections": [
            {"panel": "ELECTROLYTES", "title": 2, "drop": ["CA_ION"],
             "values": {"NA": 140, "K": 4.2, "CL": 103, "CA": 9.4, "PHOS": 3.4,
                        "MG": 2.0}},
            {"heading": "Liver Follow-up",
             "rows": [{"code": "ALT", "value": 58, "flag": "H"},
                      {"code": "AST", "value": 44, "flag": "H"},
                      {"label": "FIB-4 Index", "value": "0.94", "unit": "",
                       "reference": "< 1.30", "marker": "1", "trap": "ratio_no_code"},
                      {"label": "AST / ALT Ratio", "value": "0.76", "unit": "",
                       "reference": "< 1.0", "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R05 -- pre-operative screen ----------------------------------------
    {
        "collected": "2023-06-07 07:40", "reported": "2023-06-07 14:50",
        "lab": "swaminarayan", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": PATEL_R, "specimen": "Serum, Citrate plasma, Whole blood (EDTA)",
        "alias": 0, "traps": ["text_result", "method_sub_line"],
        "note": "Pre-operative screen for elective inguinal hernia repair.",
        "sections": [
            {"panel": "COAGULATION", "title": 2, "methods": True,
             "values": {"PT": 12.6, "INR": 1.04, "APTT": 30.2, "D_DIMER": 210}},
            {"panel": "SEROLOGY", "title": 4, "drop": ["WIDAL", "DENGUE_NS1",
                                                       "DENGUE_IGM", "MP"],
             "values": {"HBSAG": "Non Reactive", "ANTI_HCV": "Non Reactive",
                        "HIV": "Non Reactive", "VDRL": "Non Reactive"},
             "row_traps": {"HBSAG": "text_result"}},
            {"heading": "Liver Enzymes",
             "rows": [{"code": "ALT", "value": 49}, {"code": "AST", "value": 38}]},
        ],
    },
    # ---- R06 -- second post-operative day, by fax --------------------------
    {
        "collected": "2023-06-11 06:50", "reported": "2023-06-11 09:20",
        "lab": "swaminarayan", "layout_style": "fax_header",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": PATEL_R, "specimen": "Whole blood (EDTA), Serum, Urine",
        "alias": 1, "traps": ["text_result", "no_reference_column"],
        "note": "Transmitted to the surgical ward. Original with the laboratory.",
        "sections": [
            {"heading": "Post-operative Counts",
             "rows": [{"code": "HGB", "value": 13.9}, {"code": "PCV", "value": 41.8},
                      {"code": "WBC", "value": 12800, "flag": "H"},
                      {"code": "NEUT_PCT", "value": 79},
                      {"code": "PLT", "value": 288000}]},
            {"heading": "Microbiology",
             "rows": [{"code": "URINE_CULTURE",
                       "value": "No growth after 48 hours of aerobic incubation.",
                       "trap": "text_result"},
                      {"code": "CRP", "value": 62.4, "flag": "H"}]},
        ],
    },
    # ---- R07 -- annual review, best enzymes ---------------------------------
    {
        "collected": "2023-11-28 08:00", "reported": "2023-11-28 19:40",
        "lab": "sabarmati", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "UHID",
        "doctor": DESAI, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 2, "traps": ["merged_panel_heading", "text_result", "method_sub_line"],
        "note": "Annual fatty liver review package.",
        "sections": [
            {"panel": "CBC", "title": 3, "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "values": {"HGB": 14.6, "RBC": 4.88, "PCV": 43.2, "MCV": 88.5, "MCH": 29.9,
                        "WBC": 6900, "NEUT_PCT": 58, "LYMPH_PCT": 32, "MONO_PCT": 6,
                        "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 254000}},
            {"panel": "LIPID", "title": 2, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 186, "TRIG": 158, "HDL": 42}},
            {"panels": ["LFT", "KFT"], "heading": "Biochemistry - Liver and Renal",
             "trap": "merged_panel_heading",
             "drop": ["AG_RATIO", "GLOB", "BILI_I", "BUN"],
             "values": {"BILI_T": 0.7, "BILI_D": 0.2, "ALT": 34, "AST": 30, "ALP": 88,
                        "GGT": 42, "PROT_T": 7.3, "ALB": 4.5,
                        "CREAT": 0.94, "UREA": 30, "UA": 6.0}},
            {"panel": "IRON", "title": 1, "drop": ["UIBC"], "methods": True,
             "values": {"FERRITIN": 268, "IRON": 108, "TIBC": 322}},
            {"panel": "VITAMIN", "title": 2,
             "values": {"VIT_D": 22.8, "VIT_B12": 336, "FOLATE": 7.8}},
            {"heading": "Other",
             "rows": [{"code": "BLOOD_GROUP", "value": "A Negative", "trap": "text_result"},
                      {"code": "HBA1C", "value": 5.8}]},
        ],
    },
    # ---- R08 -- the knee injury ---------------------------------------------
    {
        "collected": "2024-05-14 09:10", "reported": "2024-05-14 16:20",
        "lab": "riverfront", "layout_style": "two_column",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": SHAH, "specimen": "Serum",
        "alias": 3, "traps": ["sno_column", "sparse_panel"],
        "sections": [
            {"panel": "THYROID", "title": 3, "drop": ["T3_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel",
             "values": {"TSH": 3.06, "T4_TOTAL": 8.8, "FT4": 1.26}},
            {"panel": "DIABETES", "title": 3, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 106, "GLU_PP": 152, "HBA1C": 6.0}},
        ],
    },
    # ---- R09 -- weight and enzymes climbing ---------------------------------
    {
        "collected": "2024-10-30 08:50", "reported": "2024-10-30 17:05",
        "lab": "sabarmati", "layout_style": "duplicate_watermark",
        "header_style": "letterhead_logo_left", "uhid_label": "UHID",
        "doctor": DESAI, "specimen": "Serum",
        "alias": 0, "traps": ["prev_value_column", "abnormal_shaded"],
        "note": "Duplicate copy issued at the patient's request on 02/11/2024.",
        "sections": [
            {"heading": "Liver Function - Follow-up",
             "prev": {"ALT": "34 (28/11/2023)", "AST": "30 (28/11/2023)",
                      "GGT": "42 (28/11/2023)", "ALP": "88 (28/11/2023)"},
             "rows": [{"code": "ALT", "value": 62, "flag": "H"},
                      {"code": "AST", "value": 46, "flag": "H"},
                      {"code": "GGT", "value": 58},
                      {"code": "ALP", "value": 96},
                      {"code": "BILI_T", "value": 0.8},
                      {"label": "Lipase", "value": "38", "unit": "U/L",
                       "reference": "13 - 60"}]},
        ],
    },
    # ---- R10 -- relapse confirmed -------------------------------------------
    {
        "collected": "2025-03-25 08:35", "reported": "2025-03-25 18:00",
        "lab": "swaminarayan", "layout_style": "poor_scan",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": DESAI, "specimen": "Serum, Urine (midstream)",
        "alias": 1, "traps": ["ambiguous_abbreviation", "legend_lines"],
        "stamp": "REVIEW<br>HEPATOLOGY",
        "sections": [
            {"panel": "LFT", "title": 4, "legend": LFT_LEGEND,
             "values": {"BILI_T": 1.0, "BILI_D": 0.3, "ALT": 86, "AST": 58, "ALP": 108,
                        "GGT": 82, "PROT_T": 7.5, "ALB": 4.4}},
            {"panel": "URINE_ROUTINE", "title": 4,
             "labels": {"UR_PROT": "ALB"},
             "row_traps": {"UR_PROT": "ambiguous_abbreviation"},
             "values": {"UR_COLOUR": "Yellow", "UR_PH": 5.5, "UR_SPGR": 1.024,
                        "UR_PROT": "Trace", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 3, "UR_RBC": 1, "UR_EPITH": 3, "MICROALB": 16,
                        "ACR": 18}},
        ],
    },
    # ---- R11 -- swimming instead --------------------------------------------
    {
        "collected": "2025-08-12 09:20", "reported": "2025-08-12 14:40",
        "lab": "riverfront", "layout_style": "thermal_slip",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": SHAH, "specimen": "Serum",
        "alias": 2, "traps": ["no_reference_column"],
        "note": "Collection centre print. Full report available online.",
        "sections": [
            {"heading": "SGPT (ALT)",
             "rows": [{"code": "ALT", "value": 71, "flag": "H"}]},
        ],
    },
    # ---- R12 -- responding again --------------------------------------------
    {
        "collected": "2025-12-18 08:15", "reported": "2025-12-18 17:30",
        "lab": "sabarmati", "layout_style": "clean_table",
        "header_style": "barcode_header", "uhid_label": "UHID",
        "doctor": DESAI, "specimen": "Whole blood (EDTA), Serum",
        "alias": 3, "traps": ["not_reported"],
        "sections": [
            {"panel": "CBC", "title": 5, "drop": ["ANC", "ALC"],
             "values": {"HGB": 14.4, "RBC": 4.82, "PCV": 42.6, "MCV": 88.4, "MCH": 29.9,
                        "MCHC": 33.8, "RDW": 13.1, "WBC": 7300, "NEUT_PCT": 60,
                        "LYMPH_PCT": 30, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 262000, "MPV": 9.8}},
            {"panel": "KFT", "title": 1,
             "values": {"CREAT": 0.98, "UREA": 32, "UA": 6.4}},
            {"heading": "Liver Enzymes",
             "rows": [{"code": "ALT", "value": 54, "flag": "H"},
                      {"code": "AST", "value": 42, "flag": "H"},
                      {"label": "Amylase", "value": "Not Reported", "unit": "U/L",
                       "reference": "28 - 100", "trap": "not_reported"}]},
        ],
    },
    # ---- R13 -- one repeat ALT ----------------------------------------------
    {
        "collected": "2026-03-07 09:40", "reported": "2026-03-07 13:10",
        "lab": "riverfront", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Patient ID",
        "doctor": SHAH, "specimen": "Serum",
        "alias": 0, "traps": ["no_header_row"],
        "sections": [
            {"heading": "SGPT (ALT) - Repeat",
             "rows": [{"code": "ALT", "value": 47}]},
        ],
    },
    # ---- R14 -- annual review, two pages ------------------------------------
    {
        "collected": "2026-06-24 07:50", "reported": "2026-06-24 20:15",
        "lab": "sabarmati", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "UHID",
        "doctor": DESAI, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["footnote_marker", "prev_value_column"],
        "page_break_after": 3,
        "footnotes": [("1", "Fibroscan booked for 12/07/2026; result not included here.")],
        "sections": [
            {"panel": "CBC", "title": 4,
             "values": {"HGB": 14.8, "RBC": 4.91, "PCV": 43.8, "MCV": 89.2, "MCH": 30.1,
                        "MCHC": 33.8, "RDW": 12.9, "WBC": 6800, "NEUT_PCT": 57,
                        "LYMPH_PCT": 33, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 249000, "MPV": 9.6}},
            {"panel": "LIPID", "title": 5,
             "prev": {"CHOL": "186 (28/11/2023)", "TRIG": "158 (28/11/2023)"},
             "values": {"CHOL": 178, "TRIG": 142, "HDL": 44}},
            {"panel": "DIABETES", "title": 4, "drop": ["GLU_R"],
             "values": {"GLU_F": 98, "GLU_PP": 138, "HBA1C": 5.7, "INSULIN_F": 12.6}},
            {"panel": "ELECTROLYTES", "title": 4, "drop": ["CA_ION", "MG"],
             "values": {"NA": 141, "K": 4.3, "CL": 104, "CA": 9.5, "PHOS": 3.3}},
            {"heading": "Liver Function - Comparative",
             "prev": {"ALT": "47 (07/03/2026)", "AST": "42 (18/12/2025)",
                      "GGT": "64 (12/08/2025)"},
             "rows": [{"code": "BILI_T", "value": 0.7}, {"code": "ALT", "value": 43,
                       "marker": "1"},
                      {"code": "AST", "value": 34}, {"code": "ALP", "value": 86},
                      {"code": "GGT", "value": 48}, {"code": "ALB", "value": 4.5}]},
            {"panel": "KFT", "title": 4,
             "values": {"CREAT": 0.96, "UREA": 31, "UA": 6.1}},
            {"heading": "Additional",
             "rows": [{"label": "Homocysteine", "value": "12.4", "unit": "umol/L",
                       "reference": "5.0 - 15.0"}]},
        ],
    },
    # ---- R15 -- lowest weight in five years ---------------------------------
    {
        "collected": "2026-09-16 08:25", "reported": "2026-09-16 16:10",
        "lab": "swaminarayan", "layout_style": "mixed_print_hand",
        "header_style": "stamp_and_signature", "uhid_label": "Hospital No",
        "doctor": DESAI, "specimen": "Serum", "stamp": "HEPATOLOGY<br>REVIEWED",
        "alias": 2, "traps": ["method_sub_line"],
        "sections": [
            {"panel": "IRON", "title": 3, "methods": True,
             "values": {"FERRITIN": 186, "IRON": 96, "TIBC": 330}},
            {"panel": "VITAMIN", "title": 4, "methods": True,
             "values": {"VIT_D": 32.6, "VIT_B12": 392, "FOLATE": 9.4}},
            {"heading": "Noted at the clinic", "hand_addendum": True,
             "rows": [{"code": "ALT", "value": 41}, {"code": "AST", "value": 33}]},
        ],
    },
]
