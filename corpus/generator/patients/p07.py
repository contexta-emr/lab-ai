"""Patient 7 of 20 - Endocrinology. Hypothyroidism, dose titration to euthyroid.

Female, 34 at the first report, Lucknow. Presents with TSH 42.6, free T4 0.52 and strongly
positive anti-TPO - autoimmune hypothyroidism. Thyroxine is titrated 50 -> 75 -> 100 mcg
over a year and she reaches 2.4. The setback is 2024, when she stops the tablet for four
months believing she is cured and TSH climbs back to 14.8; it is brought down again and
she ends stable at 2.1.

Cardiac markers appear here as the palpitation workup during the over-replaced spell in
2023, when TSH was suppressed to 0.09.
"""

from __future__ import annotations

PATIENT = {
    "number": 7,
    "name": "Shalini Awasthi",
    "sex": "F",
    "dob": "1987-02-25",
    "uhid": "MLC/607318",
    "department": "Endocrinology",
    "city": "Lucknow",
    "age_at_first": 34,
    "tracked": ["TSH"],
    "brief": "Hypothyroidism, dose titration to euthyroid",
}


def check_arc(series):
    tsh = [v for _, v in series["TSH"]]
    fails = []
    if not tsh[0] > 20:
        fails.append(f"should start frankly hypothyroid, TSH {tsh[0]}")
    if not min(tsh) < 1.0:
        fails.append("never over-replaced, so the palpitation workup makes no sense")
    if not any(t > 10 for t in tsh[6:]):
        fails.append("no relapse after stopping the tablet")
    if not 0.5 <= tsh[-1] <= 5.0:
        fails.append(f"should end euthyroid, TSH {tsh[-1]}")
    return fails


LABS = {
    "gomti": {
        "abbr": "GDC", "acc_style": 0,
        "name": "Gomti Diagnostic Centre",
        "name_local": "गोमती डायग्नोस्टिक सेंटर",
        "addr": "Hazratganj, Lucknow 226001",
        "addr_local": "हजरतगंज, लखनऊ 226001",
        "city": "Lucknow",
        "phone": "0522 262 7180",
        "accred": "NABL Accredited (MC-7210) | ISO 15189:2012",
        "path": {"name": "Dr. Archana Srivastava", "qual": "MD (Pathology)",
                 "regn": "UPMC 2006/08/4417", "scrawl": "A Srivastava"},
    },
    "awadh": {
        "abbr": "APL", "acc_style": 3,
        "name": "Awadh Path Labs",
        "name_local": "अवध पैथ लैब्स",
        "addr": "Aliganj, Lucknow 226024",
        "addr_local": "अलीगंज, लखनऊ 226024",
        "city": "Lucknow",
        "phone": "0522 237 9944",
        "accred": "NABL Accredited (M-4471)",
        "path": {"name": "Dr. Zeeshan Ahmad", "qual": "MBBS, MD (Path.)",
                 "regn": "UPMC 2012/03/8853", "scrawl": "Z Ahmad"},
    },
    "malhotra": {
        "abbr": "MLC", "acc_style": 1,
        "name": "Malhotra Life Care Hospital Laboratory",
        "name_local": "मल्होत्रा लाइफ केयर हॉस्पिटल प्रयोगशाला",
        "addr": "Gomti Nagar, Lucknow 226010",
        "addr_local": "गोमती नगर, लखनऊ 226010",
        "city": "Lucknow",
        "phone": "0522 400 6600",
        "accred": "Department of Laboratory Medicine",
        "path": {"name": "Dr. Sunita Rastogi", "qual": "MD, DNB (Pathology)",
                 "regn": "UPMC 1999/10/1163", "scrawl": "S Rastogi"},
    },
}

VERMA = "Dr. Anupam Verma, MBBS, MD, DM (Endocrinology)"
KHAN = "Dr. Farah Khan, MBBS, MD (Medicine)"
MISHRA = "Dr. S. K. Mishra, MBBS, MD (Medicine)"

TSH_LEGEND = [
    ("TSH on thyroxine replacement", "TSH uIU/mL"),
    ("0.55 - 4.78", "Euthyroid, continue current dose"),
    ("4.79 - 10.00", "Under-replaced, consider increasing"),
    ("Above 10.00", "Clearly under-replaced"),
    ("Below 0.40", "Over-replaced, reduce the dose"),
]

# Ten kilos come off as she becomes euthyroid; some return during the four months
# off treatment. Pulse-related symptoms in 2023 coincide with the suppressed TSH.
HEIGHT_CM = 158.0

VITALS = {
    1: {"weight_kg": 71.4, "bp": "124/82", "spo2": 98, "temp_f": 97.8,
        "context": "Tired, cold intolerant, weight gain over a year. TSH markedly raised."},
    2: {"weight_kg": 70.2, "bp": "122/80", "spo2": 98, "temp_f": 98.0,
        "context": "Six weeks on thyroxine 50 mcg. Symptoms a little better."},
    3: {"weight_kg": 68.6, "bp": "120/78", "spo2": 99, "temp_f": 98.2,
        "context": "Dose increased to 75 mcg."},
    4: {"weight_kg": 66.8, "bp": "118/76", "spo2": 98, "temp_f": 98.4,
        "context": "Much improved. Dose at 100 mcg."},
    5: {"weight_kg": 65.2, "bp": "116/74", "spo2": 99, "temp_f": 98.4,
        "context": "Euthyroid for the first time."},
    6: {"weight_kg": 63.8, "bp": "118/76", "spo2": 98, "temp_f": 98.6,
        "context": "Palpitations and tremor for three weeks. Over-replacement suspected."},
    7: {"weight_kg": 64.4, "bp": "114/74", "spo2": 99, "temp_f": 98.2,
        "context": "Dose reduced to 88 mcg, symptoms settled."},
    8: {"weight_kg": 64.0, "bp": "116/74", "spo2": 98, "temp_f": 98.4,
        "context": "Annual review. Stable and well."},
    9: {"weight_kg": 66.2, "bp": "120/78", "spo2": 98, "temp_f": 98.2,
        "context": "Stopped the tablet four months ago, believing she was cured."},
    10: {"weight_kg": 68.9, "bp": "124/80", "spo2": 97, "temp_f": 97.9,
         "context": "Symptoms back. Thyroxine restarted at 88 mcg."},
    11: {"weight_kg": 67.4, "bp": "122/78", "spo2": 98, "temp_f": 98.2,
         "context": "Responding to the restarted dose."},
    12: {"weight_kg": 66.0, "bp": "118/76", "spo2": 98, "temp_f": 98.4,
         "context": "Nearly back to target."},
    13: {"weight_kg": 65.4, "bp": "118/76", "spo2": 99, "temp_f": 98.2,
         "context": "Single confirmatory TSH before the annual review."},
    14: {"weight_kg": 64.8, "bp": "116/74", "spo2": 98, "temp_f": 98.4,
         "context": "Annual review. Euthyroid, compliance good."},
    15: {"weight_kg": 64.2, "bp": "114/74", "spo2": 99, "temp_f": 98.6,
         "context": "Stable. Yearly monitoring agreed."},
}

REPORTS = [
    # ---- R01 -- diagnosis ---------------------------------------------------
    {
        "collected": "2021-10-08 09:10", "reported": "2021-10-08 18:30",
        "lab": "malhotra", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": VERMA, "specimen": "Serum",
        "alias": 0, "traps": ["legend_lines", "method_sub_line"],
        "note": "Primary hypothyroidism with positive thyroid autoantibodies.",
        "sections": [
            {"panel": "THYROID", "title": 0, "methods": True, "legend": TSH_LEGEND,
             "values": {"TSH": 42.6, "T3_TOTAL": 68, "T4_TOTAL": 3.8, "FT3": 1.9,
                        "FT4": 0.52, "ANTI_TPO": 486.0}},
            {"panel": "LIPID", "title": 0,
             "values": {"CHOL": 246, "TRIG": 172, "HDL": 46}},
        ],
    },
    # ---- R02 -- six weeks on 50 mcg -----------------------------------------
    {
        "collected": "2021-12-14 08:40", "reported": "2021-12-14 15:20",
        "lab": "gomti", "layout_style": "minimal_lines",
        "header_style": "bilingual_header", "uhid_label": "Patient ID",
        "doctor": VERMA, "specimen": "Serum, Urine (midstream)",
        "alias": 1, "traps": ["unit_in_value_cell", "sample_type_row"],
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 1, "sample_row": "Urine, Midstream",
             "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.5, "UR_SPGR": 1.016,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 3, "UR_RBC": 1, "UR_EPITH": 4}},
            {"heading": "Thyroid Function",
             "rows": [{"code": "TSH", "value": 24.8, "flag": "H"},
                      {"code": "FT4", "value": 0.78, "flag": "L"}]},
        ],
    },
    # ---- R03 -- dose up to 75 -----------------------------------------------
    {
        "collected": "2022-04-02 09:25", "reported": "2022-04-02 16:50",
        "lab": "awadh", "layout_style": "landscape_wide",
        "header_style": "barcode_header", "uhid_label": "Reg. No",
        "doctor": VERMA, "specimen": "Serum",
        "alias": 2, "traps": ["prev_value_column"],
        "sections": [
            {"panel": "THYROID", "title": 2, "drop": ["ANTI_TPO"],
             "prev": {"TSH": "24.80 (14/12/2021)", "FT4": "0.78 (14/12/2021)",
                      "T4_TOTAL": "3.8 (08/10/2021)"},
             "values": {"TSH": 11.40, "T3_TOTAL": 92, "T4_TOTAL": 6.4, "FT3": 2.6,
                        "FT4": 0.94}},
            {"panel": "ELECTROLYTES", "title": 1, "drop": ["CA_ION", "MG"],
             "values": {"NA": 139, "K": 4.1, "CL": 102, "CA": 9.2, "PHOS": 3.6}},
        ],
    },
    # ---- R04 -- on 100 mcg --------------------------------------------------
    {
        "collected": "2022-09-19 08:15", "reported": "2022-09-19 17:00",
        "lab": "gomti", "layout_style": "kv_header_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": KHAN, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 3, "traps": ["footnote_marker"],
        "footnotes": [("1", "Sample drawn before the morning dose of thyroxine.")],
        "sections": [
            {"panel": "IRON", "title": 0,
             "values": {"FERRITIN": 18, "IRON": 58, "TIBC": 412}},
            {"heading": "Thyroid Function",
             "rows": [{"code": "TSH", "value": 5.62, "flag": "H", "marker": "1"},
                      {"code": "FT4", "value": 1.12}]},
        ],
    },
    # ---- R05 -- euthyroid ---------------------------------------------------
    {
        "collected": "2023-02-27 08:50", "reported": "2023-02-27 16:10",
        "lab": "malhotra", "layout_style": "two_column",
        "header_style": "banner_with_qr", "uhid_label": "Hospital No",
        "doctor": VERMA, "specimen": "Serum",
        "alias": 0, "traps": ["sno_column", "flag_as_words"],
        "sections": [
            {"panel": "LFT", "title": 1, "drop": ["GGT", "BILI_I"],
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 26, "AST": 24, "ALP": 76,
                        "PROT_T": 7.2, "ALB": 4.2}},
            {"panel": "ELECTROLYTES", "title": 3, "drop": ["CA_ION", "PHOS"],
             "values": {"NA": 140, "K": 4.3, "CL": 103, "CA": 9.4, "MG": 2.1}},
            {"heading": "Thyroid Function",
             "rows": [{"code": "TSH", "value": 2.42},
                      {"code": "FT4", "value": 1.24},
                      {"code": "T3_TOTAL", "value": 118},
                      {"label": "Anti-TG Antibody (Thyroglobulin)", "value": "148",
                       "unit": "IU/mL", "reference": "< 115", "flag": "H"}]},
        ],
    },
    # ---- R06 -- palpitations, over-replaced ---------------------------------
    {
        "collected": "2023-08-16 11:05", "reported": "2023-08-16 19:20",
        "lab": "malhotra", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": MISHRA, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 1, "traps": ["abnormal_shaded", "method_sub_line"],
        "note": "Suppressed TSH on replacement. Cardiac markers negative; symptoms "
                "attributed to over-replacement.",
        "sections": [
            {"panel": "CARDIAC", "title": 2, "methods": True,
             "values": {"TROP_I": 0.012, "CPK_MB": 14, "NT_PROBNP": 62}},
            {"heading": "Thyroid Function",
             "rows": [{"code": "TSH", "value": 0.09, "flag": "L"},
                      {"code": "FT4", "value": 2.08, "flag": "H"},
                      {"code": "FT3", "value": 4.8, "flag": "H"},
                      {"label": "CPK - Total", "value": "96", "unit": "U/L",
                       "reference": "26 - 192"},
                      {"code": "BLOOD_GROUP", "value": "O Negative",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R07 -- dose reduced ------------------------------------------------
    {
        "collected": "2023-12-04 09:00", "reported": "2023-12-04 15:45",
        "lab": "awadh", "layout_style": "thermal_slip",
        "header_style": "centred_title_only", "uhid_label": "Reg. No",
        "doctor": VERMA, "specimen": "Serum",
        "alias": 2, "traps": ["no_reference_column"],
        "sections": [
            {"heading": "Thyroid Profile",
             "rows": [{"code": "TSH", "value": 1.86},
                      {"code": "FT4", "value": 1.36},
                      {"code": "T4_TOTAL", "value": 9.2}]},
        ],
    },
    # ---- R08 -- annual review -----------------------------------------------
    {
        "collected": "2024-05-21 07:55", "reported": "2024-05-21 19:10",
        "lab": "gomti", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Patient ID",
        "doctor": VERMA, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 3, "traps": ["merged_panel_heading", "text_result", "method_sub_line"],
        "note": "Annual thyroid review package.",
        "sections": [
            {"panel": "CBC", "title": 1, "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "values": {"HGB": 12.4, "RBC": 4.32, "PCV": 37.8, "MCV": 87.5, "MCH": 28.7,
                        "WBC": 6600, "NEUT_PCT": 58, "LYMPH_PCT": 32, "MONO_PCT": 6,
                        "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 268000}},
            {"panel": "LIPID", "title": 3, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 192, "TRIG": 128, "HDL": 54}},
            {"panels": ["LFT", "KFT"], "heading": "Biochemistry - Liver and Renal",
             "trap": "merged_panel_heading",
             "drop": ["AG_RATIO", "GLOB", "BILI_I", "GGT", "BUN"],
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 24, "AST": 22, "ALP": 72,
                        "PROT_T": 7.1, "ALB": 4.1,
                        "CREAT": 0.72, "UREA": 24, "UA": 4.4}},
            {"panel": "VITAMIN", "title": 0, "methods": True,
             "values": {"VIT_D": 17.2, "VIT_B12": 246, "FOLATE": 6.2}},
            {"heading": "Other",
             "rows": [{"code": "BLOOD_GROUP", "value": "O Negative", "trap": "text_result"},
                      {"code": "TSH", "value": 3.08},
                      {"code": "HBA1C", "value": 5.4}]},
        ],
    },
    # ---- R09 -- off the tablet ----------------------------------------------
    {
        "collected": "2024-11-09 09:30", "reported": "2024-11-09 17:40",
        "lab": "malhotra", "layout_style": "poor_scan",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": VERMA, "specimen": "Serum",
        "alias": 0, "traps": ["legend_lines", "ambiguous_abbreviation"],
        "stamp": "RECALL<br>PATIENT",
        "sections": [
            {"panel": "THYROID", "title": 3, "drop": ["FT3"], "legend": TSH_LEGEND,
             "labels": {"T4_TOTAL": "T4"},
             "row_traps": {"T4_TOTAL": "ambiguous_abbreviation"},
             "values": {"TSH": 14.80, "T3_TOTAL": 78, "T4_TOTAL": 5.6, "FT4": 0.82,
                        "ANTI_TPO": 392.0}},
        ],
    },
    # ---- R10 -- restarted ---------------------------------------------------
    {
        "collected": "2025-03-18 08:20", "reported": "2025-03-18 16:30",
        "lab": "awadh", "layout_style": "duplicate_watermark",
        "header_style": "letterhead_logo_left", "uhid_label": "Reg. No",
        "doctor": KHAN, "specimen": "Serum, Urine (midstream)",
        "alias": 1, "traps": ["prev_value_column", "not_reported"],
        "note": "Duplicate copy for the patient's file.",
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 3,
             "values": {"UR_COLOUR": "Yellow", "UR_PH": 6.0, "UR_SPGR": 1.018,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 4, "UR_RBC": 1, "UR_EPITH": 3, "MICROALB": 12,
                        "ACR": 14}},
            {"heading": "Thyroid Function",
             "prev": {"TSH": "14.80 (09/11/2024)", "FT4": "0.82 (09/11/2024)"},
             "rows": [{"code": "TSH", "value": 8.96, "flag": "H"},
                      {"code": "FT4", "value": 0.98},
                      {"code": "ANTI_TPO", "value": "Not Reported",
                       "trap": "not_reported"}]},
        ],
    },
    # ---- R11 -- responding --------------------------------------------------
    {
        "collected": "2025-08-07 08:45", "reported": "2025-08-07 15:15",
        "lab": "gomti", "layout_style": "carbon_copy",
        "header_style": "minimal_text_top", "uhid_label": "Patient ID",
        "doctor": VERMA, "specimen": "Serum",
        "alias": 2, "traps": ["range_with_unit"],
        "sections": [
            {"heading": "TSH - Ultrasensitive",
             "rows": [{"code": "TSH", "value": 4.42}]},
        ],
    },
    # ---- R12 -- nearly at target --------------------------------------------
    {
        "collected": "2025-12-11 09:05", "reported": "2025-12-11 16:55",
        "lab": "malhotra", "layout_style": "mixed_print_hand",
        "header_style": "stamp_and_signature", "uhid_label": "Hospital No",
        "doctor": VERMA, "specimen": "Whole blood (EDTA), Serum",
        "alias": 3, "traps": ["text_result"], "stamp": "ENDOCRINE<br>CLINIC",
        "sections": [
            {"panel": "CBC", "title": 2, "drop": ["ANC", "ALC", "MPV"],
             "values": {"HGB": 12.8, "RBC": 4.41, "PCV": 38.6, "MCV": 87.5, "MCH": 29.0,
                        "MCHC": 33.2, "RDW": 13.4, "WBC": 6900, "NEUT_PCT": 60,
                        "LYMPH_PCT": 30, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 276000}},
            {"panel": "DIABETES", "title": 2, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 92, "GLU_PP": 124, "HBA1C": 5.3}},
            {"heading": "Serology",
             "rows": [{"code": "PERIPH_SMEAR",
                       "value": "Normocytic normochromic red cells, adequate platelets.",
                       "trap": "text_result"},
                      {"label": "Vitamin B6 (Pyridoxal-5-phosphate)", "value": "12.4",
                       "unit": "ng/mL", "reference": "5.0 - 50.0"}]},
            {"heading": "Written in at the clinic", "hand_addendum": True,
             "rows": [{"code": "TSH", "value": 3.24}, {"code": "FT4", "value": 1.20}]},
        ],
    },
    # ---- R13 -- one confirmatory TSH ----------------------------------------
    {
        "collected": "2026-03-26 09:50", "reported": "2026-03-26 13:40",
        "lab": "awadh", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": KHAN, "specimen": "Serum",
        "alias": 0, "traps": ["no_header_row"],
        "sections": [
            {"heading": "TSH - Ultrasensitive",
             "rows": [{"code": "TSH", "value": 2.68}]},
        ],
    },
    # ---- R14 -- annual review, two pages ------------------------------------
    {
        "collected": "2026-07-15 07:45", "reported": "2026-07-15 20:00",
        "lab": "gomti", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": VERMA, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["ratio_no_code", "footnote_marker"],
        "page_break_after": 3,
        "footnotes": [("1", "Anti-TPO not repeated; a positive titre does not change "
                            "management once replacement is established.")],
        "sections": [
            {"panel": "CBC", "title": 4,
             "values": {"HGB": 13.0, "RBC": 4.48, "PCV": 39.2, "MCV": 87.5, "MCH": 29.0,
                        "MCHC": 33.2, "RDW": 13.1, "WBC": 6700, "NEUT_PCT": 59,
                        "LYMPH_PCT": 31, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 271000, "MPV": 9.5}},
            {"panel": "LIPID", "title": 4,
             "values": {"CHOL": 176, "TRIG": 112, "HDL": 58}},
            {"panel": "DIABETES", "title": 5, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 90, "GLU_PP": 118, "HBA1C": 5.2}},
            {"panel": "LFT", "title": 4,
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 22, "AST": 21, "ALP": 70,
                        "GGT": 18, "PROT_T": 7.2, "ALB": 4.3}},
            {"panel": "KFT", "title": 2,
             "values": {"CREAT": 0.70, "UREA": 23, "UA": 4.2}},
            {"heading": "Thyroid and Derived",
             "rows": [{"code": "TSH", "value": 2.16, "marker": "1"},
                      {"code": "FT4", "value": 1.22},
                      {"label": "FT3 / FT4 Ratio", "value": "2.6", "unit": "",
                       "reference": "2.0 - 3.5", "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R15 -- stable ------------------------------------------------------
    {
        "collected": "2026-09-10 08:30", "reported": "2026-09-10 16:20",
        "lab": "malhotra", "layout_style": "kv_header_table",
        "header_style": "barcode_header", "uhid_label": "Hospital No",
        "doctor": VERMA, "specimen": "Serum",
        "alias": 2, "traps": ["method_sub_line"],
        "sections": [
            {"panel": "IRON", "title": 3, "methods": True,
             "values": {"FERRITIN": 42, "IRON": 82, "TIBC": 348}},
            {"panel": "VITAMIN", "title": 3, "methods": True,
             "values": {"VIT_D": 31.4, "VIT_B12": 342, "FOLATE": 8.6}},
            {"heading": "Thyroid Function",
             "rows": [{"code": "TSH", "value": 2.08}, {"code": "FT4", "value": 1.26}]},
        ],
    },
]
