"""Patient 10 of 20 - Cardiology. Hypertension with dyslipidaemia, stable on treatment.

Male, 48 at the first report, Bhopal. Hypertension found at a workplace camp with
cholesterol 268 and hs-CRP 4.2. Amlodipine and a statin bring both under control over two
years. The setback is 2024: he stops both tablets for five months after reading about side
effects, blood pressure reaches 168/104 at the clinic and cholesterol returns to 242. Back
on treatment he ends the five years controlled but not as well as in 2023.
"""

from __future__ import annotations

PATIENT = {
    "number": 10,
    "name": "Devendra Singh Thakur",
    "sex": "M",
    "dob": "1973-03-05",
    "uhid": "NBH/409376",
    "department": "Cardiology",
    "city": "Bhopal",
    "age_at_first": 48,
    "tracked": ["CHOL"],
    "brief": "Hypertension with dyslipidaemia, stable on treatment",
}


def check_arc(series):
    chol = [v for _, v in series["CHOL"]]
    fails = []
    if not chol[0] > 250:
        fails.append(f"should start clearly dyslipidaemic, cholesterol {chol[0]}")
    if not min(chol) < 180:
        fails.append(f"treatment never controls it, best {min(chol)}")
    if not any(chol[j] > min(chol[:j]) + 50 for j in range(1, len(chol))):
        fails.append("no relapse when the tablets were stopped")
    if not chol[-1] < 210:
        fails.append(f"should end controlled, cholesterol {chol[-1]}")
    return fails


LABS = {
    "narmada": {
        "abbr": "NDC", "acc_style": 0,
        "name": "Narmada Diagnostic Clinic",
        "name_local": "नर्मदा डायग्नोस्टिक क्लिनिक",
        "addr": "MP Nagar Zone 1, Bhopal 462011",
        "addr_local": "एमपी नगर जोन 1, भोपाल 462011",
        "city": "Bhopal",
        "phone": "0755 242 6680",
        "accred": "NABL Accredited (MC-9033) | ISO 15189:2012",
        "path": {"name": "Dr. Alka Dubey", "qual": "MD (Pathology)",
                 "regn": "MPMC 2007/03/5514", "scrawl": "A Dubey"},
    },
    "bhojpur": {
        "abbr": "BPL", "acc_style": 3,
        "name": "Bhojpur Path Services",
        "name_local": "भोजपुर पैथ सर्विसेज",
        "addr": "New Market, TT Nagar, Bhopal 462003",
        "addr_local": "न्यू मार्केट, टीटी नगर, भोपाल 462003",
        "city": "Bhopal",
        "phone": "0755 255 4471",
        "accred": "NABL Accredited (M-6627)",
        "path": {"name": "Dr. Imtiaz Qureshi", "qual": "MBBS, MD (Path.)",
                 "regn": "MPMC 2011/08/8840", "scrawl": "I Qureshi"},
    },
    "nirogdham": {
        "abbr": "NBH", "acc_style": 2,
        "name": "Nirogdham Heart Hospital Laboratory",
        "name_local": "निरोगधाम हार्ट हॉस्पिटल प्रयोगशाला",
        "addr": "Hoshangabad Road, Bhopal 462026",
        "addr_local": "होशंगाबाद रोड, भोपाल 462026",
        "city": "Bhopal",
        "phone": "0755 400 2200",
        "accred": "Department of Laboratory Medicine, Cardiac Services",
        "path": {"name": "Dr. Sandeep Chouhan", "qual": "MD, DNB (Pathology)",
                 "regn": "MPMC 2001/05/1372", "scrawl": "S Chouhan"},
    },
}

TOMAR = "Dr. Vivek Tomar, MBBS, MD, DM (Cardiology)"
SAXENA = "Dr. Neelima Saxena, MBBS, MD (Medicine)"
KURESHI = "Dr. Arif Kureshi, MBBS, DNB (Cardiology)"

BP_LEGEND = [
    ("Cholesterol and cardiovascular risk", "Total Cholesterol"),
    ("Below 200 mg/dL", "Desirable"),
    ("200 - 239 mg/dL", "Borderline high"),
    ("240 mg/dL and above", "High"),
]

# Blood pressure is the story in the vitals: 162/102 untreated, controlled to
# 126/80, back to 168/104 in the year off treatment, then controlled again.
HEIGHT_CM = 170.0

VITALS = {
    1: {"weight_kg": 84.6, "bp": "162/102", "spo2": 97, "temp_f": 98.4,
        "context": "Workplace camp. Blood pressure high on three readings."},
    2: {"weight_kg": 83.8, "bp": "150/96", "spo2": 98, "temp_f": 98.2,
        "context": "Amlodipine 5 mg started, salt reduced."},
    3: {"weight_kg": 82.4, "bp": "142/90", "spo2": 98, "temp_f": 98.6,
        "context": "Statin added for cholesterol."},
    4: {"weight_kg": 81.0, "bp": "136/86", "spo2": 98, "temp_f": 98.4,
        "context": "Both tablets tolerated. Walking daily."},
    5: {"weight_kg": 79.8, "bp": "130/84", "spo2": 99, "temp_f": 98.2,
        "context": "Annual review. Control good."},
    6: {"weight_kg": 78.6, "bp": "126/80", "spo2": 98, "temp_f": 98.4,
        "context": "Best figures of the five years."},
    7: {"weight_kg": 79.2, "bp": "128/82", "spo2": 98, "temp_f": 98.6,
        "context": "Stable. Six-monthly review."},
    8: {"weight_kg": 81.4, "bp": "146/92", "spo2": 97, "temp_f": 98.4,
        "context": "Admits stopping both tablets three months ago."},
    9: {"weight_kg": 83.9, "bp": "168/104", "spo2": 97, "temp_f": 98.2,
        "context": "Headache and epistaxis. Blood pressure dangerously high, restarted."},
    10: {"weight_kg": 83.1, "bp": "152/94", "spo2": 98, "temp_f": 98.6,
         "context": "Back on treatment for six weeks, improving."},
    11: {"weight_kg": 82.0, "bp": "140/88", "spo2": 98, "temp_f": 98.4,
         "context": "Second antihypertensive added."},
    12: {"weight_kg": 80.8, "bp": "134/86", "spo2": 98, "temp_f": 98.2,
         "context": "Approaching target again."},
    13: {"weight_kg": 80.2, "bp": "132/84", "spo2": 99, "temp_f": 98.4,
         "context": "Single repeat cholesterol before the annual visit."},
    14: {"weight_kg": 79.4, "bp": "130/82", "spo2": 98, "temp_f": 98.6,
         "context": "Annual review. Controlled, adherence discussed at length."},
    15: {"weight_kg": 78.9, "bp": "128/82", "spo2": 98, "temp_f": 98.2,
         "context": "Stable. Understands the tablets are lifelong."},
}

REPORTS = [
    # ---- R01 -- the camp ----------------------------------------------------
    {
        "collected": "2021-10-16 08:40", "reported": "2021-10-16 17:50",
        "lab": "narmada", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Patient ID",
        "doctor": SAXENA, "specimen": "Serum, Fluoride plasma",
        "alias": 0, "traps": ["legend_lines"],
        "interpretation": "Dyslipidaemia with a raised high-sensitivity CRP in a newly "
                          "hypertensive man. Ten year cardiovascular risk is appreciable; "
                          "lifestyle change plus statin therapy is advised.",
        "sections": [
            {"panel": "LIPID", "title": 0, "legend": BP_LEGEND,
             "values": {"CHOL": 268, "TRIG": 242, "HDL": 34}},
            {"panel": "DIABETES", "title": 0, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 104, "GLU_PP": 148, "HBA1C": 5.8}},
            {"panel": "INFLAMMATION", "title": 0, "drop": ["RA_FACTOR", "ASO"],
             "values": {"CRP": 5.8, "HS_CRP": 4.20}},
        ],
    },
    # ---- R02 -- amlodipine started ------------------------------------------
    {
        "collected": "2022-01-24 09:10", "reported": "2022-01-24 15:40",
        "lab": "bhojpur", "layout_style": "ledger_ruled",
        "header_style": "centred_title_only", "uhid_label": "Reg. No",
        "doctor": SAXENA, "specimen": "Serum, Urine (midstream)",
        "alias": 1, "traps": ["unit_in_label", "sample_type_row"],
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 1, "sample_row": "Urine, Midstream",
             "values": {"UR_COLOUR": "Yellow", "UR_PH": 6.0, "UR_SPGR": 1.022,
                        "UR_PROT": "Trace", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 3, "UR_RBC": 1, "UR_EPITH": 3, "MICROALB": 24,
                        "ACR": 28}},
            {"panel": "KFT", "title": 0,
             "values": {"CREAT": 1.06, "UREA": 34, "UA": 7.0}},
        ],
    },
    # ---- R03 -- statin added ------------------------------------------------
    {
        "collected": "2022-06-08 08:30", "reported": "2022-06-08 16:20",
        "lab": "narmada", "layout_style": "landscape_wide",
        "header_style": "barcode_header", "uhid_label": "Patient ID",
        "doctor": TOMAR, "specimen": "Serum",
        "alias": 2, "traps": ["prev_value_column", "method_sub_line"],
        "sections": [
            {"panel": "LIPID", "title": 2, "methods": True,
             "prev": {"CHOL": "268 (16/10/2021)", "TRIG": "242 (16/10/2021)",
                      "HDL": "34 (16/10/2021)"},
             "values": {"CHOL": 228, "TRIG": 196, "HDL": 36}},
            {"panel": "LFT", "title": 0,
             "drop": ["GGT", "BILI_I", "BILI_D", "PROT_T", "GLOB", "AG_RATIO"],
             "values": {"BILI_T": 0.8, "ALT": 38, "AST": 32, "ALP": 88, "ALB": 4.4}},
        ],
    },
    # ---- R04 -- tolerating both ---------------------------------------------
    {
        "collected": "2022-11-19 09:00", "reported": "2022-11-19 16:50",
        "lab": "bhojpur", "layout_style": "typewriter_manual",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": TOMAR, "specimen": "Serum",
        "alias": 3, "traps": ["no_reference_column"],
        "sections": [
            {"panel": "THYROID", "title": 1, "drop": ["FT3", "ANTI_TPO"],
             "values": {"TSH": 2.44, "T3_TOTAL": 124, "T4_TOTAL": 8.8, "FT4": 1.26}},
            {"heading": "Lipid Recheck",
             "rows": [{"code": "CHOL", "value": 204}, {"code": "TRIG", "value": 168},
                      {"code": "HDL", "value": 38}, {"code": "LDL"}]},
        ],
    },
    # ---- R05 -- annual review -----------------------------------------------
    {
        "collected": "2023-04-03 07:50", "reported": "2023-04-03 19:20",
        "lab": "narmada", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Patient ID",
        "doctor": TOMAR, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 0, "traps": ["merged_panel_heading", "text_result", "method_sub_line"],
        "note": "Annual cardiovascular review package.",
        "sections": [
            {"panel": "CBC", "title": 1, "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "values": {"HGB": 15.1, "RBC": 5.06, "PCV": 45.2, "MCV": 89.3, "MCH": 29.8,
                        "WBC": 7400, "NEUT_PCT": 60, "LYMPH_PCT": 30, "MONO_PCT": 6,
                        "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 254000}},
            {"panels": ["LFT", "ELECTROLYTES"], "heading": "Biochemistry - Liver and Minerals",
             "trap": "merged_panel_heading",
             "drop": ["GGT", "AG_RATIO", "GLOB", "BILI_I", "CA_ION", "MG"],
             "values": {"BILI_T": 0.7, "BILI_D": 0.2, "ALT": 34, "AST": 29, "ALP": 84,
                        "PROT_T": 7.3, "ALB": 4.3,
                        "NA": 141, "K": 4.1, "CL": 104, "CA": 9.4, "PHOS": 3.4}},
            {"panel": "IRON", "title": 2, "drop": ["UIBC"], "methods": True,
             "values": {"FERRITIN": 168, "IRON": 102, "TIBC": 330}},
            {"panel": "VITAMIN", "title": 2,
             "values": {"VIT_D": 20.4, "VIT_B12": 312, "FOLATE": 8.0}},
            {"heading": "Lipids and Other",
             "rows": [{"code": "CHOL", "value": 182}, {"code": "TRIG", "value": 152},
                      {"code": "HDL", "value": 40}, {"code": "LDL"},
                      {"code": "BLOOD_GROUP", "value": "A Positive",
                       "trap": "text_result"},
                      {"code": "HBA1C", "value": 5.6}]},
        ],
    },
    # ---- R06 -- best figures ------------------------------------------------
    {
        "collected": "2023-10-11 08:20", "reported": "2023-10-11 17:00",
        "lab": "nirogdham", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": TOMAR, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 1, "traps": ["flag_as_words"],
        "sections": [
            {"heading": "Lipid Screen",
             "rows": [{"code": "CHOL", "value": 168}, {"code": "TRIG", "value": 138},
                      {"code": "HDL", "value": 44}, {"code": "LDL"},
                      {"label": "Apolipoprotein B", "value": "82", "unit": "mg/dL",
                       "reference": "< 90"}]},
            {"panel": "INFLAMMATION", "title": 1, "drop": ["RA_FACTOR", "ASO"],
             "values": {"CRP": 2.4, "HS_CRP": 1.10}},
        ],
    },
    # ---- R07 -- six-monthly review ------------------------------------------
    {
        "collected": "2024-03-27 09:25", "reported": "2024-03-27 15:55",
        "lab": "bhojpur", "layout_style": "thermal_slip",
        "header_style": "centred_title_only", "uhid_label": "Reg. No",
        "doctor": SAXENA, "specimen": "Serum",
        "alias": 2, "traps": ["no_reference_column"],
        "sections": [
            {"heading": "Total Cholesterol",
             "rows": [{"code": "CHOL", "value": 176}]},
        ],
    },
    # ---- R08 -- off treatment -----------------------------------------------
    {
        "collected": "2024-09-14 08:55", "reported": "2024-09-14 17:30",
        "lab": "narmada", "layout_style": "kv_header_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": TOMAR, "specimen": "Serum, Urine (midstream)",
        "alias": 3, "traps": ["abnormal_shaded", "ambiguous_abbreviation"],
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 3, "drop": ["MICROALB", "ACR"],
             "labels": {"UR_PROT": "ALB"},
             "row_traps": {"UR_PROT": "ambiguous_abbreviation"},
             "values": {"UR_COLOUR": "Yellow", "UR_PH": 5.5, "UR_SPGR": 1.024,
                        "UR_PROT": "Trace", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 4, "UR_RBC": 1, "UR_EPITH": 3}},
            {"heading": "Lipid Profile",
             "rows": [{"code": "CHOL", "value": 224, "flag": "H"},
                      {"code": "TRIG", "value": 208, "flag": "H"},
                      {"code": "HDL", "value": 36, "flag": "L"},
                      {"code": "LDL"}, {"code": "NON_HDL"}]},
        ],
    },
    # ---- R09 -- hypertensive urgency ----------------------------------------
    {
        "collected": "2025-01-08 21:15", "reported": "2025-01-08 23:50",
        "lab": "nirogdham", "layout_style": "poor_scan",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": KURESHI, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 0, "traps": ["sno_column", "text_result"],
        "stamp": "URGENT<br>CARDIOLOGY",
        "note": "Blood pressure 168/104 at presentation. No end-organ damage on this "
                "screen; antihypertensive therapy restarted.",
        "sections": [
            {"panel": "KFT", "title": 3,
             "values": {"CREAT": 1.16, "UREA": 38, "UA": 7.4}},
            {"panel": "ELECTROLYTES", "title": 1, "drop": ["CA_ION"],
             "values": {"NA": 139, "K": 3.9, "CL": 103, "CA": 9.2, "PHOS": 3.2,
                        "MG": 2.0}},
            {"heading": "Cardiac and Urine Screen",
             "rows": [{"code": "TROP_I", "value": 0.014},
                      {"code": "BLOOD_GROUP", "value": "A Positive",
                       "trap": "text_result"},
                      {"code": "URINE_CULTURE",
                       "value": "No growth after 48 hours of aerobic incubation.",
                       "trap": "text_result"},
                      {"code": "PERIPH_SMEAR",
                       "value": "Normocytic normochromic. No abnormal cells seen.",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R10 -- six weeks back on treatment ---------------------------------
    {
        "collected": "2025-05-20 08:45", "reported": "2025-05-20 16:15",
        "lab": "narmada", "layout_style": "duplicate_watermark",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": TOMAR, "specimen": "Serum",
        "alias": 1, "traps": ["prev_value_column"],
        "note": "Duplicate copy issued for the patient's file.",
        "sections": [
            {"heading": "Lipid Profile - Comparative",
             "prev": {"CHOL": "242 (08/01/2025)", "TRIG": "224 (08/01/2025)",
                      "HDL": "35 (08/01/2025)"},
             "rows": [{"code": "CHOL", "value": 212, "flag": "H"},
                      {"code": "TRIG", "value": 186, "flag": "H"},
                      {"code": "HDL", "value": 38, "flag": "L"},
                      {"code": "LDL"}, {"code": "NON_HDL"}]},
            {"heading": "Liver Enzymes on Statin",
             "rows": [{"code": "ALT", "value": 42}, {"code": "AST", "value": 34},
                      {"code": "ALP", "value": 90},
                      {"label": "CPK - Total", "value": "164", "unit": "U/L",
                       "reference": "26 - 192"}]},
        ],
    },
    # ---- R11 -- second antihypertensive -------------------------------------
    {
        "collected": "2025-09-30 09:05", "reported": "2025-09-30 16:40",
        "lab": "bhojpur", "layout_style": "two_column",
        "header_style": "bilingual_header", "uhid_label": "Reg. No",
        "doctor": KURESHI, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["sno_column", "footnote_marker"],
        "footnotes": [("1", "ASO and RA factor requested for joint pains, which settled "
                            "without treatment.")],
        "sections": [
            {"panel": "INFLAMMATION", "title": 3,
             "values": {"CRP": 3.6, "HS_CRP": 2.10, "RA_FACTOR": 9.4, "ASO": 118},
             "row_traps": {"ASO": "footnote_marker"}},
            {"panel": "THYROID", "title": 4, "drop": ["T3_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel",
             "values": {"TSH": 2.86, "T4_TOTAL": 8.4, "FT4": 1.20}},
        ],
    },
    # ---- R12 -- approaching target ------------------------------------------
    {
        "collected": "2026-01-14 08:35", "reported": "2026-01-14 17:20",
        "lab": "nirogdham", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Hospital No",
        "doctor": TOMAR, "specimen": "Whole blood (EDTA), Serum",
        "alias": 3, "traps": ["unit_in_label", "not_reported"],
        "sections": [
            {"panel": "CBC", "title": 4, "drop": ["ANC", "ALC"],
             "values": {"HGB": 14.8, "RBC": 4.94, "PCV": 44.0, "MCV": 89.1, "MCH": 30.0,
                        "MCHC": 33.6, "RDW": 13.0, "WBC": 7000, "NEUT_PCT": 59,
                        "LYMPH_PCT": 31, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 248000, "MPV": 9.7}},
            {"heading": "Lipid Profile",
             "rows": [{"code": "CHOL", "value": 194}, {"code": "TRIG", "value": 164},
                      {"code": "HDL", "value": 40}, {"code": "LDL"},
                      {"code": "INSULIN_F", "value": "Not Reported",
                       "trap": "not_reported"}]},
        ],
    },
    # ---- R13 -- one repeat cholesterol --------------------------------------
    {
        "collected": "2026-04-29 09:50", "reported": "2026-04-29 13:30",
        "lab": "bhojpur", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": SAXENA, "specimen": "Serum",
        "alias": 0, "traps": ["no_header_row"],
        "sections": [
            {"heading": "Total Cholesterol",
             "rows": [{"code": "CHOL", "value": 188}]},
        ],
    },
    # ---- R14 -- annual review, two pages ------------------------------------
    {
        "collected": "2026-07-22 07:45", "reported": "2026-07-22 20:05",
        "lab": "narmada", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": TOMAR, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["ratio_no_code", "method_sub_line"],
        "page_break_after": 3,
        "sections": [
            {"panel": "CBC", "title": 5,
             "values": {"HGB": 14.9, "RBC": 4.98, "PCV": 44.4, "MCV": 89.2, "MCH": 29.9,
                        "MCHC": 33.6, "RDW": 12.9, "WBC": 6800, "NEUT_PCT": 58,
                        "LYMPH_PCT": 32, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 246000, "MPV": 9.6}},
            {"panel": "LIPID", "title": 5, "methods": True,
             "values": {"CHOL": 182, "TRIG": 148, "HDL": 42}},
            {"panel": "DIABETES", "title": 3, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 102, "GLU_PP": 142, "HBA1C": 5.9}},
            {"panel": "LFT", "title": 5,
             "values": {"BILI_T": 0.7, "BILI_D": 0.2, "ALT": 36, "AST": 30, "ALP": 86,
                        "GGT": 46, "PROT_T": 7.3, "ALB": 4.3}},
            {"panel": "KFT", "title": 5,
             "values": {"CREAT": 1.10, "UREA": 35, "UA": 6.8}},
            {"heading": "Derived Indices",
             "rows": [{"label": "TG / HDL Ratio", "value": "3.5", "unit": "",
                       "reference": "< 3.5", "trap": "ratio_no_code"},
                      {"label": "Lipoprotein (a)", "value": "26", "unit": "mg/dL",
                       "reference": "< 30"}]},
        ],
    },
    # ---- R15 -- stable ------------------------------------------------------
    {
        "collected": "2026-09-11 08:50", "reported": "2026-09-11 16:30",
        "lab": "nirogdham", "layout_style": "mixed_print_hand",
        "header_style": "stamp_and_signature", "uhid_label": "Hospital No",
        "doctor": TOMAR, "specimen": "Serum", "stamp": "CARDIOLOGY<br>REVIEWED",
        "alias": 2, "traps": ["method_sub_line"],
        "sections": [
            {"panel": "IRON", "title": 4, "methods": True,
             "values": {"FERRITIN": 152, "IRON": 96, "TIBC": 336}},
            {"panel": "VITAMIN", "title": 4, "methods": True,
             "values": {"VIT_D": 29.8, "VIT_B12": 356, "FOLATE": 8.6}},
            {"heading": "Noted at the clinic", "hand_addendum": True,
             "rows": [{"code": "CHOL", "value": 186}, {"code": "HDL", "value": 43}]},
        ],
    },
]
