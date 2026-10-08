"""Patient 13 of 20 - Endocrinology. Prediabetes progressing to diabetes despite advice.

Male, 41 at the first report, Ludhiana. HbA1c 5.9 at a corporate check in 2021 with
advice, a pamphlet and no follow-up. It climbs through prediabetes year on year - 6.1,
6.3, 6.6 - and crosses into diabetes at 7.1 in 2025. Metformin is started late and the
last two readings improve only slightly, to 6.9. This is the case where nothing dramatic
happens and the trend is the entire finding.

The counterpoint is 2024, the one year he did lose weight and HbA1c fell to 6.2, before
the effort lapsed - that dip is the setback in reverse and a trend line has to survive it.

Fifth wave of layouts: continuous pin-feed stationery, a chain lab's glossy print, a
half-sheet with a cut line, an internal test-code column, and reference ranges split into
separate low and high columns.
"""

from __future__ import annotations

PATIENT = {
    "number": 13,
    "name": "Gurpreet Singh Sahni",
    "sex": "M",
    "dob": "1980-08-14",
    "uhid": "DMC/470913",
    "department": "Endocrinology",
    "city": "Ludhiana",
    "age_at_first": 41,
    "tracked": ["HBA1C"],
    "brief": "Prediabetes progressing to diabetes despite advice",
}


def check_arc(series):
    a1c = [v for _, v in series["HBA1C"]]
    fails = []
    if not 5.7 <= a1c[0] < 6.5:
        fails.append(f"should start in the prediabetes band, got {a1c[0]}")
    if not max(a1c) >= 7.0:
        fails.append(f"never crosses into diabetes, peak {max(a1c)}")
    if not a1c[-1] > a1c[0]:
        fails.append("ends no worse than it started, which is not this case")
    if not any(a1c[j] < a1c[j - 1] - 0.3 for j in range(1, len(a1c))):
        fails.append("no dip for the year he lost weight")
    return fails


LABS = {
    "satluj": {
        "abbr": "SDC", "acc_style": 0,
        "name": "Satluj Diagnostic Centre",
        "name_local": "ਸਤਲੁਜ ਡਾਇਗਨੌਸਟਿਕ ਸੈਂਟਰ",
        "addr": "Sarabha Nagar, Ludhiana 141001",
        "addr_local": "ਸਰਾਭਾ ਨਗਰ, ਲੁਧਿਆਣਾ 141001",
        "city": "Ludhiana",
        "phone": "0161 246 7730",
        "accred": "NABL Accredited (MC-3318) | ISO 15189:2012",
        "path": {"name": "Dr. Harpreet Kaur Gill", "qual": "MD (Pathology)",
                 "regn": "PMC 2006/05/2214", "scrawl": "H K Gill"},
    },
    "punjab": {
        "abbr": "PPL", "acc_style": 3,
        "name": "Punjab Path Line",
        "name_local": "ਪੰਜਾਬ ਪੈਥ ਲਾਈਨ",
        "addr": "Model Town Extension, Ludhiana 141002",
        "addr_local": "ਮਾਡਲ ਟਾਊਨ ਐਕਸਟੈਂਸ਼ਨ, ਲੁਧਿਆਣਾ 141002",
        "city": "Ludhiana",
        "phone": "0161 277 1140",
        "accred": "NABL Accredited (M-8846)",
        "path": {"name": "Dr. Vikram Bedi", "qual": "MBBS, MD (Path.)",
                 "regn": "PMC 2012/09/6690", "scrawl": "V Bedi"},
    },
    "doaba": {
        "abbr": "DMC", "acc_style": 2,
        "name": "Doaba Medical Centre Laboratory",
        "name_local": "ਦੋਆਬਾ ਮੈਡੀਕਲ ਸੈਂਟਰ ਪ੍ਰਯੋਗਸ਼ਾਲਾ",
        "addr": "Ferozepur Road, Ludhiana 141012",
        "addr_local": "ਫਿਰੋਜ਼ਪੁਰ ਰੋਡ, ਲੁਧਿਆਣਾ 141012",
        "city": "Ludhiana",
        "phone": "0161 501 3300",
        "accred": "Department of Laboratory Medicine",
        "path": {"name": "Dr. Ravinder Sethi", "qual": "MD, DNB (Pathology)",
                 "regn": "PMC 2001/11/1128", "scrawl": "R Sethi"},
    },
}

GREWAL = "Dr. J. S. Grewal, MBBS, MD, DM (Endocrinology)"
ARORA = "Dr. Neha Arora, MBBS, MD (Medicine)"
DHILLON = "Dr. Manpreet Dhillon, MBBS, MD (Family Medicine)"

A1C_LEGEND = [
    ("HbA1c - diagnostic categories (ADA)", "HbA1c"),
    ("Below 5.7 %", "Normal"),
    ("5.7 - 6.4 %", "Prediabetes"),
    ("6.5 % and above", "Diabetes mellitus"),
]

# The weight is the story the patient would not hear: 92 kg creeping to 101,
# one good year in 2024 when it fell to 94, then back up.
HEIGHT_CM = 175.0

VITALS = {
    1: {"weight_kg": 92.4, "bp": "132/84", "spo2": 98, "temp_f": 98.4,
        "context": "Corporate health check. Told he is at risk and given a diet sheet."},
    2: {"weight_kg": 93.8, "bp": "134/86", "spo2": 98, "temp_f": 98.2,
        "context": "Repeat at six months. No change in habits."},
    3: {"weight_kg": 95.2, "bp": "136/86", "spo2": 97, "temp_f": 98.6,
        "context": "Annual check. Advice repeated."},
    4: {"weight_kg": 96.6, "bp": "138/88", "spo2": 98, "temp_f": 98.4,
        "context": "Family history of diabetes discussed again."},
    5: {"weight_kg": 97.8, "bp": "140/88", "spo2": 97, "temp_f": 98.2,
        "context": "Annual check. Now clearly in the prediabetes band."},
    6: {"weight_kg": 96.2, "bp": "136/86", "spo2": 98, "temp_f": 98.4,
        "context": "Joined a gym in January. Some weight lost."},
    7: {"weight_kg": 94.0, "bp": "132/84", "spo2": 98, "temp_f": 98.6,
        "context": "Best result of the five years. Six kilos down from the peak."},
    8: {"weight_kg": 95.6, "bp": "134/86", "spo2": 98, "temp_f": 98.4,
        "context": "Gym stopped after a shoulder injury."},
    9: {"weight_kg": 98.4, "bp": "140/90", "spo2": 97, "temp_f": 98.2,
        "context": "Weight back above the previous peak."},
    10: {"weight_kg": 100.2, "bp": "142/90", "spo2": 97, "temp_f": 98.6,
         "context": "Now diabetic on the HbA1c criterion. Metformin started."},
    11: {"weight_kg": 101.0, "bp": "144/92", "spo2": 97, "temp_f": 98.4,
         "context": "Tolerating metformin. Diet still poor."},
    12: {"weight_kg": 100.4, "bp": "140/88", "spo2": 98, "temp_f": 98.2,
         "context": "Dose increased. Referred to a dietician, attended once."},
    13: {"weight_kg": 99.6, "bp": "138/88", "spo2": 98, "temp_f": 98.4,
         "context": "Single repeat HbA1c three months after the dose change."},
    14: {"weight_kg": 98.8, "bp": "136/86", "spo2": 98, "temp_f": 98.6,
         "context": "Annual review. Slight improvement, still above target."},
    15: {"weight_kg": 98.2, "bp": "136/86", "spo2": 98, "temp_f": 98.2,
         "context": "Established type 2 diabetes, on treatment."},
}

REPORTS = [
    # ---- R01 -- the corporate check ------------------------------------------
    {
        "collected": "2021-10-14 08:20", "reported": "2021-10-14 17:40",
        "lab": "satluj", "layout_style": "glossy_marketing",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": DHILLON, "specimen": "Fluoride plasma, Serum",
        "alias": 0, "traps": ["legend_lines", "test_code_column"],
        "interpretation": "HbA1c is in the prediabetes range. Weight reduction of five to "
                          "seven per cent and 150 minutes of activity a week are advised, "
                          "with a repeat in six months.",
        "sections": [
            {"panel": "DIABETES", "title": 0, "drop": ["GLU_R"],
             "legend": A1C_LEGEND,
             "lab_codes": {"GLU_F": "T-1042", "GLU_PP": "T-1043", "HBA1C": "T-2210",
                           "EAG": "T-2211", "INSULIN_F": "T-3304"},
             "values": {"GLU_F": 108, "GLU_PP": 152, "HBA1C": 5.9, "INSULIN_F": 18.6}},
            {"panel": "LIPID", "title": 0,
             "lab_codes": {"CHOL": "T-1101", "TRIG": "T-1102", "HDL": "T-1103",
                           "LDL": "T-1104", "VLDL": "T-1105"},
             "values": {"CHOL": 214, "TRIG": 198, "HDL": 38}},
        ],
    },
    # ---- R02 -- six month repeat ---------------------------------------------
    {
        "collected": "2022-04-09 09:00", "reported": "2022-04-09 15:30",
        "lab": "punjab", "layout_style": "dot_matrix_pinfeed",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": DHILLON, "specimen": "Fluoride plasma",
        "alias": 1, "traps": ["range_split_columns"],
        "sections": [
            {"heading": "Blood Sugar Profile",
             "rows": [{"code": "GLU_F", "value": 112, "flag": "H"},
                      {"code": "GLU_PP", "value": 158, "flag": "H"},
                      {"code": "HBA1C", "value": 6.1, "flag": "H"},
                      {"code": "EAG"}]},
        ],
    },
    # ---- R03 -- annual check -------------------------------------------------
    {
        "collected": "2022-10-25 08:40", "reported": "2022-10-25 18:20",
        "lab": "satluj", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Patient ID",
        "doctor": ARORA, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 2, "traps": ["merged_panel_heading", "text_result", "method_sub_line"],
        "note": "Annual health check package.",
        "sections": [
            {"panel": "CBC", "title": 1, "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "values": {"HGB": 15.0, "RBC": 5.02, "PCV": 44.6, "MCV": 88.8, "MCH": 29.9,
                        "WBC": 7200, "NEUT_PCT": 60, "LYMPH_PCT": 30, "MONO_PCT": 6,
                        "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 258000}},
            {"panels": ["LFT", "KFT"], "heading": "Biochemistry - Liver and Renal",
             "trap": "merged_panel_heading",
             "drop": ["GGT", "AG_RATIO", "GLOB", "BILI_I", "BUN"],
             "values": {"BILI_T": 0.8, "BILI_D": 0.2, "ALT": 52, "AST": 38, "ALP": 92,
                        "PROT_T": 7.4, "ALB": 4.4,
                        "CREAT": 0.98, "UREA": 30, "UA": 6.8}},
            {"panel": "THYROID", "title": 1, "drop": ["FT3", "ANTI_TPO"],
             "values": {"TSH": 3.02, "T3_TOTAL": 128, "T4_TOTAL": 8.6, "FT4": 1.18}},
            {"panel": "VITAMIN", "title": 1, "methods": True,
             "values": {"VIT_D": 15.8, "VIT_B12": 286, "FOLATE": 7.4}},
            {"heading": "Glycaemic and Other",
             "rows": [{"code": "HBA1C", "value": 6.3, "flag": "H"},
                      {"code": "EAG"},
                      {"code": "BLOOD_GROUP", "value": "B Positive",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R04 -- family history discussed -------------------------------------
    {
        "collected": "2023-03-18 09:15", "reported": "2023-03-18 16:00",
        "lab": "punjab", "layout_style": "cut_sheet",
        "header_style": "centred_title_only", "uhid_label": "Reg. No",
        "doctor": DHILLON, "specimen": "Fluoride plasma, Serum",
        "alias": 3, "traps": ["unit_in_label"],
        "sections": [
            {"heading": "Glycaemic Profile",
             "rows": [{"code": "GLU_F", "value": 116, "flag": "H"},
                      {"code": "HBA1C", "value": 6.4, "flag": "H"},
                      {"code": "EAG"},
                      {"label": "Fructosamine", "value": "268", "unit": "umol/L",
                       "reference": "205 - 285"}]},
        ],
    },
    # ---- R05 -- annual check -------------------------------------------------
    {
        "collected": "2023-10-30 08:30", "reported": "2023-10-30 17:15",
        "lab": "doaba", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Hospital No",
        "doctor": ARORA, "specimen": "Serum, Urine (midstream)",
        "alias": 0, "traps": ["test_code_column", "flag_as_words"],
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 0,
             "lab_codes": {"UR_COLOUR": "U-01", "UR_PH": "U-02", "UR_SPGR": "U-03",
                           "UR_PROT": "U-04", "UR_GLU": "U-05", "UR_KET": "U-06",
                           "UR_PUS": "U-11", "UR_RBC": "U-12", "UR_EPITH": "U-13",
                           "MICROALB": "U-20", "ACR": "U-21"},
             "values": {"UR_COLOUR": "Yellow", "UR_PH": 5.5, "UR_SPGR": 1.024,
                        "UR_PROT": "Absent", "UR_GLU": "Trace", "UR_KET": "Absent",
                        "UR_PUS": 3, "UR_RBC": 1, "UR_EPITH": 3, "MICROALB": 22,
                        "ACR": 26}},
            {"panel": "LIPID", "title": 3,
             "lab_codes": {"CHOL": "T-1101", "TRIG": "T-1102", "HDL": "T-1103"},
             "values": {"CHOL": 228, "TRIG": 224, "HDL": 36}},
            {"heading": "Glycaemic",
             "lab_codes": {"HBA1C": "T-2210"},
             "rows": [{"code": "HBA1C", "value": 6.6, "flag": "H"}, {"code": "EAG"}]},
        ],
    },
    # ---- R06 -- the gym year -------------------------------------------------
    {
        "collected": "2024-04-06 09:10", "reported": "2024-04-06 15:50",
        "lab": "satluj", "layout_style": "thermal_slip",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": DHILLON, "specimen": "Fluoride plasma",
        "alias": 1, "traps": ["no_reference_column"],
        "sections": [
            {"heading": "HbA1c",
             "rows": [{"code": "HBA1C", "value": 6.4, "flag": "H"}]},
        ],
    },
    # ---- R07 -- best result --------------------------------------------------
    {
        "collected": "2024-09-21 08:45", "reported": "2024-09-21 17:00",
        "lab": "doaba", "layout_style": "landscape_wide",
        "header_style": "barcode_header", "uhid_label": "Hospital No",
        "doctor": GREWAL, "specimen": "Serum, Fluoride plasma",
        "alias": 2, "traps": ["prev_value_column", "method_sub_line"],
        "sections": [
            {"heading": "Glycaemic Profile - Comparative", "methods": True,
             "prev": {"HBA1C": "6.6 (30/10/2023)", "GLU_F": "116 (18/03/2023)",
                      "INSULIN_F": "18.6 (14/10/2021)"},
             "rows": [{"code": "GLU_F", "value": 96}, {"code": "GLU_PP", "value": 128},
                      {"code": "HBA1C", "value": 5.9, "flag": "H"}, {"code": "EAG"},
                      {"code": "INSULIN_F", "value": 14.2}]},
            {"panel": "LFT", "title": 2, "drop": ["GGT", "BILI_I", "GLOB", "AG_RATIO"],
             "values": {"BILI_T": 0.7, "BILI_D": 0.2, "ALT": 44, "AST": 34, "ALP": 86,
                        "PROT_T": 7.3, "ALB": 4.3}},
        ],
    },
    # ---- R08 -- gym stopped --------------------------------------------------
    {
        "collected": "2025-02-12 09:30", "reported": "2025-02-12 16:20",
        "lab": "punjab", "layout_style": "ledger_ruled",
        "header_style": "bilingual_header", "uhid_label": "Reg. No",
        "doctor": ARORA, "specimen": "Serum, Fluoride plasma",
        "alias": 3, "traps": ["range_split_columns", "sparse_panel"],
        "sections": [
            {"panel": "THYROID", "title": 3, "drop": ["T3_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel",
             "values": {"TSH": 3.24, "T4_TOTAL": 8.4, "FT4": 1.14}},
            {"panel": "ELECTROLYTES", "title": 3, "drop": ["CA_ION", "PHOS"],
             "values": {"NA": 140, "K": 4.2, "CL": 104, "CA": 9.2, "MG": 2.0}},
            {"heading": "Glycaemic Profile",
             "rows": [{"code": "GLU_F", "value": 124, "flag": "H"},
                      {"code": "GLU_PP", "value": 178, "flag": "H"},
                      {"code": "HBA1C", "value": 6.8, "flag": "H"},
                      {"code": "EAG"}]},
        ],
    },
    # ---- R09 -- weight back above the peak -----------------------------------
    {
        "collected": "2025-06-25 08:55", "reported": "2025-06-25 17:30",
        "lab": "satluj", "layout_style": "clean_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": GREWAL, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 0, "traps": ["abnormal_shaded", "footnote_marker"],
        "footnotes": [("1", "PSA requested as part of the over-forty male screening "
                            "package offered by this laboratory.")],
        "sections": [
            {"panel": "TUMOUR_MARKERS", "title": 0,
             "values": {"PSA": 1.42}, "row_traps": {"PSA": "footnote_marker"}},
            {"panel": "SEROLOGY", "title": 3, "drop": ["WIDAL", "DENGUE_NS1",
                                                       "DENGUE_IGM", "MP", "VDRL"],
             "values": {"HBSAG": "Non Reactive", "ANTI_HCV": "Non Reactive",
                        "HIV": "Non Reactive"},
             "row_traps": {"HBSAG": "text_result"}},
            {"panel": "URINE_ROUTINE", "title": 4, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Yellow", "UR_PH": 5.5, "UR_SPGR": 1.026,
                        "UR_PROT": "Trace", "UR_GLU": "+", "UR_KET": "Absent",
                        "UR_PUS": 4, "UR_RBC": 1, "UR_EPITH": 4}},
            {"heading": "Glycaemic",
             "rows": [{"code": "HBA1C", "value": 6.9, "flag": "H"}, {"code": "EAG"},
                      {"label": "Anti-CCP Antibody", "value": "4.2", "unit": "U/mL",
                       "reference": "< 17"}]},
        ],
    },
    # ---- R10 -- crosses into diabetes ----------------------------------------
    {
        "collected": "2025-11-08 08:15", "reported": "2025-11-08 18:40",
        "lab": "doaba", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": GREWAL, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["legend_lines", "abnormal_shaded"],
        "note": "HbA1c above the diagnostic threshold on a second occasion. Type 2 "
                "diabetes mellitus; metformin started today.",
        "sections": [
            {"panel": "DIABETES", "title": 4, "drop": ["GLU_R"],
             "legend": A1C_LEGEND,
             "values": {"GLU_F": 148, "GLU_PP": 216, "HBA1C": 7.1, "INSULIN_F": 22.8}},
            {"panel": "KFT", "title": 0,
             "values": {"CREAT": 1.02, "UREA": 32, "UA": 7.2}},
            {"panel": "ELECTROLYTES", "title": 0, "drop": ["CA_ION", "MG"],
             "values": {"NA": 139, "K": 4.4, "CL": 103, "CA": 9.4, "PHOS": 3.4}},
        ],
    },
    # ---- R11 -- on metformin -------------------------------------------------
    {
        "collected": "2026-01-19 09:20", "reported": "2026-01-19 16:10",
        "lab": "punjab", "layout_style": "typewriter_manual",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": ARORA, "specimen": "Serum, Fluoride plasma",
        "alias": 2, "traps": ["no_reference_column", "not_reported"],
        "sections": [
            {"heading": "Glycaemic and Vitamins",
             "rows": [{"code": "HBA1C", "value": 7.2, "flag": "H"},
                      {"code": "GLU_F", "value": 152, "flag": "H"},
                      {"code": "VIT_B12", "value": 246},
                      {"code": "VIT_D", "value": "Not Reported",
                       "trap": "not_reported"}]},
        ],
    },
    # ---- R12 -- dose increased -----------------------------------------------
    {
        "collected": "2026-04-14 08:50", "reported": "2026-04-14 17:05",
        "lab": "satluj", "layout_style": "glossy_marketing",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": GREWAL, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 3, "traps": ["test_code_column", "text_result"],
        "interpretation": "Glycaemic control remains above target six months after "
                          "starting metformin. Dose escalation and a dietician review "
                          "are advised before adding a second agent.",
        "sections": [
            {"panel": "CBC", "title": 3,
             "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW", "MCH", "BASO_PCT", "EOS_PCT"],
             "lab_codes": {"HGB": "H-01", "RBC": "H-02", "PCV": "H-03", "MCV": "H-04",
                           "WBC": "H-10", "PLT": "H-20"},
             "values": {"HGB": 15.2, "RBC": 5.08, "PCV": 45.2, "MCV": 89.0,
                        "WBC": 7600, "NEUT_PCT": 61, "LYMPH_PCT": 29, "MONO_PCT": 6,
                        "PLT": 264000}},
            {"panel": "IRON", "title": 1, "drop": ["UIBC"],
             "lab_codes": {"FERRITIN": "B-40", "IRON": "B-41", "TIBC": "B-42"},
             "values": {"FERRITIN": 236, "IRON": 102, "TIBC": 316}},
            {"heading": "Glycaemic",
             "lab_codes": {"HBA1C": "T-2210", "EAG": "T-2211"},
             "rows": [{"code": "HBA1C", "value": 7.0, "flag": "H"}, {"code": "EAG"},
                      {"code": "PERIPH_SMEAR",
                       "value": "Normocytic normochromic. No abnormal cells.",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R13 -- one repeat HbA1c ---------------------------------------------
    {
        "collected": "2026-06-27 09:40", "reported": "2026-06-27 13:15",
        "lab": "punjab", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": ARORA, "specimen": "Whole blood (EDTA)",
        "alias": 0, "traps": ["no_header_row"],
        "sections": [
            {"heading": "Glycosylated Haemoglobin",
             "rows": [{"code": "HBA1C", "value": 6.9, "flag": "H"}]},
        ],
    },
    # ---- R14 -- annual review, two pages -------------------------------------
    {
        "collected": "2026-08-18 07:50", "reported": "2026-08-18 20:00",
        "lab": "doaba", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "Hospital No",
        "doctor": GREWAL, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["ratio_no_code", "method_sub_line"],
        "page_break_after": 3,
        "sections": [
            {"panel": "CBC", "title": 5,
             "values": {"HGB": 15.0, "RBC": 5.04, "PCV": 44.8, "MCV": 88.9, "MCH": 29.8,
                        "MCHC": 33.5, "RDW": 13.1, "WBC": 7400, "NEUT_PCT": 60,
                        "LYMPH_PCT": 30, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 260000, "MPV": 9.8}},
            {"panel": "LIPID", "title": 5, "methods": True,
             "values": {"CHOL": 206, "TRIG": 212, "HDL": 37}},
            {"panel": "DIABETES", "title": 5, "drop": ["GLU_R"],
             "values": {"GLU_F": 138, "GLU_PP": 192, "HBA1C": 6.9, "INSULIN_F": 19.4}},
            {"panel": "LFT", "title": 5,
             "values": {"BILI_T": 0.8, "BILI_D": 0.2, "ALT": 56, "AST": 40, "ALP": 94,
                        "GGT": 68, "PROT_T": 7.4, "ALB": 4.4}},
            {"panel": "KFT", "title": 5,
             "values": {"CREAT": 1.06, "UREA": 33, "UA": 7.4}},
            {"heading": "Derived",
             "rows": [{"label": "TG / HDL Ratio", "value": "5.7", "unit": "",
                       "reference": "< 3.5", "flag": "H", "trap": "ratio_no_code"},
                      {"label": "Homocysteine", "value": "15.8", "unit": "umol/L",
                       "reference": "5.0 - 15.0", "flag": "H"}]},
        ],
    },
    # ---- R15 -- established diabetes -----------------------------------------
    {
        "collected": "2026-09-15 08:40", "reported": "2026-09-15 16:30",
        "lab": "satluj", "layout_style": "mixed_print_hand",
        "header_style": "stamp_and_signature", "uhid_label": "Patient ID",
        "doctor": GREWAL, "specimen": "Serum", "stamp": "DIABETES<br>CLINIC",
        "alias": 2, "traps": ["method_sub_line"],
        "sections": [
            {"panel": "IRON", "title": 4, "methods": True,
             "values": {"FERRITIN": 214, "IRON": 98, "TIBC": 320}},
            {"panel": "VITAMIN", "title": 4, "methods": True,
             "values": {"VIT_D": 22.6, "VIT_B12": 232, "FOLATE": 6.8}},
            {"heading": "Written in at the clinic", "hand_addendum": True,
             "rows": [{"code": "HBA1C", "value": 6.9}, {"code": "GLU_F", "value": 132}]},
        ],
    },
]
