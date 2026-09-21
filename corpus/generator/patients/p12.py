"""Patient 12 of 20 - General medicine. Enteric fever episode, then annual health checks.

Male, 26 at the first report, Patna. Admitted in November 2021 with a week of fever, a
Widal titre of 1:320, leucopenia at 3200 and transaminases twice normal - enteric fever,
with cardiac markers checked on day four for chest discomfort and a tachycardia, which
turned out to be nothing. He recovers completely and the next three years are ordinary
annual checks.

The setback is March 2025: a relapse of enteric fever after incomplete treatment abroad,
milder than the first, with the white count down to 3600 again. After that he is well.
"""

from __future__ import annotations

PATIENT = {
    "number": 12,
    "name": "Ranjan Kumar Choudhary",
    "sex": "M",
    "dob": "1995-04-19",
    "uhid": "JPH/318064",
    "department": "General Medicine",
    "city": "Patna",
    "age_at_first": 26,
    "tracked": ["WBC"],
    "brief": "Enteric fever episode, then annual health checks",
}


def check_arc(series):
    wbc = [v for _, v in series["WBC"]]
    fails = []
    if not wbc[0] < 4000:
        fails.append(f"enteric fever should open with leucopenia, got {wbc[0]}")
    if not max(wbc) > 6000:
        fails.append("count never recovers to a normal range")
    if len([v for v in wbc if v < 4200]) < 2:
        fails.append("only one leucopenic spell, so there is no relapse")
    if not 4000 <= wbc[-1] <= 11000:
        fails.append(f"should end with a normal white count, got {wbc[-1]}")
    return fails


LABS = {
    "ganga": {
        "abbr": "GDL", "acc_style": 0,
        "name": "Ganga Diagnostic Laboratory",
        "name_local": "गंगा डायग्नोस्टिक लेबोरेटरी",
        "addr": "Boring Road, Patna 800001",
        "addr_local": "बोरिंग रोड, पटना 800001",
        "city": "Patna",
        "phone": "0612 253 8890",
        "accred": "NABL Accredited (MC-2271) | ISO 15189:2012",
        "path": {"name": "Dr. Nutan Priya", "qual": "MD (Pathology)",
                 "regn": "BMC 2008/07/4413", "scrawl": "N Priya"},
    },
    "magadh": {
        "abbr": "MPL", "acc_style": 2,
        "name": "Magadh Path Labs",
        "name_local": "मगध पैथ लैब्स",
        "addr": "Kankarbagh Main Road, Patna 800020",
        "addr_local": "कंकड़बाग मुख्य मार्ग, पटना 800020",
        "city": "Patna",
        "phone": "0612 235 6614",
        "accred": "NABL Accredited (M-5583)",
        "path": {"name": "Dr. Abhishek Ranjan", "qual": "MBBS, MD (Path.)",
                 "regn": "BMC 2013/10/7728", "scrawl": "A Ranjan"},
    },
    "jeevan": {
        "abbr": "JPH", "acc_style": 1,
        "name": "Jeevan Prakash Hospital Laboratory",
        "name_local": "जीवन प्रकाश हॉस्पिटल प्रयोगशाला",
        "addr": "Bailey Road, Patna 800014",
        "addr_local": "बेली रोड, पटना 800014",
        "city": "Patna",
        "phone": "0612 222 7700",
        "accred": "Department of Laboratory Medicine",
        "path": {"name": "Dr. Shashi Bhushan Sinha", "qual": "MD, DNB (Pathology)",
                 "regn": "BMC 2000/03/0967", "scrawl": "S B Sinha"},
    },
}

JHA = "Dr. Rakesh Jha, MBBS, MD (General Medicine)"
KUMARI = "Dr. Sweta Kumari, MBBS, MD (Medicine)"
PRASAD = "Dr. Umesh Prasad, MBBS, MD, DM (Cardiology)"

WIDAL_LEGEND = [
    ("Widal slide agglutination - interpretation", "Titre"),
    ("1:80 or below", "Not significant in an endemic area"),
    ("1:160", "Suggestive, repeat after five days"),
    ("1:320 or above", "Significant, supports enteric fever"),
]

# He loses six kilos during the first illness and takes a year to regain them.
# Two febrile visits in the record - November 2021 and March 2025.
HEIGHT_CM = 171.0

VITALS = {
    1: {"weight_kg": 64.2, "bp": "106/68", "spo2": 97, "temp_f": 103.4,
        "context": "Seventh day of continuous fever, headache, abdominal discomfort."},
    2: {"weight_kg": 62.8, "bp": "104/66", "spo2": 97, "temp_f": 100.8,
        "context": "Fourth hospital day. Chest discomfort and a fast pulse, investigated."},
    3: {"weight_kg": 62.0, "bp": "110/70", "spo2": 98, "temp_f": 98.6,
        "context": "Two weeks after discharge. Afebrile, appetite returning."},
    4: {"weight_kg": 64.6, "bp": "114/72", "spo2": 99, "temp_f": 98.2,
        "context": "Fully recovered, back at work."},
    5: {"weight_kg": 66.8, "bp": "116/74", "spo2": 98, "temp_f": 98.4,
        "context": "Annual health check, first one."},
    6: {"weight_kg": 68.2, "bp": "118/76", "spo2": 99, "temp_f": 98.2,
        "context": "Well. Pre-employment medical for a new job."},
    7: {"weight_kg": 69.4, "bp": "118/74", "spo2": 98, "temp_f": 98.6,
        "context": "Annual health check."},
    8: {"weight_kg": 70.6, "bp": "120/78", "spo2": 98, "temp_f": 98.4,
        "context": "Well. Gym membership medical."},
    9: {"weight_kg": 71.2, "bp": "122/78", "spo2": 99, "temp_f": 98.2,
        "context": "Annual health check, nothing of note."},
    10: {"weight_kg": 68.4, "bp": "108/68", "spo2": 97, "temp_f": 102.2,
         "context": "Fever again after a trip. Relapse of enteric fever suspected."},
    11: {"weight_kg": 67.8, "bp": "112/70", "spo2": 98, "temp_f": 99.4,
         "context": "Fifth day of the second course. Fever breaking."},
    12: {"weight_kg": 69.6, "bp": "116/74", "spo2": 98, "temp_f": 98.4,
         "context": "Convalescent. Counts checked."},
    13: {"weight_kg": 70.8, "bp": "118/76", "spo2": 99, "temp_f": 98.2,
         "context": "Single confirmatory white count before returning to work."},
    14: {"weight_kg": 72.0, "bp": "120/78", "spo2": 98, "temp_f": 98.6,
         "context": "Annual health check. Completely recovered."},
    15: {"weight_kg": 72.6, "bp": "118/76", "spo2": 99, "temp_f": 98.2,
         "context": "Well. No further episodes."},
}

REPORTS = [
    # ---- R01 -- admission with enteric fever ---------------------------------
    {
        "collected": "2021-11-12 21:30", "reported": "2021-11-13 01:10",
        "lab": "jeevan", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": JHA, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["legend_lines", "text_result", "abnormal_shaded"],
        "note": "Leucopenia with a significant Widal titre in the second week of fever. "
                "Blood culture sent separately.",
        "sections": [
            {"panel": "CBC", "title": 0, "drop": ["ANC", "ALC", "MPV"],
             "values": {"HGB": 13.2, "RBC": 4.58, "PCV": 39.6, "MCV": 86.5, "MCH": 28.8,
                        "MCHC": 33.3, "RDW": 13.4, "WBC": 3200, "NEUT_PCT": 48,
                        "LYMPH_PCT": 44, "MONO_PCT": 6, "EOS_PCT": 1, "BASO_PCT": 1,
                        "PLT": 132000}},
            {"heading": "Fever Panel", "legend": WIDAL_LEGEND,
             "rows": [{"code": "WIDAL", "value": "Reactive, O 1:320, H 1:160",
                       "flag": "H", "trap": "text_result"},
                      {"code": "DENGUE_NS1", "value": "Negative", "trap": "text_result"},
                      {"code": "MP", "value": "Not Detected", "trap": "text_result"},
                      {"code": "CRP", "value": 92.6, "flag": "H"}]},
        ],
    },
    # ---- R02 -- fourth hospital day, cardiac workup -------------------------
    {
        "collected": "2021-11-15 14:20", "reported": "2021-11-15 18:40",
        "lab": "jeevan", "layout_style": "fax_header",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": PRASAD, "specimen": "Serum",
        "alias": 1, "traps": ["no_reference_column", "method_sub_line"],
        "note": "Faxed to the medical ward. Cardiac markers not raised; the tachycardia "
                "is attributed to fever.",
        "sections": [
            {"panel": "CARDIAC", "title": 3, "methods": True,
             "values": {"TROP_I": 0.018, "CPK_MB": 18, "NT_PROBNP": 88}},
            {"heading": "Liver Enzymes",
             "rows": [{"code": "ALT", "value": 98, "flag": "H"},
                      {"code": "AST", "value": 84, "flag": "H"},
                      {"code": "WBC", "value": 3600, "flag": "L"}]},
        ],
    },
    # ---- R03 -- two weeks after discharge -----------------------------------
    {
        "collected": "2021-12-02 09:40", "reported": "2021-12-02 15:10",
        "lab": "ganga", "layout_style": "ledger_ruled",
        "header_style": "bilingual_header", "uhid_label": "Patient ID",
        "doctor": JHA, "specimen": "Whole blood (EDTA), Serum",
        "alias": 2, "traps": ["unit_in_label"],
        "sections": [
            {"panel": "LFT", "title": 0, "drop": ["GGT"],
             "values": {"BILI_T": 0.9, "BILI_D": 0.3, "ALT": 62, "AST": 54, "ALP": 104,
                        "PROT_T": 6.8, "ALB": 3.8}},
            {"heading": "Haematology",
             "rows": [{"code": "WBC", "value": 5400}, {"code": "PLT", "value": 224000},
                      {"code": "HGB", "value": 13.0}]},
        ],
    },
    # ---- R04 -- fully recovered ---------------------------------------------
    {
        "collected": "2022-04-20 08:55", "reported": "2022-04-20 16:00",
        "lab": "magadh", "layout_style": "thermal_slip",
        "header_style": "centred_title_only", "uhid_label": "Reg. No",
        "doctor": KUMARI, "specimen": "Whole blood (EDTA)",
        "alias": 3, "traps": ["no_reference_column"],
        "sections": [
            {"heading": "Total Leucocyte Count",
             "rows": [{"code": "WBC", "value": 7200}]},
        ],
    },
    # ---- R05 -- first annual check ------------------------------------------
    {
        "collected": "2022-10-08 07:50", "reported": "2022-10-08 19:30",
        "lab": "ganga", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Patient ID",
        "doctor": KUMARI, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 0, "traps": ["merged_panel_heading", "text_result", "method_sub_line"],
        "note": "Annual health check package.",
        "sections": [
            {"panel": "CBC", "title": 2, "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "values": {"HGB": 14.6, "RBC": 4.92, "PCV": 43.4, "MCV": 88.2, "MCH": 29.7,
                        "WBC": 7600, "NEUT_PCT": 58, "LYMPH_PCT": 32, "MONO_PCT": 6,
                        "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 268000}},
            {"panel": "LIPID", "title": 0, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 172, "TRIG": 124, "HDL": 44}},
            {"panels": ["LFT", "KFT"], "heading": "Biochemistry - Liver and Renal",
             "trap": "merged_panel_heading",
             "drop": ["GGT", "AG_RATIO", "GLOB", "BILI_I", "BUN"],
             "values": {"BILI_T": 0.7, "BILI_D": 0.2, "ALT": 28, "AST": 26, "ALP": 88,
                        "PROT_T": 7.2, "ALB": 4.4,
                        "CREAT": 0.92, "UREA": 26, "UA": 5.6}},
            {"panel": "IRON", "title": 0, "drop": ["UIBC"], "methods": True,
             "values": {"FERRITIN": 88, "IRON": 96, "TIBC": 338}},
            {"panel": "VITAMIN", "title": 0,
             "values": {"VIT_D": 21.2, "VIT_B12": 356, "FOLATE": 9.0}},
            {"heading": "Other",
             "rows": [{"code": "BLOOD_GROUP", "value": "B Positive", "trap": "text_result"},
                      {"code": "HBA1C", "value": 5.2}]},
        ],
    },
    # ---- R06 -- pre-employment medical ---------------------------------------
    {
        "collected": "2023-03-16 09:10", "reported": "2023-03-16 17:20",
        "lab": "magadh", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Reg. No",
        "doctor": KUMARI, "specimen": "Serum, Urine (midstream)",
        "alias": 1, "traps": ["text_result", "flag_as_words"],
        "interpretation": "Fit for employment. No abnormality detected on this screen.",
        "sections": [
            {"panel": "SEROLOGY", "title": 1, "drop": ["WIDAL", "DENGUE_NS1",
                                                       "DENGUE_IGM", "MP"],
             "values": {"HBSAG": "Non Reactive", "ANTI_HCV": "Non Reactive",
                        "HIV": "Non Reactive", "VDRL": "Non Reactive"},
             "row_traps": {"HBSAG": "text_result"}},
            {"panel": "URINE_ROUTINE", "title": 3, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.0, "UR_SPGR": 1.018,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 2, "UR_RBC": 0, "UR_EPITH": 2}},
            {"heading": "Haematology",
             "rows": [{"code": "WBC", "value": 6900}, {"code": "HGB", "value": 14.8}]},
        ],
    },
    # ---- R07 -- annual check -------------------------------------------------
    {
        "collected": "2023-10-21 08:40", "reported": "2023-10-21 16:50",
        "lab": "ganga", "layout_style": "landscape_wide",
        "header_style": "barcode_header", "uhid_label": "Patient ID",
        "doctor": KUMARI, "specimen": "Serum",
        "alias": 2, "traps": ["prev_value_column"],
        "sections": [
            {"panel": "LIPID", "title": 2,
             "prev": {"CHOL": "172 (08/10/2022)", "TRIG": "124 (08/10/2022)",
                      "HDL": "44 (08/10/2022)"},
             "values": {"CHOL": 184, "TRIG": 142, "HDL": 42}},
            {"panel": "THYROID", "title": 0, "drop": ["FT3", "ANTI_TPO"],
             "values": {"TSH": 2.06, "T3_TOTAL": 132, "T4_TOTAL": 9.4, "FT4": 1.30}},
            {"heading": "Haematology",
             "prev": {"WBC": "6900 (16/03/2023)"},
             "rows": [{"code": "WBC", "value": 7100}]},
        ],
    },
    # ---- R08 -- gym medical --------------------------------------------------
    {
        "collected": "2024-04-11 09:25", "reported": "2024-04-11 15:40",
        "lab": "magadh", "layout_style": "typewriter_manual",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": JHA, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 3, "traps": ["no_reference_column", "sparse_panel"],
        "sections": [
            {"panel": "DIABETES", "title": 3, "drop": ["GLU_R", "INSULIN_F", "EAG"],
             "trap": "sparse_panel",
             "values": {"GLU_F": 86, "GLU_PP": 112, "HBA1C": 5.1}},
            {"heading": "Haematology",
             "rows": [{"code": "WBC", "value": 7400}, {"code": "HGB", "value": 15.0},
                      {"code": "PLT", "value": 262000},
                      {"label": "CPK - Total", "value": "186", "unit": "U/L",
                       "reference": "26 - 192"}]},
        ],
    },
    # ---- R09 -- annual check -------------------------------------------------
    {
        "collected": "2024-10-26 08:15", "reported": "2024-10-26 17:05",
        "lab": "ganga", "layout_style": "kv_header_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": KUMARI, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 0, "traps": ["footnote_marker", "ratio_no_code"],
        "footnotes": [("1", "Vitamin D remains low despite supplementation advice given "
                            "in 2022.")],
        "sections": [
            {"panel": "ELECTROLYTES", "title": 2, "drop": ["CA_ION"],
             "values": {"NA": 140, "K": 4.4, "CL": 103, "CA": 9.6, "PHOS": 3.8,
                        "MG": 2.1}},
            {"panel": "URINE_ROUTINE", "title": 5, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.5, "UR_SPGR": 1.020,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 2, "UR_RBC": 0, "UR_EPITH": 3}},
            {"heading": "Haematology and Vitamins",
             "rows": [{"code": "WBC", "value": 7800},
                      {"code": "VIT_D", "value": 19.4, "flag": "L", "marker": "1"},
                      {"label": "Neutrophil - Lymphocyte Ratio", "value": "1.8",
                       "unit": "", "reference": "1.0 - 3.0", "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R10 -- relapse ------------------------------------------------------
    {
        "collected": "2025-03-30 20:50", "reported": "2025-03-31 00:30",
        "lab": "jeevan", "layout_style": "poor_scan",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": JHA, "specimen": "Whole blood (EDTA), Serum",
        "alias": 1, "traps": ["text_result", "abnormal_shaded"],
        "stamp": "RELAPSE<br>ENTERIC FEVER",
        "sections": [
            {"heading": "Haemogram - Fever Workup",
             "rows": [{"code": "HGB", "value": 13.8}, {"code": "PCV", "value": 41.0},
                      {"code": "WBC", "value": 3600, "flag": "L"},
                      {"code": "NEUT_PCT", "value": 46},
                      {"code": "LYMPH_PCT", "value": 46, "flag": "H"},
                      {"code": "PLT", "value": 156000}]},
            {"heading": "Fever Panel",
             "rows": [{"code": "WIDAL", "value": "Reactive, O 1:160, H 1:160",
                       "flag": "H", "trap": "text_result"},
                      {"code": "DENGUE_NS1", "value": "Negative", "trap": "text_result"},
                      {"code": "CRP", "value": 74.8, "flag": "H"},
                      {"label": "Procalcitonin", "value": "1.24", "unit": "ng/mL",
                       "reference": "< 0.50", "flag": "H"}]},
        ],
    },
    # ---- R11 -- fifth day of the second course ------------------------------
    {
        "collected": "2025-04-04 07:20", "reported": "2025-04-04 11:00",
        "lab": "jeevan", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": JHA, "specimen": "Whole blood (EDTA), Serum",
        "alias": 2, "traps": ["no_header_row"],
        "sections": [
            {"heading": "Daily Counts",
             "rows": [{"code": "WBC", "value": 4400},
                      {"code": "PLT", "value": 198000},
                      {"code": "CRP", "value": 28.4, "flag": "H"}]},
        ],
    },
    # ---- R12 -- convalescent -------------------------------------------------
    {
        "collected": "2025-08-13 09:00", "reported": "2025-08-13 16:30",
        "lab": "magadh", "layout_style": "two_column",
        "header_style": "stamp_and_signature", "uhid_label": "Reg. No",
        "doctor": KUMARI, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 3, "traps": ["sno_column"], "stamp": "CONVALESCENT<br>REVIEW",
        "sections": [
            {"heading": "Liver and Renal",
             "rows": [{"code": "BILI_T", "value": 0.7}, {"code": "ALT", "value": 34},
                      {"code": "AST", "value": 30}, {"code": "ALP", "value": 92},
                      {"code": "CREAT", "value": 0.94}, {"code": "UREA", "value": 28},
                      {"label": "LDH (Lactate Dehydrogenase)", "value": "268",
                       "unit": "U/L", "reference": "140 - 280"}]},
            {"panel": "THYROID", "title": 3, "drop": ["T3_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel",
             "values": {"TSH": 2.32, "T4_TOTAL": 9.0, "FT4": 1.24}},
            {"heading": "Haematology",
             "rows": [{"code": "WBC", "value": 6200}, {"code": "HGB", "value": 14.2}]},
        ],
    },
    # ---- R13 -- one white count ---------------------------------------------
    {
        "collected": "2025-12-09 09:45", "reported": "2025-12-09 13:20",
        "lab": "ganga", "layout_style": "thermal_slip",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": KUMARI, "specimen": "Whole blood (EDTA)",
        "alias": 0, "traps": ["no_reference_column"],
        "sections": [
            {"heading": "Total Leucocyte Count",
             "rows": [{"code": "WBC", "value": 7000}]},
        ],
    },
    # ---- R14 -- annual check, two pages --------------------------------------
    {
        "collected": "2026-05-19 07:45", "reported": "2026-05-19 19:55",
        "lab": "ganga", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": KUMARI, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["method_sub_line", "not_reported"],
        "page_break_after": 3,
        "sections": [
            {"panel": "CBC", "title": 5,
             "values": {"HGB": 15.2, "RBC": 5.08, "PCV": 45.0, "MCV": 88.6, "MCH": 29.9,
                        "MCHC": 33.8, "RDW": 12.8, "WBC": 7600, "NEUT_PCT": 59,
                        "LYMPH_PCT": 31, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 272000, "MPV": 9.4}},
            {"panel": "LIPID", "title": 5, "methods": True,
             "values": {"CHOL": 190, "TRIG": 156, "HDL": 42}},
            {"panel": "DIABETES", "title": 5, "drop": ["GLU_R"],
             "values": {"GLU_F": 92, "GLU_PP": 124, "HBA1C": 5.3,
                        "INSULIN_F": "Not Reported"},
             "row_traps": {"INSULIN_F": "not_reported"}},
            {"panel": "LFT", "title": 5,
             "values": {"BILI_T": 0.8, "BILI_D": 0.2, "ALT": 30, "AST": 27, "ALP": 90,
                        "GGT": 28, "PROT_T": 7.3, "ALB": 4.5}},
            {"panel": "KFT", "title": 5,
             "values": {"CREAT": 0.96, "UREA": 29, "UA": 6.0}},
            {"heading": "Vitamins and Other",
             "rows": [{"code": "VIT_D", "value": 26.8, "flag": "L"},
                      {"code": "VIT_B12", "value": 388},
                      {"label": "Amylase", "value": "62", "unit": "U/L",
                       "reference": "28 - 100"}]},
        ],
    },
    # ---- R15 -- well ---------------------------------------------------------
    {
        "collected": "2026-09-07 08:50", "reported": "2026-09-07 16:15",
        "lab": "magadh", "layout_style": "mixed_print_hand",
        "header_style": "bilingual_header", "uhid_label": "Reg. No",
        "doctor": JHA, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["method_sub_line"],
        "sections": [
            {"panel": "ELECTROLYTES", "title": 4, "drop": ["CA_ION", "MG"],
             "values": {"NA": 141, "K": 4.3, "CL": 104, "CA": 9.5, "PHOS": 3.6}},
            {"panel": "IRON", "title": 2, "methods": True,
             "values": {"FERRITIN": 104, "IRON": 104, "TIBC": 326}},
            {"panel": "VITAMIN", "title": 4, "methods": True,
             "values": {"VIT_D": 31.2, "VIT_B12": 402, "FOLATE": 10.4}},
            {"heading": "Noted at the desk", "hand_addendum": True,
             "rows": [{"code": "WBC", "value": 7300}, {"code": "HGB", "value": 15.0}]},
        ],
    },
]
