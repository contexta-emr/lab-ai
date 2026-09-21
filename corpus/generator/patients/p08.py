"""Patient 8 of 20 - Obstetrics. Two pregnancies: anaemia and gestational diabetes screening.

Female, 29 at the first report, Bhubaneswar. Two pregnancies inside the five years. The
first (2022) runs with iron-deficiency anaemia - haemoglobin 9.2 at booking, corrected to
11.6 by term on oral iron. The second (2025-26) brings gestational diabetes: the 75 g
screen at 26 weeks gives a 2 hour value of 168 and she is managed on diet and metformin,
with the anaemia returning more mildly.

Serology is the routine antenatal viral screen, repeated at the second booking. The
tumour marker is CA 125 for an ovarian cyst seen on the postnatal scan - it has no code
in the Contexta vocabulary and the key records none, which is the point of printing it.
Roster group 3 nominates PSA; that is a prostate assay and is not printed for a woman.
"""

from __future__ import annotations

PATIENT = {
    "number": 8,
    "name": "Sasmita Pradhan",
    "sex": "F",
    "dob": "1992-06-18",
    "uhid": "KGH/731592",
    "department": "Obstetrics",
    "city": "Bhubaneswar",
    "age_at_first": 29,
    "tracked": ["HGB"],
    "brief": "Two pregnancies: anaemia and gestational diabetes screening",
}


def check_arc(series):
    hgb = [v for _, v in series["HGB"]]
    fails = []
    if not min(hgb) < 10.0:
        fails.append(f"anaemia of pregnancy never appears, lowest {min(hgb)}")
    if not max(hgb) >= 11.5:
        fails.append("never corrected to a normal antenatal haemoglobin")
    if len([v for v in hgb if v < 10.5]) < 2:
        fails.append("only one anaemic spell for two pregnancies")
    return fails


LABS = {
    "utkal": {
        "abbr": "UDC", "acc_style": 0,
        "name": "Utkal Diagnostic Centre",
        "name_local": "ଉତ୍କଳ ଡାଏଗ୍ନୋଷ୍ଟିକ ସେଣ୍ଟର",
        "addr": "Saheed Nagar, Bhubaneswar 751007",
        "addr_local": "ଶହୀଦ ନଗର, ଭୁବନେଶ୍ୱର 751007",
        "city": "Bhubaneswar",
        "phone": "0674 254 3300",
        "accred": "NABL Accredited (MC-8104) | ISO 15189:2012",
        "path": {"name": "Dr. Sanjukta Mohapatra", "qual": "MD (Pathology)",
                 "regn": "OCMR 2008/04/2219", "scrawl": "S Mohapatra"},
    },
    "kalinga": {
        "abbr": "KGH", "acc_style": 1,
        "name": "Kalinga Womens Hospital Laboratory",
        "name_local": "କଳିଙ୍ଗ ମହିଳା ହସ୍ପିଟାଲ ଲାବୋରେଟୋରୀ",
        "addr": "Unit 4, Bhubaneswar 751001",
        "addr_local": "ୟୁନିଟ 4, ଭୁବନେଶ୍ୱର 751001",
        "city": "Bhubaneswar",
        "phone": "0674 239 8800",
        "accred": "Department of Laboratory Medicine, Obstetric Services",
        "path": {"name": "Dr. Priyabrata Sahoo", "qual": "MD, DNB (Pathology)",
                 "regn": "OCMR 2003/07/1052", "scrawl": "P Sahoo"},
    },
    "jagannath": {
        "abbr": "JPL", "acc_style": 3,
        "name": "Jagannath Path Lab",
        "name_local": "ଜଗନ୍ନାଥ ପାଥ ଲାବ",
        "addr": "Rasulgarh, Bhubaneswar 751010",
        "addr_local": "ରସୁଲଗଡ଼, ଭୁବନେଶ୍ୱର 751010",
        "city": "Bhubaneswar",
        "phone": "0674 258 1177",
        "accred": "NABL Accredited (M-2298)",
        "path": {"name": "Dr. Lopamudra Das", "qual": "MBBS, MD (Path.)",
                 "regn": "OCMR 2014/01/9930", "scrawl": "L Das"},
    },
}

MISHRA_O = "Dr. Snigdha Mishra, MBBS, MS (Obstetrics and Gynaecology)"
BEHERA = "Dr. Amiya Behera, MBBS, MD (Medicine)"
ROUT = "Dr. Kalpana Rout, MBBS, DGO"

GDM_LEGEND = [
    ("75 g oral glucose tolerance test in pregnancy (DIPSI)", "2 hour plasma glucose"),
    ("Below 140 mg/dL", "Normal"),
    ("140 - 199 mg/dL", "Gestational diabetes mellitus"),
    ("200 mg/dL and above", "Diabetes in pregnancy"),
]

ANC_LEGEND = [
    ("Haemoglobin in pregnancy (WHO)", "Haemoglobin"),
    ("11.0 g/dL and above", "Normal"),
    ("10.0 - 10.9 g/dL", "Mild anaemia"),
    ("7.0 - 9.9 g/dL", "Moderate anaemia"),
]

# Two pregnancies: weight climbs about 11 kg each time and comes off over the
# following year. The second brings a blood pressure scare at 34 weeks.
HEIGHT_CM = 156.0

VITALS = {
    1: {"weight_kg": 52.4, "bp": "112/72", "spo2": 99, "temp_f": 98.2,
        "context": "Pre-conception counselling. Already anaemic."},
    2: {"weight_kg": 53.1, "bp": "110/70", "spo2": 99, "temp_f": 98.4,
        "context": "First pregnancy, booking visit at nine weeks."},
    3: {"weight_kg": 55.8, "bp": "108/68", "spo2": 98, "temp_f": 98.2,
        "context": "Eighteen weeks. Oral iron continued, tolerating it."},
    4: {"weight_kg": 59.2, "bp": "112/72", "spo2": 98, "temp_f": 98.6,
        "context": "Twenty-six weeks. Glucose tolerance test normal."},
    5: {"weight_kg": 62.6, "bp": "116/74", "spo2": 98, "temp_f": 98.4,
        "context": "Thirty-four weeks. Haemoglobin much improved."},
    6: {"weight_kg": 64.8, "bp": "118/76", "spo2": 98, "temp_f": 98.8,
        "context": "Admitted in labour at thirty-nine weeks."},
    7: {"weight_kg": 58.4, "bp": "114/74", "spo2": 99, "temp_f": 98.4,
        "context": "Six weeks postnatal. Breastfeeding, iron continued."},
    8: {"weight_kg": 55.6, "bp": "112/72", "spo2": 99, "temp_f": 98.2,
        "context": "Annual health check, back to pre-pregnancy weight."},
    9: {"weight_kg": 54.9, "bp": "110/70", "spo2": 98, "temp_f": 98.4,
        "context": "Well. Routine bloods before planning a second pregnancy."},
    10: {"weight_kg": 55.2, "bp": "112/70", "spo2": 99, "temp_f": 98.6,
         "context": "Burning on passing urine for three days."},
    11: {"weight_kg": 56.8, "bp": "114/72", "spo2": 98, "temp_f": 98.2,
         "context": "Second pregnancy, booking visit at ten weeks."},
    12: {"weight_kg": 62.4, "bp": "122/78", "spo2": 98, "temp_f": 98.4,
         "context": "Twenty-six weeks. Glucose tolerance test abnormal this time."},
    13: {"weight_kg": 66.1, "bp": "148/96", "spo2": 97, "temp_f": 98.6,
         "context": "Thirty-four weeks. Blood pressure raised, monitored closely."},
    14: {"weight_kg": 68.2, "bp": "132/84", "spo2": 98, "temp_f": 98.8,
         "context": "Admitted at thirty-eight weeks for induction."},
    15: {"weight_kg": 60.4, "bp": "116/74", "spo2": 99, "temp_f": 98.2,
         "context": "Four months postnatal. Ovarian cyst seen on the scan."},
}

REPORTS = [
    # ---- R01 -- pre-conception ----------------------------------------------
    {
        "collected": "2021-11-09 09:15", "reported": "2021-11-09 17:20",
        "lab": "utkal", "layout_style": "clean_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": ROUT, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["legend_lines", "text_result"],
        "sections": [
            {"panel": "CBC", "title": 0, "drop": ["ANC", "ALC", "MPV"],
             "legend": ANC_LEGEND,
             "values": {"HGB": 9.8, "RBC": 4.12, "PCV": 31.4, "MCV": 76.2, "MCH": 23.8,
                        "MCHC": 31.2, "RDW": 16.4, "WBC": 7400, "NEUT_PCT": 60,
                        "LYMPH_PCT": 30, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 296000}},
            {"panel": "IRON", "title": 4,
             "values": {"FERRITIN": 8, "IRON": 34, "TIBC": 448}},
            {"heading": "Other",
             "rows": [{"code": "BLOOD_GROUP", "value": "B Negative",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R02 -- first booking visit ------------------------------------------
    {
        "collected": "2022-02-15 08:30", "reported": "2022-02-15 18:00",
        "lab": "kalinga", "layout_style": "dense_multipanel",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": MISHRA_O, "specimen": "Whole blood (EDTA), Serum, Urine",
        "alias": 1, "traps": ["text_result", "method_sub_line"],
        "note": "Routine antenatal booking profile at nine weeks.",
        "sections": [
            {"panel": "SEROLOGY", "title": 2, "drop": ["WIDAL", "DENGUE_NS1",
                                                       "DENGUE_IGM", "MP"],
             "methods": True,
             "values": {"HBSAG": "Non Reactive", "ANTI_HCV": "Non Reactive",
                        "HIV": "Non Reactive", "VDRL": "Non Reactive"},
             "row_traps": {"HIV": "text_result"}},
            {"panel": "THYROID", "title": 0, "drop": ["T3_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel",
             "values": {"TSH": 2.18, "T4_TOTAL": 10.4, "FT4": 1.32}},
            {"panel": "URINE_ROUTINE", "title": 2, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.5, "UR_SPGR": 1.014,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 4, "UR_RBC": 1, "UR_EPITH": 5}},
            {"heading": "Booking Bloods",
             "rows": [{"code": "HGB", "value": 9.2, "flag": "L"},
                      {"code": "GLU_F", "value": 84},
                      {"label": "Rubella IgG Antibody", "value": "Immune (48.2 IU/mL)",
                       "unit": "", "reference": "Immune above 10 IU/mL",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R03 -- eighteen weeks ----------------------------------------------
    {
        "collected": "2022-04-26 09:40", "reported": "2022-04-26 15:50",
        "lab": "jagannath", "layout_style": "minimal_lines",
        "header_style": "bilingual_header", "uhid_label": "Reg. No",
        "doctor": ROUT, "specimen": "Serum, Urine (midstream)",
        "alias": 2, "traps": ["unit_in_value_cell", "sample_type_row"],
        "sections": [
            {"panel": "IRON", "title": 5, "sample_row": "Serum, fasting not required",
             "drop": ["UIBC"],
             "values": {"FERRITIN": 14, "IRON": 48, "TIBC": 424}},
            {"panel": "URINE_ROUTINE", "title": 5, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.0, "UR_SPGR": 1.012,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 3, "UR_RBC": 0, "UR_EPITH": 4}},
            {"heading": "Haemoglobin",
             "rows": [{"code": "HGB", "value": 10.2, "flag": "L"}]},
        ],
    },
    # ---- R04 -- glucose tolerance test, first pregnancy --------------------
    {
        "collected": "2022-07-12 08:00", "reported": "2022-07-12 14:30",
        "lab": "kalinga", "layout_style": "landscape_wide",
        "header_style": "barcode_header", "uhid_label": "Hospital No",
        "doctor": MISHRA_O, "specimen": "Fluoride plasma",
        "alias": 3, "traps": ["legend_lines", "prev_value_column"],
        "note": "75 g oral glucose tolerance test performed at twenty-six weeks.",
        "sections": [
            {"panel": "DIABETES", "title": 1, "drop": ["GLU_R", "INSULIN_F", "EAG"],
             "legend": GDM_LEGEND,
             "prev": {"GLU_F": "84 (15/02/2022)"},
             "values": {"GLU_F": 88, "GLU_PP": 124, "HBA1C": 5.2},
             "extra_rows": [
                 {"label": "Plasma Glucose - 1 hour (75 g load)", "value": "146",
                  "unit": "mg/dL", "reference": "< 180"},
             ]},
        ],
    },
    # ---- R05 -- thirty-four weeks -------------------------------------------
    {
        "collected": "2022-09-20 09:05", "reported": "2022-09-20 17:15",
        "lab": "utkal", "layout_style": "two_column",
        "header_style": "banner_with_qr", "uhid_label": "Patient ID",
        "doctor": ROUT, "specimen": "Serum",
        "alias": 0, "traps": ["sno_column", "flag_as_words"],
        "sections": [
            {"panel": "LFT", "title": 3, "drop": ["GGT", "BILI_I"],
             "values": {"BILI_T": 0.5, "BILI_D": 0.1, "ALT": 18, "AST": 20, "ALP": 156,
                        "PROT_T": 6.4, "ALB": 3.4}},
            {"panel": "KFT", "title": 1, "drop": ["UA"],
             "values": {"CREAT": 0.54, "UREA": 16}},
            {"heading": "Haemoglobin",
             "rows": [{"code": "HGB", "value": 11.2}]},
        ],
    },
    # ---- R06 -- admitted in labour ------------------------------------------
    {
        "collected": "2022-11-24 03:10", "reported": "2022-11-24 05:40",
        "lab": "kalinga", "layout_style": "fax_header",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": MISHRA_O, "specimen": "Whole blood (EDTA), Serum",
        "alias": 1, "traps": ["no_reference_column", "text_result"],
        "note": "Faxed to the labour room. Cross-match sample held.",
        "sections": [
            {"panel": "CBC", "title": 4, "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "values": {"HGB": 11.6, "RBC": 4.38, "PCV": 35.2, "MCV": 80.4, "MCH": 26.5,
                        "WBC": 11800, "NEUT_PCT": 76, "LYMPH_PCT": 18, "MONO_PCT": 4,
                        "EOS_PCT": 1, "BASO_PCT": 1, "PLT": 232000}},
            {"panel": "ELECTROLYTES", "title": 0, "drop": ["CA_ION", "MG", "PHOS"],
             "values": {"NA": 137, "K": 4.0, "CL": 101, "CA": 8.8}},
            {"heading": "Blood Bank",
             "rows": [{"code": "BLOOD_GROUP", "value": "B Negative, Anti-D given",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R07 -- six weeks postnatal, one test -------------------------------
    {
        "collected": "2023-01-11 10:20", "reported": "2023-01-11 13:50",
        "lab": "jagannath", "layout_style": "thermal_slip",
        "header_style": "centred_title_only", "uhid_label": "Reg. No",
        "doctor": ROUT, "specimen": "Whole blood (EDTA)",
        "alias": 2, "traps": ["no_reference_column"],
        "sections": [
            {"heading": "Haemoglobin",
             "rows": [{"code": "HGB", "value": 11.8}]},
        ],
    },
    # ---- R08 -- annual health check -----------------------------------------
    {
        "collected": "2023-09-08 07:50", "reported": "2023-09-08 19:30",
        "lab": "utkal", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Patient ID",
        "doctor": BEHERA, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 3, "traps": ["merged_panel_heading", "method_sub_line"],
        "note": "Annual health check package.",
        "sections": [
            {"panel": "LIPID", "title": 1, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 168, "TRIG": 104, "HDL": 52}},
            {"panels": ["LFT", "ELECTROLYTES"], "heading": "Biochemistry Screen",
             "trap": "merged_panel_heading",
             "drop": ["GGT", "AG_RATIO", "GLOB", "BILI_I", "CA_ION", "MG"],
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 20, "AST": 22, "ALP": 78,
                        "PROT_T": 7.2, "ALB": 4.2,
                        "NA": 140, "K": 4.2, "CL": 103, "CA": 9.4, "PHOS": 3.8}},
            {"panel": "THYROID", "title": 4, "drop": ["T3_TOTAL", "FT3"],
             "values": {"TSH": 2.86, "T4_TOTAL": 9.2, "FT4": 1.18, "ANTI_TPO": 14.2}},
            {"panel": "VITAMIN", "title": 1, "methods": True,
             "values": {"VIT_D": 18.6, "VIT_B12": 274, "FOLATE": 7.2}},
            {"heading": "Other",
             "rows": [{"code": "HGB", "value": 12.2}, {"code": "HBA1C", "value": 5.3}]},
        ],
    },
    # ---- R09 -- planning again ----------------------------------------------
    {
        "collected": "2024-04-17 09:00", "reported": "2024-04-17 16:10",
        "lab": "jagannath", "layout_style": "kv_header_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Reg. No",
        "doctor": ROUT, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 0, "traps": ["footnote_marker"],
        "footnotes": [("1", "Homocysteine and vitamin B12 checked before conception as "
                            "part of the pre-pregnancy profile.")],
        "sections": [
            {"heading": "Pre-pregnancy Profile",
             "rows": [{"code": "HGB", "value": 12.4},
                      {"code": "FERRITIN", "value": 32},
                      {"code": "VIT_B12", "value": 288},
                      {"label": "Homocysteine", "value": "11.6", "unit": "umol/L",
                       "reference": "5.0 - 15.0", "marker": "1"}]},
        ],
    },
    # ---- R10 -- urinary symptoms --------------------------------------------
    {
        "collected": "2024-11-23 10:40", "reported": "2024-11-24 11:20",
        "lab": "utkal", "layout_style": "clean_table",
        "header_style": "stamp_and_signature", "uhid_label": "Patient ID",
        "doctor": BEHERA, "specimen": "Urine (midstream)",
        "alias": 1, "traps": ["text_result", "abnormal_shaded"],
        "stamp": "CULTURE<br>POSITIVE",
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 0,
             "values": {"UR_COLOUR": "Hazy Yellow", "UR_PH": 6.5, "UR_SPGR": 1.020,
                        "UR_PROT": "Trace", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 42, "UR_RBC": 6, "UR_EPITH": 8, "MICROALB": 14,
                        "ACR": 16}},
            {"heading": "Microbiology",
             "rows": [{"code": "URINE_CULTURE",
                       "value": "Escherichia coli, >100000 CFU/mL. Sensitive: "
                                "Nitrofurantoin, Fosfomycin. Resistant: Ampicillin.",
                       "flag": "H", "trap": "text_result"}]},
        ],
    },
    # ---- R11 -- second booking visit ----------------------------------------
    {
        "collected": "2025-03-14 08:25", "reported": "2025-03-14 18:10",
        "lab": "kalinga", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": MISHRA_O, "specimen": "Whole blood (EDTA), Serum",
        "alias": 2, "traps": ["text_result", "prev_value_column"],
        "sections": [
            {"panel": "SEROLOGY", "title": 3, "drop": ["WIDAL", "DENGUE_NS1",
                                                       "DENGUE_IGM", "MP"],
             "prev": {"HBSAG": "Non Reactive (15/02/2022)",
                      "HIV": "Non Reactive (15/02/2022)"},
             "values": {"HBSAG": "Non Reactive", "ANTI_HCV": "Non Reactive",
                        "HIV": "Non Reactive", "VDRL": "Non Reactive"},
             "row_traps": {"VDRL": "text_result"}},
            {"panel": "THYROID", "title": 1, "drop": ["T3_TOTAL", "FT3", "ANTI_TPO"],
             "values": {"TSH": 2.42, "T4_TOTAL": 10.8, "FT4": 1.28}},
            {"panel": "KFT", "title": 3, "drop": ["UA"],
             "values": {"CREAT": 0.58, "UREA": 18}},
            {"heading": "Booking Bloods",
             "prev": {"HGB": "12.4 (17/04/2024)"},
             "rows": [{"code": "HGB", "value": 11.4, "flag": "L"}]},
        ],
    },
    # ---- R12 -- gestational diabetes ----------------------------------------
    {
        "collected": "2025-07-29 07:45", "reported": "2025-07-29 14:05",
        "lab": "kalinga", "layout_style": "duplicate_watermark",
        "header_style": "barcode_header", "uhid_label": "Hospital No",
        "doctor": MISHRA_O, "specimen": "Fluoride plasma",
        "alias": 3, "traps": ["legend_lines", "abnormal_shaded"],
        "note": "Gestational diabetes mellitus. Referred to the diabetes in pregnancy "
                "clinic. Duplicate copy issued for the antenatal card.",
        "sections": [
            {"panel": "DIABETES", "title": 4, "drop": ["GLU_R", "INSULIN_F"],
             "legend": GDM_LEGEND,
             "values": {"GLU_F": 104, "GLU_PP": 168, "HBA1C": 5.9},
             "extra_rows": [
                 {"label": "Plasma Glucose - 1 hour (75 g load)", "value": "196",
                  "unit": "mg/dL", "reference": "< 180", "flag": "H"},
             ]},
            {"heading": "Haemoglobin",
             "rows": [{"code": "HGB", "value": 10.4, "flag": "L"}]},
        ],
    },
    # ---- R13 -- thirty-four weeks, one test ---------------------------------
    {
        "collected": "2025-10-18 08:10", "reported": "2025-10-18 11:35",
        "lab": "jagannath", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": ROUT, "specimen": "Fluoride plasma",
        "alias": 0, "traps": ["no_header_row"],
        "sections": [
            {"heading": "Blood Sugar - Fasting",
             "rows": [{"code": "GLU_F", "value": 96}]},
        ],
    },
    # ---- R14 -- admitted for induction, two pages ---------------------------
    {
        "collected": "2026-01-21 05:50", "reported": "2026-01-21 16:40",
        "lab": "kalinga", "layout_style": "continuation",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": MISHRA_O, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["footnote_marker", "ratio_no_code"],
        "page_break_after": 3,
        "footnotes": [("1", "Pre-induction profile. Anaesthetic review completed.")],
        "sections": [
            {"panel": "CBC", "title": 5,
             "values": {"HGB": 11.0, "RBC": 4.22, "PCV": 33.8, "MCV": 80.1, "MCH": 26.1,
                        "MCHC": 32.5, "RDW": 15.1, "WBC": 12400, "NEUT_PCT": 78,
                        "LYMPH_PCT": 16, "MONO_PCT": 4, "EOS_PCT": 1, "BASO_PCT": 1,
                        "PLT": 218000, "MPV": 10.2}},
            {"panel": "LIPID", "title": 5, "drop": ["LDL_HDL_RATIO"],
             "values": {"CHOL": 214, "TRIG": 216, "HDL": 58}},
            {"panel": "DIABETES", "title": 5, "drop": ["GLU_R"],
             "values": {"GLU_F": 98, "GLU_PP": 142, "HBA1C": 5.7, "INSULIN_F": 16.4},
             "row_traps": {"GLU_F": "footnote_marker"}},
            {"panel": "LFT", "title": 5,
             "values": {"BILI_T": 0.5, "BILI_D": 0.1, "ALT": 22, "AST": 24, "ALP": 182,
                        "GGT": 16, "PROT_T": 6.6, "ALB": 3.3}},
            {"panel": "KFT", "title": 5,
             "values": {"CREAT": 0.62, "UREA": 20, "UA": 5.4}},
            {"heading": "Derived",
             "rows": [{"label": "Urea / Creatinine Ratio", "value": "32", "unit": "",
                       "reference": "20 - 35", "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R15 -- four months postnatal ---------------------------------------
    {
        "collected": "2026-06-05 09:20", "reported": "2026-06-05 17:00",
        "lab": "utkal", "layout_style": "mobile_photo",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": ROUT, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["method_sub_line"],
        "note": "Photographed copy received from the patient by email.",
        "sections": [
            {"panel": "IRON", "title": 2, "methods": True,
             "values": {"FERRITIN": 26, "IRON": 68, "TIBC": 386}},
            {"panel": "VITAMIN", "title": 5, "methods": True,
             "values": {"VIT_D": 24.2, "VIT_B12": 312, "FOLATE": 8.8}},
            {"heading": "Tumour Marker",
             "rows": [{"label": "CA 125", "value": "28.6", "unit": "U/mL",
                       "reference": "< 35.0"},
                      {"code": "HGB", "value": 11.9}]},
        ],
    },
]
