"""Patient 17 of 20 - Paediatrics. Thalassaemia trait, monitored, no progression.

Male, 9 at the first report and 14 at the last, Mysuru. Picked up when iron was given for
a "mild anaemia" that never corrected: haemoglobin 10.8 with an MCV of 64 and an HbA2 of
5.2 per cent - beta thalassaemia trait, not iron deficiency. The record is five years of
deliberately uneventful monitoring: haemoglobin between 10.4 and 11.6, MCV always under
72, ferritin normal once the unnecessary iron was stopped.

The near-setback is September 2024, when a different clinic restarted iron on the old
assumption and ferritin rose to 486 before it was stopped again. Nothing progresses; the
value of the case is that a trend line through it should be flat and a parser should not
confuse the persistently low MCV for deterioration.

Cardiac markers appear once, in 2025, for chest pain during a school sports day that
turned out to be musculoskeletal.
"""

from __future__ import annotations

PATIENT = {
    "number": 17,
    "name": "Kiran Gowda Shivakumar",
    "sex": "M",
    "dob": "2012-04-26",
    "uhid": "CHM/384051",
    "department": "Paediatrics",
    "city": "Mysuru",
    "age_at_first": 9,
    "tracked": ["HGB"],
    "brief": "Thalassaemia trait, monitored, no progression",
}


def check_arc(series):
    hgb = [v for _, v in series["HGB"]]
    fails = []
    if not all(9.8 <= v <= 12.2 for v in hgb):
        fails.append(f"trait should stay mildly anaemic throughout: {hgb}")
    if max(hgb) - min(hgb) > 1.6:
        fails.append("too much movement for a condition that does not progress")
    if len(hgb) < 8:
        fails.append("not enough points to show the flat line")
    return fails


LABS = {
    "chamundi": {
        "abbr": "CHM", "acc_style": 1,
        "name": "Chamundi Childrens Hospital Laboratory",
        "name_local": "ಚಾಮುಂಡಿ ಮಕ್ಕಳ ಆಸ್ಪತ್ರೆ ಪ್ರಯೋಗಾಲಯ",
        "addr": "JLB Road, Mysuru 570005",
        "addr_local": "ಜೆಎಲ್‌ಬಿ ರಸ್ತೆ, ಮೈಸೂರು 570005",
        "city": "Mysuru",
        "phone": "0821 242 6600",
        "accred": "Department of Laboratory Medicine, Paediatric Haematology",
        "path": {"name": "Dr. Shakuntala Rao", "qual": "MD, DNB (Pathology)",
                 "regn": "KMC 2003/06/1926", "scrawl": "S Rao"},
    },
    "kaveri_m": {
        "abbr": "KDM", "acc_style": 0,
        "name": "Kaveri Diagnostics Mysuru",
        "name_local": "ಕಾವೇರಿ ಡಯಾಗ್ನೋಸ್ಟಿಕ್ಸ್ ಮೈಸೂರು",
        "addr": "Saraswathipuram, Mysuru 570009",
        "addr_local": "ಸರಸ್ವತಿಪುರಂ, ಮೈಸೂರು 570009",
        "city": "Mysuru",
        "phone": "0821 251 3340",
        "accred": "NABL Accredited (MC-7756) | ISO 15189:2012",
        "path": {"name": "Dr. Nagaraj Hegde", "qual": "MD (Pathology)",
                 "regn": "KMC 2008/11/4482", "scrawl": "N Hegde"},
    },
    "mandya": {
        "abbr": "MPL", "acc_style": 3,
        "name": "Mandya Road Path Lab",
        "name_local": "ಮಂಡ್ಯ ರಸ್ತೆ ಪ್ಯಾಥ್ ಲ್ಯಾಬ್",
        "addr": "Bannimantap, Mysuru 570015",
        "addr_local": "ಬನ್ನಿಮಂಟಪ, ಮೈಸೂರು 570015",
        "city": "Mysuru",
        "phone": "0821 244 9917",
        "accred": "NABL Accredited (M-3327)",
        "path": {"name": "Dr. Latha Prasad", "qual": "MBBS, MD (Path.)",
                 "regn": "KMC 2014/08/8863", "scrawl": "L Prasad"},
    },
}

SHETTY = "Dr. Ramesh Shetty, MBBS, MD (Paediatrics)"
DEVI = "Dr. Asha Devi, MBBS, DCH"
KRISHNAMURTHY = "Dr. B. Krishnamurthy, MBBS, MD, DM (Paediatric Haematology)"

TRAIT_LEGEND = [
    ("HbA2 - beta thalassaemia trait", "HbA2 fraction"),
    ("2.2 - 3.5 %", "Normal"),
    ("3.6 - 4.0 %", "Borderline, repeat with iron studies"),
    ("Above 4.0 %", "Consistent with beta thalassaemia trait"),
]

# A boy growing normally: 132 cm at nine, 166 cm at fourteen. The trait does not
# hold him back, which is part of what the record is meant to show.
HEIGHT_CM = 132.0

VITALS = {
    1: {"height_cm": 132.0, "weight_kg": 27.4, "bp": "100/64", "spo2": 98, "temp_f": 98.4,
        "context": "Referred after iron syrup for six months failed to raise the count."},
    2: {"height_cm": 135.0, "weight_kg": 29.2, "bp": "102/66", "spo2": 99, "temp_f": 98.2,
        "context": "Electrophoresis confirms trait. Iron stopped, family counselled."},
    3: {"height_cm": 138.0, "weight_kg": 31.0, "bp": "102/66", "spo2": 98, "temp_f": 98.6,
        "context": "Well. Parents screened; mother also has the trait."},
    4: {"height_cm": 141.0, "weight_kg": 33.4, "bp": "104/68", "spo2": 99, "temp_f": 98.4,
        "context": "Annual check. Growing along his centile."},
    5: {"height_cm": 144.0, "weight_kg": 35.8, "bp": "106/68", "spo2": 98, "temp_f": 98.2,
        "context": "Playing school cricket, no exercise limitation."},
    6: {"height_cm": 148.0, "weight_kg": 38.6, "bp": "106/70", "spo2": 99, "temp_f": 98.4,
        "context": "Annual check. Counts unchanged, as expected."},
    7: {"height_cm": 152.0, "weight_kg": 41.4, "bp": "108/70", "spo2": 98, "temp_f": 98.6,
        "context": "Well. Reviewed at the request of the school medical officer."},
    8: {"height_cm": 155.0, "weight_kg": 44.0, "bp": "110/70", "spo2": 98, "temp_f": 98.4,
        "context": "Another clinic restarted iron for the low haemoglobin."},
    9: {"height_cm": 157.0, "weight_kg": 46.2, "bp": "110/72", "spo2": 99, "temp_f": 98.2,
        "context": "Chest pain on sports day. Cardiac assessment requested by the school."},
    10: {"height_cm": 159.0, "weight_kg": 48.6, "bp": "112/72", "spo2": 98, "temp_f": 98.6,
         "context": "Ferritin high from the unnecessary iron. Stopped again."},
    11: {"height_cm": 161.0, "weight_kg": 50.8, "bp": "114/72", "spo2": 99, "temp_f": 98.4,
         "context": "Iron stores falling back towards normal."},
    12: {"height_cm": 163.0, "weight_kg": 53.0, "bp": "114/74", "spo2": 98, "temp_f": 98.2,
         "context": "Well. Pre-university medical form completed."},
    13: {"height_cm": 164.0, "weight_kg": 54.6, "bp": "116/74", "spo2": 99, "temp_f": 98.4,
         "context": "Single confirmatory haemoglobin before the annual review."},
    14: {"height_cm": 165.0, "weight_kg": 56.2, "bp": "116/74", "spo2": 98, "temp_f": 98.6,
         "context": "Annual review. Genetic counselling discussed for later life."},
    15: {"height_cm": 166.0, "weight_kg": 57.4, "bp": "118/76", "spo2": 99, "temp_f": 98.2,
         "context": "Discharged to two-yearly follow-up."},
}

REPORTS = [
    # ---- R01 -- the referral --------------------------------------------------
    {
        "collected": "2021-10-18 09:40", "reported": "2021-10-18 17:20",
        "lab": "chamundi", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": SHETTY, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["legend_lines", "paediatric_range"],
        "damage": ["aged", "fold"],
        "interpretation": "Microcytosis out of proportion to the haemoglobin, with normal "
                          "iron stores and a raised HbA2. This is beta thalassaemia trait; "
                          "iron therapy is not indicated and should be stopped.",
        "sections": [
            {"panel": "CBC", "title": 0, "drop": ["ANC", "ALC", "MPV"],
             "trap": "paediatric_range",
             "values": {"HGB": 10.8, "RBC": 5.42, "PCV": 34.6, "MCV": 63.8, "MCH": 19.9,
                        "MCHC": 31.2, "RDW": 14.2, "WBC": 7400, "NEUT_PCT": 48,
                        "LYMPH_PCT": 42, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 318000}},
            {"heading": "Haemoglobin Studies", "legend": TRAIT_LEGEND,
             "rows": [{"label": "HbA2 (HPLC)", "value": "5.2", "unit": "%",
                       "reference": "2.2 - 3.5", "flag": "H"},
                      {"label": "HbF (HPLC)", "value": "1.4", "unit": "%",
                       "reference": "< 2.0"},
                      {"code": "FERRITIN", "value": 58}]},
        ],
    },
    # ---- R02 -- trait confirmed ------------------------------------------------
    {
        "collected": "2022-01-29 09:00", "reported": "2022-01-29 15:40",
        "lab": "kaveri_m", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Patient ID",
        "doctor": KRISHNAMURTHY, "specimen": "Whole blood (EDTA), Serum",
        "alias": 1, "traps": ["unit_in_label"],
        "sections": [
            {"panel": "IRON", "title": 0,
             "values": {"FERRITIN": 62, "IRON": 84, "TIBC": 332}},
            {"panel": "THYROID", "title": 2, "drop": ["T3_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel",
             "values": {"TSH": 3.10, "T4_TOTAL": 9.6, "FT4": 1.30}},
            {"heading": "Haematology",
             "rows": [{"code": "HGB", "value": 11.0, "flag": "L"},
                      {"code": "MCV", "value": 64.2, "flag": "L"},
                      {"code": "RDW", "value": 13.8},
                      {"code": "PERIPH_SMEAR",
                       "value": "Microcytic hypochromic red cells with target forms. "
                                "No abnormal cells.", "trap": "text_result"}]},
        ],
    },
    # ---- R03 -- family screened ------------------------------------------------
    {
        "collected": "2022-07-23 09:20", "reported": "2022-07-23 16:00",
        "lab": "mandya", "layout_style": "ledger_ruled",
        "header_style": "bilingual_header", "uhid_label": "Reg. No",
        "doctor": DEVI, "specimen": "Serum, Urine (midstream)",
        "alias": 2, "traps": ["range_split_columns", "sample_type_row"],
        "damage": ["dark"],
        "note": "Photographed by the family for the school records.",
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 0, "sample_row": "Urine, Midstream",
             "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.0, "UR_SPGR": 1.016,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 2, "UR_RBC": 0, "UR_EPITH": 2}},
            {"heading": "Haemoglobin",
             "rows": [{"code": "HGB", "value": 10.9, "flag": "L"},
                      {"code": "MCV", "value": 63.4, "flag": "L"}]},
        ],
    },
    # ---- R04 -- annual check ---------------------------------------------------
    {
        "collected": "2023-01-14 08:00", "reported": "2023-01-14 18:40",
        "lab": "chamundi", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Hospital No",
        "doctor": SHETTY, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 3, "traps": ["merged_panel_heading", "text_result", "paediatric_range"],
        "note": "Annual paediatric review package.",
        "sections": [
            {"panel": "CBC", "title": 2, "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "trap": "paediatric_range",
             "values": {"HGB": 11.2, "RBC": 5.58, "PCV": 35.8, "MCV": 64.2, "MCH": 20.1,
                        "WBC": 7000, "NEUT_PCT": 50, "LYMPH_PCT": 40, "MONO_PCT": 6,
                        "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 302000}},
            {"panel": "LIPID", "title": 2, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 146, "TRIG": 72, "HDL": 50}},
            {"panels": ["LFT", "KFT"], "heading": "Biochemistry Screen",
             "trap": "merged_panel_heading",
             "drop": ["GGT", "AG_RATIO", "GLOB", "BILI_I", "BUN", "EGFR"],
             "values": {"BILI_T": 1.1, "BILI_D": 0.3, "ALT": 22, "AST": 28, "ALP": 264,
                        "PROT_T": 7.2, "ALB": 4.4,
                        "CREAT": 0.54, "UREA": 24, "UA": 4.2}},
            {"panel": "VITAMIN", "title": 2,
             "values": {"VIT_D": 21.4, "VIT_B12": 392, "FOLATE": 9.8}},
            {"heading": "Other",
             "rows": [{"code": "BLOOD_GROUP", "value": "B Positive", "trap": "text_result"},
                      {"code": "HBA1C", "value": 5.0}]},
        ],
    },
    # ---- R05 -- playing cricket -----------------------------------------------
    {
        "collected": "2023-08-05 09:30", "reported": "2023-08-05 14:50",
        "lab": "kaveri_m", "layout_style": "thermal_slip",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": DEVI, "specimen": "Whole blood (EDTA)",
        "alias": 0, "traps": ["no_reference_column"],
        "sections": [
            {"heading": "Haemoglobin",
             "rows": [{"code": "HGB", "value": 11.4, "flag": "L"}]},
        ],
    },
    # ---- R06 -- annual check, cropped -----------------------------------------
    {
        "collected": "2024-01-20 08:50", "reported": "2024-01-20 17:10",
        "lab": "mandya", "layout_style": "kv_header_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Reg. No",
        "doctor": SHETTY, "specimen": "Whole blood (EDTA), Serum",
        "alias": 1, "traps": ["paediatric_range", "flag_as_words"],
        "damage": ["crop-right", "aged"],
        "sections": [
            {"panel": "THYROID", "title": 0, "drop": ["FT3", "ANTI_TPO"],
             "values": {"TSH": 2.86, "T3_TOTAL": 146, "T4_TOTAL": 9.8, "FT4": 1.28}},
            {"heading": "Haematology", "trap": "paediatric_range",
             "rows": [{"code": "HGB", "value": 11.1, "flag": "L"},
                      {"code": "MCV", "value": 65.0, "flag": "L"},
                      {"code": "FERRITIN", "value": 66}]},
        ],
    },
    # ---- R07 -- school medical officer review ---------------------------------
    {
        "collected": "2024-06-08 09:10", "reported": "2024-06-08 16:20",
        "lab": "kaveri_m", "layout_style": "typewriter_manual",
        "header_style": "minimal_text_top", "uhid_label": "Patient ID",
        "doctor": DEVI, "specimen": "Whole blood (EDTA), Serum",
        "alias": 2, "traps": ["no_reference_column"],
        "damage": ["fold", "stain"],
        "sections": [
            {"heading": "Haemogram and Iron",
             "rows": [{"code": "HGB", "value": 11.3, "flag": "L"},
                      {"code": "MCV", "value": 64.8, "flag": "L"},
                      {"code": "RBC", "value": 5.62},
                      {"code": "FERRITIN", "value": 74},
                      {"label": "G6PD (Quantitative)", "value": "9.4", "unit": "U/g Hb",
                       "reference": "6.8 - 13.0"}]},
        ],
    },
    # ---- R08 -- iron restarted elsewhere ---------------------------------------
    {
        "collected": "2024-09-14 09:00", "reported": "2024-09-14 15:30",
        "lab": "mandya", "layout_style": "cut_sheet",
        "header_style": "centred_title_only", "uhid_label": "Reg. No",
        "doctor": DEVI, "specimen": "Serum",
        "alias": 3, "traps": ["test_code_column"],
        "damage": ["aged"],
        "sections": [
            {"heading": "Iron Studies",
             "lab_codes": {"FERRITIN": "B-40", "IRON": "B-41", "TIBC": "B-42",
                           "TSAT": "B-43"},
             "rows": [{"code": "FERRITIN", "value": 264, "flag": "H"},
                      {"code": "IRON", "value": 148},
                      {"code": "TIBC", "value": 288},
                      {"code": "TSAT"}]},
        ],
    },
    # ---- R09 -- chest pain on sports day ---------------------------------------
    {
        "collected": "2025-02-07 16:40", "reported": "2025-02-07 20:15",
        "lab": "chamundi", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": KRISHNAMURTHY, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 0, "traps": ["method_sub_line", "sno_column"],
        "note": "Chest pain during school sports. Cardiac markers not raised; pain "
                "reproducible on palpation and attributed to the chest wall.",
        "sections": [
            {"panel": "CARDIAC", "title": 0, "methods": True,
             "values": {"TROP_I": 0.008, "CPK_MB": 16, "NT_PROBNP": 46}},
            {"panel": "KFT", "title": 1, "drop": ["EGFR", "BUN"],
             "values": {"CREAT": 0.68, "UREA": 26, "UA": 4.8}},
            {"panel": "ELECTROLYTES", "title": 1, "drop": ["CA_ION", "MG", "PHOS"],
             "values": {"NA": 139, "K": 4.3, "CL": 102, "CA": 9.6}},
            {"heading": "Haematology",
             "rows": [{"code": "HGB", "value": 11.0, "flag": "L"},
                      {"code": "MCV", "value": 65.4, "flag": "L"}]},
        ],
    },
    # ---- R10 -- ferritin high from the unnecessary iron ------------------------
    {
        "collected": "2025-05-19 08:40", "reported": "2025-05-19 16:50",
        "lab": "kaveri_m", "layout_style": "glossy_marketing",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": KRISHNAMURTHY, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 1, "traps": ["abnormal_shaded"],
        "damage": ["blur"],
        "interpretation": "Ferritin is raised because iron was restarted without "
                          "indication. In thalassaemia trait iron is not deficient and "
                          "supplementation risks overload. Stop the supplement.",
        "sections": [
            {"panel": "IRON", "title": 3,
             "values": {"FERRITIN": 486, "IRON": 172, "TIBC": 264}},
            {"heading": "Haematology",
             "rows": [{"code": "HGB", "value": 11.2, "flag": "L"},
                      {"code": "MCV", "value": 64.6, "flag": "L"}]},
        ],
    },
    # ---- R11 -- stores falling back --------------------------------------------
    {
        "collected": "2025-10-27 09:25", "reported": "2025-10-27 16:10",
        "lab": "mandya", "layout_style": "dot_matrix_pinfeed",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": DEVI, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["range_split_columns"],
        "damage": ["fold", "aged"],
        "sections": [
            {"heading": "Iron and Counts",
             "rows": [{"code": "FERRITIN", "value": 218, "flag": "H"},
                      {"code": "HGB", "value": 11.5, "flag": "L"},
                      {"code": "MCV", "value": 66.0, "flag": "L"},
                      {"code": "PLT", "value": 288000}]},
        ],
    },
    # ---- R12 -- pre-university medical -----------------------------------------
    {
        "collected": "2026-02-16 08:30", "reported": "2026-02-16 17:20",
        "lab": "chamundi", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Hospital No",
        "doctor": SHETTY, "specimen": "Whole blood (EDTA), Serum, Urine",
        "alias": 3, "traps": ["text_result", "paediatric_range"],
        "damage": ["crop-bottom", "dark"],
        "sections": [
            {"heading": "Haemogram", "trap": "paediatric_range",
             "rows": [{"code": "HGB", "value": 11.6, "flag": "L"},
                      {"code": "RBC", "value": 5.74, "flag": "H"},
                      {"code": "PCV", "value": 37.2},
                      {"code": "MCV", "value": 64.8, "flag": "L"},
                      {"code": "WBC", "value": 6800},
                      {"code": "PLT", "value": 296000}]},
            {"panel": "DIABETES", "title": 3, "drop": ["GLU_R", "INSULIN_F", "EAG"],
             "trap": "sparse_panel",
             "values": {"GLU_F": 90, "GLU_PP": 118, "HBA1C": 5.2}},
            {"panel": "URINE_ROUTINE", "title": 3, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.5, "UR_SPGR": 1.018,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 2, "UR_RBC": 0, "UR_EPITH": 2}},
            {"heading": "Other",
             "rows": [{"code": "BLOOD_GROUP", "value": "B Positive",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R13 -- one haemoglobin -------------------------------------------------
    {
        "collected": "2026-05-11 09:45", "reported": "2026-05-11 13:15",
        "lab": "kaveri_m", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Patient ID",
        "doctor": DEVI, "specimen": "Whole blood (EDTA)",
        "alias": 0, "traps": ["no_header_row"],
        "damage": ["scanborder", "aged"],
        "sections": [
            {"heading": "Haemoglobin",
             "rows": [{"code": "HGB", "value": 11.4, "flag": "L"}]},
        ],
    },
    # ---- R14 -- annual review, two pages ---------------------------------------
    {
        "collected": "2026-07-28 07:50", "reported": "2026-07-28 19:40",
        "lab": "chamundi", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "Hospital No",
        "doctor": KRISHNAMURTHY, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["ratio_no_code", "footnote_marker", "paediatric_range"],
        "page_break_after": 3,
        "footnotes": [("1", "Genetic counselling will be offered before marriage; partner "
                            "screening is the key measure in trait.")],
        "sections": [
            {"panel": "CBC", "title": 5, "trap": "paediatric_range",
             "values": {"HGB": 11.5, "RBC": 5.70, "PCV": 36.8, "MCV": 64.6, "MCH": 20.2,
                        "MCHC": 31.3, "RDW": 13.6, "WBC": 6900, "NEUT_PCT": 55,
                        "LYMPH_PCT": 35, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 292000, "MPV": 9.0}},
            {"panel": "LIPID", "title": 5, "drop": ["LDL_HDL_RATIO"],
             "values": {"CHOL": 152, "TRIG": 86, "HDL": 48}},
            {"panel": "DIABETES", "title": 5, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 88, "GLU_PP": 114, "HBA1C": 5.1}},
            {"panel": "LFT", "title": 4,
             "values": {"BILI_T": 1.2, "BILI_D": 0.3, "ALT": 24, "AST": 26, "ALP": 218,
                        "GGT": 18, "PROT_T": 7.4, "ALB": 4.6}},
            {"panel": "ELECTROLYTES", "title": 4, "drop": ["CA_ION", "MG"],
             "values": {"NA": 140, "K": 4.4, "CL": 103, "CA": 9.8, "PHOS": 4.6}},
            {"heading": "Haemoglobin Studies and Derived",
             "rows": [{"label": "HbA2 (HPLC)", "value": "5.0", "unit": "%",
                       "reference": "2.2 - 3.5", "flag": "H", "marker": "1"},
                      {"label": "Mentzer Index (MCV / RBC)", "value": "11.3", "unit": "",
                       "reference": "< 13 suggests thalassaemia trait",
                       "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R15 -- discharged to two-yearly follow-up -----------------------------
    {
        "collected": "2026-09-16 08:55", "reported": "2026-09-16 16:00",
        "lab": "mandya", "layout_style": "mixed_print_hand",
        "header_style": "stamp_and_signature", "uhid_label": "Reg. No",
        "doctor": KRISHNAMURTHY, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["method_sub_line"], "stamp": "PAEDIATRIC<br>DISCHARGED",
        "damage": ["fold"],
        "sections": [
            {"panel": "IRON", "title": 5, "methods": True,
             "values": {"FERRITIN": 96, "IRON": 102, "TIBC": 318}},
            {"panel": "VITAMIN", "title": 5, "methods": True,
             "values": {"VIT_D": 26.8, "VIT_B12": 428, "FOLATE": 10.2}},
            {"heading": "Noted at the clinic", "hand_addendum": True,
             "rows": [{"code": "HGB", "value": 11.4}, {"code": "MCV", "value": 65.2}]},
        ],
    },
]
