"""Patient 20 of 20 - Endocrinology. Thyrotoxicosis treated to hypothyroid, then stable.

Female, 31 at the first report, Thiruvananthapuram. Presents thyrotoxic: TSH below 0.01,
free T4 4.2, weight falling, pulse 118. Carbimazole controls it for two years, she relapses
when the drug is stopped in 2023, and radioiodine in early 2024 does what radioiodine does -
she becomes hypothyroid four months later with TSH 48.6, and is settled on thyroxine by the
end of the record. The curve therefore crosses the reference interval twice, from below and
from above, which is what makes it worth charting.

The setback is the 2023 relapse; the radioiodine admission in 2024 is the turning point.

Five of the fifteen are unusual documents: two chat screenshots of the lab sending values,
a photographed page of the collection centre register, the two-page discharge summary from
the radioiodine admission, and one report in the range-bar format.
"""

from __future__ import annotations

PATIENT = {
    "number": 20,
    "name": "Divya Sreekumar",
    "sex": "F",
    "dob": "1990-07-19",
    "uhid": "ANT/826135",
    "department": "Endocrinology",
    "city": "Thiruvananthapuram",
    "age_at_first": 31,
    "tracked": ["TSH"],
    "brief": "Thyrotoxicosis treated to hypothyroid, then stable",
}


def check_arc(series):
    tsh = [v for _, v in series["TSH"]]
    fails = []
    if not tsh[0] < 0.1:
        fails.append(f"should present thyrotoxic, TSH {tsh[0]}")
    if not max(tsh) > 20:
        fails.append(f"radioiodine should make her hypothyroid, peak TSH {max(tsh)}")
    if not 0.4 <= tsh[-1] <= 5.0:
        fails.append(f"should end euthyroid on thyroxine, TSH {tsh[-1]}")
    if len([v for v in tsh if v < 0.4]) < 3:
        fails.append("the thyrotoxic phase is too short to chart")
    return fails


LABS = {
    "anantha": {
        "abbr": "ANT", "acc_style": 1,
        "name": "Anantha Speciality Hospital Laboratory",
        "name_local": "അനന്ത സ്പെഷ്യാലിറ്റി ഹോസ്പിറ്റൽ ലബോറട്ടറി",
        "addr": "Vazhuthacaud, Thiruvananthapuram 695014",
        "addr_local": "വഴുതക്കാട്, തിരുവനന്തപുരം 695014",
        "city": "Thiruvananthapuram",
        "phone": "0471 232 8800",
        "accred": "Department of Laboratory Medicine, Endocrine Services",
        "path": {"name": "Dr. Remya Vasudevan", "qual": "MD, DNB (Pathology)",
                 "regn": "TCMC 2005/03/1194", "scrawl": "R Vasudevan"},
    },
    "padma": {
        "abbr": "PDL", "acc_style": 0,
        "name": "Padmanabha Diagnostic Labs",
        "name_local": "പദ്മനാഭ ഡയഗ്നോസ്റ്റിക് ലാബ്സ്",
        "addr": "Pattom, Thiruvananthapuram 695004",
        "addr_local": "പട്ടം, തിരുവനന്തപുരം 695004",
        "city": "Thiruvananthapuram",
        "phone": "0471 244 6617",
        "accred": "NABL Accredited (MC-6693) | ISO 15189:2012",
        "path": {"name": "Dr. Jayakrishnan Nair", "qual": "MD (Pathology)",
                 "regn": "TCMC 2009/08/5528", "scrawl": "J Nair"},
    },
    "kovalam": {
        "abbr": "KPC", "acc_style": 3,
        "name": "Kovalam Road Path Centre",
        "name_local": "കോവളം റോഡ് പാത്ത് സെന്റർ",
        "addr": "Kazhakkoottam, Thiruvananthapuram 695582",
        "addr_local": "കഴക്കൂട്ടം, തിരുവനന്തപുരം 695582",
        "city": "Thiruvananthapuram",
        "phone": "0471 270 3345",
        "accred": "Clinical Laboratory, Reg. No. TVM/DL/2018/3312",
        "path": {"name": "Dr. Beena Thomas", "qual": "MBBS, DCP",
                 "regn": "TCMC 2013/05/8840", "scrawl": "B Thomas"},
    },
}

MENON = "Dr. Hari Menon, MBBS, MD, DM (Endocrinology)"
LEKHA = "Dr. Lekha Pillai, MBBS, MD (General Medicine)"
RAJAN = "Dr. S. Rajan, MBBS, MD (Nuclear Medicine)"

TSH_LEGEND = [
    ("TSH - interpretation", "TSH uIU/mL"),
    ("Below 0.40", "Suppressed, consistent with thyrotoxicosis"),
    ("0.55 - 4.78", "Euthyroid"),
    ("4.79 - 10.00", "Subclinical hypothyroidism"),
    ("Above 10.00", "Overt hypothyroidism"),
]

# Thyrotoxicosis takes eight kilos off and the pulse and blood pressure with it;
# the weight comes back as she becomes euthyroid and then hypothyroid.
HEIGHT_CM = 160.0

VITALS = {
    1: {"weight_kg": 49.2, "bp": "138/72", "spo2": 99, "temp_f": 99.2,
        "context": "Palpitations, tremor, eight kilos lost in four months. Pulse 118."},
    2: {"weight_kg": 50.6, "bp": "132/74", "spo2": 98, "temp_f": 98.6,
        "context": "Six weeks on carbimazole. Tremor settling, pulse 92."},
    3: {"weight_kg": 53.4, "bp": "124/76", "spo2": 99, "temp_f": 98.4,
        "context": "Much better. Weight returning, propranolol stopped."},
    4: {"weight_kg": 55.8, "bp": "120/76", "spo2": 98, "temp_f": 98.2,
        "context": "Euthyroid on a maintenance dose."},
    5: {"weight_kg": 56.4, "bp": "118/74", "spo2": 99, "temp_f": 98.4,
        "context": "Stable. Carbimazole dose reduced further."},
    6: {"weight_kg": 55.0, "bp": "128/74", "spo2": 98, "temp_f": 98.6,
        "context": "Carbimazole stopped after eighteen months, as planned."},
    7: {"weight_kg": 52.2, "bp": "136/72", "spo2": 99, "temp_f": 99.0,
        "context": "Relapse. Symptoms back within three months of stopping."},
    8: {"weight_kg": 51.8, "bp": "134/74", "spo2": 98, "temp_f": 98.8,
        "context": "Admitted for radioiodine. Counselled on lifelong monitoring."},
    9: {"weight_kg": 53.6, "bp": "126/76", "spo2": 99, "temp_f": 98.4,
        "context": "Six weeks after radioiodine. Symptoms improving."},
    10: {"weight_kg": 57.2, "bp": "118/74", "spo2": 98, "temp_f": 97.9,
         "context": "Now hypothyroid, as expected. Thyroxine started."},
    11: {"weight_kg": 58.4, "bp": "116/74", "spo2": 98, "temp_f": 98.2,
         "context": "Dose being titrated upward."},
    12: {"weight_kg": 57.8, "bp": "116/72", "spo2": 99, "temp_f": 98.4,
         "context": "Approaching target on 100 mcg."},
    13: {"weight_kg": 57.2, "bp": "114/72", "spo2": 98, "temp_f": 98.2,
         "context": "Single confirmatory TSH before the annual review."},
    14: {"weight_kg": 56.6, "bp": "114/72", "spo2": 99, "temp_f": 98.4,
         "context": "Annual review. Euthyroid on a settled dose."},
    15: {"weight_kg": 56.2, "bp": "112/72", "spo2": 98, "temp_f": 98.6,
         "context": "Stable. Yearly TSH agreed, pregnancy planning discussed."},
}

REPORTS = [
    # ---- R01 -- thyrotoxic at presentation -----------------------------------
    {
        "collected": "2021-10-11 09:20", "reported": "2021-10-11 18:40",
        "lab": "anantha", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": MENON, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 0, "traps": ["legend_lines", "abnormal_shaded"],
        "damage": ["aged", "fold"],
        "interpretation": "Biochemical thyrotoxicosis with a strongly positive TSH "
                          "receptor antibody, in keeping with Graves disease. Start "
                          "carbimazole with a beta blocker and review in six weeks.",
        "sections": [
            {"panel": "THYROID", "title": 0, "legend": TSH_LEGEND,
             "values": {"TSH": 0.01, "T3_TOTAL": 268, "T4_TOTAL": 18.4, "FT3": 9.6,
                        "FT4": 4.20, "ANTI_TPO": 186.0}},
            {"heading": "Additional",
             "rows": [{"label": "TSH Receptor Antibody (TRAb)", "value": "12.4",
                       "unit": "IU/L", "reference": "< 1.75", "flag": "H"},
                      {"code": "ALT", "value": 62, "flag": "H"}]},
        ],
    },
    # ---- R02 -- six weeks on carbimazole, sent over chat ---------------------
    {
        "collected": "2021-12-02 09:10", "reported": "2021-12-02 17:30",
        "lab": "kovalam", "layout_style": "chat_screenshot",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": MENON, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 1, "traps": [],
        "note": "Screenshot saved to the endocrine clinic file by the patient.",
        "sections": [
            {"heading": "Madam your reports",
             "rows": [{"code": "TSH", "value": 0.02, "flag": "L"},
                      {"code": "FT4", "value": 2.84, "flag": "H"},
                      {"code": "WBC", "value": 5200}]},
        ],
    },
    # ---- R03 -- much better ---------------------------------------------------
    {
        "collected": "2022-04-14 08:50", "reported": "2022-04-14 16:20",
        "lab": "padma", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Patient ID",
        "doctor": MENON, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["unit_in_label"],
        "sections": [
            {"panel": "CBC", "title": 0, "drop": ["ANC", "ALC", "MPV"],
             "values": {"HGB": 12.4, "RBC": 4.32, "PCV": 37.6, "MCV": 87.0, "MCH": 28.7,
                        "MCHC": 33.0, "RDW": 13.2, "WBC": 5600, "NEUT_PCT": 56,
                        "LYMPH_PCT": 34, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 268000}},
            {"heading": "Thyroid Function",
             "rows": [{"code": "TSH", "value": 0.18, "flag": "L"},
                      {"code": "FT4", "value": 1.62},
                      {"code": "T3_TOTAL", "value": 168}]},
        ],
    },
    # ---- R04 -- euthyroid on maintenance --------------------------------------
    {
        "collected": "2022-09-28 08:30", "reported": "2022-09-28 17:10",
        "lab": "anantha", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Hospital No",
        "doctor": MENON, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 3, "traps": ["merged_panel_heading", "text_result", "method_sub_line"],
        "note": "Annual review package with carbimazole monitoring bloods.",
        "sections": [
            {"panel": "LIPID", "title": 0, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 168, "TRIG": 98, "HDL": 56}},
            {"panels": ["LFT", "KFT"], "heading": "Carbimazole Monitoring",
             "trap": "merged_panel_heading",
             "drop": ["GGT", "AG_RATIO", "GLOB", "BILI_I", "BUN", "BILI_D", "PROT_T",
                      "UA"],
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 32, "AST": 28, "ALP": 78,
                        "PROT_T": 7.2, "ALB": 4.3,
                        "CREAT": 0.64, "UREA": 21, "UA": 4.0}},
            {"panel": "IRON", "title": 0, "drop": ["UIBC"], "methods": True,
             "values": {"FERRITIN": 38, "IRON": 76, "TIBC": 356}},
            {"panel": "URINE_ROUTINE", "title": 2, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.5, "UR_SPGR": 1.014,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 2, "UR_RBC": 0, "UR_EPITH": 3}},
            {"panel": "ELECTROLYTES", "title": 2, "drop": ["CA_ION", "PHOS"],
             "values": {"NA": 140, "K": 4.2, "CL": 103, "CA": 9.4, "MG": 2.1}},
            {"panel": "VITAMIN", "title": 0,
             "values": {"VIT_D": 18.2, "VIT_B12": 318, "FOLATE": 8.2}},
            {"heading": "Thyroid and Other",
             "rows": [{"code": "TSH", "value": 1.86},
                      {"code": "FT4", "value": 1.24},
                      {"code": "BLOOD_GROUP", "value": "O Positive",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R05 -- the collection centre register --------------------------------
    {
        "collected": "2023-02-17 10:40", "reported": "2023-02-17 15:50",
        "lab": "kovalam", "layout_style": "register_page",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": LEKHA, "specimen": "Serum",
        "alias": 0, "traps": [],
        "damage": ["aged", "dark"],
        "sections": [
            {"heading": "Register Entries",
             "rows": [{"code": "TSH", "value": 2.42},
                      {"code": "FT4", "value": 1.18}]},
        ],
    },
    # ---- R06 -- carbimazole stopped --------------------------------------------
    {
        "collected": "2023-06-30 09:00", "reported": "2023-06-30 14:40",
        "lab": "padma", "layout_style": "thermal_slip",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": MENON, "specimen": "Serum",
        "alias": 1, "traps": ["no_reference_column"],
        "sections": [
            {"heading": "TSH - Ultrasensitive",
             "rows": [{"code": "TSH", "value": 1.42}]},
        ],
    },
    # ---- R07 -- the relapse ----------------------------------------------------
    {
        "collected": "2023-11-18 09:30", "reported": "2023-11-18 18:00",
        "lab": "anantha", "layout_style": "clean_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Hospital No",
        "doctor": MENON, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["legend_lines", "abnormal_shaded"],
        "damage": ["crop-right", "dark"],
        "note": "Relapse of thyrotoxicosis three months after stopping carbimazole. "
                "Definitive treatment discussed.",
        "sections": [
            {"panel": "THYROID", "title": 2, "legend": TSH_LEGEND, "drop": ["ANTI_TPO"],
             "values": {"TSH": 0.01, "T3_TOTAL": 242, "T4_TOTAL": 16.8, "FT3": 8.4,
                        "FT4": 3.68}},
            {"panel": "INFLAMMATION", "title": 0, "drop": ["RA_FACTOR", "ASO"],
             "values": {"CRP": 3.2, "HS_CRP": 1.40}},
            {"heading": "Haematology",
             "rows": [{"code": "PERIPH_SMEAR",
                       "value": "Normocytic normochromic red cells. No abnormal cells.",
                       "trap": "text_result"},
                      {"code": "ESR", "value": 14}]},
        ],
    },
    # ---- R08 -- radioiodine admission, discharge summary ----------------------
    {
        "collected": "2024-02-08 07:40", "reported": "2024-02-08 12:20",
        "lab": "anantha", "layout_style": "discharge_summary",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": RAJAN, "specimen": "Serum, Whole blood (EDTA), Urine",
        "alias": 3, "traps": ["text_result"],
        "discharge": {
            "diagnosis": "Graves disease, relapsed after a completed course of "
                         "carbimazole. Treated with oral radioiodine, 12 mCi.",
            "history": "Thyrotoxic since 2021, controlled on carbimazole for eighteen "
                       "months and relapsed within three months of stopping it. "
                       "Definitive treatment was discussed at length and radioiodine "
                       "chosen over surgery.",
            "examination": "Pulse 104 regular, fine tremor, small diffuse goitre with no "
                           "bruit. No eye signs. Weight 51.8 kg.",
            "course": "Admitted for the day. Pregnancy test negative before dosing. Oral "
                      "radioiodine given at 10:15 hrs. Observed for four hours with no "
                      "immediate reaction and discharged the same evening with radiation "
                      "protection instructions.",
            "treatment": "Radioiodine (I-131) 12 mCi orally. Propranolol 20 mg three "
                         "times daily to continue for six weeks. Carbimazole stopped "
                         "four days before dosing as planned.",
            "advice": "Avoid close contact with children and pregnant women for seven "
                      "days. Avoid pregnancy for six months. Thyroid function to be "
                      "checked at six weeks and then every six weeks - hypothyroidism is "
                      "expected and is not a complication. Report any neck swelling, "
                      "fever or sore throat at once.",
        },
        "sections": [
            {"heading": "Before Dosing (08/02/2024)",
             "rows": [{"code": "TSH", "value": 0.01, "flag": "L"},
                      {"code": "FT4", "value": 3.42, "flag": "H"},
                      {"code": "T3_TOTAL", "value": 228, "flag": "H"},
                      {"code": "WBC", "value": 5400},
                      {"code": "ALT", "value": 38},
                      {"code": "CREAT", "value": 0.62}]},
            {"heading": "Pre-treatment Screen",
             "rows": [{"label": "Urine Pregnancy Test", "value": "Negative", "unit": "",
                       "reference": "Negative", "trap": "text_result"},
                      {"label": "Radioiodine Uptake at 24 hours", "value": "62",
                       "unit": "%", "reference": "15 - 35", "flag": "H"}]},
        ],
    },
    # ---- R09 -- six weeks after radioiodine ------------------------------------
    {
        "collected": "2024-03-22 09:15", "reported": "2024-03-22 16:40",
        "lab": "padma", "layout_style": "range_bar",
        "header_style": "two_line_ribbon", "uhid_label": "Patient ID",
        "doctor": RAJAN, "specimen": "Serum",
        "alias": 0, "traps": ["method_sub_line"],
        "sections": [
            {"heading": "Thyroid Function - Post Radioiodine", "methods": True,
             "rows": [{"code": "TSH", "value": 0.06, "flag": "L"},
                      {"code": "T3_TOTAL", "value": 148},
                      {"code": "T4_TOTAL", "value": 9.8},
                      {"code": "FT3", "value": 3.6},
                      {"code": "FT4", "value": 1.48}]},
            {"panel": "DIABETES", "title": 0, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 88, "GLU_PP": 116, "HBA1C": 5.2}},
        ],
    },
    # ---- R10 -- hypothyroid, as expected ---------------------------------------
    {
        "collected": "2024-06-14 08:40", "reported": "2024-06-14 17:20",
        "lab": "anantha", "layout_style": "kv_header_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Hospital No",
        "doctor": MENON, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 1, "traps": ["legend_lines", "flag_as_words"],
        "damage": ["fold", "stain"],
        "sections": [
            {"panel": "THYROID", "title": 4, "legend": TSH_LEGEND, "drop": ["FT3"],
             "values": {"TSH": 48.60, "T3_TOTAL": 62, "T4_TOTAL": 3.4, "FT4": 0.46,
                        "ANTI_TPO": 142.0}},
            {"panel": "LIPID", "title": 4, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 238, "TRIG": 164, "HDL": 52}},
        ],
    },
    # ---- R11 -- dose being titrated ---------------------------------------------
    {
        "collected": "2024-11-02 09:20", "reported": "2024-11-02 16:00",
        "lab": "kovalam", "layout_style": "chat_screenshot",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": MENON, "specimen": "Serum",
        "alias": 2, "traps": [],
        "note": "Second screenshot in the file; the clinic asked for the printed copy.",
        "sections": [
            {"heading": "Reports madam",
             "rows": [{"code": "TSH", "value": 12.40, "flag": "H"},
                      {"code": "FT4", "value": 0.86, "flag": "L"}]},
        ],
    },
    # ---- R12 -- approaching target -----------------------------------------------
    {
        "collected": "2025-04-19 08:55", "reported": "2025-04-19 17:00",
        "lab": "padma", "layout_style": "ledger_ruled",
        "header_style": "bilingual_header", "uhid_label": "Patient ID",
        "doctor": MENON, "specimen": "Serum, Urine (midstream)",
        "alias": 3, "traps": ["range_split_columns", "sample_type_row"],
        "damage": ["aged"],
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 0, "sample_row": "Urine, Midstream",
             "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.0, "UR_SPGR": 1.016,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 3, "UR_RBC": 1, "UR_EPITH": 4}},
            {"panel": "ELECTROLYTES", "title": 0, "drop": ["CA_ION", "MG"],
             "values": {"NA": 139, "K": 4.1, "CL": 102, "CA": 9.2, "PHOS": 3.4}},
            {"heading": "Thyroid Function",
             "rows": [{"code": "TSH", "value": 5.42, "flag": "H"},
                      {"code": "FT4", "value": 1.08}]},
        ],
    },
    # ---- R13 -- one confirmatory TSH -----------------------------------------------
    {
        "collected": "2025-10-08 09:40", "reported": "2025-10-08 13:10",
        "lab": "kovalam", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": LEKHA, "specimen": "Serum",
        "alias": 0, "traps": ["no_header_row"],
        "damage": ["scanborder", "aged"],
        "sections": [
            {"heading": "TSH - Ultrasensitive",
             "rows": [{"code": "TSH", "value": 3.18}]},
        ],
    },
    # ---- R14 -- annual review, two pages --------------------------------------------
    {
        "collected": "2026-04-27 07:50", "reported": "2026-04-27 19:40",
        "lab": "anantha", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "Hospital No",
        "doctor": MENON, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["footnote_marker", "ratio_no_code"],
        "page_break_after": 3,
        "footnotes": [("1", "Thyroxine 100 mcg daily. If pregnancy is planned the dose "
                            "will need increasing and TSH checking every four weeks.")],
        "sections": [
            {"panel": "CBC", "title": 5,
             "values": {"HGB": 12.8, "RBC": 4.44, "PCV": 38.6, "MCV": 86.9, "MCH": 28.8,
                        "MCHC": 33.2, "RDW": 12.8, "WBC": 6200, "NEUT_PCT": 57,
                        "LYMPH_PCT": 33, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 262000, "MPV": 9.4}},
            {"panel": "LIPID", "title": 5,
             "values": {"CHOL": 184, "TRIG": 108, "HDL": 58}},
            {"panel": "DIABETES", "title": 5, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 86, "GLU_PP": 114, "HBA1C": 5.1}},
            {"panel": "LFT", "title": 5,
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 24, "AST": 22, "ALP": 74,
                        "GGT": 16, "PROT_T": 7.2, "ALB": 4.3}},
            {"panel": "KFT", "title": 5,
             "values": {"CREAT": 0.66, "UREA": 22, "UA": 4.2}},
            {"heading": "Thyroid and Derived",
             "rows": [{"code": "TSH", "value": 2.64, "marker": "1"},
                      {"code": "FT4", "value": 1.22},
                      {"label": "FT3 / FT4 Ratio", "value": "2.7", "unit": "",
                       "reference": "2.0 - 3.5", "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R15 -- stable, planning a pregnancy -----------------------------------------
    {
        "collected": "2026-09-14 08:45", "reported": "2026-09-14 16:10",
        "lab": "padma", "layout_style": "mixed_print_hand",
        "header_style": "stamp_and_signature", "uhid_label": "Patient ID",
        "doctor": MENON, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["method_sub_line"], "stamp": "ENDOCRINE<br>CLINIC",
        "damage": ["fold"],
        "sections": [
            {"panel": "IRON", "title": 4, "methods": True,
             "values": {"FERRITIN": 32, "IRON": 72, "TIBC": 368}},
            {"panel": "VITAMIN", "title": 4, "methods": True,
             "values": {"VIT_D": 24.6, "VIT_B12": 336, "FOLATE": 9.8}},
            {"panel": "INFLAMMATION", "title": 2, "drop": ["RA_FACTOR", "ASO"],
             "values": {"CRP": 2.4, "HS_CRP": 0.90}},
            {"heading": "Pre-pregnancy Screen",
             "rows": [{"code": "HBSAG", "value": "Non Reactive", "trap": "text_result"},
                      {"code": "BLOOD_GROUP", "value": "O Positive",
                       "trap": "text_result"}]},
            {"heading": "Written in at the clinic", "hand_addendum": True,
             "rows": [{"code": "TSH", "value": 2.28}, {"code": "FT4", "value": 1.26}]},
        ],
    },
]
