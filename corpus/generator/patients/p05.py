"""Patient 5 of 20 - Paediatrics. Recurrent febrile illness, dengue episode, full recovery.

Male, 11 at the first report and 16 at the last, Jaipur. A run of ordinary childhood
fevers, then the event the record is built around: dengue in September 2023, platelets
falling to 42,000 with a rising haematocrit, three reports inside eight days, and full
recovery by the following month. Nothing chronic is left behind - the last two years are
a normal adolescent.

First patient to use the second wave of layouts: the 80mm thermal slip a collection
centre prints, a page photographed on a phone rather than scanned, a barcode letterhead
and a Hindi-English bilingual one. Also the first with reports that print no reference
column at all, spell their flags as HIGH and LOW, shade abnormal rows instead of flagging
them, and group sections by specimen rather than by panel.
"""

from __future__ import annotations

PATIENT = {
    "number": 5,
    "name": "Devansh Choudhary",
    "sex": "M",
    "dob": "2010-03-14",
    "uhid": "MCH/226104",
    "department": "Paediatrics",
    "city": "Jaipur",
    "age_at_first": 11,
    "tracked": ["PLT"],
    "brief": "Recurrent febrile illness, dengue episode, full recovery",
}


def check_arc(series):
    plt = [v for _, v in series["PLT"]]
    fails = []
    if not min(plt) < 60000:
        fails.append(f"dengue nadir never reached, lowest platelet count {min(plt)}")
    if not plt[-1] > 150000:
        fails.append(f"should recover fully, ends at {plt[-1]}")
    if not plt[0] > 150000:
        fails.append("should start with a normal platelet count")
    return fails


LABS = {
    "aravali": {
        "abbr": "ADL", "acc_style": 0,
        "name": "Aravali Diagnostics",
        "name_local": "अरावली डायग्नोस्टिक्स",
        "addr": "Tonk Road, Jaipur 302015",
        "addr_local": "टोंक रोड, जयपुर 302015",
        "city": "Jaipur",
        "phone": "0141 274 5500",
        "accred": "NABL Accredited (MC-5162) | ISO 15189:2012",
        "path": {"name": "Dr. Nirmala Bhargava", "qual": "MD (Pathology)",
                 "regn": "RMC 2007/05/3341", "scrawl": "N Bhargava"},
    },
    "pinkcity": {
        "abbr": "PCP", "acc_style": 3,
        "name": "Pink City Path Lab",
        "name_local": "पिंक सिटी पैथ लैब",
        "addr": "Chandpole Bazar, Jaipur 302001",
        "addr_local": "चांदपोल बाजार, जयपुर 302001",
        "city": "Jaipur",
        "phone": "0141 236 8820",
        "accred": "NABL Accredited (M-8830)",
        "path": {"name": "Dr. Rakesh Saini", "qual": "MBBS, MD (Path.)",
                 "regn": "RMC 2011/09/6672", "scrawl": "R Saini"},
    },
    "maharana": {
        "abbr": "MCH", "acc_style": 2,
        "name": "Maharana Childrens Hospital Laboratory",
        "name_local": "महाराणा चिल्ड्रन्स हॉस्पिटल प्रयोगशाला",
        "addr": "Bani Park, Jaipur 302016",
        "addr_local": "बनी पार्क, जयपुर 302016",
        "city": "Jaipur",
        "phone": "0141 220 9100",
        "accred": "Paediatric and Neonatal Laboratory Services",
        "path": {"name": "Dr. Suman Agarwal", "qual": "MD, DNB (Pathology)",
                 "regn": "RMC 2002/12/1194", "scrawl": "S Agarwal"},
    },
}

MEENA = "Dr. H. L. Meena, MBBS, MD (Paediatrics)"
SHEKHAWAT = "Dr. Pooja Shekhawat, MBBS, DCH"
JOSHI = "Dr. Anand Joshi, MBBS, MD (Paediatrics)"

DENGUE_LEGEND = [
    ("Platelet count - dengue monitoring", "Platelet count"),
    ("Above 150000 /uL", "Normal"),
    ("50000 - 150000 /uL", "Monitor twice daily"),
    ("20000 - 50000 /uL", "Admit, watch for bleeding"),
    ("Below 20000 /uL", "Transfusion may be required"),
]

# An adolescent growth spurt: 142 cm at eleven, 172 cm at sixteen. Weight drops 3 kg
# during the dengue week and is regained afterwards.
HEIGHT_CM = 142.0

VITALS = {
    1: {"height_cm": 142.0, "weight_kg": 34.2, "bp": "104/66", "spo2": 98, "temp_f": 100.8,
        "context": "Third fever this year. Throat inflamed, otherwise well."},
    2: {"height_cm": 145.0, "weight_kg": 35.8, "bp": "106/68", "spo2": 99, "temp_f": 98.4,
        "context": "Well between illnesses. Routine bloods at the mother's request."},
    3: {"height_cm": 149.0, "weight_kg": 38.4, "bp": "106/68", "spo2": 98, "temp_f": 101.2,
        "context": "Fever with cough for four days. Chest clear on examination."},
    4: {"height_cm": 153.0, "weight_kg": 41.0, "bp": "108/70", "spo2": 99, "temp_f": 98.6,
        "context": "Recovered. Follow-up counts requested."},
    5: {"height_cm": 156.0, "weight_kg": 43.6, "bp": "110/70", "spo2": 98, "temp_f": 98.4,
        "context": "Annual school health check."},
    6: {"height_cm": 158.0, "weight_kg": 44.8, "bp": "108/68", "spo2": 97, "temp_f": 103.1,
        "context": "Day three of high fever with severe body ache and retro-orbital pain."},
    7: {"height_cm": 158.0, "weight_kg": 42.9, "bp": "100/62", "spo2": 96, "temp_f": 101.4,
        "context": "Day five. Platelets falling, admitted for observation and fluids."},
    8: {"height_cm": 158.0, "weight_kg": 42.4, "bp": "104/66", "spo2": 97, "temp_f": 99.2,
        "context": "Day eight. Afebrile, platelets recovering, discharged."},
    9: {"height_cm": 160.0, "weight_kg": 45.2, "bp": "110/70", "spo2": 99, "temp_f": 98.2,
        "context": "One month after discharge. Back at school, eating well."},
    10: {"height_cm": 164.0, "weight_kg": 48.6, "bp": "112/72", "spo2": 98, "temp_f": 98.6,
         "context": "Well. Counts confirmed normal before sports selection."},
    11: {"height_cm": 167.0, "weight_kg": 51.4, "bp": "114/72", "spo2": 99, "temp_f": 98.4,
         "context": "Growth spurt under way. No further febrile episodes."},
    12: {"height_cm": 169.0, "weight_kg": 53.8, "bp": "116/74", "spo2": 98, "temp_f": 99.6,
         "context": "Brief viral fever, settled in two days without treatment."},
    13: {"height_cm": 170.0, "weight_kg": 55.2, "bp": "116/74", "spo2": 99, "temp_f": 98.2,
         "context": "Single confirmatory platelet count after that fever."},
    14: {"height_cm": 171.0, "weight_kg": 56.9, "bp": "118/74", "spo2": 98, "temp_f": 98.4,
         "context": "Annual check before the board examination year."},
    15: {"height_cm": 172.0, "weight_kg": 58.2, "bp": "118/76", "spo2": 99, "temp_f": 98.6,
         "context": "Fit and well. Discharged from paediatric follow-up."},
}

REPORTS = [
    # ---- R01 -- one of the ordinary fevers ---------------------------------
    {
        "collected": "2021-10-28 11:20", "reported": "2021-10-28 16:40",
        "lab": "maharana", "layout_style": "clean_table",
        "header_style": "barcode_header", "uhid_label": "Hospital No",
        "doctor": MEENA, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["paediatric_range", "text_result"],
        "sections": [
            {"heading": "Haemogram", "trap": "paediatric_range",
             "rows": [{"code": "HGB", "value": 12.6}, {"code": "PCV", "value": 38.4},
                      {"code": "WBC", "value": 11200, "flag": "H"},
                      {"code": "NEUT_PCT", "value": 68, "flag": "H"},
                      {"code": "LYMPH_PCT", "value": 24},
                      {"code": "PLT", "value": 246000}]},
            {"heading": "Fever Screen",
             "rows": [{"code": "CRP", "value": 28.6, "flag": "H"},
                      {"code": "WIDAL", "value": "Non Reactive", "trap": "text_result"},
                      {"code": "MP", "value": "Not Detected", "trap": "text_result"}]},
        ],
    },
    # ---- R02 -- the thermal slip from a collection centre ------------------
    {
        "collected": "2022-03-09 08:40", "reported": "2022-03-09 12:10",
        "lab": "pinkcity", "layout_style": "thermal_slip",
        "header_style": "centred_title_only", "uhid_label": "Reg. No",
        "doctor": SHEKHAWAT, "specimen": "Whole blood (EDTA)",
        "alias": 1, "traps": ["no_reference_column"],
        "note": "Not valid for medico-legal purposes.",
        "sections": [
            {"heading": "Haemogram",
             "rows": [{"code": "HGB", "value": 12.9}, {"code": "WBC", "value": 7600},
                      {"code": "PLT", "value": 268000}, {"code": "PCV", "value": 39.1},
                      {"code": "MCV", "value": 83.0}]},
        ],
    },
    # ---- R03 -- fever with cough -------------------------------------------
    {
        "collected": "2022-08-17 10:15", "reported": "2022-08-17 17:50",
        "lab": "aravali", "layout_style": "kv_header_table",
        "header_style": "bilingual_header", "uhid_label": "Patient ID",
        "doctor": MEENA, "specimen": "Whole blood (EDTA), Serum, Urine",
        "alias": 2, "traps": ["flag_as_words", "grouped_by_specimen"],
        "note": "Sections grouped by specimen as per this laboratory's format.",
        "sections": [
            {"panels": ["CBC"], "heading": "Whole Blood (EDTA)",
             "trap": "grouped_by_specimen", "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "values": {"HGB": 12.8, "RBC": 4.71, "PCV": 38.9, "MCV": 82.6, "MCH": 27.2,
                        "WBC": 13400, "NEUT_PCT": 74, "LYMPH_PCT": 19, "MONO_PCT": 4,
                        "EOS_PCT": 2, "BASO_PCT": 1, "PLT": 232000}},
            {"panels": ["URINE_ROUTINE"], "heading": "Urine, Midstream",
             "trap": "grouped_by_specimen", "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Yellow", "UR_PH": 6.0, "UR_SPGR": 1.020,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Trace",
                        "UR_PUS": 3, "UR_RBC": 0, "UR_EPITH": 2}},
        ],
    },
    # ---- R04 -- follow-up counts -------------------------------------------
    {
        "collected": "2023-01-24 09:30", "reported": "2023-01-24 15:20",
        "lab": "pinkcity", "layout_style": "minimal_lines",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": SHEKHAWAT, "specimen": "Serum",
        "alias": 3, "traps": ["range_with_unit", "method_sub_line"],
        "sections": [
            {"panel": "LFT", "title": 2, "methods": True, "drop": ["GGT", "BILI_I"],
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 24, "AST": 28, "ALP": 268,
                        "PROT_T": 7.2, "ALB": 4.4}},
            {"panel": "THYROID", "title": 4, "drop": ["FT3", "FT4", "ANTI_TPO"],
             "trap": "sparse_panel", "methods": True,
             "values": {"TSH": 2.94, "T3_TOTAL": 138, "T4_TOTAL": 9.1}},
            {"heading": "Platelet Count",
             "rows": [{"code": "PLT", "value": 284000},
                      {"label": "LDH (Lactate Dehydrogenase)", "value": "286",
                       "unit": "U/L", "reference": "180 - 430"}]},
        ],
    },
    # ---- R05 -- school health check ----------------------------------------
    {
        "collected": "2023-05-30 08:00", "reported": "2023-05-30 18:40",
        "lab": "maharana", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Hospital No",
        "doctor": MEENA, "specimen": "Whole blood (EDTA), Serum, Urine",
        "alias": 0, "traps": ["merged_panel_heading", "text_result", "paediatric_range"],
        "note": "School health check package.",
        "sections": [
            {"heading": "Complete Haemogram", "trap": "paediatric_range",
             "rows": [{"code": "HGB", "value": 13.2}, {"code": "RBC", "value": 4.82},
                      {"code": "PCV", "value": 40.1}, {"code": "MCV", "value": 83.2},
                      {"code": "WBC", "value": 7200}, {"code": "PLT", "value": 272000},
                      {"label": "G6PD (Qualitative)", "value": "Normal activity",
                       "unit": "", "reference": "Normal activity"}]},
            {"panel": "LIPID", "title": 3, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 154, "TRIG": 86, "HDL": 46}},
            {"panels": ["LFT", "ELECTROLYTES"], "heading": "Biochemistry Screen",
             "trap": "merged_panel_heading",
             "drop": ["GGT", "AG_RATIO", "GLOB", "BILI_I", "CA_ION", "MG", "CL"],
             "values": {"BILI_T": 0.5, "BILI_D": 0.2, "ALT": 22, "AST": 26, "ALP": 292,
                        "PROT_T": 7.3, "ALB": 4.5,
                        "NA": 140, "K": 4.4, "CA": 9.9, "PHOS": 4.8}},
            {"panel": "IRON", "title": 1, "drop": ["UIBC"],
             "values": {"FERRITIN": 48, "IRON": 86, "TIBC": 352}},
            {"panel": "VITAMIN", "title": 2,
             "values": {"VIT_D": 19.6, "VIT_B12": 388, "FOLATE": 9.2}},
            {"heading": "Other",
             "rows": [{"code": "BLOOD_GROUP", "value": "AB Positive", "trap": "text_result"},
                      {"code": "HBA1C", "value": 5.0}]},
        ],
    },
    # ---- R06 -- day three of the dengue -------------------------------------
    {
        "collected": "2023-09-11 12:40", "reported": "2023-09-11 18:05",
        "lab": "maharana", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": JOSHI, "specimen": "Whole blood (EDTA), Serum",
        "alias": 1, "traps": ["legend_lines", "text_result", "abnormal_shaded"],
        "note": "NS1 antigen positive. Advise daily platelet counts and oral fluids.",
        "sections": [
            {"heading": "Haemogram - Dengue Watch", "legend": DENGUE_LEGEND,
             "rows": [{"code": "HGB", "value": 13.8}, {"code": "PCV", "value": 43.6},
                      {"code": "WBC", "value": 3600, "flag": "L"},
                      {"code": "NEUT_PCT", "value": 44},
                      {"code": "LYMPH_PCT", "value": 46, "flag": "H"},
                      {"code": "PLT", "value": 118000, "flag": "L"},
                      {"label": "Procalcitonin", "value": "0.08", "unit": "ng/mL",
                       "reference": "< 0.50"}]},
            {"heading": "Dengue Serology",
             "rows": [{"code": "DENGUE_NS1", "value": "Positive", "flag": "H",
                       "trap": "text_result"},
                      {"code": "DENGUE_IGM", "value": "Negative", "trap": "text_result"}]},
        ],
    },
    # ---- R07 -- day five, the nadir, photographed not scanned --------------
    {
        "collected": "2023-09-13 07:10", "reported": "2023-09-13 11:30",
        "lab": "maharana", "layout_style": "mobile_photo",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": JOSHI, "specimen": "Whole blood (EDTA), Serum",
        "alias": 2, "traps": ["sno_column", "abnormal_shaded"],
        "stamp": "CRITICAL<br>PHONED 07:55",
        "note": "Platelet count and haematocrit telephoned to the ward. Admitted for "
                "observation.",
        "sections": [
            {"panel": "CBC", "title": 4, "drop": ["ANC", "ALC", "MPV", "MCHC"],
             "values": {"HGB": 14.6, "RBC": 5.12, "PCV": 47.2, "MCV": 82.2, "MCH": 26.8,
                        "RDW": 13.4, "WBC": 2900, "NEUT_PCT": 38, "LYMPH_PCT": 52,
                        "MONO_PCT": 7, "EOS_PCT": 2, "BASO_PCT": 1, "PLT": 42000}},
            {"panel": "ELECTROLYTES", "title": 1, "drop": ["CA_ION", "MG", "PHOS"],
             "values": {"NA": 134, "K": 3.8, "CL": 99, "CA": 8.8}},
        ],
    },
    # ---- R08 -- day eight, recovering, on the till roll --------------------
    {
        "collected": "2023-09-16 08:20", "reported": "2023-09-16 10:45",
        "lab": "maharana", "layout_style": "thermal_slip",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": JOSHI, "specimen": "Whole blood (EDTA)",
        "alias": 3, "traps": ["no_reference_column"],
        "sections": [
            {"heading": "Platelet Count - Daily",
             "rows": [{"code": "PLT", "value": 96000, "flag": "L"}]},
        ],
    },
    # ---- R09 -- one month on ------------------------------------------------
    {
        "collected": "2023-10-19 09:45", "reported": "2023-10-19 14:15",
        "lab": "aravali", "layout_style": "two_column",
        "header_style": "bilingual_header", "uhid_label": "Patient ID",
        "doctor": MEENA, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["flag_as_words"],
        "sections": [
            {"heading": "Convalescent Counts",
             "rows": [{"code": "HGB", "value": 13.4}, {"code": "PCV", "value": 40.6},
                      {"code": "WBC", "value": 6800}, {"code": "PLT", "value": 214000},
                      {"label": "Apolipoprotein A1", "value": "118", "unit": "mg/dL",
                       "reference": "110 - 180"}]},
            {"panel": "INFLAMMATION", "title": 0, "drop": ["RA_FACTOR", "ASO"],
             "values": {"CRP": 3.2, "HS_CRP": 1.14}},
        ],
    },
    # ---- R10 -- sports selection --------------------------------------------
    {
        "collected": "2024-04-06 08:55", "reported": "2024-04-06 16:25",
        "lab": "pinkcity", "layout_style": "carbon_copy",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": SHEKHAWAT, "specimen": "Serum, Urine (midstream)",
        "alias": 1, "traps": ["range_with_unit", "ambiguous_abbreviation"],
        "sections": [
            {"panel": "KFT", "title": 3, "drop": ["EGFR"],
             "values": {"CREAT": 0.74, "UREA": 28, "UA": 5.2}},
            {"panel": "URINE_ROUTINE", "title": 5, "drop": ["MICROALB", "ACR"],
             "labels": {"UR_PROT": "ALB"},
             "row_traps": {"UR_PROT": "ambiguous_abbreviation"},
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.5, "UR_SPGR": 1.016,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 2, "UR_RBC": 0, "UR_EPITH": 1}},
        ],
    },
    # ---- R11 -- growth spurt, thyroid checked -------------------------------
    {
        "collected": "2024-11-12 09:05", "reported": "2024-11-12 17:40",
        "lab": "aravali", "layout_style": "clean_table",
        "header_style": "barcode_header", "uhid_label": "Patient ID",
        "doctor": JOSHI, "specimen": "Serum",
        "alias": 2, "traps": ["sparse_panel", "footnote_marker"],
        "footnotes": [("1", "Thyroid function checked as part of the growth assessment.")],
        "sections": [
            {"panel": "THYROID", "title": 1, "drop": ["FT3", "ANTI_TPO"],
             "values": {"TSH": 2.68, "T3_TOTAL": 142, "T4_TOTAL": 9.4, "FT4": 1.24},
             "row_traps": {"TSH": "footnote_marker"}},
            {"panel": "DIABETES", "title": 4, "drop": ["GLU_R", "INSULIN_F", "EAG"],
             "trap": "sparse_panel",
             "values": {"GLU_F": 88, "GLU_PP": 112, "HBA1C": 5.1}},
        ],
    },
    # ---- R12 -- brief viral fever -------------------------------------------
    {
        "collected": "2025-06-21 20:15", "reported": "2025-06-21 23:40",
        "lab": "maharana", "layout_style": "poor_scan",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": MEENA, "specimen": "Whole blood (EDTA), Serum",
        "alias": 3, "traps": ["text_result", "no_reference_column"],
        "sections": [
            {"heading": "Fever Panel",
             "rows": [{"code": "HGB", "value": 14.2}, {"code": "WBC", "value": 5800},
                      {"code": "PLT", "value": 196000},
                      {"code": "DENGUE_NS1", "value": "Negative", "trap": "text_result"},
                      {"code": "MP", "value": "Not Detected", "trap": "text_result"},
                      {"code": "CRP", "value": 14.2, "flag": "H"}]},
        ],
    },
    # ---- R13 -- one confirmatory count --------------------------------------
    {
        "collected": "2025-07-02 10:30", "reported": "2025-07-02 13:15",
        "lab": "pinkcity", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": SHEKHAWAT, "specimen": "Whole blood (EDTA)",
        "alias": 0, "traps": ["no_header_row"],
        "sections": [
            {"heading": "Platelet Count",
             "rows": [{"code": "PLT", "value": 232000}]},
        ],
    },
    # ---- R14 -- annual check, two pages -------------------------------------
    {
        "collected": "2026-02-18 07:50", "reported": "2026-02-18 19:25",
        "lab": "maharana", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "Hospital No",
        "doctor": MEENA, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["ratio_no_code", "abnormal_shaded"],
        "page_break_after": 3,
        "sections": [
            {"panel": "CBC", "title": 1,
             "values": {"HGB": 14.8, "RBC": 5.06, "PCV": 44.2, "MCV": 87.4, "MCH": 29.2,
                        "MCHC": 33.5, "RDW": 12.8, "WBC": 7000, "NEUT_PCT": 60,
                        "LYMPH_PCT": 32, "MONO_PCT": 5, "EOS_PCT": 2, "BASO_PCT": 1,
                        "PLT": 258000, "MPV": 9.6}},
            {"panel": "LIPID", "title": 5, "drop": ["LDL_HDL_RATIO"],
             "values": {"CHOL": 162, "TRIG": 94, "HDL": 48}},
            {"panel": "DIABETES", "title": 2, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 86, "GLU_PP": 108, "HBA1C": 5.0}},
            {"panel": "LFT", "title": 4,
             "values": {"BILI_T": 0.7, "BILI_D": 0.2, "ALT": 26, "AST": 24, "ALP": 186,
                        "GGT": 19, "PROT_T": 7.4, "ALB": 4.6}},
            {"panel": "KFT", "title": 0, "drop": ["EGFR"],
             "values": {"CREAT": 0.86, "UREA": 30, "UA": 5.8}},
            {"heading": "Derived",
             "rows": [{"label": "Neutrophil - Lymphocyte Ratio", "value": "1.9",
                       "unit": "", "reference": "1.0 - 3.0", "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R15 -- discharged from follow-up -----------------------------------
    {
        "collected": "2026-08-27 09:10", "reported": "2026-08-27 15:45",
        "lab": "aravali", "layout_style": "mixed_print_hand",
        "header_style": "stamp_and_signature", "uhid_label": "Patient ID",
        "doctor": JOSHI, "specimen": "Whole blood (EDTA), Serum",
        "alias": 2, "traps": ["text_result"], "stamp": "FIT<br>FOR SPORTS",
        "sections": [
            {"panel": "IRON", "title": 4,
             "values": {"FERRITIN": 68, "IRON": 102, "TIBC": 334}},
            {"panel": "VITAMIN", "title": 0,
             "values": {"VIT_D": 28.4, "VIT_B12": 412, "FOLATE": 10.6}},
            {"panel": "INFLAMMATION", "title": 3, "drop": ["HS_CRP"],
             "values": {"CRP": 2.1, "RA_FACTOR": 8.2, "ASO": 96}},
            {"heading": "Noted at the desk", "hand_addendum": True,
             "rows": [{"code": "PLT", "value": 264000}, {"code": "HGB", "value": 15.0}]},
        ],
    },
]
