"""Patient 3 of 20 - Nephrology. CKD stage 3a progressing to 3b, diabetic nephropathy.

Female, 58 at the first report, Hyderabad. Long-standing type 2 diabetes with established
nephropathy: creatinine 1.05 -> 1.58 over five years, eGFR 58 -> 34, proteinuria worsening
and the anaemia of chronic kidney disease appearing behind it (Hb 11.8 -> 9.7). The
setback is an acute-on-chronic injury in August 2025 after a diarrhoeal illness, with
creatinine spiking to 2.36 and recovering only partly.

Serology here is the pre-dialysis-access viral screen. Tumour markers are the uncoded
CA 125 and CEA, not PSA: the roster assigns TUMOUR MARKERS to this patient, and the only
coded marker in the vocabulary is prostate-specific.
"""

from __future__ import annotations

PATIENT = {
    "number": 3,
    "name": "Padmavathi Rangaiah",
    "sex": "F",
    "dob": "1963-08-19",
    "uhid": "GCH/442719",
    "department": "Nephrology",
    "city": "Hyderabad",
    "age_at_first": 58,
    "tracked": ["CREAT"],
    "brief": "CKD stage 3a progressing to 3b, diabetic nephropathy",
}


def check_arc(series):
    creat = [v for _, v in series["CREAT"]]
    fails = []
    if not creat[0] < 1.2:
        fails.append(f"should start in CKD 3a range, creatinine {creat[0]}")
    if not creat[-1] > 1.45:
        fails.append(f"should end in CKD 3b, creatinine {creat[-1]}")
    if not max(creat) > 2.0:
        fails.append("no acute-on-chronic spike anywhere in the series")
    if not creat[-1] > creat[0] + 0.4:
        fails.append(f"no clear progression: {creat[0]} -> {creat[-1]}")
    # the spike recovers, but never back to where it started - that is the point
    spike = creat.index(max(creat))
    if not all(v > creat[0] for v in creat[spike:]):
        fails.append("renal function returns to baseline after the acute episode")
    return fails


LABS = {
    "sujatha": {
        "abbr": "SJD", "acc_style": 0,
        "name": "Sujatha Diagnostics",
        "addr": "Road No 3, Banjara Hills, Hyderabad 500034",
        "city": "Hyderabad",
        "phone": "040 2335 7711",
        "accred": "NABL Accredited (MC-2904) | ISO 15189:2012",
        "path": {"name": "Dr. Vasantha Lakshmi Mudiraj", "qual": "MD (Pathology)",
                 "regn": "TSMC 2005/06/3318", "scrawl": "V L Mudiraj"},
    },
    "golconda": {
        "abbr": "GPL", "acc_style": 3,
        "name": "Golconda Path Labs",
        "addr": "Tolichowki Main Road, Hyderabad 500008",
        "city": "Hyderabad",
        "phone": "040 2356 4420",
        "accred": "NABL Accredited (M-6621)",
        "path": {"name": "Dr. Imran Q. Baig", "qual": "MBBS, MD (Path.)",
                 "regn": "TSMC 2010/04/7745", "scrawl": "I Baig"},
    },
    "gandhi": {
        "abbr": "GCH", "acc_style": 2,
        "name": "Gandhi City Hospital Laboratory",
        "addr": "Musheerabad, Secunderabad 500020",
        "city": "Hyderabad",
        "phone": "040 2750 3000",
        "accred": "Department of Laboratory Medicine, Nephrology Services",
        "path": {"name": "Dr. Sridevi Kandukuri", "qual": "MD, DNB (Pathology)",
                 "regn": "TSMC 2001/08/1129", "scrawl": "S Kandukuri"},
    },
}

REDDY = "Dr. G. Venkat Reddy, MBBS, MD, DM (Nephrology)"
FATIMA = "Dr. Ayesha Fatima, MBBS, MD (General Medicine)"
SASTRY = "Dr. P. V. Sastry, MBBS, DNB (Nephrology)"

CKD_LEGEND = [
    ("eGFR - CKD staging (KDIGO)", "eGFR mL/min/1.73m2"),
    ("90 and above", "Stage 1, normal or high"),
    ("45 - 59", "Stage 3a, mild to moderate reduction"),
    ("30 - 44", "Stage 3b, moderate to severe reduction"),
    ("15 - 29", "Stage 4, severe reduction"),
]

# Weight falls slowly with appetite, then drops through the 2025 diarrhoeal illness.
# BP is the hard part of this case and never fully controlled.
HEIGHT_CM = 154.0

VITALS = {
    1: {"weight_kg": 64.8, "bp": "152/94", "spo2": 98, "temp_f": 98.4,
        "context": "Referred by the diabetes clinic with a rising creatinine."},
    2: {"weight_kg": 64.2, "bp": "148/92", "spo2": 98, "temp_f": 98.2,
        "context": "ACE inhibitor started. Proteinuria being monitored."},
    3: {"weight_kg": 63.6, "bp": "146/90", "spo2": 97, "temp_f": 98.6,
        "context": "Salt restriction advised, BP still above target."},
    4: {"weight_kg": 63.1, "bp": "142/88", "spo2": 98, "temp_f": 98.4,
        "context": "Second antihypertensive added."},
    5: {"weight_kg": 62.4, "bp": "144/90", "spo2": 97, "temp_f": 98.2,
        "context": "Reports ankle swelling by evening."},
    6: {"weight_kg": 61.8, "bp": "138/86", "spo2": 98, "temp_f": 98.4,
        "context": "Annual review package. BP the best it has been."},
    7: {"weight_kg": 61.2, "bp": "140/88", "spo2": 97, "temp_f": 98.6,
        "context": "Haemoglobin falling; iron studies requested."},
    8: {"weight_kg": 60.5, "bp": "146/90", "spo2": 97, "temp_f": 98.4,
        "context": "Oral iron started for anaemia of chronic kidney disease."},
    9: {"weight_kg": 60.1, "bp": "144/88", "spo2": 97, "temp_f": 98.2,
        "context": "Vascular access discussed for the first time."},
    10: {"weight_kg": 59.4, "bp": "148/92", "spo2": 96, "temp_f": 98.6,
         "context": "Now in stage 3b. Erythropoietin considered."},
    11: {"weight_kg": 56.8, "bp": "108/68", "spo2": 96, "temp_f": 100.4,
         "context": "Acute diarrhoeal illness, dehydrated and hypotensive. Admitted."},
    12: {"weight_kg": 57.6, "bp": "126/78", "spo2": 97, "temp_f": 98.8,
         "context": "Fourth day of admission, rehydrated. Creatinine coming down."},
    13: {"weight_kg": 58.4, "bp": "138/86", "spo2": 97, "temp_f": 98.4,
         "context": "Post-discharge review. Baseline renal function not fully regained."},
    14: {"weight_kg": 58.9, "bp": "142/88", "spo2": 97, "temp_f": 98.2,
         "context": "Annual review. Pre-dialysis-access viral screen done."},
    15: {"weight_kg": 58.2, "bp": "140/86", "spo2": 97, "temp_f": 98.4,
         "context": "Stable in stage 3b. Fistula planned for next year."},
}

REPORTS = [
    # ---- R01 -- nephrology referral ----------------------------------------
    {
        "collected": "2021-10-19 08:20", "reported": "2021-10-19 18:40",
        "lab": "gandhi", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": REDDY, "specimen": "Serum, Fluoride plasma, Whole blood (EDTA)",
        "alias": 0, "traps": ["legend_lines"],
        "note": "eGFR by CKD-EPI 2009. Stage 3a; suggest three-monthly monitoring.",
        "sections": [
            {"panel": "KFT", "title": 0, "legend": CKD_LEGEND,
             "values": {"CREAT": 1.05, "UREA": 46, "UA": 6.4}},
            {"panel": "DIABETES", "title": 0, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 148, "GLU_PP": 212, "HBA1C": 8.2}},
            {"panel": "ELECTROLYTES", "title": 0, "drop": ["CA_ION"],
             "values": {"NA": 138, "K": 4.8, "CL": 104, "CA": 8.9, "PHOS": 4.2,
                        "MG": 2.1}},
        ],
    },
    # ---- R02 -- proteinuria monitoring --------------------------------------
    {
        "collected": "2022-02-08 09:10", "reported": "2022-02-08 16:20",
        "lab": "sujatha", "layout_style": "minimal_lines",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": REDDY, "specimen": "Urine (midstream), Serum",
        "alias": 1, "traps": ["unit_in_value_cell", "sample_type_row"],
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 1, "sample_row": "Urine, first morning sample",
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.0, "UR_SPGR": 1.014,
                        "UR_PROT": "++", "UR_GLU": "+", "UR_KET": "Absent",
                        "UR_PUS": 4, "UR_RBC": 1, "UR_EPITH": 3, "MICROALB": 186,
                        "ACR": 248}},
            {"heading": "Renal Chemistry",
             "rows": [{"code": "CREAT", "value": 1.12}, {"code": "UREA", "value": 48},
                      {"code": "EGFR"}]},
        ],
    },
    # ---- R03 -- thyroid check ----------------------------------------------
    {
        "collected": "2022-07-12 08:45", "reported": "2022-07-12 17:30",
        "lab": "golconda", "layout_style": "kv_header_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Reg. No",
        "doctor": FATIMA, "specimen": "Serum",
        "alias": 2, "traps": ["sparse_panel", "footnote_marker"],
        "footnotes": [("1", "Mildly raised TSH is common in chronic kidney disease; repeat "
                            "before starting thyroxine.")],
        "sections": [
            {"panel": "THYROID", "title": 2, "drop": ["FT3", "FT4", "ANTI_TPO"],
             "trap": "sparse_panel",
             "values": {"TSH": 5.62, "T3_TOTAL": 96, "T4_TOTAL": 7.2}},
            {"heading": "Renal Follow-up",
             "rows": [{"code": "CREAT", "value": 1.18, "marker": "1"},
                      {"code": "EGFR"},
                      {"label": "Urea / Creatinine Ratio", "value": "42", "unit": "",
                       "reference": "20 - 35", "flag": "H", "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R04 -- second antihypertensive -------------------------------------
    {
        "collected": "2022-12-01 08:30", "reported": "2022-12-01 15:50",
        "lab": "sujatha", "layout_style": "two_column",
        "header_style": "banner_with_qr", "uhid_label": "Patient ID",
        "doctor": SASTRY, "specimen": "Serum",
        "alias": 3, "traps": ["sno_column"],
        "sections": [
            {"panel": "ELECTROLYTES", "title": 3,
             "values": {"NA": 137, "K": 5.0, "CL": 105, "CA": 8.7, "CA_ION": 4.5,
                        "PHOS": 4.6, "MG": 2.2}},
            {"heading": "Renal Follow-up",
             "rows": [{"code": "CREAT", "value": 1.24}, {"code": "UREA", "value": 52},
                      {"code": "BUN"}, {"code": "EGFR"},
                      {"label": "Bicarbonate (HCO3)", "value": "21.4", "unit": "mmol/L",
                       "reference": "22 - 29", "flag": "L"}]},
        ],
    },
    # ---- R05 -- oedema ------------------------------------------------------
    {
        "collected": "2023-05-04 09:05", "reported": "2023-05-04 16:10",
        "lab": "golconda", "layout_style": "carbon_copy",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": REDDY, "specimen": "Serum",
        "alias": 0, "traps": ["range_with_unit", "method_sub_line"],
        "sections": [
            {"panel": "LFT", "title": 1, "methods": True, "drop": ["GGT"],
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 22, "AST": 26, "ALP": 92,
                        "PROT_T": 6.4, "ALB": 3.4}},
            {"heading": "Renal Follow-up", "methods": True,
             "rows": [{"code": "CREAT", "value": 1.31}, {"code": "EGFR"},
                      {"label": "Spot Urinary Sodium", "value": "38", "unit": "mmol/L",
                       "reference": "40 - 220", "flag": "L"}]},
        ],
    },
    # ---- R06 -- annual review ----------------------------------------------
    {
        "collected": "2023-10-17 07:50", "reported": "2023-10-17 19:30",
        "lab": "gandhi", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Hospital No",
        "doctor": REDDY, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["merged_panel_heading", "text_result", "method_sub_line"],
        "note": "Annual chronic kidney disease review package.",
        "sections": [
            {"panel": "CBC", "title": 1, "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "values": {"HGB": 11.2, "RBC": 3.86, "PCV": 34.2, "MCV": 88.6, "MCH": 29.0,
                        "WBC": 6800, "NEUT_PCT": 62, "LYMPH_PCT": 28, "MONO_PCT": 6,
                        "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 232000}},
            {"panel": "LIPID", "title": 2, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 204, "TRIG": 188, "HDL": 44}},
            {"panels": ["LFT", "ELECTROLYTES"], "heading": "Biochemistry - Liver and Minerals",
             "trap": "merged_panel_heading",
             "drop": ["GGT", "AG_RATIO", "GLOB", "CA_ION", "MG", "BILI_I"],
             "values": {"BILI_T": 0.5, "BILI_D": 0.2, "ALT": 24, "AST": 28, "ALP": 98,
                        "PROT_T": 6.3, "ALB": 3.3,
                        "NA": 136, "K": 5.1, "CL": 106, "CA": 8.6, "PHOS": 4.8}},
            {"panel": "IRON", "title": 4, "drop": ["UIBC"], "methods": True,
             "values": {"FERRITIN": 42, "IRON": 48, "TIBC": 386}},
            {"panel": "VITAMIN", "title": 4, "methods": True,
             "values": {"VIT_D": 14.2, "VIT_B12": 286, "FOLATE": 5.2}},
            {"heading": "Other Investigations",
             "rows": [{"code": "BLOOD_GROUP", "value": "A Positive", "trap": "text_result"},
                      {"code": "HBA1C", "value": 7.8}]},
        ],
    },
    # ---- R07 -- anaemia appearing ------------------------------------------
    {
        "collected": "2024-03-06 08:40", "reported": "2024-03-06 17:15",
        "lab": "sujatha", "layout_style": "clean_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": SASTRY, "specimen": "Serum, Urine (midstream)",
        "alias": 2, "traps": ["ambiguous_abbreviation"],
        "sections": [
            {"panel": "THYROID", "title": 0, "drop": ["T3_TOTAL", "ANTI_TPO"],
             "values": {"TSH": 4.92, "T4_TOTAL": 7.6, "FT3": 2.6, "FT4": 1.02}},
            {"panel": "URINE_ROUTINE", "title": 3,
             "labels": {"UR_PROT": "ALBUMIN"},
             "row_traps": {"UR_PROT": "ambiguous_abbreviation"},
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 5.5, "UR_SPGR": 1.012,
                        "UR_PROT": "++", "UR_GLU": "Trace", "UR_KET": "Absent",
                        "UR_PUS": 5, "UR_RBC": 2, "UR_EPITH": 4, "MICROALB": 268,
                        "ACR": 342}},
        ],
    },
    # ---- R08 -- iron started -----------------------------------------------
    {
        "collected": "2024-08-21 09:00", "reported": "2024-08-21 16:45",
        "lab": "golconda", "layout_style": "kv_header_table",
        "header_style": "centred_title_only", "uhid_label": "Reg. No",
        "doctor": REDDY, "specimen": "Serum, Fluoride plasma",
        "alias": 3, "traps": ["not_reported"],
        "sections": [
            {"panel": "DIABETES", "title": 3, "drop": ["GLU_R"],
             "values": {"GLU_F": 136, "GLU_PP": 196, "HBA1C": 7.6,
                        "INSULIN_F": "Not Reported"},
             "row_traps": {"INSULIN_F": "not_reported"}},
            {"panel": "THYROID", "title": 4, "drop": ["T3_TOTAL", "T4_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel", "values": {"TSH": 4.48, "FT4": 1.08}},
            {"heading": "Renal Follow-up",
             "rows": [{"code": "CREAT", "value": 1.42}, {"code": "EGFR"}]},
        ],
    },
    # ---- R09 -- access discussed -------------------------------------------
    {
        "collected": "2025-01-15 10:10", "reported": "2025-01-15 15:40",
        "lab": "sujatha", "layout_style": "mixed_print_hand",
        "header_style": "stamp_and_signature", "uhid_label": "Patient ID",
        "doctor": SASTRY, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["text_result"], "stamp": "NEPHROLOGY<br>REVIEWED",
        "sections": [
            {"heading": "Haematology",
             "rows": [{"code": "HGB", "value": 10.4, "flag": "L"},
                      {"code": "ESR", "value": 34, "flag": "H"},
                      {"code": "RETIC", "value": 1.2},
                      {"code": "PERIPH_SMEAR",
                       "value": "Normocytic normochromic anaemia. No abnormal cells.",
                       "trap": "text_result"}]},
            {"heading": "Written in at the clinic", "hand_addendum": True,
             "rows": [{"code": "CREAT", "value": 1.48}, {"code": "K", "value": 5.2}]},
        ],
    },
    # ---- R10 -- stage 3b ----------------------------------------------------
    {
        "collected": "2025-05-28 08:25", "reported": "2025-05-28 18:20",
        "lab": "gandhi", "layout_style": "poor_scan",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": REDDY, "specimen": "Serum, Urine (midstream)",
        "alias": 1, "traps": ["legend_lines", "text_result"],
        "stamp": "STAGE 3b<br>CONFIRMED",
        "sections": [
            {"panel": "KFT", "title": 4, "legend": CKD_LEGEND,
             "values": {"CREAT": 1.62, "UREA": 68, "UA": 7.4}},
            {"panel": "URINE_ROUTINE", "title": 5, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Yellow", "UR_PH": 5.5, "UR_SPGR": 1.010,
                        "UR_PROT": "+++", "UR_GLU": "Trace", "UR_KET": "Absent",
                        "UR_PUS": 6, "UR_RBC": 3, "UR_EPITH": 4}},
        ],
    },
    # ---- R11 -- acute on chronic --------------------------------------------
    {
        "collected": "2025-08-09 21:50", "reported": "2025-08-10 01:15",
        "lab": "gandhi", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": REDDY, "specimen": "Serum, Whole blood (EDTA), Stool",
        "alias": 2, "traps": ["sno_column", "text_result", "footnote_marker"],
        "footnotes": [("1", "Values telephoned to the admitting registrar at 01:05 hrs.")],
        "note": "Acute kidney injury on chronic kidney disease following acute "
                "gastroenteritis. Rehydration started.",
        "sections": [
            {"heading": "Emergency Renal Panel",
             "rows": [{"code": "CREAT", "value": 2.36, "flag": "H", "marker": "1"},
                      {"code": "UREA", "value": 112, "flag": "H"},
                      {"code": "BUN"}, {"code": "EGFR"},
                      {"code": "NA", "value": 132, "flag": "L"},
                      {"code": "K", "value": 5.6, "flag": "H"},
                      {"label": "Stool Occult Blood", "value": "Negative", "unit": "",
                       "reference": "Negative", "trap": "text_result"}]},
            {"panel": "CBC", "title": 5, "drop": ["ANC", "ALC", "MPV"],
             "values": {"HGB": 9.8, "RBC": 3.42, "PCV": 30.1, "MCV": 88.0, "MCH": 28.7,
                        "MCHC": 32.6, "RDW": 15.2, "WBC": 13400, "NEUT_PCT": 80,
                        "LYMPH_PCT": 14, "MONO_PCT": 4, "EOS_PCT": 2, "BASO_PCT": 0,
                        "PLT": 268000}},
        ],
    },
    # ---- R12 -- fourth day, one test ---------------------------------------
    {
        "collected": "2025-08-13 06:40", "reported": "2025-08-13 10:05",
        "lab": "gandhi", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": REDDY, "specimen": "Serum",
        "alias": 3, "traps": ["no_header_row"],
        "sections": [
            {"heading": "Serum Creatinine - Daily",
             "rows": [{"code": "CREAT", "value": 1.84, "flag": "H"}]},
        ],
    },
    # ---- R13 -- post-discharge ----------------------------------------------
    {
        "collected": "2025-11-04 09:15", "reported": "2025-11-04 14:30",
        "lab": "golconda", "layout_style": "minimal_lines",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": SASTRY, "specimen": "Serum",
        "alias": 0, "traps": ["method_sub_line"],
        "sections": [
            {"heading": "Creatinine, Serum", "methods": True,
             "rows": [{"code": "CREAT", "value": 1.71, "flag": "H"}]},
        ],
    },
    # ---- R14 -- annual review with the access screen ------------------------
    {
        "collected": "2026-03-19 07:45", "reported": "2026-03-19 20:05",
        "lab": "gandhi", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "Hospital No",
        "doctor": REDDY, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 2, "traps": ["text_result", "footnote_marker"],
        "page_break_after": 3,
        "footnotes": [("1", "Viral screen performed as part of pre-dialysis-access workup.")],
        "sections": [
            {"panel": "CBC", "title": 3,
             "values": {"HGB": 9.9, "RBC": 3.48, "PCV": 30.8, "MCV": 88.5, "MCH": 28.4,
                        "MCHC": 32.1, "RDW": 15.6, "WBC": 7200, "NEUT_PCT": 64,
                        "LYMPH_PCT": 26, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 244000, "MPV": 9.4}},
            {"panel": "LIPID", "title": 5,
             "values": {"CHOL": 196, "TRIG": 204, "HDL": 42}},
            {"panel": "DIABETES", "title": 5, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 128, "GLU_PP": 184, "HBA1C": 7.4}},
            {"panel": "LFT", "title": 4,
             "values": {"BILI_T": 0.5, "BILI_D": 0.2, "ALT": 21, "AST": 25, "ALP": 104,
                        "GGT": 38, "PROT_T": 6.2, "ALB": 3.2}},
            {"panel": "KFT", "title": 5,
             "values": {"CREAT": 1.74, "UREA": 74, "UA": 7.6}},
            {"panel": "SEROLOGY", "title": 4, "drop": ["WIDAL", "DENGUE_NS1",
                                                       "DENGUE_IGM", "MP"],
             "values": {"HBSAG": "Non Reactive", "ANTI_HCV": "Non Reactive",
                        "HIV": "Non Reactive", "VDRL": "Non Reactive"},
             "row_traps": {"HBSAG": "text_result"}},
        ],
    },
    # ---- R15 -- stable in 3b -------------------------------------------------
    {
        "collected": "2026-08-25 08:35", "reported": "2026-08-25 17:40",
        "lab": "sujatha", "layout_style": "two_column",
        "header_style": "stamp_and_signature", "uhid_label": "Patient ID",
        "doctor": REDDY, "specimen": "Serum", "stamp": "VERIFIED<br>SUJATHA",
        "alias": 3, "traps": ["method_sub_line"],
        "sections": [
            {"panel": "IRON", "title": 5, "methods": True,
             "values": {"FERRITIN": 96, "IRON": 62, "TIBC": 348}},
            {"panel": "VITAMIN", "title": 1, "methods": True,
             "values": {"VIT_D": 26.4, "VIT_B12": 318, "FOLATE": 6.6}},
            {"heading": "Tumour Markers",
             "rows": [{"label": "CA 125", "value": "18.4", "unit": "U/mL",
                       "reference": "< 35.0"},
                      {"label": "CEA (Carcinoembryonic Antigen)", "value": "2.1",
                       "unit": "ng/mL", "reference": "< 5.0"}]},
            {"heading": "Renal Follow-up",
             "rows": [{"code": "CREAT", "value": 1.58}, {"code": "EGFR"}]},
        ],
    },
]
