"""Patient 4 of 20 - Paediatrics. Iron-deficiency anaemia in a child, treated and resolving.

Female, 6 at the first report and 11 at the last, Kochi. Presents pale and tired with
haemoglobin 8.4 and ferritin 4; oral iron brings her to 11.8 over eighteen months. The
setback is 2024: iron was stopped early and she relapses to 9.4 before a second, completed
course. She ends at 12.4 with normal indices.

Everything here is judged against paediatric reference ranges, which is the point of this
case - catalog.ref returns the child band for an under-18, so a haemoglobin of 11.6 is
flagged normal for her and would be low for an adult man. She grows through the series:
115 cm and 19.4 kg at six, 143 cm and 34.2 kg at eleven, so the vitals file carries a
height per visit rather than one constant.

Hormones here are the short-stature and rickets workup - morning cortisol and PTH.
Prolactin and testosterone are not appropriate to a prepubertal girl and are not printed.
"""

from __future__ import annotations

PATIENT = {
    "number": 4,
    "name": "Aadhya Menon",
    "sex": "F",
    "dob": "2015-06-30",
    "uhid": "SACH/108842",
    "department": "Paediatrics",
    "city": "Kochi",
    "age_at_first": 6,
    "tracked": ["HGB"],
    "brief": "Iron-deficiency anaemia in a child, treated and resolving",
}


def check_arc(series):
    hgb = [v for _, v in series["HGB"]]
    fails = []
    if not hgb[0] < 9.0:
        fails.append(f"should start anaemic, Hb {hgb[0]}")
    if not hgb[-1] >= 11.5:
        fails.append(f"should end corrected, Hb {hgb[-1]}")
    if not any(hgb[j] < max(hgb[:j]) - 1.5 for j in range(1, len(hgb))):
        fails.append("no relapse when iron was stopped")
    return fails


LABS = {
    "nirmala": {
        "abbr": "NDL", "acc_style": 0,
        "name": "Nirmala Diagnostics",
        "addr": "Chittoor Road, Ernakulam, Kochi 682011",
        "city": "Kochi",
        "phone": "0484 238 4410",
        "accred": "NABL Accredited (MC-3355) | ISO 15189:2012",
        "path": {"name": "Dr. Leela Krishnan", "qual": "MD (Pathology)",
                 "regn": "TCMC 2006/03/4412", "scrawl": "L Krishnan"},
    },
    "backwater": {
        "abbr": "BPL", "acc_style": 3,
        "name": "Backwater Path Lab",
        "addr": "Vytilla Junction, Kochi 682019",
        "city": "Kochi",
        "phone": "0484 230 7788",
        "accred": "NABL Accredited (M-7240)",
        "path": {"name": "Dr. Thomas P. Mathew", "qual": "MBBS, MD (Path.)",
                 "regn": "TCMC 2012/07/8801", "scrawl": "T Mathew"},
    },
    "alphonsa": {
        "abbr": "SACH", "acc_style": 1,
        "name": "St. Alphonsa Childrens Hospital Laboratory",
        "addr": "Kaloor, Kochi 682017",
        "city": "Kochi",
        "phone": "0484 240 1200",
        "accred": "Paediatric Laboratory Services",
        "path": {"name": "Dr. Anila Varghese", "qual": "MD, DCP (Pathology)",
                 "regn": "TCMC 2004/10/2267", "scrawl": "A Varghese"},
    },
}

PILLAI = "Dr. Rajesh Pillai, MBBS, MD (Paediatrics)"
SUSAN = "Dr. Susan Abraham, MBBS, DCH"
NAIR = "Dr. Meera Nair, MBBS, MD, DM (Paediatric Haematology)"

ANAEMIA_LEGEND = [
    ("Haemoglobin - WHO cut-offs for children", "Age group"),
    ("6 - 59 months", "Anaemia below 11.0 g/dL"),
    ("5 - 11 years", "Anaemia below 11.5 g/dL"),
    ("12 - 14 years", "Anaemia below 12.0 g/dL"),
]

# She grows about 5.5 cm a year. Weight follows, apart from the year she was unwell.
# One febrile visit in 2024 - a viral illness that brought the relapse to light.
HEIGHT_CM = 115.0

VITALS = {
    1: {"height_cm": 115.0, "weight_kg": 19.4, "bp": "96/60", "spo2": 98, "temp_f": 98.4,
        "context": "Brought in pale and tired, poor appetite for months."},
    2: {"height_cm": 117.5, "weight_kg": 19.8, "bp": "96/62", "spo2": 99, "temp_f": 98.2,
        "context": "Six weeks of oral iron. Tolerating syrup well."},
    3: {"height_cm": 120.0, "weight_kg": 20.6, "bp": "98/62", "spo2": 98, "temp_f": 98.6,
        "context": "Appetite improving, less irritable at school."},
    4: {"height_cm": 122.5, "weight_kg": 21.8, "bp": "98/64", "spo2": 99, "temp_f": 98.4,
        "context": "Haemoglobin rising steadily. Iron continued."},
    5: {"height_cm": 125.0, "weight_kg": 22.9, "bp": "100/64", "spo2": 98, "temp_f": 98.2,
        "context": "Well. Deworming repeated as per protocol."},
    6: {"height_cm": 128.0, "weight_kg": 24.4, "bp": "100/66", "spo2": 99, "temp_f": 98.4,
        "context": "Annual school health check. Growing normally."},
    7: {"height_cm": 130.5, "weight_kg": 25.6, "bp": "102/66", "spo2": 98, "temp_f": 98.6,
        "context": "Iron stopped by the family once she looked well."},
    8: {"height_cm": 133.0, "weight_kg": 26.8, "bp": "102/68", "spo2": 98, "temp_f": 98.4,
        "context": "Pallor noticed again at a school medical camp."},
    9: {"height_cm": 134.5, "weight_kg": 26.2, "bp": "104/66", "spo2": 97, "temp_f": 101.6,
        "context": "Febrile viral illness. Bloods repeated while unwell."},
    10: {"height_cm": 136.0, "weight_kg": 27.4, "bp": "104/68", "spo2": 98, "temp_f": 98.6,
         "context": "Recovered. Second course of iron started and supervised."},
    11: {"height_cm": 138.0, "weight_kg": 29.1, "bp": "106/68", "spo2": 99, "temp_f": 98.2,
         "context": "Responding well. Compliance checked at each visit."},
    12: {"height_cm": 139.5, "weight_kg": 30.6, "bp": "106/70", "spo2": 98, "temp_f": 98.4,
         "context": "Haemoglobin back above 11.5."},
    13: {"height_cm": 141.0, "weight_kg": 32.0, "bp": "108/70", "spo2": 99, "temp_f": 98.6,
         "context": "Single confirmatory haemoglobin before stopping iron."},
    14: {"height_cm": 142.0, "weight_kg": 33.4, "bp": "108/70", "spo2": 98, "temp_f": 98.4,
         "context": "Annual check. Stores replenished this time."},
    15: {"height_cm": 143.0, "weight_kg": 34.2, "bp": "110/70", "spo2": 99, "temp_f": 98.2,
         "context": "Discharged from haematology follow-up."},
}

REPORTS = [
    # ---- R01 -- first presentation -----------------------------------------
    {
        "collected": "2021-10-12 09:30", "reported": "2021-10-12 17:10",
        "lab": "alphonsa", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": PILLAI, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["legend_lines", "paediatric_range"],
        "note": "Reference intervals are age-specific for paediatric patients.",
        "sections": [
            {"panel": "CBC", "title": 0, "drop": ["ANC", "ALC", "MPV"],
             "legend": ANAEMIA_LEGEND, "trap": "paediatric_range",
             "values": {"HGB": 8.4, "RBC": 4.02, "PCV": 27.8, "MCV": 69.2, "MCH": 20.9,
                        "MCHC": 30.2, "RDW": 17.4, "WBC": 8200, "NEUT_PCT": 42,
                        "LYMPH_PCT": 48, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 418000}},
            {"heading": "Iron Studies",
             "rows": [{"code": "FERRITIN", "value": 4, "flag": "L"},
                      {"code": "IRON", "value": 22, "flag": "L"},
                      {"code": "TIBC", "value": 468, "flag": "H"},
                      {"code": "TSAT"}]},
        ],
    },
    # ---- R02 -- six weeks of iron ------------------------------------------
    {
        "collected": "2021-12-07 10:00", "reported": "2021-12-07 15:40",
        "lab": "nirmala", "layout_style": "minimal_lines",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": SUSAN, "specimen": "Whole blood (EDTA)",
        "alias": 1, "traps": ["unit_in_value_cell"],
        "sections": [
            {"heading": "Haemoglobin and Reticulocytes",
             "rows": [{"code": "HGB", "value": 9.6},
                      {"code": "RETIC", "value": 4.2, "flag": "H"},
                      {"code": "MCV", "value": 71.4}]},
        ],
    },
    # ---- R03 -- thyroid and coeliac screen ---------------------------------
    {
        "collected": "2022-04-18 09:15", "reported": "2022-04-18 16:50",
        "lab": "backwater", "layout_style": "kv_header_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Reg. No",
        "doctor": PILLAI, "specimen": "Serum",
        "alias": 2, "traps": ["sparse_panel", "footnote_marker"],
        "footnotes": [("1", "Anti-tTG requested to exclude coeliac disease as a cause of "
                            "refractory iron deficiency.")],
        "sections": [
            {"panel": "THYROID", "title": 1, "drop": ["FT3", "ANTI_TPO", "T3_TOTAL"],
             "trap": "sparse_panel",
             "values": {"TSH": 3.84, "T4_TOTAL": 9.2, "FT4": 1.28}},
            {"heading": "Additional Tests",
             "rows": [{"code": "HGB", "value": 10.4},
                      {"label": "Anti-tTG IgA (Tissue Transglutaminase)", "value": "3.2",
                       "unit": "U/mL", "reference": "< 20", "marker": "1"}]},
        ],
    },
    # ---- R04 -- responding --------------------------------------------------
    {
        "collected": "2022-09-05 09:45", "reported": "2022-09-05 16:20",
        "lab": "nirmala", "layout_style": "two_column",
        "header_style": "banner_with_qr", "uhid_label": "Patient ID",
        "doctor": SUSAN, "specimen": "Serum, Urine (midstream)",
        "alias": 3, "traps": ["sno_column"],
        "sections": [
            {"panel": "ELECTROLYTES", "title": 4, "drop": ["CA_ION", "MG"],
             "values": {"NA": 139, "K": 4.4, "CL": 103, "CA": 9.8, "PHOS": 5.1}},
            {"heading": "Haemoglobin",
             "rows": [{"code": "HGB", "value": 11.0}, {"code": "MCV", "value": 76.8},
                      {"code": "RDW", "value": 14.8}]},
        ],
    },
    # ---- R05 -- routine -----------------------------------------------------
    {
        "collected": "2023-02-20 08:50", "reported": "2023-02-20 15:15",
        "lab": "backwater", "layout_style": "carbon_copy",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": PILLAI, "specimen": "Serum",
        "alias": 0, "traps": ["range_with_unit", "method_sub_line", "paediatric_range"],
        "sections": [
            {"panel": "LFT", "title": 3, "methods": True, "drop": ["GGT", "BILI_I"],
             "trap": "paediatric_range",
             "values": {"BILI_T": 0.5, "BILI_D": 0.1, "ALT": 18, "AST": 26, "ALP": 246,
                        "PROT_T": 7.0, "ALB": 4.2}},
            {"panel": "LIPID", "title": 1, "drop": ["NON_HDL", "CHOL_HDL_RATIO",
                                                    "LDL_HDL_RATIO"],
             "values": {"CHOL": 152, "TRIG": 78, "HDL": 48}},
            {"heading": "Haemoglobin",
             "rows": [{"code": "HGB", "value": 11.4}]},
        ],
    },
    # ---- R06 -- annual school health check ---------------------------------
    {
        "collected": "2023-07-24 08:10", "reported": "2023-07-24 18:30",
        "lab": "alphonsa", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Hospital No",
        "doctor": PILLAI, "specimen": "Whole blood (EDTA), Serum, Urine",
        "alias": 1, "traps": ["merged_panel_heading", "text_result", "paediatric_range"],
        "note": "School health check package, paediatric reference intervals throughout.",
        "sections": [
            {"panel": "CBC", "title": 2, "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "trap": "paediatric_range",
             "values": {"HGB": 11.8, "RBC": 4.48, "PCV": 36.2, "MCV": 80.8, "MCH": 26.3,
                        "WBC": 7600, "NEUT_PCT": 44, "LYMPH_PCT": 46, "MONO_PCT": 6,
                        "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 322000}},
            {"panel": "IRON", "title": 3, "drop": ["UIBC"],
             "values": {"FERRITIN": 28, "IRON": 74, "TIBC": 366}},
            {"panels": ["LFT", "ELECTROLYTES"], "heading": "Biochemistry Screen",
             "trap": "merged_panel_heading",
             "drop": ["GGT", "AG_RATIO", "GLOB", "BILI_I", "CA_ION", "MG", "CL"],
             "values": {"BILI_T": 0.4, "BILI_D": 0.1, "ALT": 16, "AST": 24, "ALP": 238,
                        "PROT_T": 7.1, "ALB": 4.3,
                        "NA": 140, "K": 4.3, "CA": 9.9, "PHOS": 5.0}},
            {"panel": "VITAMIN", "title": 3,
             "values": {"VIT_D": 16.8, "VIT_B12": 342, "FOLATE": 8.4}},
            {"panel": "URINE_ROUTINE", "title": 2, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.5, "UR_SPGR": 1.015,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 2, "UR_RBC": 0, "UR_EPITH": 2}},
            {"heading": "Other",
             "rows": [{"code": "BLOOD_GROUP", "value": "B Positive", "trap": "text_result"},
                      {"label": "Stool Occult Blood", "value": "Negative", "unit": "",
                       "reference": "Negative", "trap": "text_result"}]},
        ],
    },
    # ---- R07 -- iron stopped by the family ---------------------------------
    {
        "collected": "2023-12-11 10:20", "reported": "2023-12-11 16:05",
        "lab": "nirmala", "layout_style": "clean_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": SUSAN, "specimen": "Serum, Urine (midstream)",
        "alias": 2, "traps": ["ambiguous_abbreviation"],
        "sections": [
            {"panel": "THYROID", "title": 3, "drop": ["ANTI_TPO"],
             "values": {"TSH": 3.22, "T3_TOTAL": 148, "T4_TOTAL": 9.6, "FT3": 3.8,
                        "FT4": 1.32}},
            {"panel": "URINE_ROUTINE", "title": 4, "drop": ["MICROALB", "ACR"],
             "labels": {"UR_PROT": "ALB"},
             "row_traps": {"UR_PROT": "ambiguous_abbreviation"},
             "values": {"UR_COLOUR": "Straw", "UR_PH": 6.0, "UR_SPGR": 1.018,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 3, "UR_RBC": 0, "UR_EPITH": 2}},
        ],
    },
    # ---- R08 -- relapse found at a camp ------------------------------------
    {
        "collected": "2024-06-08 09:00", "reported": "2024-06-08 15:30",
        "lab": "backwater", "layout_style": "minimal_lines",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": NAIR, "specimen": "Whole blood (EDTA), Serum",
        "alias": 3, "traps": ["not_reported", "paediatric_range"],
        "sections": [
            {"panel": "DIABETES", "title": 2, "drop": ["GLU_PP", "GLU_R", "EAG"],
             "values": {"GLU_F": 86, "HBA1C": 5.2, "INSULIN_F": "Not Reported"},
             "row_traps": {"INSULIN_F": "not_reported"}},
            {"heading": "Haematology", "trap": "paediatric_range",
             "rows": [{"code": "HGB", "value": 9.4, "flag": "L"},
                      {"code": "MCV", "value": 72.6, "flag": "L"},
                      {"code": "FERRITIN", "value": 9, "flag": "L"},
                      {"label": "HbA2 / HbF (Electrophoresis)",
                       "value": "HbA2 2.4 %, HbF 0.8 %", "unit": "",
                       "reference": "HbA2 2.2 - 3.5 %"}]},
        ],
    },
    # ---- R09 -- febrile illness ---------------------------------------------
    {
        "collected": "2024-09-19 19:40", "reported": "2024-09-19 23:10",
        "lab": "alphonsa", "layout_style": "poor_scan",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": PILLAI, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["text_result", "sno_column"],
        "stamp": "PAEDIATRIC<br>EMERGENCY",
        "note": "Febrile child, well hydrated. Dengue screen negative.",
        "sections": [
            {"heading": "Haemogram - Fever Workup",
             "rows": [{"code": "HGB", "value": 9.6, "flag": "L"},
                      {"code": "WBC", "value": 5400},
                      {"code": "NEUT_PCT", "value": 38},
                      {"code": "LYMPH_PCT", "value": 52},
                      {"code": "PLT", "value": 186000},
                      {"code": "PCV", "value": 30.4, "flag": "L"}]},
            {"heading": "Fever Screen",
             "rows": [{"code": "DENGUE_NS1", "value": "Negative", "trap": "text_result"},
                      {"code": "MP", "value": "Not Detected", "trap": "text_result"},
                      {"code": "CRP", "value": 18.4, "flag": "H"}]},
        ],
    },
    # ---- R10 -- second course started ---------------------------------------
    {
        "collected": "2025-01-23 09:35", "reported": "2025-01-23 16:00",
        "lab": "nirmala", "layout_style": "kv_header_table",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": NAIR, "specimen": "Serum",
        "alias": 1, "traps": ["method_sub_line"],
        "sections": [
            {"panel": "KFT", "title": 3, "drop": ["EGFR", "BUN"],
             "values": {"CREAT": 0.46, "UREA": 22, "UA": 3.8}},
            {"panel": "IRON", "title": 5, "methods": True,
             "values": {"FERRITIN": 11, "IRON": 38, "TIBC": 442}},
            {"panel": "VITAMIN", "title": 5, "methods": True,
             "values": {"VIT_D": 21.4, "VIT_B12": 368, "FOLATE": 9.1}},
            {"heading": "Haemoglobin",
             "rows": [{"code": "HGB", "value": 10.2, "flag": "L"}]},
        ],
    },
    # ---- R11 -- responding again --------------------------------------------
    {
        "collected": "2025-06-17 10:05", "reported": "2025-06-17 14:45",
        "lab": "backwater", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": SUSAN, "specimen": "Whole blood (EDTA)",
        "alias": 2, "traps": ["no_header_row"],
        "sections": [
            {"heading": "Haemoglobin",
             "rows": [{"code": "HGB", "value": 11.2, "flag": "L"}]},
        ],
    },
    # ---- R12 -- hormone workup for short stature ---------------------------
    {
        "collected": "2025-11-13 08:20", "reported": "2025-11-13 17:25",
        "lab": "alphonsa", "layout_style": "mixed_print_hand",
        "header_style": "stamp_and_signature", "uhid_label": "Hospital No",
        "doctor": NAIR, "specimen": "Serum", "stamp": "PAEDIATRIC<br>ENDOCRINE",
        "alias": 3, "traps": ["footnote_marker"],
        "footnotes": [("1", "Sample drawn at 08:20 hrs for the morning cortisol.")],
        "sections": [
            {"panel": "HORMONES", "title": 2, "drop": ["PROLACTIN", "TESTO_T"],
             "values": {"CORTISOL_AM": 12.6, "PTH": 52.4},
             "row_traps": {"CORTISOL_AM": "footnote_marker"}},
            {"heading": "Written in by the registrar", "hand_addendum": True,
             "rows": [{"code": "HGB", "value": 11.6}, {"code": "CA", "value": 9.7}]},
        ],
    },
    # ---- R13 -- one confirmatory test ---------------------------------------
    {
        "collected": "2026-02-26 09:50", "reported": "2026-02-26 13:20",
        "lab": "nirmala", "layout_style": "minimal_lines",
        "header_style": "minimal_text_top", "uhid_label": "Patient ID",
        "doctor": SUSAN, "specimen": "Whole blood (EDTA)",
        "alias": 0, "traps": ["paediatric_range"],
        "sections": [
            {"heading": "Haemoglobin", "trap": "paediatric_range",
             "rows": [{"code": "HGB", "value": 11.9}]},
        ],
    },
    # ---- R14 -- annual check, two pages --------------------------------------
    {
        "collected": "2026-06-10 08:05", "reported": "2026-06-10 19:15",
        "lab": "alphonsa", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "Hospital No",
        "doctor": PILLAI, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 2, "traps": ["paediatric_range", "ratio_no_code"],
        "page_break_after": 3,
        "sections": [
            {"panel": "CBC", "title": 5, "trap": "paediatric_range",
             "values": {"HGB": 12.2, "RBC": 4.62, "PCV": 37.4, "MCV": 81.0, "MCH": 26.4,
                        "MCHC": 32.6, "RDW": 13.6, "WBC": 7100, "NEUT_PCT": 48,
                        "LYMPH_PCT": 42, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 296000, "MPV": 9.2}},
            {"panel": "LIPID", "title": 4, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 148, "TRIG": 82, "HDL": 52}},
            {"panel": "DIABETES", "title": 4, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 88, "GLU_PP": 116, "HBA1C": 5.1}},
            {"panel": "KFT", "title": 2, "drop": ["EGFR"],
             "values": {"CREAT": 0.52, "UREA": 24, "UA": 4.1}},
            {"panel": "LFT", "title": 5,
             "values": {"BILI_T": 0.4, "BILI_D": 0.1, "ALT": 17, "AST": 22, "ALP": 284,
                        "GGT": 16, "PROT_T": 7.3, "ALB": 4.4}},
            {"heading": "Derived",
             "rows": [{"label": "Mentzer Index (MCV / RBC)", "value": "17.5", "unit": "",
                       "reference": "> 13 suggests iron deficiency",
                       "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R15 -- discharged from follow-up -----------------------------------
    {
        "collected": "2026-09-14 09:25", "reported": "2026-09-14 15:50",
        "lab": "backwater", "layout_style": "two_column",
        "header_style": "banner_with_qr", "uhid_label": "Reg. No",
        "doctor": NAIR, "specimen": "Whole blood (EDTA), Serum",
        "alias": 1, "traps": ["legend_lines"],
        "sections": [
            {"panel": "IRON", "title": 2,
             "values": {"FERRITIN": 42, "IRON": 88, "TIBC": 342}},
            {"heading": "Haemoglobin", "legend": ANAEMIA_LEGEND,
             "rows": [{"code": "HGB", "value": 12.4}, {"code": "MCV", "value": 82.6},
                      {"code": "RDW", "value": 13.2}]},
        ],
    },
]
