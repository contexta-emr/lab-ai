"""Patient 2 of 20 - Cardiology. Post-MI secondary prevention, statin titration.

Male, 61 at the first report, Nagpur. Presents with an anterior wall MI in November 2021
(troponin 8.42, CK-MB 96); the first two reports are three days apart around that
admission. Statin is titrated over the following years and LDL falls 168 -> 58. The
setback is December 2025: unstable angina, a second troponin rise that does not reach
infarct range, and a lipid profile that had crept back up after he stopped the higher
statin dose himself.

Only independent values are authored; every calculated analyte comes from catalog.derive.
"""

from __future__ import annotations

PATIENT = {
    "number": 2,
    "name": "Vasantrao B. Ingle",
    "sex": "M",
    "dob": "1960-05-22",
    "uhid": "SKH/318645",
    "department": "Cardiology",
    "city": "Nagpur",
    "age_at_first": 61,
    "tracked": ["LDL"],
    "brief": "Post-MI secondary prevention, statin titration",
}


def check_arc(series):
    ldl = [v for _, v in series["LDL"]]
    fails = []
    if not ldl[0] > 150:
        fails.append(f"LDL should start high after the MI, got {ldl[0]}")
    if not min(ldl) < 70:
        fails.append(f"statin titration never reaches target, best LDL {min(ldl)}")
    # somewhere in the series LDL climbs well above the best achieved up to that point:
    # that is the year he halved his own statin dose
    if not any(ldl[j] > min(ldl[:j]) + 35 for j in range(1, len(ldl))):
        fails.append("no lipid relapse above the best result so far")
    if not ldl[-1] < 70:
        fails.append(f"should end back at target, got {ldl[-1]}")
    return fails


LABS = {
    "shreeji": {
        "abbr": "SHD", "acc_style": 0,
        "name": "Shreeji Diagnostics",
        "addr": "Plot 22, Ramdaspeth, Nagpur 440010",
        "city": "Nagpur",
        "phone": "0712 254 6611",
        "accred": "NABL Accredited (MC-4417) | ISO 15189:2012",
        "path": {"name": "Dr. Manjusha R. Deolalikar", "qual": "MD (Pathology)",
                 "regn": "MMC 2003/09/2214", "scrawl": "M Deolalikar"},
    },
    "orange": {
        "abbr": "OCP", "acc_style": 2,
        "name": "Orange City Path Lab",
        "addr": "Central Avenue, Sitabuldi, Nagpur 440012",
        "city": "Nagpur",
        "phone": "0712 663 2280",
        "accred": "NABL Accredited (M-5108)",
        "path": {"name": "Dr. Alok S. Chourasia", "qual": "MBBS, MD (Path.)",
                 "regn": "MMC 2009/02/5530", "scrawl": "A Chourasia"},
    },
    "skh": {
        "abbr": "SKH", "acc_style": 1,
        "name": "Shree Krishna Heart Institute Laboratory",
        "addr": "Wardha Road, Nagpur 440015",
        "city": "Nagpur",
        "phone": "0712 229 4000",
        "accred": "Department of Laboratory Medicine, Cardiac Sciences Block",
        "path": {"name": "Dr. Sunil V. Mahajan", "qual": "MD, DNB (Pathology)",
                 "regn": "MMC 1998/11/0745", "scrawl": "S Mahajan"},
    },
}

DESHMUKH = "Dr. A. P. Deshmukh, MBBS, MD, DM (Cardiology)"
RAUT = "Dr. Kavita Raut, MBBS, MD (Medicine)"
TIWARI = "Dr. Shrikant Tiwari, MBBS, DNB (Cardiology)"

LIPID_LEGEND = [
    ("LDL cholesterol targets - very high risk (ESC 2019)", "LDL Cholesterol"),
    ("Below 55 mg/dL", "Target after myocardial infarction"),
    ("55 - 99 mg/dL", "Above target, intensify therapy"),
    ("100 mg/dL and above", "High"),
]

TROP_LEGEND = [
    ("Troponin I - interpretation", "Troponin I"),
    ("Below 0.04 ng/mL", "Normal"),
    ("0.04 - 0.40 ng/mL", "Myocardial injury, correlate clinically"),
    ("Above 0.40 ng/mL", "Consistent with myocardial infarction"),
]

# Cardiac rehab takes 6 kg off over two years; it creeps back when he lapses in 2025.
# The MI admission is the only visit with a low saturation.
HEIGHT_CM = 168.0

VITALS = {
    1: {"weight_kg": 81.2, "bp": "158/96", "spo2": 94, "temp_f": 98.8,
        "context": "Anterior wall MI. Admitted through casualty, primary PCI the same day."},
    2: {"weight_kg": 80.6, "bp": "132/84", "spo2": 96, "temp_f": 99.1,
        "context": "Third post-procedure day. Ambulating, enzymes falling."},
    3: {"weight_kg": 79.4, "bp": "136/86", "spo2": 97, "temp_f": 98.4,
        "context": "First outpatient review. Statin and dual antiplatelet started."},
    4: {"weight_kg": 77.8, "bp": "132/84", "spo2": 98, "temp_f": 98.2,
        "context": "Cardiac rehabilitation under way, walking 40 minutes daily."},
    5: {"weight_kg": 76.5, "bp": "128/82", "spo2": 98, "temp_f": 98.6,
        "context": "Statin dose increased; LDL still above target."},
    6: {"weight_kg": 75.3, "bp": "126/80", "spo2": 98, "temp_f": 98.4,
        "context": "Annual review. Best weight since the infarct."},
    7: {"weight_kg": 75.0, "bp": "124/78", "spo2": 99, "temp_f": 98.2,
        "context": "Stable on therapy, asymptomatic."},
    8: {"weight_kg": 74.6, "bp": "122/78", "spo2": 98, "temp_f": 98.4,
        "context": "LDL at target for the first time. Ezetimibe added earlier this year."},
    9: {"weight_kg": 75.2, "bp": "126/80", "spo2": 98, "temp_f": 98.6,
        "context": "Well. Routine six-monthly bloods."},
    10: {"weight_kg": 76.4, "bp": "130/82", "spo2": 98, "temp_f": 98.2,
         "context": "Admits reducing the statin dose himself after muscle aches."},
    11: {"weight_kg": 78.1, "bp": "136/86", "spo2": 97, "temp_f": 98.4,
         "context": "Weight and lipids both drifting up."},
    12: {"weight_kg": 78.6, "bp": "148/92", "spo2": 96, "temp_f": 98.8,
         "context": "Chest pain at rest. Admitted as unstable angina, angiography planned."},
    13: {"weight_kg": 78.2, "bp": "134/84", "spo2": 97, "temp_f": 98.6,
         "context": "Third day of admission. Troponin plateaued, no infarct."},
    14: {"weight_kg": 76.8, "bp": "128/80", "spo2": 98, "temp_f": 98.4,
         "context": "Annual review after restarting full-dose statin."},
    15: {"weight_kg": 75.9, "bp": "126/78", "spo2": 98, "temp_f": 98.2,
         "context": "Back on track. LDL below target again."},
}

REPORTS = [
    # ---- R01 -- the infarct ------------------------------------------------
    {
        "collected": "2021-11-03 02:20", "reported": "2021-11-03 05:10",
        "lab": "skh", "layout_style": "dense_multipanel",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": DESHMUKH, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 0, "traps": ["legend_lines", "repeat_test_same_day"],
        "note": "Sample received through casualty. Results telephoned to the cardiology "
                "registrar at 04:55 hrs.",
        "sections": [
            {"panel": "CARDIAC", "title": 1, "methods": True, "legend": TROP_LEGEND,
             "values": {"TROP_I": 8.42, "CPK_MB": 96, "NT_PROBNP": 1840},
             "extra_rows": [
                 {"code": "TROP_I", "label": "Troponin I (6 hour repeat)", "value": "11.260",
                  "unit": "ng/mL", "reference": "< 0.04", "flag": "H",
                  "trap": "repeat_test_same_day"},
             ]},
            {"panel": "CBC", "title": 0, "drop": ["MPV", "RDW"],
             "values": {"HGB": 13.6, "RBC": 4.62, "PCV": 41.2, "MCV": 89.1, "MCH": 29.4,
                        "MCHC": 33.0, "WBC": 12600, "NEUT_PCT": 78, "LYMPH_PCT": 15,
                        "MONO_PCT": 5, "EOS_PCT": 2, "BASO_PCT": 0, "PLT": 274000}},
            {"panel": "ELECTROLYTES", "title": 2, "drop": ["CA_ION", "MG"],
             "values": {"NA": 138, "K": 4.6, "CL": 102, "CA": 9.1, "PHOS": 3.5}},
        ],
    },
    # ---- R02 -- three days later, one test ---------------------------------
    {
        "collected": "2021-11-06 07:00", "reported": "2021-11-06 10:30",
        "lab": "skh", "layout_style": "minimal_lines",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": DESHMUKH, "specimen": "Serum",
        "alias": 1, "traps": ["method_sub_line"],
        "sections": [
            {"heading": "Cardiac Marker - Serial", "methods": True,
             "rows": [{"code": "TROP_I", "value": 1.940, "flag": "H"}]},
        ],
    },
    # ---- R03 -- first outpatient review ------------------------------------
    {
        "collected": "2022-02-14 08:30", "reported": "2022-02-14 17:20",
        "lab": "shreeji", "layout_style": "kv_header_table",
        "header_style": "letterhead_logo_left", "uhid_label": "UHID",
        "doctor": DESHMUKH, "specimen": "Serum, Fluoride plasma",
        "alias": 1, "traps": ["legend_lines", "footnote_marker"],
        "footnotes": [("1", "Lipids measured after a 12 hour fast. Statin therapy started "
                            "on 08/11/2021.")],
        "sections": [
            {"panel": "LIPID", "title": 0, "legend": LIPID_LEGEND,
             "values": {"CHOL": 238, "TRIG": 196, "HDL": 31}},
            {"panel": "KFT", "title": 1, "drop": ["UA"],
             "values": {"CREAT": 1.08, "UREA": 34}},
            {"heading": "Glycaemic Screen",
             "rows": [{"code": "GLU_F", "value": 102, "marker": "1"},
                      {"code": "HBA1C", "value": 5.9}]},
        ],
    },
    # ---- R04 -- rehab going well -------------------------------------------
    {
        "collected": "2022-07-19 09:10", "reported": "2022-07-19 16:40",
        "lab": "orange", "layout_style": "two_column",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": RAUT, "specimen": "Serum, Urine (midstream)",
        "alias": 2, "traps": ["sno_column"],
        "sections": [
            {"panel": "LFT", "title": 2, "drop": ["GGT", "BILI_I"],
             "values": {"BILI_T": 0.7, "BILI_D": 0.2, "ALT": 42, "AST": 34, "ALP": 84,
                        "PROT_T": 7.0, "ALB": 4.1}},
            {"panel": "URINE_ROUTINE", "title": 1, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.0, "UR_SPGR": 1.018,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 2, "UR_RBC": 0, "UR_EPITH": 2}},
            {"heading": "Lipid Recheck",
             "rows": [{"code": "CHOL", "value": 186}, {"code": "TRIG", "value": 164},
                      {"code": "HDL", "value": 36}, {"code": "LDL"}]},
        ],
    },
    # ---- R05 -- statin increased -------------------------------------------
    {
        "collected": "2022-12-06 08:05", "reported": "2022-12-06 15:25",
        "lab": "shreeji", "layout_style": "carbon_copy",
        "header_style": "minimal_text_top", "uhid_label": "UHID",
        "doctor": DESHMUKH, "specimen": "Serum",
        "alias": 3, "traps": ["range_with_unit", "method_sub_line"],
        "sections": [
            {"panel": "THYROID", "title": 1, "drop": ["FT3", "ANTI_TPO"], "methods": True,
             "values": {"TSH": 3.44, "T3_TOTAL": 112, "T4_TOTAL": 8.1, "FT4": 1.18}},
            {"heading": "Lipids and Muscle Enzymes",
             "rows": [{"code": "CHOL", "value": 164}, {"code": "TRIG", "value": 148},
                      {"code": "HDL", "value": 38}, {"code": "LDL"},
                      {"label": "CPK - Total", "value": "212", "unit": "U/L",
                       "reference": "38 - 174", "flag": "H"}]},
        ],
    },
    # ---- R06 -- annual health check ----------------------------------------
    {
        "collected": "2023-05-23 07:40", "reported": "2023-05-23 19:50",
        "lab": "orange", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "MRN",
        "doctor": RAUT, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 0, "traps": ["merged_panel_heading", "text_result", "method_sub_line"],
        "note": "Annual cardiac review package.",
        "sections": [
            {"panel": "CBC", "title": 2, "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "values": {"HGB": 14.0, "RBC": 4.71, "PCV": 42.4, "MCV": 90.0, "MCH": 29.7,
                        "WBC": 7100, "NEUT_PCT": 60, "LYMPH_PCT": 30, "MONO_PCT": 6,
                        "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 258000}},
            {"panel": "LIPID", "title": 4, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 148, "TRIG": 132, "HDL": 40}},
            {"panels": ["LFT", "ELECTROLYTES"], "heading": "Biochemistry - Liver and Minerals",
             "trap": "merged_panel_heading",
             "drop": ["GGT", "AG_RATIO", "GLOB", "CA_ION", "MG", "PHOS"],
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 38, "AST": 30, "ALP": 79,
                        "PROT_T": 7.1, "ALB": 4.2,
                        "NA": 140, "K": 4.2, "CL": 103, "CA": 9.3}},
            {"panel": "IRON", "title": 2, "drop": ["UIBC"], "methods": True,
             "values": {"FERRITIN": 128, "IRON": 94, "TIBC": 336}},
            {"panel": "VITAMIN", "title": 2,
             "values": {"VIT_D": 24.6, "VIT_B12": 302, "FOLATE": 7.4}},
            {"heading": "Other Investigations",
             "rows": [{"code": "BLOOD_GROUP", "value": "O Positive", "trap": "text_result"},
                      {"code": "HBA1C", "value": 6.0},
                      {"label": "Apolipoprotein B", "value": "78", "unit": "mg/dL",
                       "reference": "< 90"}]},
        ],
    },
    # ---- R07 -- stable ------------------------------------------------------
    {
        "collected": "2023-11-08 09:20", "reported": "2023-11-08 18:10",
        "lab": "shreeji", "layout_style": "clean_table",
        "header_style": "letterhead_logo_left", "uhid_label": "UHID",
        "doctor": TIWARI, "specimen": "Serum, Urine (midstream)",
        "alias": 1, "traps": ["sample_type_row"],
        "sections": [
            {"panel": "KFT", "title": 3, "sample_row": "Serum, fasting",
             "values": {"CREAT": 1.12, "UREA": 36, "UA": 6.4}},
            {"panel": "URINE_ROUTINE", "title": 4,
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.5, "UR_SPGR": 1.020,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 3, "UR_RBC": 1, "UR_EPITH": 2, "MICROALB": 18,
                        "ACR": 22}},
        ],
    },
    # ---- R08 -- LDL at target ----------------------------------------------
    {
        "collected": "2024-04-16 08:15", "reported": "2024-04-16 17:05",
        "lab": "orange", "layout_style": "kv_header_table",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": DESHMUKH, "specimen": "Serum, Fluoride plasma",
        "alias": 2, "traps": ["not_reported", "legend_lines"],
        "sections": [
            {"heading": "Lipid Profile - Fasting", "legend": LIPID_LEGEND,
             "rows": [{"code": "CHOL", "value": 118}, {"code": "TRIG", "value": 110},
                      {"code": "HDL", "value": 42}, {"code": "LDL"}, {"code": "NON_HDL"}]},
            {"panel": "THYROID", "title": 3, "drop": ["T3_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel",
             "values": {"TSH": 3.18, "T4_TOTAL": 8.4, "FT4": 1.22}},
            {"panel": "DIABETES", "title": 1, "drop": ["GLU_R", "GLU_PP"],
             "values": {"GLU_F": 98, "HBA1C": 5.8, "INSULIN_F": "Not Reported"},
             "row_traps": {"INSULIN_F": "not_reported"}},
        ],
    },
    # ---- R09 -- routine six-monthly ----------------------------------------
    {
        "collected": "2024-09-24 10:05", "reported": "2024-09-24 16:35",
        "lab": "shreeji", "layout_style": "mixed_print_hand",
        "header_style": "stamp_and_signature", "uhid_label": "UHID",
        "doctor": TIWARI, "specimen": "Serum", "stamp": "REVIEWED<br>CARDIOLOGY",
        "alias": 3, "traps": ["text_result"],
        "sections": [
            {"heading": "Biochemistry",
             "rows": [{"code": "CHOL", "value": 124}, {"code": "TRIG", "value": 118},
                      {"code": "HDL", "value": 41}, {"code": "LDL"},
                      {"code": "CREAT", "value": 1.14},
                      {"label": "Homocysteine", "value": "13.8", "unit": "umol/L",
                       "reference": "5.0 - 15.0"}]},
            {"heading": "Added at the clinic", "hand_addendum": True,
             "rows": [{"code": "K", "value": 4.4}, {"code": "HBA1C", "value": 5.9}]},
        ],
    },
    # ---- R10 -- self-reduced the statin ------------------------------------
    {
        "collected": "2025-03-11 08:50", "reported": "2025-03-11 17:45",
        "lab": "orange", "layout_style": "clean_table",
        "header_style": "banner_with_qr", "uhid_label": "MRN",
        "doctor": DESHMUKH, "specimen": "Serum, Urine (midstream)",
        "alias": 0, "traps": ["ambiguous_abbreviation", "ratio_no_code"],
        "sections": [
            {"heading": "Cholesterol Profile",
             "rows": [{"code": "CHOL", "label": "TC", "value": 176,
                       "trap": "ambiguous_abbreviation"},
                      {"code": "TRIG", "value": 162}, {"code": "HDL", "value": 38},
                      {"code": "LDL"}, {"code": "VLDL"}]},
            {"panel": "URINE_ROUTINE", "title": 5, "drop": ["MICROALB", "ACR", "UR_KET"],
             "values": {"UR_COLOUR": "Yellow", "UR_PH": 6.0, "UR_SPGR": 1.022,
                        "UR_PROT": "Trace", "UR_GLU": "Absent", "UR_PUS": 3,
                        "UR_RBC": 1, "UR_EPITH": 3}},
            {"heading": "Derived Indices",
             "rows": [{"label": "TG / HDL Ratio", "value": "4.3", "unit": "",
                       "reference": "< 3.5", "flag": "H", "trap": "ratio_no_code"},
                      {"label": "Urea / Creatinine Ratio", "value": "32", "unit": "",
                       "reference": "20 - 35", "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R11 -- drifting further -------------------------------------------
    {
        "collected": "2025-08-19 09:00", "reported": "2025-08-19 14:20",
        "lab": "shreeji", "layout_style": "minimal_lines",
        "header_style": "minimal_text_top", "uhid_label": "UHID",
        "doctor": TIWARI, "specimen": "Serum",
        "alias": 1, "traps": ["unit_in_value_cell"],
        "sections": [
            {"heading": "Lipid Profile - Short",
             "rows": [{"code": "CHOL", "value": 192}, {"code": "TRIG", "value": 178},
                      {"code": "HDL", "value": 36}, {"code": "LDL"}]},
        ],
    },
    # ---- R12 -- unstable angina --------------------------------------------
    {
        "collected": "2025-12-02 23:40", "reported": "2025-12-03 02:15",
        "lab": "skh", "layout_style": "poor_scan",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": DESHMUKH, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["sno_column", "text_result"],
        "stamp": "CRITICAL<br>VALUE PHONED",
        "note": "Troponin raised but below infarct range. Serial sample advised at 6 hours.",
        "sections": [
            {"panel": "CARDIAC", "title": 0, "methods": True,
             "values": {"TROP_I": 0.186, "CPK_MB": 31, "NT_PROBNP": 640}},
            {"heading": "Haematology - Admission Screen",
             "rows": [{"code": "HGB", "value": 13.2}, {"code": "WBC", "value": 9800},
                      {"code": "NEUT_PCT", "value": 71}, {"code": "LYMPH_PCT", "value": 21},
                      {"code": "PLT", "value": 246000}, {"code": "MPV", "value": 10.1}]},
            {"heading": "Bedside Chemistry",
             "rows": [{"code": "K", "value": 4.1}, {"code": "CREAT", "value": 1.26},
                      {"code": "BLOOD_GROUP", "value": "O Positive", "trap": "text_result"},
                      {"code": "PERIPH_SMEAR",
                       "value": "Normocytic normochromic picture. Neutrophilia noted. "
                                "No immature forms.", "trap": "text_result"}]},
        ],
    },
    # ---- R13 -- third day, one test ----------------------------------------
    {
        "collected": "2025-12-05 06:30", "reported": "2025-12-05 09:45",
        "lab": "skh", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": DESHMUKH, "specimen": "Serum",
        "alias": 3, "traps": ["no_header_row"],
        "sections": [
            {"heading": "Serial Troponin",
             "rows": [{"code": "TROP_I", "value": 0.092, "flag": "H"}]},
        ],
    },
    # ---- R14 -- annual review, two pages -----------------------------------
    {
        "collected": "2026-05-12 07:35", "reported": "2026-05-12 20:10",
        "lab": "orange", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "MRN",
        "doctor": DESHMUKH, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 2, "traps": ["footnote_marker", "method_sub_line"],
        "page_break_after": 3,
        "footnotes": [("1", "Lp(a) measured once in a lifetime is sufficient unless therapy "
                            "changes.")],
        "note": "Full-dose statin with ezetimibe resumed in January 2026.",
        "sections": [
            {"panel": "CBC", "title": 3,
             "values": {"HGB": 13.8, "RBC": 4.66, "PCV": 41.6, "MCV": 89.3, "MCH": 29.6,
                        "MCHC": 33.2, "RDW": 13.4, "WBC": 7400, "NEUT_PCT": 62,
                        "LYMPH_PCT": 28, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 262000, "MPV": 9.7}},
            {"panel": "LIPID", "title": 1, "methods": True,
             "values": {"CHOL": 132, "TRIG": 118, "HDL": 43}},
            {"panel": "DIABETES", "title": 3, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 104, "GLU_PP": 138, "HBA1C": 6.1}},
            {"panel": "LFT", "title": 5,
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 40, "AST": 32, "ALP": 82,
                        "GGT": 44, "PROT_T": 7.0, "ALB": 4.1}},
            {"panel": "KFT", "title": 5,
             "values": {"CREAT": 1.18, "UREA": 38, "UA": 6.6}},
            {"heading": "Additional Investigations",
             "rows": [{"label": "Lipoprotein (a)", "value": "22", "unit": "mg/dL",
                       "reference": "< 30", "marker": "1"},
                      {"label": "Apolipoprotein A1", "value": "126", "unit": "mg/dL",
                       "reference": "110 - 180"}]},
        ],
    },
    # ---- R15 -- back at target ---------------------------------------------
    {
        "collected": "2026-09-08 08:40", "reported": "2026-09-08 16:50",
        "lab": "shreeji", "layout_style": "two_column",
        "header_style": "stamp_and_signature", "uhid_label": "UHID",
        "doctor": TIWARI, "specimen": "Serum", "stamp": "VERIFIED<br>SHREEJI",
        "alias": 3, "traps": ["method_sub_line"],
        "sections": [
            {"panel": "IRON", "title": 3, "methods": True,
             "values": {"FERRITIN": 142, "IRON": 98, "TIBC": 328}},
            {"panel": "VITAMIN", "title": 4, "methods": True,
             "values": {"VIT_D": 34.2, "VIT_B12": 356, "FOLATE": 8.1}},
            {"heading": "Lipid Profile - Short",
             "rows": [{"code": "CHOL", "value": 114}, {"code": "TRIG", "value": 104},
                      {"code": "HDL", "value": 44}, {"code": "LDL"}]},
        ],
    },
]
