"""Patient 9 of 20 - Haematology. B12 deficiency anaemia, macrocytic, corrected.

Female, 66 at the first report, Chennai. Presents with haemoglobin 8.6, MCV 112 and B12 of
94 - a macrocytic anaemia from years of a strict vegetarian diet plus metformin. Monthly
injections bring B12 to 640 and the MCV back under 98 by 2023. The setback is late 2024:
injections were spaced out to six-monthly and stopped being given at all, B12 falls to 168
with the MCV climbing again, and a supervised course restores it.

Fourth wave of layouts arrives with this patient - a green-bar ledger sheet, panels in
cards the way a lab app exports them, a page typed on a manual machine, a ribbon
letterhead, units folded into the test name, and a prose interpretation block.
"""

from __future__ import annotations

PATIENT = {
    "number": 9,
    "name": "Rajalakshmi Srinivasan",
    "sex": "F",
    "dob": "1955-01-30",
    "uhid": "ARH/845027",
    "department": "Haematology",
    "city": "Chennai",
    "age_at_first": 66,
    "tracked": ["VIT_B12"],
    "brief": "B12 deficiency anaemia, macrocytic, corrected",
}


def check_arc(series):
    b12 = [v for _, v in series["VIT_B12"]]
    fails = []
    if not b12[0] < 150:
        fails.append(f"should start frankly deficient, B12 {b12[0]}")
    if not max(b12) > 400:
        fails.append(f"injections never corrected it, best {max(b12)}")
    if not any(b12[j] < 200 for j in range(3, len(b12))):
        fails.append("no relapse after the injections were spaced out")
    if not b12[-1] > 300:
        fails.append(f"should end replete, B12 {b12[-1]}")
    return fails


LABS = {
    "marina": {
        "abbr": "MDL", "acc_style": 0,
        "name": "Marina Diagnostic Labs",
        "name_local": "மெரினா டயக்னாஸ்டிக் லேப்ஸ்",
        "addr": "Royapettah High Road, Chennai 600014",
        "addr_local": "ராயப்பேட்டை நெடுஞ்சாலை, சென்னை 600014",
        "city": "Chennai",
        "phone": "044 2811 4420",
        "accred": "NABL Accredited (MC-1187) | ISO 15189:2012",
        "path": {"name": "Dr. Meenakshi Sundaram", "qual": "MD (Pathology)",
                 "regn": "TNMC 2004/02/3308", "scrawl": "M Sundaram"},
    },
    "adyar": {
        "abbr": "APC", "acc_style": 2,
        "name": "Adyar Path Care",
        "name_local": "அடையாறு பாத் கேர்",
        "addr": "Sardar Patel Road, Adyar, Chennai 600020",
        "addr_local": "சர்தார் படேல் சாலை, அடையாறு, சென்னை 600020",
        "city": "Chennai",
        "phone": "044 2445 9910",
        "accred": "NABL Accredited (M-3390)",
        "path": {"name": "Dr. Karthik Ramanathan", "qual": "MBBS, MD (Path.)",
                 "regn": "TNMC 2010/11/7761", "scrawl": "K Ramanathan"},
    },
    "arogya": {
        "abbr": "ARH", "acc_style": 1,
        "name": "Arogya Speciality Hospital Laboratory",
        "name_local": "ஆரோக்கிய சிறப்பு மருத்துவமனை ஆய்வகம்",
        "addr": "Anna Nagar West, Chennai 600040",
        "addr_local": "அண்ணா நகர் மேற்கு, சென்னை 600040",
        "city": "Chennai",
        "phone": "044 2626 7000",
        "accred": "Department of Laboratory Medicine, Haematology Division",
        "path": {"name": "Dr. Vasanthi Natarajan", "qual": "MD, DM (Haematology)",
                 "regn": "TNMC 1997/06/0921", "scrawl": "V Natarajan"},
    },
}

IYER = "Dr. Suresh Iyer, MBBS, MD, DM (Clinical Haematology)"
FRANCIS = "Dr. Anita Francis, MBBS, MD (General Medicine)"
BALAJI = "Dr. R. Balaji, MBBS, MD (Medicine)"

B12_LEGEND = [
    ("Vitamin B12 - interpretation", "Vitamin B12 pg/mL"),
    ("Below 200", "Deficient"),
    ("200 - 300", "Borderline, correlate with homocysteine"),
    ("Above 300", "Replete"),
]

# Weight recovers as the anaemia corrects and appetite returns. Blood pressure
# is unremarkable; there is one febrile visit in 2023 with a chest infection.
HEIGHT_CM = 151.0

VITALS = {
    1: {"weight_kg": 48.2, "bp": "128/78", "spo2": 97, "temp_f": 98.2,
        "context": "Breathless on the stairs for months, tongue sore, tingling feet."},
    2: {"weight_kg": 48.9, "bp": "126/78", "spo2": 98, "temp_f": 98.4,
        "context": "Four weekly B12 injections given. Feeling stronger."},
    3: {"weight_kg": 50.4, "bp": "124/76", "spo2": 98, "temp_f": 98.2,
        "context": "Monthly injections. Haemoglobin rising."},
    4: {"weight_kg": 51.8, "bp": "126/78", "spo2": 98, "temp_f": 98.6,
        "context": "Neuropathy improving, walking without support."},
    5: {"weight_kg": 52.6, "bp": "124/76", "spo2": 97, "temp_f": 101.4,
        "context": "Chest infection, febrile. Counts checked while unwell."},
    6: {"weight_kg": 53.2, "bp": "122/76", "spo2": 98, "temp_f": 98.4,
        "context": "Recovered. Annual review package."},
    7: {"weight_kg": 54.0, "bp": "124/78", "spo2": 99, "temp_f": 98.2,
        "context": "Best she has felt in years. Injections spaced to three-monthly."},
    8: {"weight_kg": 53.6, "bp": "126/78", "spo2": 98, "temp_f": 98.4,
        "context": "Injections spaced further, to six-monthly."},
    9: {"weight_kg": 52.4, "bp": "128/80", "spo2": 97, "temp_f": 98.6,
        "context": "Two doses missed. Tiredness returning."},
    10: {"weight_kg": 51.2, "bp": "130/80", "spo2": 97, "temp_f": 98.2,
         "context": "Relapse confirmed. Loading course restarted under supervision."},
    11: {"weight_kg": 51.9, "bp": "128/78", "spo2": 98, "temp_f": 98.4,
         "context": "Responding again. Nurse-administered injections arranged."},
    12: {"weight_kg": 52.8, "bp": "126/78", "spo2": 98, "temp_f": 98.2,
         "context": "Indices back to normal."},
    13: {"weight_kg": 53.4, "bp": "124/76", "spo2": 99, "temp_f": 98.4,
         "context": "Single confirmatory B12 before the annual visit."},
    14: {"weight_kg": 54.2, "bp": "124/76", "spo2": 98, "temp_f": 98.6,
         "context": "Annual review. Stable on a fixed injection schedule."},
    15: {"weight_kg": 54.6, "bp": "122/74", "spo2": 99, "temp_f": 98.2,
         "context": "Well. Two-yearly follow-up agreed."},
}

REPORTS = [
    # ---- R01 -- presentation ------------------------------------------------
    {
        "collected": "2021-10-22 09:20", "reported": "2021-10-22 18:50",
        "lab": "arogya", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Hospital No",
        "doctor": IYER, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["legend_lines", "text_result"],
        "interpretation": "Macrocytic anaemia with a low serum B12 and a hypersegmented "
                          "neutrophil picture on the smear. Folate is adequate. Suggest "
                          "parenteral B12 replacement and review at six weeks.",
        "sections": [
            {"panel": "CBC", "title": 0, "drop": ["ANC", "ALC", "MPV"],
             "values": {"HGB": 8.6, "RBC": 2.42, "PCV": 27.1, "MCV": 112.0, "MCH": 35.5,
                        "MCHC": 31.7, "RDW": 18.6, "WBC": 3800, "NEUT_PCT": 52,
                        "LYMPH_PCT": 38, "MONO_PCT": 7, "EOS_PCT": 2, "BASO_PCT": 1,
                        "PLT": 142000}},
            {"panel": "VITAMIN", "title": 0, "legend": B12_LEGEND,
             "values": {"VIT_D": 16.4, "VIT_B12": 94, "FOLATE": 8.2}},
            {"heading": "Peripheral Smear",
             "rows": [{"code": "PERIPH_SMEAR",
                       "value": "Macrocytic red cells with anisopoikilocytosis. "
                                "Hypersegmented neutrophils seen. Platelets reduced.",
                       "trap": "text_result"},
                      {"code": "RETIC", "value": 0.6, "flag": "L"}]},
        ],
    },
    # ---- R02 -- loading course ----------------------------------------------
    {
        "collected": "2021-12-20 09:50", "reported": "2021-12-20 15:30",
        "lab": "marina", "layout_style": "ledger_ruled",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": IYER, "specimen": "Whole blood (EDTA), Serum",
        "alias": 1, "traps": ["unit_in_label"],
        "sections": [
            {"heading": "Haematology Follow-up",
             "rows": [{"code": "HGB", "value": 9.4, "flag": "L"},
                      {"code": "MCV", "value": 106.4, "flag": "H"},
                      {"code": "RETIC", "value": 4.8, "flag": "H"},
                      {"code": "VIT_B12", "value": 286},
                      {"code": "PLT", "value": 186000}]},
        ],
    },
    # ---- R03 -- monthly injections ------------------------------------------
    {
        "collected": "2022-04-11 08:45", "reported": "2022-04-11 17:10",
        "lab": "adyar", "layout_style": "kv_header_table",
        "header_style": "bilingual_header", "uhid_label": "Reg. No",
        "doctor": FRANCIS, "specimen": "Serum",
        "alias": 2, "traps": ["footnote_marker", "method_sub_line"],
        "footnotes": [("1", "Sample drawn before the next scheduled injection.")],
        "sections": [
            {"panel": "THYROID", "title": 0, "drop": ["FT3", "ANTI_TPO"], "methods": True,
             "values": {"TSH": 4.12, "T3_TOTAL": 96, "T4_TOTAL": 7.8, "FT4": 1.04}},
            {"heading": "Vitamin Assay",
             "rows": [{"code": "VIT_B12", "value": 412, "marker": "1"},
                      {"code": "FOLATE", "value": 9.4},
                      {"label": "Homocysteine", "value": "14.8", "unit": "umol/L",
                       "reference": "5.0 - 15.0"}]},
        ],
    },
    # ---- R04 -- neuropathy improving ----------------------------------------
    {
        "collected": "2022-09-06 09:15", "reported": "2022-09-06 16:40",
        "lab": "marina", "layout_style": "two_column",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": IYER, "specimen": "Serum, Urine (midstream)",
        "alias": 3, "traps": ["sno_column"],
        "sections": [
            {"panel": "KFT", "title": 1,
             "values": {"CREAT": 0.82, "UREA": 30, "UA": 4.8}},
            {"panel": "URINE_ROUTINE", "title": 1, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.0, "UR_SPGR": 1.016,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 3, "UR_RBC": 1, "UR_EPITH": 4}},
            {"heading": "Vitamin B12",
             "rows": [{"code": "VIT_B12", "value": 526}]},
        ],
    },
    # ---- R05 -- chest infection ---------------------------------------------
    {
        "collected": "2023-02-14 19:30", "reported": "2023-02-14 23:15",
        "lab": "arogya", "layout_style": "typewriter_manual",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": BALAJI, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["no_reference_column", "text_result"],
        "sections": [
            {"heading": "Emergency Counts",
             "rows": [{"code": "HGB", "value": 10.8, "flag": "L"},
                      {"code": "WBC", "value": 14600, "flag": "H"},
                      {"code": "NEUT_PCT", "value": 82, "flag": "H"},
                      {"code": "PLT", "value": 322000},
                      {"code": "CRP", "value": 86.4, "flag": "H"},
                      {"code": "MP", "value": "Not Detected", "trap": "text_result"}]},
        ],
    },
    # ---- R06 -- annual review -----------------------------------------------
    {
        "collected": "2023-07-25 07:55", "reported": "2023-07-25 19:40",
        "lab": "marina", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Patient ID",
        "doctor": IYER, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["merged_panel_heading", "text_result", "method_sub_line"],
        "note": "Annual review package for a patient on B12 replacement.",
        "sections": [
            {"panel": "CBC", "title": 2, "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "values": {"HGB": 12.2, "RBC": 4.06, "PCV": 37.2, "MCV": 91.6, "MCH": 30.0,
                        "WBC": 6200, "NEUT_PCT": 58, "LYMPH_PCT": 32, "MONO_PCT": 6,
                        "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 236000}},
            {"panel": "LIPID", "title": 2, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 198, "TRIG": 146, "HDL": 48}},
            {"panels": ["LFT", "ELECTROLYTES"], "heading": "Biochemistry Screen",
             "trap": "merged_panel_heading",
             "drop": ["GGT", "AG_RATIO", "GLOB", "BILI_I", "CA_ION", "MG"],
             "values": {"BILI_T": 0.7, "BILI_D": 0.2, "ALT": 20, "AST": 24, "ALP": 84,
                        "PROT_T": 6.9, "ALB": 3.9,
                        "NA": 139, "K": 4.4, "CL": 102, "CA": 9.0, "PHOS": 3.6}},
            {"panel": "IRON", "title": 3, "drop": ["UIBC"], "methods": True,
             "values": {"FERRITIN": 64, "IRON": 78, "TIBC": 344}},
            {"panel": "VITAMIN", "title": 3, "methods": True,
             "values": {"VIT_D": 26.8, "VIT_B12": 640, "FOLATE": 11.2}},
            {"heading": "Other",
             "rows": [{"code": "BLOOD_GROUP", "value": "A Positive", "trap": "text_result"},
                      {"code": "HBA1C", "value": 6.4}]},
        ],
    },
    # ---- R07 -- injections spaced to three-monthly --------------------------
    {
        "collected": "2024-01-16 09:05", "reported": "2024-01-16 16:20",
        "lab": "adyar", "layout_style": "clean_table",
        "header_style": "barcode_header", "uhid_label": "Reg. No",
        "doctor": FRANCIS, "specimen": "Serum",
        "alias": 2, "traps": ["prev_value_column", "sparse_panel"],
        "sections": [
            {"panel": "THYROID", "title": 3, "drop": ["T3_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel",
             "prev": {"TSH": "4.12 (11/04/2022)"},
             "values": {"TSH": 3.68, "T4_TOTAL": 8.4, "FT4": 1.12}},
            {"panel": "DIABETES", "title": 1, "drop": ["GLU_R", "INSULIN_F"],
             "prev": {"HBA1C": "6.4 (25/07/2023)"},
             "values": {"GLU_F": 118, "GLU_PP": 164, "HBA1C": 6.5}},
            {"heading": "Vitamin B12",
             "prev": {"VIT_B12": "640 (25/07/2023)"},
             "rows": [{"code": "VIT_B12", "value": 486}]},
        ],
    },
    # ---- R08 -- spaced to six-monthly ---------------------------------------
    {
        "collected": "2024-06-28 08:50", "reported": "2024-06-28 15:10",
        "lab": "marina", "layout_style": "thermal_slip",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": FRANCIS, "specimen": "Serum",
        "alias": 3, "traps": ["no_reference_column"],
        "sections": [
            {"heading": "Vitamin B12",
             "rows": [{"code": "VIT_B12", "value": 322}]},
        ],
    },
    # ---- R09 -- doses missed ------------------------------------------------
    {
        "collected": "2024-12-05 09:35", "reported": "2024-12-05 17:25",
        "lab": "arogya", "layout_style": "ledger_ruled",
        "header_style": "two_line_ribbon", "uhid_label": "Hospital No",
        "doctor": IYER, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["unit_in_label", "abnormal_shaded"],
        "interpretation": "Rising mean cell volume with a falling B12 in a patient who has "
                          "missed two scheduled injections. The picture is of early "
                          "recurrence rather than a new diagnosis.",
        "sections": [
            {"heading": "Haemogram",
             "rows": [{"code": "HGB", "value": 10.9, "flag": "L"},
                      {"code": "RBC", "value": 3.44, "flag": "L"},
                      {"code": "PCV", "value": 33.6, "flag": "L"},
                      {"code": "MCV", "value": 97.7},
                      {"code": "RDW", "value": 15.8, "flag": "H"},
                      {"code": "PLT", "value": 198000}]},
            {"heading": "Vitamin Assay",
             "rows": [{"code": "VIT_B12", "value": 216, "flag": "L"},
                      {"code": "FOLATE", "value": 7.8}]},
        ],
    },
    # ---- R10 -- relapse confirmed -------------------------------------------
    {
        "collected": "2025-04-22 08:30", "reported": "2025-04-22 18:05",
        "lab": "arogya", "layout_style": "poor_scan",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": IYER, "specimen": "Whole blood (EDTA), Serum",
        "alias": 1, "traps": ["legend_lines", "text_result"],
        "stamp": "RESTART<br>LOADING DOSE",
        "sections": [
            {"panel": "VITAMIN", "title": 4, "legend": B12_LEGEND,
             "values": {"VIT_D": 22.4, "VIT_B12": 168, "FOLATE": 6.4}},
            {"heading": "Haematology",
             "rows": [{"code": "HGB", "value": 10.2, "flag": "L"},
                      {"code": "MCV", "value": 101.4, "flag": "H"},
                      {"code": "PERIPH_SMEAR",
                       "value": "Occasional macrocytes and hypersegmented neutrophils.",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R11 -- responding again --------------------------------------------
    {
        "collected": "2025-09-13 09:10", "reported": "2025-09-13 16:35",
        "lab": "adyar", "layout_style": "boxed_panels",
        "header_style": "letterhead_logo_left", "uhid_label": "Reg. No",
        "doctor": IYER, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["method_sub_line", "flag_as_words"],
        "sections": [
            {"panel": "HORMONES", "title": 0, "drop": ["TESTO_T"], "methods": True,
             "values": {"CORTISOL_AM": 14.2, "PROLACTIN": 11.6, "PTH": 68.4}},
            {"heading": "Vitamin B12",
             "rows": [{"code": "VIT_B12", "value": 384},
                      {"code": "RETIC", "value": 3.4, "flag": "H"}]},
        ],
    },
    # ---- R12 -- indices normal ----------------------------------------------
    {
        "collected": "2026-01-30 08:40", "reported": "2026-01-30 17:00",
        "lab": "marina", "layout_style": "clean_table",
        "header_style": "stamp_and_signature", "uhid_label": "Patient ID",
        "doctor": FRANCIS, "specimen": "Whole blood (EDTA), Serum",
        "alias": 3, "traps": ["not_reported"], "stamp": "HAEMATOLOGY<br>REVIEWED",
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 4,
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.5, "UR_SPGR": 1.014,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 4, "UR_RBC": 1, "UR_EPITH": 5, "MICROALB": 18,
                        "ACR": 22}},
            {"heading": "Haemogram",
             "rows": [{"code": "HGB", "value": 12.0}, {"code": "MCV", "value": 91.0},
                      {"code": "WBC", "value": 6000}, {"code": "PLT", "value": 228000},
                      {"code": "RDW", "value": 13.8}]},
            {"panel": "IRON", "title": 0, "drop": ["TSAT"],
             "values": {"FERRITIN": 58, "IRON": 74, "TIBC": 352},
             "extra_rows": [
                 {"label": "Transferrin", "value": "Not Reported", "unit": "mg/dL",
                  "reference": "200 - 360", "trap": "not_reported"},
             ]},
            {"heading": "Vitamin B12",
             "rows": [{"code": "VIT_B12", "value": 512}]},
        ],
    },
    # ---- R13 -- one confirmatory assay --------------------------------------
    {
        "collected": "2026-04-18 09:45", "reported": "2026-04-18 13:20",
        "lab": "adyar", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": FRANCIS, "specimen": "Serum",
        "alias": 0, "traps": ["no_header_row"],
        "sections": [
            {"heading": "Vitamin B12 - Repeat",
             "rows": [{"code": "VIT_B12", "value": 468}]},
        ],
    },
    # ---- R14 -- annual review, two pages ------------------------------------
    {
        "collected": "2026-07-09 07:40", "reported": "2026-07-09 20:20",
        "lab": "marina", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": IYER, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["ratio_no_code", "footnote_marker"],
        "page_break_after": 3,
        "footnotes": [("1", "Injection schedule: 1000 mcg hydroxocobalamin every two "
                            "months, nurse administered.")],
        "sections": [
            {"panel": "CBC", "title": 5,
             "values": {"HGB": 12.6, "RBC": 4.18, "PCV": 38.0, "MCV": 90.9, "MCH": 30.1,
                        "MCHC": 33.2, "RDW": 13.2, "WBC": 6400, "NEUT_PCT": 58,
                        "LYMPH_PCT": 32, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 242000, "MPV": 9.6}},
            {"panel": "LIPID", "title": 4,
             "values": {"CHOL": 186, "TRIG": 132, "HDL": 50}},
            {"panel": "DIABETES", "title": 4, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 112, "GLU_PP": 156, "HBA1C": 6.3}},
            {"panel": "LFT", "title": 2,
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 19, "AST": 22, "ALP": 82,
                        "GGT": 22, "PROT_T": 7.0, "ALB": 4.0}},
            {"panel": "KFT", "title": 4,
             "values": {"CREAT": 0.86, "UREA": 32, "UA": 5.0}},
            {"heading": "Vitamin and Derived",
             "rows": [{"code": "VIT_B12", "value": 534, "marker": "1"},
                      {"label": "Methylmalonic Acid", "value": "0.24", "unit": "umol/L",
                       "reference": "0.08 - 0.56"},
                      {"label": "Neutrophil - Lymphocyte Ratio", "value": "1.8",
                       "unit": "", "reference": "1.0 - 3.0", "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R15 -- discharged to two-yearly follow-up --------------------------
    {
        "collected": "2026-09-12 08:55", "reported": "2026-09-12 16:45",
        "lab": "arogya", "layout_style": "mixed_print_hand",
        "header_style": "two_line_ribbon", "uhid_label": "Hospital No",
        "doctor": IYER, "specimen": "Serum",
        "alias": 2, "traps": ["method_sub_line"],
        "sections": [
            {"heading": "Vitamin Assay", "methods": True,
             "rows": [{"code": "VIT_D", "value": 34.6}, {"code": "VIT_B12", "value": 496},
                      {"code": "FOLATE", "value": 12.4}]},
            {"panel": "ELECTROLYTES", "title": 4, "drop": ["CA_ION", "MG"],
             "values": {"NA": 140, "K": 4.2, "CL": 103, "CA": 9.2, "PHOS": 3.4}},
            {"heading": "Noted at the clinic", "hand_addendum": True,
             "rows": [{"code": "HGB", "value": 12.8}, {"code": "MCV", "value": 90.2}]},
        ],
    },
]
