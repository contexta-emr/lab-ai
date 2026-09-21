"""Patient 18 of 20 - Oncology follow-up. Post-treatment monitoring, counts recovering.

Female, 55 at the first report, Visakhapatnam. Six cycles of adjuvant chemotherapy for
breast cancer finished a month before the first report, and the record is the recovery
that follows: white count 2.1 rising to 5.9 over eighteen months, haemoglobin 9.4 to 12.4,
platelets back above 200,000, and quarterly tumour markers that stay normal.

The setback is February 2024 - febrile neutropenia during a late course of antibiotics for
a dental abscess, white count 1.4 with an absolute neutrophil count of 460, admitted for
48 hours. After that the counts settle and the last two years are uneventful.

Tumour markers here are CA 15-3 and CEA, neither of which has a code in the Contexta
vocabulary, so the key records a blank code for both. The roster nominates PSA for this
group; it is a prostate assay and is not printed for a woman.
"""

from __future__ import annotations

PATIENT = {
    "number": 18,
    "name": "Vijayalakshmi Appalaraju",
    "sex": "F",
    "dob": "1966-02-17",
    "uhid": "SGO/573910",
    "department": "Oncology Follow-up",
    "city": "Visakhapatnam",
    "age_at_first": 55,
    "tracked": ["WBC"],
    "brief": "Post-treatment monitoring, counts recovering",
}


def check_arc(series):
    wbc = [v for _, v in series["WBC"]]
    fails = []
    if not wbc[0] < 3500:
        fails.append(f"should start suppressed after chemotherapy, got {wbc[0]}")
    if not max(wbc) > 5000:
        fails.append(f"marrow never recovers, best {max(wbc)}")
    if not min(wbc) < 2000:
        fails.append("no neutropenic episode anywhere in the series")
    if not wbc[-1] > 4000:
        fails.append(f"should end with a normal count, got {wbc[-1]}")
    return fails


LABS = {
    "sagar": {
        "abbr": "SGO", "acc_style": 1,
        "name": "Sagar Oncology Centre Laboratory",
        "name_local": "సాగర్ ఆంకాలజీ సెంటర్ ప్రయోగశాల",
        "addr": "Beach Road, Visakhapatnam 530017",
        "addr_local": "బీచ్ రోడ్, విశాఖపట్నం 530017",
        "city": "Visakhapatnam",
        "phone": "0891 273 5500",
        "accred": "Department of Laboratory Medicine, Medical Oncology",
        "path": {"name": "Dr. Yamini Chowdary", "qual": "MD, DNB (Pathology)",
                 "regn": "APMC 2002/05/1483", "scrawl": "Y Chowdary"},
    },
    "vizag": {
        "abbr": "VDL", "acc_style": 0,
        "name": "Vizag Diagnostic Labs",
        "name_local": "వైజాగ్ డయాగ్నస్టిక్ ల్యాబ్స్",
        "addr": "Dwaraka Nagar, Visakhapatnam 530016",
        "addr_local": "ద్వారకా నగర్, విశాఖపట్నం 530016",
        "city": "Visakhapatnam",
        "phone": "0891 256 8820",
        "accred": "NABL Accredited (MC-4471) | ISO 15189:2012",
        "path": {"name": "Dr. Srinivas Pothuri", "qual": "MD (Pathology)",
                 "regn": "APMC 2010/09/6617", "scrawl": "S Pothuri"},
    },
    "gajuwaka": {
        "abbr": "GPL", "acc_style": 3,
        "name": "Gajuwaka Path Lab",
        "name_local": "గాజువాక ప్యాత్ ల్యాబ్",
        "addr": "Gajuwaka Junction, Visakhapatnam 530026",
        "addr_local": "గాజువాక జంక్షన్, విశాఖపట్నం 530026",
        "city": "Visakhapatnam",
        "phone": "0891 251 4430",
        "accred": "NABL Accredited (M-8891)",
        "path": {"name": "Dr. Kavitha Rani", "qual": "MBBS, MD (Path.)",
                 "regn": "APMC 2013/12/9948", "scrawl": "K Rani"},
    },
}

RAJU = "Dr. P. Sudhakar Raju, MBBS, MD, DM (Medical Oncology)"
SIREESHA = "Dr. Sireesha Varma, MBBS, MD (Medicine)"
NAIDU = "Dr. Venkat Naidu, MBBS, MS (Surgical Oncology)"

ANC_LEGEND = [
    ("Absolute neutrophil count - neutropenia grading", "ANC /uL"),
    ("Above 1500", "Normal"),
    ("1000 - 1500", "Mild neutropenia"),
    ("500 - 999", "Moderate neutropenia"),
    ("Below 500", "Severe neutropenia, admit if febrile"),
]

# Weight comes back slowly after chemotherapy, then holds. The February 2024
# admission is the only febrile visit and the only low saturation.
HEIGHT_CM = 152.0

VITALS = {
    1: {"weight_kg": 48.6, "bp": "112/72", "spo2": 97, "temp_f": 98.4,
        "context": "One month after the sixth cycle. Tired, hair regrowing."},
    2: {"weight_kg": 49.8, "bp": "114/74", "spo2": 98, "temp_f": 98.2,
        "context": "Counts recovering. Started on letrozole."},
    3: {"weight_kg": 51.4, "bp": "116/74", "spo2": 98, "temp_f": 98.6,
        "context": "Three-monthly review. Eating better, walking daily."},
    4: {"weight_kg": 53.0, "bp": "118/76", "spo2": 98, "temp_f": 98.4,
        "context": "First annual surveillance. Mammogram clear."},
    5: {"weight_kg": 54.2, "bp": "118/76", "spo2": 99, "temp_f": 98.2,
        "context": "Well. Joint aches from letrozole, managed with exercise."},
    6: {"weight_kg": 55.0, "bp": "120/78", "spo2": 98, "temp_f": 98.4,
        "context": "Counts fully recovered for the first time."},
    7: {"weight_kg": 55.6, "bp": "120/76", "spo2": 98, "temp_f": 98.6,
        "context": "Three-monthly review, markers normal."},
    8: {"weight_kg": 53.8, "bp": "102/62", "spo2": 95, "temp_f": 102.8,
        "context": "Febrile with a dental abscess. Neutropenic, admitted."},
    9: {"weight_kg": 54.2, "bp": "112/70", "spo2": 97, "temp_f": 99.2,
        "context": "Second day of admission. Count rising on filgrastim."},
    10: {"weight_kg": 55.4, "bp": "118/76", "spo2": 98, "temp_f": 98.4,
         "context": "Six weeks after discharge. Abscess drained and healed."},
    11: {"weight_kg": 56.2, "bp": "120/78", "spo2": 98, "temp_f": 98.2,
         "context": "Second annual surveillance. Imaging clear."},
    12: {"weight_kg": 56.8, "bp": "120/78", "spo2": 99, "temp_f": 98.6,
         "context": "Well. Bone density checked on letrozole."},
    13: {"weight_kg": 57.0, "bp": "118/76", "spo2": 98, "temp_f": 98.4,
         "context": "Single confirmatory white count before the annual visit."},
    14: {"weight_kg": 57.4, "bp": "118/76", "spo2": 98, "temp_f": 98.2,
         "context": "Third annual surveillance. Five years disease free approaching."},
    15: {"weight_kg": 57.8, "bp": "116/74", "spo2": 99, "temp_f": 98.4,
         "context": "Well. Moving to yearly follow-up with the surgeon."},
}

REPORTS = [
    # ---- R01 -- one month after the last cycle -------------------------------
    {
        "collected": "2021-10-21 09:10", "reported": "2021-10-21 17:50",
        "lab": "sagar", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": RAJU, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["legend_lines", "abnormal_shaded"],
        "damage": ["aged", "fold"],
        "interpretation": "Pancytopenia consistent with recent chemotherapy. No "
                          "transfusion is required at these levels; repeat in six weeks "
                          "and expect recovery.",
        "sections": [
            {"panel": "CBC", "title": 0, "legend": ANC_LEGEND,
             "values": {"HGB": 9.4, "RBC": 3.24, "PCV": 28.8, "MCV": 88.9, "MCH": 29.0,
                        "MCHC": 32.6, "RDW": 15.8, "WBC": 2100, "NEUT_PCT": 42,
                        "LYMPH_PCT": 48, "MONO_PCT": 7, "EOS_PCT": 2, "BASO_PCT": 1,
                        "PLT": 118000, "MPV": 10.4}},
        ],
    },
    # ---- R02 -- counts recovering ---------------------------------------------
    {
        "collected": "2022-01-13 08:50", "reported": "2022-01-13 16:20",
        "lab": "vizag", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Patient ID",
        "doctor": RAJU, "specimen": "Whole blood (EDTA), Serum",
        "alias": 1, "traps": ["unit_in_label"],
        "sections": [
            {"panel": "LFT", "title": 0, "drop": ["GGT", "BILI_I"],
             "values": {"BILI_T": 0.7, "BILI_D": 0.2, "ALT": 34, "AST": 30, "ALP": 92,
                        "PROT_T": 6.8, "ALB": 3.8}},
            {"heading": "Haematology and Markers",
             "rows": [{"code": "WBC", "value": 3200, "flag": "L"},
                      {"code": "HGB", "value": 10.2, "flag": "L"},
                      {"code": "PLT", "value": 164000},
                      {"label": "CA 15-3", "value": "18.4", "unit": "U/mL",
                       "reference": "< 30.0"},
                      {"label": "CEA (Carcinoembryonic Antigen)", "value": "2.6",
                       "unit": "ng/mL", "reference": "< 5.0"}]},
        ],
    },
    # ---- R03 -- three-monthly review -------------------------------------------
    {
        "collected": "2022-06-09 09:30", "reported": "2022-06-09 15:40",
        "lab": "gajuwaka", "layout_style": "ledger_ruled",
        "header_style": "bilingual_header", "uhid_label": "Reg. No",
        "doctor": SIREESHA, "specimen": "Whole blood (EDTA), Serum",
        "alias": 2, "traps": ["range_split_columns"],
        "damage": ["dark", "fold"],
        "note": "Photographed and sent by the family for the oncology file.",
        "sections": [
            {"panel": "THYROID", "title": 0, "drop": ["FT3", "ANTI_TPO"],
             "values": {"TSH": 3.42, "T3_TOTAL": 104, "T4_TOTAL": 8.2, "FT4": 1.12}},
            {"heading": "Haematology",
             "rows": [{"code": "WBC", "value": 4100},
                      {"code": "HGB", "value": 11.0, "flag": "L"},
                      {"code": "PLT", "value": 198000}]},
        ],
    },
    # ---- R04 -- first annual surveillance --------------------------------------
    {
        "collected": "2022-11-17 07:50", "reported": "2022-11-17 19:10",
        "lab": "sagar", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Hospital No",
        "doctor": RAJU, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 3, "traps": ["merged_panel_heading", "text_result", "method_sub_line"],
        "note": "Annual surveillance package.",
        "sections": [
            {"panel": "CBC", "title": 2,
             "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW", "MCH", "BASO_PCT", "EOS_PCT"],
             "values": {"HGB": 11.6, "RBC": 3.92, "PCV": 35.2, "MCV": 89.8,
                        "WBC": 4800, "NEUT_PCT": 52, "LYMPH_PCT": 38, "MONO_PCT": 6,
                        "PLT": 214000}},
            {"panel": "LIPID", "title": 2,
             "drop": ["NON_HDL", "LDL_HDL_RATIO", "CHOL_HDL_RATIO", "VLDL"],
             "values": {"CHOL": 204, "TRIG": 148, "HDL": 54}},
            {"panels": ["LFT", "KFT"], "heading": "Biochemistry - Liver and Renal",
             "trap": "merged_panel_heading",
             "drop": ["GGT", "AG_RATIO", "GLOB", "BILI_I", "BUN"],
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 28, "AST": 26, "ALP": 96,
                        "PROT_T": 7.0, "ALB": 4.0,
                        "CREAT": 0.74, "UREA": 26, "UA": 4.8}},
            {"panel": "VITAMIN", "title": 2, "methods": True,
             "values": {"VIT_D": 16.4, "VIT_B12": 322, "FOLATE": 7.6}},
            {"panel": "IRON", "title": 1, "drop": ["UIBC"],
             "values": {"FERRITIN": 48, "IRON": 68, "TIBC": 368}},
            {"panel": "DIABETES", "title": 1, "drop": ["GLU_R", "INSULIN_F", "EAG"],
             "trap": "sparse_panel",
             "values": {"GLU_F": 94, "GLU_PP": 126, "HBA1C": 5.4}},
            {"heading": "Markers and Other",
             "rows": [{"label": "CA 15-3", "value": "16.2", "unit": "U/mL",
                       "reference": "< 30.0"},
                      {"code": "BLOOD_GROUP", "value": "A Positive",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R05 -- well, joint aches ----------------------------------------------
    {
        "collected": "2023-04-27 09:00", "reported": "2023-04-27 16:30",
        "lab": "vizag", "layout_style": "cut_sheet",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": SIREESHA, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 0, "traps": ["test_code_column"],
        "damage": ["aged", "stain"],
        "sections": [
            {"heading": "Bone and Counts",
             "lab_codes": {"CA": "B-20", "PHOS": "B-21", "ALP": "L-30", "WBC": "H-10"},
             "rows": [{"code": "CA", "value": 9.4}, {"code": "PHOS", "value": 3.6},
                      {"code": "ALP", "value": 104, "flag": "H"},
                      {"code": "VIT_D", "value": 22.8, "flag": "L"},
                      {"code": "WBC", "value": 5200}]},
        ],
    },
    # ---- R06 -- counts fully recovered ------------------------------------------
    {
        "collected": "2023-10-12 09:20", "reported": "2023-10-12 16:50",
        "lab": "sagar", "layout_style": "thermal_slip",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": RAJU, "specimen": "Whole blood (EDTA)",
        "alias": 1, "traps": ["no_reference_column"],
        "sections": [
            {"heading": "Total Leucocyte Count",
             "rows": [{"code": "WBC", "value": 5900}]},
        ],
    },
    # ---- R07 -- three-monthly review --------------------------------------------
    {
        "collected": "2023-12-15 08:40", "reported": "2023-12-15 17:00",
        "lab": "gajuwaka", "layout_style": "landscape_wide",
        "header_style": "barcode_header", "uhid_label": "Reg. No",
        "doctor": RAJU, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["prev_value_column"],
        "damage": ["fold"],
        "sections": [
            {"heading": "Tumour Markers and Counts",
             "prev": {"WBC": "5900 (12/10/2023)", "HGB": "11.6 (17/11/2022)"},
             "rows": [{"label": "CA 15-3", "value": "14.8", "unit": "U/mL",
                       "reference": "< 30.0"},
                      {"label": "CEA (Carcinoembryonic Antigen)", "value": "2.2",
                       "unit": "ng/mL", "reference": "< 5.0"},
                      {"code": "WBC", "value": 5600},
                      {"code": "HGB", "value": 12.0}]},
        ],
    },
    # ---- R08 -- febrile neutropenia ---------------------------------------------
    {
        "collected": "2024-02-23 23:20", "reported": "2024-02-24 02:40",
        "lab": "sagar", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": RAJU, "specimen": "Whole blood (EDTA), Serum",
        "alias": 3, "traps": ["sno_column", "abnormal_shaded", "legend_lines"],
        "stamp": "CRITICAL<br>PHONED 02:25",
        "note": "Febrile neutropenia. Blood cultures taken and broad spectrum "
                "antibiotics started. Filgrastim given.",
        "sections": [
            {"heading": "Emergency Haemogram", "legend": ANC_LEGEND,
             "rows": [{"code": "HGB", "value": 10.8, "flag": "L"},
                      {"code": "WBC", "value": 1400, "flag": "L"},
                      {"code": "NEUT_PCT", "value": 33, "flag": "L"},
                      {"code": "LYMPH_PCT", "value": 56, "flag": "H"},
                      {"code": "ANC", "value": 462, "flag": "L"},
                      {"code": "PLT", "value": 142000, "flag": "L"}]},
            {"heading": "Sepsis Screen",
             "rows": [{"code": "CRP", "value": 164.0, "flag": "H"},
                      {"label": "Procalcitonin", "value": "2.86", "unit": "ng/mL",
                       "reference": "< 0.50", "flag": "H"}]},
        ],
    },
    # ---- R09 -- second day of admission -----------------------------------------
    {
        "collected": "2024-02-25 06:40", "reported": "2024-02-25 09:50",
        "lab": "sagar", "layout_style": "fax_header",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": RAJU, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["no_reference_column"],
        "note": "Faxed to the oncology ward at 09:55 hrs.",
        "sections": [
            {"heading": "Daily Counts",
             "rows": [{"code": "WBC", "value": 3400, "flag": "L"},
                      {"code": "ANC", "value": 2108},
                      {"code": "HGB", "value": 10.6, "flag": "L"},
                      {"code": "CRP", "value": 88.4, "flag": "H"}]},
        ],
    },
    # ---- R10 -- six weeks after discharge ---------------------------------------
    {
        "collected": "2024-04-06 09:15", "reported": "2024-04-06 16:10",
        "lab": "vizag", "layout_style": "kv_header_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": SIREESHA, "specimen": "Whole blood (EDTA), Serum, Urine",
        "alias": 1, "traps": ["text_result", "flag_as_words"],
        "damage": ["crop-right", "aged"],
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 1, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.0, "UR_SPGR": 1.018,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 3, "UR_RBC": 1, "UR_EPITH": 4}},
            {"panel": "ELECTROLYTES", "title": 4, "drop": ["CA_ION", "PHOS"],
             "values": {"NA": 139, "K": 4.0, "CL": 102, "CA": 9.4, "MG": 2.0}},
            {"heading": "Haematology and Culture",
             "rows": [{"code": "WBC", "value": 5100},
                      {"code": "HGB", "value": 11.8, "flag": "L"},
                      {"code": "URINE_CULTURE",
                       "value": "No growth after 48 hours of aerobic incubation.",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R11 -- second annual surveillance ---------------------------------------
    {
        "collected": "2024-11-23 08:20", "reported": "2024-11-23 17:40",
        "lab": "sagar", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Hospital No",
        "doctor": RAJU, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["text_result", "method_sub_line"],
        "damage": ["blur", "dark", "thumb"], "illegible": True,
        "note": "Copy photographed at the patient's home; a clean copy was requested "
                "from the records department.",
        "sections": [
            {"panel": "SEROLOGY", "title": 2, "drop": ["WIDAL", "DENGUE_NS1",
                                                       "DENGUE_IGM", "MP", "VDRL"],
             "methods": True,
             "values": {"HBSAG": "Non Reactive", "ANTI_HCV": "Non Reactive",
                        "HIV": "Non Reactive"},
             "row_traps": {"HBSAG": "text_result"}},
            {"heading": "Markers and Counts",
             "rows": [{"label": "CA 15-3", "value": "15.6", "unit": "U/mL",
                       "reference": "< 30.0"},
                      {"code": "WBC", "value": 5400},
                      {"code": "HGB", "value": 12.2}]},
        ],
    },
    # ---- R12 -- bone density year ------------------------------------------------
    {
        "collected": "2025-05-10 08:50", "reported": "2025-05-10 16:30",
        "lab": "gajuwaka", "layout_style": "typewriter_manual",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": SIREESHA, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 3, "traps": ["no_reference_column", "not_reported"],
        "damage": ["fold", "stain", "aged"],
        "sections": [
            {"panel": "ELECTROLYTES", "title": 2, "drop": ["CA_ION", "MG"],
             "values": {"NA": 140, "K": 4.2, "CL": 103, "CA": 9.6, "PHOS": 3.4}},
            {"panel": "THYROID", "title": 4, "drop": ["T3_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel",
             "values": {"TSH": 3.68, "T4_TOTAL": 8.6, "FT4": 1.16}},
            {"heading": "Bone and Counts",
             "rows": [{"code": "WBC", "value": 5700},
                      {"code": "VIT_D", "value": 28.4, "flag": "L"},
                      {"code": "PTH", "value": "Not Reported", "trap": "not_reported"},
                      {"label": "Beta CrossLaps (CTX)", "value": "0.54", "unit": "ng/mL",
                       "reference": "0.10 - 0.70"}]},
        ],
    },
    # ---- R13 -- one white count ---------------------------------------------------
    {
        "collected": "2025-11-18 09:40", "reported": "2025-11-18 13:20",
        "lab": "vizag", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Patient ID",
        "doctor": SIREESHA, "specimen": "Whole blood (EDTA)",
        "alias": 0, "traps": ["no_header_row"],
        "damage": ["scanborder"],
        "sections": [
            {"heading": "Total Leucocyte Count",
             "rows": [{"code": "WBC", "value": 5800}]},
        ],
    },
    # ---- R14 -- third annual surveillance, two pages ------------------------------
    {
        "collected": "2026-04-14 07:45", "reported": "2026-04-14 20:00",
        "lab": "sagar", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "Hospital No",
        "doctor": RAJU, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["footnote_marker", "ratio_no_code"],
        "page_break_after": 3,
        "footnotes": [("1", "Letrozole continues to year five. Bone density repeated "
                            "two-yearly while on treatment.")],
        "sections": [
            {"panel": "CBC", "title": 5,
             "values": {"HGB": 12.4, "RBC": 4.16, "PCV": 37.4, "MCV": 89.9, "MCH": 29.8,
                        "MCHC": 33.2, "RDW": 13.2, "WBC": 5900, "NEUT_PCT": 56,
                        "LYMPH_PCT": 34, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 232000, "MPV": 9.6}},
            {"panel": "LIPID", "title": 5,
             "values": {"CHOL": 212, "TRIG": 156, "HDL": 56}},
            {"panel": "DIABETES", "title": 5, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 96, "GLU_PP": 128, "HBA1C": 5.5}},
            {"panel": "LFT", "title": 5,
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 26, "AST": 24, "ALP": 98,
                        "GGT": 26, "PROT_T": 7.1, "ALB": 4.1},
             "row_traps": {"ALP": "footnote_marker"}},
            {"panel": "KFT", "title": 5,
             "values": {"CREAT": 0.72, "UREA": 25, "UA": 4.6}},
            {"heading": "Markers and Derived",
             "rows": [{"label": "CA 15-3", "value": "13.8", "unit": "U/mL",
                       "reference": "< 30.0"},
                      {"label": "CEA (Carcinoembryonic Antigen)", "value": "1.9",
                       "unit": "ng/mL", "reference": "< 5.0"},
                      {"label": "Neutrophil - Lymphocyte Ratio", "value": "1.6",
                       "unit": "", "reference": "1.0 - 3.0", "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R15 -- moving to yearly follow-up ----------------------------------------
    {
        "collected": "2026-09-02 08:45", "reported": "2026-09-02 16:20",
        "lab": "vizag", "layout_style": "mixed_print_hand",
        "header_style": "stamp_and_signature", "uhid_label": "Patient ID",
        "doctor": NAIDU, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["method_sub_line"], "stamp": "ONCOLOGY<br>SURVEILLANCE",
        "damage": ["fold", "aged"],
        "sections": [
            {"panel": "IRON", "title": 4, "methods": True,
             "values": {"FERRITIN": 82, "IRON": 88, "TIBC": 344}},
            {"panel": "URINE_ROUTINE", "title": 4, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.5, "UR_SPGR": 1.016,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 2, "UR_RBC": 0, "UR_EPITH": 3}},
            {"panel": "VITAMIN", "title": 4, "methods": True,
             "values": {"VIT_D": 32.6, "VIT_B12": 386, "FOLATE": 9.4}},
            {"heading": "Noted at the clinic", "hand_addendum": True,
             "rows": [{"code": "WBC", "value": 6100}, {"code": "HGB", "value": 12.5}]},
        ],
    },
]
