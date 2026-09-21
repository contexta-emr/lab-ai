"""Patient 11 of 20 - Nephrology. Recurrent UTI with stones, kidney function preserved.

Female, 37 at the first report, Surat. Four culture-proven urinary infections across the
five years, two of them with a 6 mm right renal calculus visible on ultrasound. The point
of the case is what does *not* happen: creatinine stays between 0.64 and 0.88 throughout
and eGFR never leaves the normal range, so a trend line drawn through it should be flat.

The setback is September 2024 - an obstructed, infected system needing admission and
ureteric stenting, with the only fever, the only leucocytosis and the only coagulation
screen in the record.
"""

from __future__ import annotations

PATIENT = {
    "number": 11,
    "name": "Hetal D. Rathod",
    "sex": "F",
    "dob": "1984-09-27",
    "uhid": "SKD/562840",
    "department": "Nephrology",
    "city": "Surat",
    "age_at_first": 37,
    "tracked": ["CREAT"],
    "brief": "Recurrent UTI with stones, kidney function preserved",
}


def check_arc(series):
    creat = [v for _, v in series["CREAT"]]
    fails = []
    if max(creat) > 1.10:
        fails.append(f"renal function was meant to stay preserved, peak {max(creat)}")
    if max(creat) - min(creat) > 0.40:
        fails.append("creatinine swings too widely for a preserved-function case")
    if not len(creat) >= 8:
        fails.append("not enough creatinine points to show the flat line")
    return fails


LABS = {
    "tapi": {
        "abbr": "TDL", "acc_style": 0,
        "name": "Tapi Diagnostic Laboratory",
        "name_local": "તાપી ડાયગ્નોસ્ટિક લેબોરેટરી",
        "addr": "Ghod Dod Road, Surat 395007",
        "addr_local": "ઘોડ દોડ રોડ, સુરત 395007",
        "city": "Surat",
        "phone": "0261 279 3310",
        "accred": "NABL Accredited (MC-4426) | ISO 15189:2012",
        "path": {"name": "Dr. Bhavna Zaveri", "qual": "MD (Pathology)",
                 "regn": "GMC 2009/01/6628", "scrawl": "B Zaveri"},
    },
    "diamond": {
        "abbr": "DPL", "acc_style": 3,
        "name": "Diamond City Path Lab",
        "name_local": "ડાયમંડ સિટી પેથ લેબ",
        "addr": "Adajan Gam, Surat 395009",
        "addr_local": "અડાજણ ગામ, સુરત 395009",
        "city": "Surat",
        "phone": "0261 266 8845",
        "accred": "NABL Accredited (M-7715)",
        "path": {"name": "Dr. Mehul Gajjar", "qual": "MBBS, MD (Path.)",
                 "regn": "GMC 2014/06/9917", "scrawl": "M Gajjar"},
    },
    "sanskar": {
        "abbr": "SKD", "acc_style": 1,
        "name": "Sanskardham Kidney Hospital Laboratory",
        "name_local": "સંસ્કારધામ કિડની હોસ્પિટલ પ્રયોગશાળા",
        "addr": "Piplod, Surat 395007",
        "addr_local": "પીપલોદ, સુરત 395007",
        "city": "Surat",
        "phone": "0261 223 5000",
        "accred": "Department of Laboratory Medicine, Urology and Nephrology",
        "path": {"name": "Dr. Ashwin Kapadia", "qual": "MD, DNB (Pathology)",
                 "regn": "GMC 2002/09/1748", "scrawl": "A Kapadia"},
    },
}

MODI = "Dr. Dhruv Modi, MBBS, MS, MCh (Urology)"
PARIKH = "Dr. Sheetal Parikh, MBBS, MD (Medicine)"
JARIWALA = "Dr. Nilesh Jariwala, MBBS, MD, DM (Nephrology)"

UTI_LEGEND = [
    ("Significant bacteriuria - interpretation", "Colony count"),
    ("Below 10000 CFU/mL", "Not significant"),
    ("10000 - 100000 CFU/mL", "Doubtful, repeat if symptomatic"),
    ("Above 100000 CFU/mL", "Significant bacteriuria"),
]

# Weight and blood pressure barely move: this is a well woman with a recurring
# infection, not a progressive disease. Only the September 2024 admission is febrile.
HEIGHT_CM = 159.0

VITALS = {
    1: {"weight_kg": 58.4, "bp": "118/76", "spo2": 99, "temp_f": 99.4,
        "context": "Third episode of burning and frequency this year."},
    2: {"weight_kg": 58.9, "bp": "116/74", "spo2": 98, "temp_f": 98.4,
        "context": "Treated and asymptomatic. Ultrasound shows a 6 mm right calculus."},
    3: {"weight_kg": 59.2, "bp": "118/76", "spo2": 99, "temp_f": 98.2,
        "context": "Advised high fluid intake and citrate. Stone unchanged."},
    4: {"weight_kg": 59.6, "bp": "120/78", "spo2": 98, "temp_f": 100.2,
        "context": "Second infection of the year, low-grade fever, treated as outpatient."},
    5: {"weight_kg": 59.1, "bp": "118/76", "spo2": 99, "temp_f": 98.4,
        "context": "Recovered. Metabolic stone workup requested."},
    6: {"weight_kg": 58.8, "bp": "116/74", "spo2": 99, "temp_f": 98.2,
        "context": "Annual review. Renal function entirely normal."},
    7: {"weight_kg": 59.4, "bp": "118/76", "spo2": 98, "temp_f": 98.6,
        "context": "Well. Six-monthly check."},
    8: {"weight_kg": 58.2, "bp": "104/64", "spo2": 96, "temp_f": 102.6,
        "context": "Rigors and right loin pain. Obstructed infected system, admitted."},
    9: {"weight_kg": 57.6, "bp": "112/70", "spo2": 97, "temp_f": 99.8,
        "context": "Second day after stenting. Fever settling on antibiotics."},
    10: {"weight_kg": 58.4, "bp": "116/74", "spo2": 98, "temp_f": 98.4,
         "context": "Stent removed. Stone cleared by lithotripsy."},
    11: {"weight_kg": 58.9, "bp": "118/76", "spo2": 99, "temp_f": 98.2,
         "context": "Recovered fully. Function unchanged from before the episode."},
    12: {"weight_kg": 59.2, "bp": "116/74", "spo2": 98, "temp_f": 98.4,
         "context": "Fourth infection, milder, no fever."},
    13: {"weight_kg": 59.0, "bp": "118/76", "spo2": 99, "temp_f": 98.2,
         "context": "Single confirmatory creatinine at the patient's request."},
    14: {"weight_kg": 59.4, "bp": "116/74", "spo2": 98, "temp_f": 98.6,
         "context": "Annual review. No new stones, function preserved."},
    15: {"weight_kg": 59.8, "bp": "114/74", "spo2": 99, "temp_f": 98.2,
         "context": "Discharged to yearly follow-up with the urologist."},
}

REPORTS = [
    # ---- R01 -- third infection ---------------------------------------------
    {
        "collected": "2021-10-25 10:30", "reported": "2021-10-27 11:15",
        "lab": "tapi", "layout_style": "clean_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": PARIKH, "specimen": "Urine (midstream), Serum",
        "alias": 0, "traps": ["legend_lines", "text_result"],
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 0,
             "values": {"UR_COLOUR": "Hazy Yellow", "UR_PH": 7.0, "UR_SPGR": 1.018,
                        "UR_PROT": "Trace", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 56, "UR_RBC": 8, "UR_EPITH": 6, "MICROALB": 18,
                        "ACR": 20}},
            {"heading": "Microbiology", "legend": UTI_LEGEND,
             "rows": [{"code": "URINE_CULTURE",
                       "value": "Escherichia coli, >100000 CFU/mL. Sensitive: "
                                "Nitrofurantoin, Fosfomycin, Amikacin. Resistant: "
                                "Ciprofloxacin, Cefixime.",
                       "flag": "H", "trap": "text_result"},
                      {"code": "CREAT", "value": 0.72}]},
        ],
    },
    # ---- R02 -- stone found -------------------------------------------------
    {
        "collected": "2022-02-11 09:20", "reported": "2022-02-11 16:30",
        "lab": "sanskar", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Hospital No",
        "doctor": MODI, "specimen": "Serum, Urine (midstream)",
        "alias": 1, "traps": ["unit_in_label"],
        "interpretation": "Renal function is normal. The calculus is small and "
                          "non-obstructing; conservative management with high fluid "
                          "intake is appropriate.",
        "sections": [
            {"panel": "KFT", "title": 0,
             "values": {"CREAT": 0.68, "UREA": 22, "UA": 5.8}},
            {"panel": "ELECTROLYTES", "title": 0,
             "values": {"NA": 140, "K": 4.2, "CL": 103, "CA": 9.8, "CA_ION": 5.0,
                        "PHOS": 3.4, "MG": 2.1}},
        ],
    },
    # ---- R03 -- stone unchanged ---------------------------------------------
    {
        "collected": "2022-07-30 08:50", "reported": "2022-07-30 15:20",
        "lab": "diamond", "layout_style": "ledger_ruled",
        "header_style": "bilingual_header", "uhid_label": "Reg. No",
        "doctor": MODI, "specimen": "Urine (24 hour), Serum",
        "alias": 2, "traps": ["footnote_marker", "sample_type_row"],
        "footnotes": [("1", "24 hour collection; volume 1850 mL. Container with acid "
                            "preservative.")],
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 2, "sample_row": "Urine, 24 hour collection",
             "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.5, "UR_SPGR": 1.010,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 4, "UR_RBC": 2, "UR_EPITH": 4}},
            {"heading": "Stone Metabolic Workup",
             "rows": [{"code": "CREAT", "value": 0.70, "marker": "1"},
                      {"code": "UA", "value": 5.4},
                      {"code": "CA", "value": 9.6},
                      {"label": "Urinary Calcium, 24 hour", "value": "218", "unit": "mg/24h",
                       "reference": "100 - 300"},
                      {"label": "Urinary Oxalate, 24 hour", "value": "34", "unit": "mg/24h",
                       "reference": "< 45"},
                      {"label": "Urinary Citrate, 24 hour", "value": "286", "unit": "mg/24h",
                       "reference": "> 320", "flag": "L"}]},
        ],
    },
    # ---- R04 -- second infection --------------------------------------------
    {
        "collected": "2023-01-18 11:40", "reported": "2023-01-20 12:10",
        "lab": "tapi", "layout_style": "typewriter_manual",
        "header_style": "minimal_text_top", "uhid_label": "Patient ID",
        "doctor": PARIKH, "specimen": "Urine (midstream), Whole blood (EDTA)",
        "alias": 3, "traps": ["no_reference_column", "text_result"],
        "sections": [
            {"heading": "Urine and Counts",
             "rows": [{"code": "UR_PUS", "value": 38, "flag": "H"},
                      {"code": "UR_RBC", "value": 4, "flag": "H"},
                      {"code": "WBC", "value": 11400, "flag": "H"},
                      {"code": "CREAT", "value": 0.74},
                      {"code": "URINE_CULTURE",
                       "value": "Klebsiella pneumoniae, >100000 CFU/mL. Sensitive: "
                                "Meropenem, Amikacin, Nitrofurantoin.",
                       "flag": "H", "trap": "text_result"}]},
        ],
    },
    # ---- R05 -- recovered ----------------------------------------------------
    {
        "collected": "2023-06-14 09:00", "reported": "2023-06-14 16:45",
        "lab": "diamond", "layout_style": "two_column",
        "header_style": "barcode_header", "uhid_label": "Reg. No",
        "doctor": JARIWALA, "specimen": "Serum",
        "alias": 0, "traps": ["sno_column", "flag_as_words"],
        "sections": [
            {"panel": "LFT", "title": 1, "drop": ["GGT", "BILI_I"],
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 21, "AST": 23, "ALP": 74,
                        "PROT_T": 7.1, "ALB": 4.2}},
            {"panel": "THYROID", "title": 1, "drop": ["FT3", "ANTI_TPO"],
             "values": {"TSH": 2.28, "T3_TOTAL": 122, "T4_TOTAL": 9.0, "FT4": 1.24}},
            {"heading": "Renal",
             "rows": [{"code": "CREAT", "value": 0.66}, {"code": "EGFR"}]},
        ],
    },
    # ---- R06 -- annual review ------------------------------------------------
    {
        "collected": "2023-12-02 07:55", "reported": "2023-12-02 19:15",
        "lab": "tapi", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Patient ID",
        "doctor": JARIWALA, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["merged_panel_heading", "text_result", "method_sub_line"],
        "note": "Annual review package.",
        "sections": [
            {"panel": "CBC", "title": 1, "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "values": {"HGB": 12.6, "RBC": 4.38, "PCV": 38.2, "MCV": 87.2, "MCH": 28.8,
                        "WBC": 6800, "NEUT_PCT": 58, "LYMPH_PCT": 32, "MONO_PCT": 6,
                        "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 262000}},
            {"panel": "LIPID", "title": 1, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 176, "TRIG": 108, "HDL": 54}},
            {"panels": ["KFT", "ELECTROLYTES"], "heading": "Biochemistry - Renal and Minerals",
             "trap": "merged_panel_heading", "drop": ["BUN", "CA_ION", "MG"],
             "values": {"CREAT": 0.71, "UREA": 24, "UA": 5.2,
                        "NA": 140, "K": 4.3, "CL": 104, "CA": 9.7, "PHOS": 3.6}},
            {"panel": "IRON", "title": 1, "drop": ["UIBC"], "methods": True,
             "values": {"FERRITIN": 34, "IRON": 76, "TIBC": 368}},
            {"panel": "VITAMIN", "title": 1,
             "values": {"VIT_D": 18.8, "VIT_B12": 322, "FOLATE": 8.4}},
            {"heading": "Other",
             "rows": [{"code": "BLOOD_GROUP", "value": "O Positive", "trap": "text_result"},
                      {"code": "HBA1C", "value": 5.2}]},
        ],
    },
    # ---- R07 -- six-monthly check -------------------------------------------
    {
        "collected": "2024-05-09 09:30", "reported": "2024-05-09 14:50",
        "lab": "diamond", "layout_style": "thermal_slip",
        "header_style": "centred_title_only", "uhid_label": "Reg. No",
        "doctor": PARIKH, "specimen": "Serum",
        "alias": 2, "traps": ["no_reference_column"],
        "sections": [
            {"heading": "Serum Creatinine",
             "rows": [{"code": "CREAT", "value": 0.69}]},
        ],
    },
    # ---- R08 -- obstructed infected system ----------------------------------
    {
        "collected": "2024-09-21 23:40", "reported": "2024-09-22 03:20",
        "lab": "sanskar", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": MODI, "specimen": "Whole blood (EDTA), Citrate plasma, Serum, Urine",
        "alias": 3, "traps": ["sno_column", "text_result", "abnormal_shaded"],
        "note": "Emergency admission with an obstructed, infected right system. "
                "Ureteric stenting planned tonight.",
        "sections": [
            {"panel": "CBC", "title": 4, "drop": ["ANC", "ALC", "MPV", "MCHC"],
             "values": {"HGB": 11.8, "RBC": 4.12, "PCV": 35.8, "MCV": 86.9, "MCH": 28.6,
                        "RDW": 14.2, "WBC": 19600, "NEUT_PCT": 88, "LYMPH_PCT": 8,
                        "MONO_PCT": 3, "EOS_PCT": 1, "BASO_PCT": 0, "PLT": 342000}},
            {"panel": "COAGULATION", "title": 1,
             "values": {"PT": 13.4, "INR": 1.08, "APTT": 31.6, "D_DIMER": 780}},
            {"heading": "Emergency Chemistry and Culture",
             "rows": [{"code": "CREAT", "value": 0.88},
                      {"code": "UREA", "value": 42, "flag": "H"},
                      {"code": "CRP", "value": 148.0, "flag": "H"},
                      {"code": "URINE_CULTURE",
                       "value": "Escherichia coli, >100000 CFU/mL, ESBL producer. "
                                "Sensitive: Meropenem, Amikacin. Resistant: "
                                "Ceftriaxone, Ciprofloxacin.",
                       "flag": "H", "trap": "text_result"}]},
        ],
    },
    # ---- R09 -- second day after stenting -----------------------------------
    {
        "collected": "2024-09-23 06:30", "reported": "2024-09-23 09:50",
        "lab": "sanskar", "layout_style": "fax_header",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": MODI, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 0, "traps": ["no_reference_column"],
        "note": "Faxed to the urology ward at 09:55 hrs.",
        "sections": [
            {"heading": "Daily Bloods",
             "rows": [{"code": "CREAT", "value": 0.82},
                      {"code": "WBC", "value": 13800, "flag": "H"},
                      {"code": "CRP", "value": 64.2, "flag": "H"},
                      {"code": "HGB", "value": 11.4, "flag": "L"}]},
        ],
    },
    # ---- R10 -- stent removed -----------------------------------------------
    {
        "collected": "2025-01-27 09:15", "reported": "2025-01-27 16:05",
        "lab": "sanskar", "layout_style": "duplicate_watermark",
        "header_style": "letterhead_logo_left", "uhid_label": "Hospital No",
        "doctor": MODI, "specimen": "Serum, Urine (midstream)",
        "alias": 1, "traps": ["prev_value_column", "text_result"],
        "note": "Duplicate copy for the urology file.",
        "sections": [
            {"heading": "Renal Function - Comparative",
             "prev": {"CREAT": "0.88 (21/09/2024)", "UREA": "42 (21/09/2024)"},
             "rows": [{"code": "CREAT", "value": 0.74}, {"code": "UREA", "value": 26},
                      {"code": "BUN"}, {"code": "UA", "value": 5.0},
                      {"code": "EGFR"}]},
            {"heading": "Microbiology",
             "rows": [{"code": "URINE_CULTURE",
                       "value": "No growth after 48 hours of aerobic incubation.",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R11 -- recovered fully ---------------------------------------------
    {
        "collected": "2025-06-11 08:40", "reported": "2025-06-11 17:10",
        "lab": "tapi", "layout_style": "kv_header_table",
        "header_style": "two_line_ribbon", "uhid_label": "Patient ID",
        "doctor": JARIWALA, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["method_sub_line", "sparse_panel"],
        "sections": [
            {"panel": "THYROID", "title": 4, "drop": ["T3_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel", "methods": True,
             "values": {"TSH": 2.64, "T4_TOTAL": 9.4, "FT4": 1.30}},
            {"panel": "DIABETES", "title": 2, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 88, "GLU_PP": 116, "HBA1C": 5.1}},
            {"heading": "Renal",
             "rows": [{"code": "CREAT", "value": 0.70}, {"code": "EGFR"}]},
        ],
    },
    # ---- R12 -- fourth infection, milder ------------------------------------
    {
        "collected": "2025-11-19 10:50", "reported": "2025-11-21 11:40",
        "lab": "diamond", "layout_style": "mobile_photo",
        "header_style": "centred_title_only", "uhid_label": "Reg. No",
        "doctor": PARIKH, "specimen": "Urine (midstream)",
        "alias": 3, "traps": ["text_result", "ambiguous_abbreviation"],
        "note": "Photographed copy sent by the patient on WhatsApp.",
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 4, "drop": ["MICROALB", "ACR"],
             "labels": {"UR_PROT": "ALB"},
             "row_traps": {"UR_PROT": "ambiguous_abbreviation"},
             "values": {"UR_COLOUR": "Hazy Yellow", "UR_PH": 6.5, "UR_SPGR": 1.020,
                        "UR_PROT": "Trace", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 24, "UR_RBC": 3, "UR_EPITH": 6}},
            {"heading": "Microbiology",
             "rows": [{"code": "URINE_CULTURE",
                       "value": "Enterococcus faecalis, 80000 CFU/mL. Sensitive: "
                                "Nitrofurantoin, Linezolid, Vancomycin.",
                       "trap": "text_result"},
                      {"code": "CREAT", "value": 0.72}]},
        ],
    },
    # ---- R13 -- one creatinine ----------------------------------------------
    {
        "collected": "2026-03-05 09:35", "reported": "2026-03-05 13:10",
        "lab": "tapi", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Patient ID",
        "doctor": JARIWALA, "specimen": "Serum",
        "alias": 0, "traps": ["no_header_row"],
        "sections": [
            {"heading": "Creatinine, Serum",
             "rows": [{"code": "CREAT", "value": 0.68}]},
        ],
    },
    # ---- R14 -- annual review, two pages ------------------------------------
    {
        "collected": "2026-06-30 07:50", "reported": "2026-06-30 20:10",
        "lab": "tapi", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": JARIWALA, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["ratio_no_code", "footnote_marker"],
        "page_break_after": 3,
        "footnotes": [("1", "Ultrasound on the same day: no calculus, no hydronephrosis.")],
        "sections": [
            {"panel": "CBC", "title": 5,
             "values": {"HGB": 12.8, "RBC": 4.44, "PCV": 38.8, "MCV": 87.4, "MCH": 28.8,
                        "MCHC": 33.0, "RDW": 13.0, "WBC": 6600, "NEUT_PCT": 57,
                        "LYMPH_PCT": 33, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 258000, "MPV": 9.4}},
            {"panel": "LIPID", "title": 5,
             "values": {"CHOL": 182, "TRIG": 116, "HDL": 56}},
            {"panel": "DIABETES", "title": 5, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 90, "GLU_PP": 120, "HBA1C": 5.2}},
            {"panel": "LFT", "title": 5,
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 22, "AST": 24, "ALP": 76,
                        "GGT": 18, "PROT_T": 7.2, "ALB": 4.3}},
            {"panel": "KFT", "title": 5,
             "values": {"CREAT": 0.72, "UREA": 25, "UA": 5.4},
             "row_traps": {"CREAT": "footnote_marker"}},
            {"heading": "Derived",
             "rows": [{"label": "Urea / Creatinine Ratio", "value": "35", "unit": "",
                       "reference": "20 - 35", "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R15 -- discharged to yearly follow-up ------------------------------
    {
        "collected": "2026-09-05 08:45", "reported": "2026-09-05 16:20",
        "lab": "sanskar", "layout_style": "mixed_print_hand",
        "header_style": "stamp_and_signature", "uhid_label": "Hospital No",
        "doctor": MODI, "specimen": "Serum, Urine (midstream)",
        "alias": 2, "traps": ["method_sub_line"], "stamp": "UROLOGY<br>DISCHARGED",
        "sections": [
            {"panel": "IRON", "title": 5, "methods": True,
             "values": {"FERRITIN": 42, "IRON": 84, "TIBC": 356}},
            {"panel": "VITAMIN", "title": 5, "methods": True,
             "values": {"VIT_D": 28.6, "VIT_B12": 368, "FOLATE": 9.8}},
            {"heading": "Written in at the clinic", "hand_addendum": True,
             "rows": [{"code": "CREAT", "value": 0.70}, {"code": "UR_PUS", "value": 2}]},
        ],
    },
]
