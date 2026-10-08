"""Patient 16 of 20 - Hepatology. Hepatitis B carrier under surveillance, stable.

Male, 39 at the first report, Kolkata. Found HBsAg positive at a blood donation camp and
entered six-monthly surveillance: ALT, viral load, alpha-fetoprotein and an ultrasound. He
is an inactive carrier throughout - ALT mostly 30-45, viral load low, no fibrosis - which
is the finding, and the record has to show five years of almost nothing convincingly.

The setback is April 2025, a genuine hepatitis flare with ALT 268 and a viral load two
logs higher, treated with tenofovir and settled by the following visit.

Eight of the fifteen reports are physically damaged: an old file copy that has been folded
and refolded, two phone photographs, a page with the left margin cropped away, and a
report that spent time in a drawer with something wet.
"""

from __future__ import annotations

PATIENT = {
    "number": 16,
    "name": "Subhankar Ghoshal",
    "sex": "M",
    "dob": "1982-06-23",
    "uhid": "SNH/912476",
    "department": "Hepatology",
    "city": "Kolkata",
    "age_at_first": 39,
    "tracked": ["ALT"],
    "brief": "Hepatitis B carrier under surveillance, stable",
}


def check_arc(series):
    alt = [v for _, v in series["ALT"]]
    fails = []
    quiet = [v for v in alt if v < 60]
    if len(quiet) < len(alt) - 2:
        fails.append("an inactive carrier should be quiet on most visits")
    if not max(alt) > 200:
        fails.append(f"the 2025 flare never shows, peak ALT {max(alt)}")
    if not alt[-1] < 60:
        fails.append(f"should settle after treatment, ends {alt[-1]}")
    return fails


LABS = {
    "hooghly": {
        "abbr": "HDC", "acc_style": 0,
        "name": "Hooghly Diagnostic Centre",
        "name_local": "হুগলি ডায়াগনস্টিক সেন্টার",
        "addr": "Rashbehari Avenue, Kolkata 700029",
        "addr_local": "রাসবিহারী অ্যাভিনিউ, কলকাতা 700029",
        "city": "Kolkata",
        "phone": "033 2464 7710",
        "accred": "NABL Accredited (MC-1904) | ISO 15189:2012",
        "path": {"name": "Dr. Sutapa Chatterjee", "qual": "MD (Pathology)",
                 "regn": "WBMC 2005/02/2218", "scrawl": "S Chatterjee"},
    },
    "saltlake": {
        "abbr": "SLP", "acc_style": 2,
        "name": "Salt Lake Path Point",
        "name_local": "সল্টলেক পাথ পয়েন্ট",
        "addr": "Sector 2, Salt Lake City, Kolkata 700091",
        "addr_local": "সেক্টর 2, সল্টলেক সিটি, কলকাতা 700091",
        "city": "Kolkata",
        "phone": "033 2359 8842",
        "accred": "NABL Accredited (M-6674)",
        "path": {"name": "Dr. Arindam Bose", "qual": "MBBS, MD (Path.)",
                 "regn": "WBMC 2011/07/7736", "scrawl": "A Bose"},
    },
    "sonarbangla": {
        "abbr": "SNH", "acc_style": 1,
        "name": "Sonar Bangla Hospital Laboratory",
        "name_local": "সোনার বাংলা হাসপাতাল পরীক্ষাগার",
        "addr": "EM Bypass, Kolkata 700105",
        "addr_local": "ইএম বাইপাস, কলকাতা 700105",
        "city": "Kolkata",
        "phone": "033 6620 4000",
        "accred": "Department of Laboratory Medicine, Liver Unit",
        "path": {"name": "Dr. Debjani Roy", "qual": "MD, DNB (Pathology)",
                 "regn": "WBMC 1999/09/0873", "scrawl": "D Roy"},
    },
}

BANERJEE = "Dr. Anirban Banerjee, MBBS, MD, DM (Hepatology)"
MUKHERJEE = "Dr. Sohini Mukherjee, MBBS, MD (Medicine)"
DUTTA = "Dr. Kaushik Dutta, MBBS, MS (General Surgery)"

HBV_LEGEND = [
    ("ALT in chronic hepatitis B surveillance", "ALT (SGPT)"),
    ("Below 40 U/L", "Within reference interval"),
    ("40 - 80 U/L", "Mildly raised, repeat in three months"),
    ("Above 80 U/L", "Flare, check viral load and treat"),
]

# A well man whose weight barely moves, apart from four kilos lost during the
# 2025 flare. The flare visit is the only one with a temperature.
HEIGHT_CM = 169.0

VITALS = {
    1: {"weight_kg": 70.4, "bp": "124/78", "spo2": 98, "temp_f": 98.2,
        "context": "Turned away at a blood donation camp; HBsAg positive on screening."},
    2: {"weight_kg": 70.8, "bp": "122/78", "spo2": 98, "temp_f": 98.4,
        "context": "First hepatology visit. Viral load low, no treatment needed."},
    3: {"weight_kg": 71.2, "bp": "124/80", "spo2": 99, "temp_f": 98.2,
        "context": "Six-monthly surveillance. Well, working normally."},
    4: {"weight_kg": 71.6, "bp": "126/80", "spo2": 98, "temp_f": 98.6,
        "context": "Annual review with ultrasound. Liver texture normal."},
    5: {"weight_kg": 72.0, "bp": "124/78", "spo2": 98, "temp_f": 98.4,
        "context": "Surveillance visit. Family screened and vaccinated."},
    6: {"weight_kg": 72.4, "bp": "126/82", "spo2": 98, "temp_f": 98.2,
        "context": "Well. Fibroscan booked for next year."},
    7: {"weight_kg": 72.8, "bp": "124/80", "spo2": 99, "temp_f": 98.4,
        "context": "Annual review. Fibroscan shows no significant fibrosis."},
    8: {"weight_kg": 73.2, "bp": "126/80", "spo2": 98, "temp_f": 98.6,
        "context": "Pre-operative bloods for a hernia repair."},
    9: {"weight_kg": 72.6, "bp": "122/78", "spo2": 98, "temp_f": 99.4,
        "context": "Second day after surgery. Wound clean, mild temperature."},
    10: {"weight_kg": 68.8, "bp": "118/74", "spo2": 97, "temp_f": 100.6,
         "context": "Jaundiced, nauseated, dark urine for a week. Hepatitis flare."},
    11: {"weight_kg": 69.6, "bp": "120/76", "spo2": 98, "temp_f": 98.8,
         "context": "Four weeks on tenofovir. Jaundice fading."},
    12: {"weight_kg": 71.0, "bp": "122/78", "spo2": 98, "temp_f": 98.4,
         "context": "Enzymes almost normal. Treatment continues."},
    13: {"weight_kg": 71.8, "bp": "124/78", "spo2": 98, "temp_f": 98.2,
         "context": "Single repeat ALT before the annual review."},
    14: {"weight_kg": 72.4, "bp": "124/80", "spo2": 98, "temp_f": 98.6,
         "context": "Annual review. Suppressed on treatment, no fibrosis."},
    15: {"weight_kg": 72.8, "bp": "122/78", "spo2": 99, "temp_f": 98.2,
         "context": "Stable. Six-monthly surveillance continues indefinitely."},
}

REPORTS = [
    # ---- R01 -- the donation camp screen ------------------------------------
    {
        "collected": "2021-11-06 10:20", "reported": "2021-11-08 12:40",
        "lab": "hooghly", "layout_style": "clean_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": MUKHERJEE, "specimen": "Serum",
        "alias": 0, "traps": ["text_result"],
        "damage": ["aged", "fold"],
        "sections": [
            {"panel": "SEROLOGY", "title": 0, "drop": ["WIDAL", "DENGUE_NS1",
                                                       "DENGUE_IGM", "MP"],
             "values": {"HBSAG": "Reactive", "ANTI_HCV": "Non Reactive",
                        "HIV": "Non Reactive", "VDRL": "Non Reactive"},
             "row_traps": {"HBSAG": "text_result"}},
            {"heading": "Liver Enzymes",
             "rows": [{"code": "ALT", "value": 42}, {"code": "AST", "value": 34},
                      {"code": "BILI_T", "value": 0.9}]},
        ],
    },
    # ---- R02 -- first hepatology visit ---------------------------------------
    {
        "collected": "2022-02-19 08:50", "reported": "2022-02-19 18:30",
        "lab": "sonarbangla", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Hospital No",
        "doctor": BANERJEE, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 1, "traps": ["legend_lines"],
        "interpretation": "Inactive carrier state: HBeAg negative, viral load low and "
                          "transaminases within the reference interval. Six-monthly "
                          "surveillance with ALT and alpha-fetoprotein is appropriate.",
        "sections": [
            {"panel": "LFT", "title": 0, "legend": HBV_LEGEND,
             "values": {"BILI_T": 0.8, "BILI_D": 0.2, "ALT": 38, "AST": 30, "ALP": 84,
                        "GGT": 32, "PROT_T": 7.4, "ALB": 4.4}},
            {"heading": "Viral Markers",
             "rows": [{"label": "HBV DNA (Quantitative)", "value": "1240", "unit": "IU/mL",
                       "reference": "< 2000"},
                      {"label": "HBeAg", "value": "Non Reactive", "unit": "",
                       "reference": "Non Reactive", "trap": "text_result"},
                      {"label": "Alpha Fetoprotein (AFP)", "value": "3.8", "unit": "ng/mL",
                       "reference": "< 10.0"}]},
        ],
    },
    # ---- R03 -- six-monthly, photographed -----------------------------------
    {
        "collected": "2022-08-27 09:15", "reported": "2022-08-27 16:10",
        "lab": "saltlake", "layout_style": "kv_header_table",
        "header_style": "bilingual_header", "uhid_label": "Reg. No",
        "doctor": BANERJEE, "specimen": "Serum",
        "alias": 2, "traps": ["unit_in_label"],
        "damage": ["dark", "fold"],
        "note": "Photographed and emailed by the patient.",
        "sections": [
            {"panel": "KFT", "title": 0,
             "values": {"CREAT": 0.92, "UREA": 28, "UA": 6.0}},
            {"panel": "DIABETES", "title": 0, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 96, "GLU_PP": 130, "HBA1C": 5.3}},
            {"panel": "THYROID", "title": 0, "drop": ["FT3", "ANTI_TPO"],
             "values": {"TSH": 2.42, "T3_TOTAL": 124, "T4_TOTAL": 9.0, "FT4": 1.26}},
            {"heading": "Liver Enzymes",
             "rows": [{"code": "ALT", "value": 34}, {"code": "AST", "value": 28},
                      {"code": "GGT", "value": 30}]},
        ],
    },
    # ---- R04 -- annual review with ultrasound --------------------------------
    {
        "collected": "2023-03-11 07:50", "reported": "2023-03-11 19:00",
        "lab": "sonarbangla", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Hospital No",
        "doctor": BANERJEE, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 3, "traps": ["merged_panel_heading", "text_result", "method_sub_line"],
        "note": "Annual surveillance package.",
        "sections": [
            {"panel": "CBC", "title": 1, "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "values": {"HGB": 14.8, "RBC": 4.96, "PCV": 44.0, "MCV": 88.7, "MCH": 29.8,
                        "WBC": 6800, "NEUT_PCT": 58, "LYMPH_PCT": 32, "MONO_PCT": 6,
                        "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 232000}},
            {"panel": "LIPID", "title": 1, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 186, "TRIG": 142, "HDL": 44}},
            {"panels": ["LFT", "ELECTROLYTES"], "heading": "Biochemistry Screen",
             "trap": "merged_panel_heading",
             "drop": ["AG_RATIO", "GLOB", "BILI_I", "CA_ION", "MG"],
             "values": {"BILI_T": 0.8, "BILI_D": 0.2, "ALT": 41, "AST": 33, "ALP": 88,
                        "GGT": 36, "PROT_T": 7.3, "ALB": 4.3,
                        "NA": 140, "K": 4.2, "CL": 103, "CA": 9.4, "PHOS": 3.6}},
            {"panel": "VITAMIN", "title": 1, "methods": True,
             "values": {"VIT_D": 19.8, "VIT_B12": 346, "FOLATE": 8.6}},
            {"panel": "IRON", "title": 4, "drop": ["UIBC"],
             "values": {"FERRITIN": 164, "IRON": 88, "TIBC": 340}},
            {"heading": "Surveillance",
             "rows": [{"label": "Alpha Fetoprotein (AFP)", "value": "4.2", "unit": "ng/mL",
                       "reference": "< 10.0"},
                      {"code": "BLOOD_GROUP", "value": "O Positive",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R05 -- surveillance, left margin cropped away -----------------------
    {
        "collected": "2023-09-16 09:00", "reported": "2023-09-16 16:20",
        "lab": "hooghly", "layout_style": "ledger_ruled",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": MUKHERJEE, "specimen": "Serum, Urine (midstream)",
        "alias": 0, "traps": ["range_split_columns"],
        "damage": ["crop-left", "aged"],
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 0, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Yellow", "UR_PH": 6.0, "UR_SPGR": 1.020,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 2, "UR_RBC": 0, "UR_EPITH": 3}},
            {"heading": "Liver Enzymes",
             "rows": [{"code": "ALT", "value": 36}, {"code": "AST", "value": 31}]},
        ],
    },
    # ---- R06 -- well ----------------------------------------------------------
    {
        "collected": "2024-02-24 09:30", "reported": "2024-02-24 15:40",
        "lab": "saltlake", "layout_style": "thermal_slip",
        "header_style": "centred_title_only", "uhid_label": "Reg. No",
        "doctor": BANERJEE, "specimen": "Serum",
        "alias": 1, "traps": ["no_reference_column"],
        "sections": [
            {"heading": "SGPT (ALT)",
             "rows": [{"code": "ALT", "value": 44, "flag": "H"}]},
        ],
    },
    # ---- R07 -- annual review, fibroscan year --------------------------------
    {
        "collected": "2024-07-13 08:20", "reported": "2024-07-13 17:30",
        "lab": "sonarbangla", "layout_style": "landscape_wide",
        "header_style": "barcode_header", "uhid_label": "Hospital No",
        "doctor": BANERJEE, "specimen": "Serum",
        "alias": 2, "traps": ["prev_value_column", "method_sub_line"],
        "damage": ["fold"],
        "sections": [
            {"heading": "Liver Function - Comparative", "methods": True,
             "prev": {"ALT": "44 (24/02/2024)", "AST": "33 (11/03/2023)",
                      "GGT": "36 (11/03/2023)"},
             "rows": [{"code": "BILI_T", "value": 0.9}, {"code": "ALT", "value": 39},
                      {"code": "AST", "value": 32}, {"code": "ALP", "value": 86},
                      {"code": "GGT", "value": 34}, {"code": "ALB", "value": 4.4}]},
            {"heading": "Surveillance",
             "prev": {},
             "rows": [{"label": "HBV DNA (Quantitative)", "value": "980", "unit": "IU/mL",
                       "reference": "< 2000"},
                      {"label": "Fibroscan (kPa)", "value": "5.4", "unit": "kPa",
                       "reference": "< 7.0"}]},
        ],
    },
    # ---- R08 -- pre-operative screen ------------------------------------------
    {
        "collected": "2024-11-29 07:40", "reported": "2024-11-29 14:20",
        "lab": "sonarbangla", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": DUTTA, "specimen": "Citrate plasma, Serum, Whole blood (EDTA)",
        "alias": 3, "traps": ["text_result", "sno_column"],
        "note": "Pre-operative screen for elective hernia repair. Theatre informed of "
                "hepatitis B carrier status.",
        "sections": [
            {"panel": "COAGULATION", "title": 2,
             "values": {"PT": 12.8, "INR": 1.02, "APTT": 29.6, "D_DIMER": 180}},
            {"panel": "CBC", "title": 3, "drop": ["ANC", "ALC", "MPV", "MCHC"],
             "values": {"HGB": 14.6, "RBC": 4.90, "PCV": 43.4, "MCV": 88.6, "MCH": 29.8,
                        "RDW": 13.0, "WBC": 7000, "NEUT_PCT": 59, "LYMPH_PCT": 31,
                        "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 228000}},
            {"heading": "Liver and Group",
             "rows": [{"code": "ALT", "value": 43}, {"code": "BILI_T", "value": 0.8},
                      {"code": "BLOOD_GROUP", "value": "O Positive",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R09 -- second post-operative day ------------------------------------
    {
        "collected": "2024-12-03 06:30", "reported": "2024-12-03 10:10",
        "lab": "sonarbangla", "layout_style": "fax_header",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": DUTTA, "specimen": "Whole blood (EDTA), Serum, Urine",
        "alias": 0, "traps": ["no_reference_column", "text_result"],
        "sections": [
            {"heading": "Post-operative Screen",
             "rows": [{"code": "HGB", "value": 13.8}, {"code": "WBC", "value": 11600,
                       "flag": "H"},
                      {"code": "CRP", "value": 48.2, "flag": "H"},
                      {"code": "URINE_CULTURE",
                       "value": "No growth after 48 hours of aerobic incubation.",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R10 -- the flare, on a page that got wet ---------------------------
    {
        "collected": "2025-04-22 10:15", "reported": "2025-04-22 19:50",
        "lab": "sonarbangla", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": BANERJEE, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 1, "traps": ["legend_lines", "abnormal_shaded"],
        "damage": ["stain", "torn", "aged"],
        "note": "Hepatitis B flare with a two log rise in viral load. Tenofovir started "
                "today; repeat liver function in four weeks.",
        "sections": [
            {"panel": "LFT", "title": 4, "legend": HBV_LEGEND,
             "values": {"BILI_T": 4.8, "BILI_D": 3.2, "ALT": 268, "AST": 196, "ALP": 148,
                        "GGT": 124, "PROT_T": 7.0, "ALB": 3.6}},
            {"heading": "Viral Markers",
             "rows": [{"label": "HBV DNA (Quantitative)", "value": "248000",
                       "unit": "IU/mL", "reference": "< 2000", "flag": "H"},
                      {"label": "HBeAg", "value": "Reactive", "unit": "",
                       "reference": "Non Reactive", "flag": "H", "trap": "text_result"},
                      {"code": "INR", "value": 1.12}]},
        ],
    },
    # ---- R11 -- four weeks on treatment, badly photographed -----------------
    {
        "collected": "2025-05-27 09:05", "reported": "2025-05-27 16:30",
        "lab": "saltlake", "layout_style": "kv_header_table",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": BANERJEE, "specimen": "Serum",
        "alias": 2, "traps": ["method_sub_line"],
        "damage": ["blur", "dark", "thumb"], "illegible": True,
        "note": "Image supplied by the patient; a legible copy was requested.",
        "sections": [
            {"heading": "Liver Function - Four Weeks On Treatment", "methods": True,
             "rows": [{"code": "BILI_T", "value": 2.1, "flag": "H"},
                      {"code": "BILI_D", "value": 1.2, "flag": "H"},
                      {"code": "ALT", "value": 96, "flag": "H"},
                      {"code": "AST", "value": 78, "flag": "H"},
                      {"code": "ALP", "value": 112, "flag": "H"},
                      {"code": "GGT", "value": 86, "flag": "H"},
                      {"code": "ALB", "value": 3.9}]},
        ],
    },
    # ---- R12 -- almost normal -------------------------------------------------
    {
        "collected": "2025-10-14 08:45", "reported": "2025-10-14 17:00",
        "lab": "hooghly", "layout_style": "glossy_marketing",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": BANERJEE, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 3, "traps": ["test_code_column"],
        "damage": ["crop-right"],
        "interpretation": "Transaminases have fallen close to normal on tenofovir and the "
                          "viral load is undetectable. Continue treatment and review in "
                          "six months.",
        "sections": [
            {"panel": "IRON", "title": 0, "drop": ["UIBC"],
             "lab_codes": {"FERRITIN": "B-40", "IRON": "B-41", "TIBC": "B-42"},
             "values": {"FERRITIN": 186, "IRON": 94, "TIBC": 332}},
            {"heading": "Liver and Virology",
             "lab_codes": {"ALT": "L-11", "AST": "L-12", "BILI_T": "L-01"},
             "rows": [{"code": "ALT", "value": 48, "flag": "H"},
                      {"code": "AST", "value": 40},
                      {"code": "BILI_T", "value": 1.0},
                      {"label": "HBV DNA (Quantitative)", "value": "< 20 (Not Detected)",
                       "unit": "IU/mL", "reference": "< 2000", "trap": "text_result"}]},
        ],
    },
    # ---- R13 -- one repeat ALT ------------------------------------------------
    {
        "collected": "2026-02-10 09:40", "reported": "2026-02-10 13:10",
        "lab": "saltlake", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": MUKHERJEE, "specimen": "Serum",
        "alias": 0, "traps": ["no_header_row"],
        "damage": ["aged", "scanborder"],
        "sections": [
            {"heading": "SGPT (ALT) - Repeat",
             "rows": [{"code": "ALT", "value": 41}]},
        ],
    },
    # ---- R14 -- annual review, two pages -------------------------------------
    {
        "collected": "2026-06-16 07:45", "reported": "2026-06-16 20:05",
        "lab": "sonarbangla", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "Hospital No",
        "doctor": BANERJEE, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["footnote_marker", "ratio_no_code"],
        "page_break_after": 3,
        "footnotes": [("1", "Tenofovir continues. Renal function and phosphate monitored "
                            "six-monthly on treatment.")],
        "sections": [
            {"panel": "CBC", "title": 5,
             "values": {"HGB": 14.9, "RBC": 4.94, "PCV": 44.2, "MCV": 89.5, "MCH": 30.2,
                        "MCHC": 33.7, "RDW": 12.9, "WBC": 6600, "NEUT_PCT": 57,
                        "LYMPH_PCT": 33, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 236000, "MPV": 9.5}},
            {"panel": "LIPID", "title": 5,
             "values": {"CHOL": 182, "TRIG": 136, "HDL": 46}},
            {"panel": "DIABETES", "title": 5, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 94, "GLU_PP": 126, "HBA1C": 5.4}},
            {"panel": "KFT", "title": 5,
             "values": {"CREAT": 0.96, "UREA": 29, "UA": 6.2},
             "row_traps": {"CREAT": "footnote_marker"}},
            {"panel": "ELECTROLYTES", "title": 5, "drop": ["CA_ION", "MG"],
             "values": {"NA": 140, "K": 4.1, "CL": 104, "CA": 9.3, "PHOS": 2.8}},
            {"heading": "Surveillance and Derived",
             "rows": [{"code": "ALT", "value": 38},
                      {"label": "Alpha Fetoprotein (AFP)", "value": "3.4",
                       "unit": "ng/mL", "reference": "< 10.0"},
                      {"label": "AST / ALT Ratio", "value": "0.84", "unit": "",
                       "reference": "< 1.0", "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R15 -- stable surveillance ------------------------------------------
    {
        "collected": "2026-09-10 08:50", "reported": "2026-09-10 16:15",
        "lab": "hooghly", "layout_style": "mixed_print_hand",
        "header_style": "stamp_and_signature", "uhid_label": "Patient ID",
        "doctor": BANERJEE, "specimen": "Serum", "stamp": "LIVER CLINIC<br>REVIEWED",
        "alias": 2, "traps": ["method_sub_line"],
        "damage": ["fold", "stain"],
        "sections": [
            {"panel": "VITAMIN", "title": 3, "methods": True,
             "values": {"VIT_D": 28.6, "VIT_B12": 372, "FOLATE": 9.2}},
            {"panel": "URINE_ROUTINE", "title": 3, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.5, "UR_SPGR": 1.018,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 2, "UR_RBC": 0, "UR_EPITH": 2}},
            {"panel": "THYROID", "title": 3, "drop": ["T3_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel",
             "values": {"TSH": 2.18, "T4_TOTAL": 9.2, "FT4": 1.24}},
            {"heading": "Noted at the clinic", "hand_addendum": True,
             "rows": [{"code": "ALT", "value": 36}, {"code": "AST", "value": 30}]},
        ],
    },
]
