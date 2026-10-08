"""Patient 22 - HELD OUT. Paediatric haematology: iron deficiency anaemia, treated.

Female, 11 at the first report, Guwahati. Presents pale and tired with haemoglobin
7.8 and a ferritin of 6 - textbook iron deficiency in a girl who has just started
menstruating. Oral iron for six months, then a short intravenous course when she
cannot tolerate the tablets, and she is back to 12.2 by the last report.

A child, deliberately: reference intervals differ by age, so any result judged
against an adult range here is judged wrong. eGFR is not printed for her at all -
the CKD-EPI equation is not valid under eighteen and the corpus omits it.

This patient is NOT part of the training corpus. See p21 for the rule on spellings:
nothing printed here may be added to catalog.py afterwards.
"""

from __future__ import annotations

HOLDOUT = True

PATIENT = {
    "number": 22,
    "name": "Ankita Bhuyan",
    "sex": "F",
    "dob": "2013-05-22",
    "uhid": "BRM/730914",
    "department": "Paediatrics",
    "city": "Guwahati",
    "age_at_first": 11,
    "tracked": ["HGB"],
    "brief": "Paediatric iron deficiency anaemia, corrected on treatment",
}


def check_arc(series):
    hb = [v for _, v in series["HGB"]]
    fails = []
    if not hb[0] < 8.5:
        fails.append(f"should present severely anaemic, Hb {hb[0]}")
    if not hb == sorted(hb):
        fails.append(f"haemoglobin should climb steadily on treatment: {hb}")
    if not hb[-1] >= 11.5:
        fails.append(f"should end within the paediatric range, Hb {hb[-1]}")
    return fails


BORAH = "Dr. Rituparna Borah"

LABS = {
    "brahma": {
        "abbr": "BRM", "acc_style": 1,
        "name": "Brahmaputra Child Health Laboratory",
        "name_local": "ব্ৰহ্মপুত্ৰ শিশু স্বাস্থ্য পৰীক্ষাগাৰ",
        "addr": "Bhangagarh, Guwahati 781032",
        "addr_local": "ভাঙাগড়, গুৱাহাটী 781032",
        "city": "Guwahati",
        "phone": "0361 246 8890",
        "accred": "NABL MC-7712 | Paediatric reference intervals applied",
        "path": {"name": "Dr. Manashi Kakati", "qual": "MD (Pathology)",
                 "regn": "ACMR 2010/02/7741", "scrawl": "M Kakati"},
    },
    "kamrup": {
        "abbr": "KMR", "acc_style": 0,
        "name": "Kamrup Diagnostics and Imaging",
        "name_local": "কামৰূপ ডায়গনষ্টিকছ",
        "addr": "GS Road, Guwahati 781005",
        "addr_local": "জি এছ ৰোড, গুৱাহাটী 781005",
        "city": "Guwahati",
        "phone": "0361 273 1155",
        "accred": "ISO 15189:2022",
        "path": {"name": "Dr. Pranab Sarma", "qual": "MD, DCP",
                 "regn": "ACMR 2006/09/3318", "scrawl": "P Sarma"},
    },
    "wellcare": {
        "abbr": "WCP", "acc_style": 2,
        "name": "WellCare Corporate Health Services",
        "name_local": "ৱেলকেয়াৰ কৰ্পোৰেট হেল্থ",
        "addr": "Six Mile, Guwahati 781022",
        "addr_local": "ছিক্স মাইল, গুৱাহাটী 781022",
        "city": "Guwahati",
        "phone": "0361 235 4400",
        "accred": "Preventive health programmes. Not an accredited testing laboratory.",
        "path": {"name": "Dr. Anindita Das", "qual": "MBBS, MPH",
                 "regn": "ACMR 2014/07/9925", "scrawl": "A Das"},
    },
}

# A child still growing: height climbs through the record, so BMI moves even
# where weight barely does.
HEIGHT_CM = 141.0

VITALS = {
    1: {"weight_kg": 31.4, "bp": "98/62", "spo2": 99, "temp_f": 98.4,
        "context": "Pale, tired, short of breath climbing stairs. Menarche four months ago."},
    2: {"weight_kg": 32.1, "bp": "100/64", "spo2": 99, "temp_f": 98.2,
        "context": "Six weeks of oral iron. Nausea and constipation reported."},
    3: {"weight_kg": 33.6, "bp": "102/64", "spo2": 100, "temp_f": 98.6,
        "context": "Tablets stopped for intolerance. Single IV iron infusion given."},
    4: {"weight_kg": 35.2, "bp": "104/66", "spo2": 99, "temp_f": 98.4,
        "context": "Much brighter. Back at games, no longer breathless."},
    5: {"weight_kg": 37.0, "bp": "106/68", "spo2": 100, "temp_f": 98.2,
        "context": "Annual review. Stores replete, dietary advice reinforced."},
}

REPORTS = [
    # ---- R01 -- presentation, results as cards not a table -------------------
    {
        "collected": "2024-06-15 09:30", "reported": "2024-06-15 17:20",
        "lab": "brahma", "layout_style": "card_grid",
        "header_style": "logo_left_banner", "uhid_label": "Patient ID",
        "doctor": BORAH, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["abnormal_shaded", "interpretation_block"],
        "interpretation": "Microcytic hypochromic anaemia with an exhausted ferritin. "
                          "Iron deficiency. Start oral iron with vitamin C and repeat "
                          "the count in six weeks.",
        "sections": [
            {"panel": "CBC", "title": 0, "drop": ["MPV", "ANC", "ALC"],
             "labels": {"HGB": "Hb (Haemoglobin)", "PCV": "HCT / PCV",
                        "RDW": "RDW-CV"},
             "values": {"HGB": 7.8, "RBC": 3.96, "PCV": 26.4, "MCV": 66.7, "MCH": 19.7,
                        "MCHC": 29.5, "RDW": 18.6, "WBC": 6800, "NEUT_PCT": 48,
                        "LYMPH_PCT": 42, "MONO_PCT": 7, "EOS_PCT": 2, "BASO_PCT": 1,
                        "PLT": 412000}},
            {"panel": "IRON", "title": 1,
             "labels": {"FERRITIN": "S. FERRITIN (CLIA)", "IRON": "IRON, SERUM",
                        "TIBC": "T.I.B.C."},
             "values": {"FERRITIN": 6.0, "IRON": 22, "TIBC": 498}},
        ],
    },
    # ---- R02 -- six weeks on iron, printed three to a column -----------------
    {
        "collected": "2024-09-07 08:50", "reported": "2024-09-07 15:35",
        "lab": "kamrup", "layout_style": "newsprint_cols",
        "header_style": "centred_classic", "uhid_label": "Reg. No",
        "doctor": BORAH, "specimen": "Whole blood (EDTA)",
        "alias": 1, "traps": ["no_reference_column", "sno_column"],
        "damage": ["aged"],
        "sections": [
            {"panel": "CBC", "title": 1, "drop": ["MPV"],
             "labels": {"HGB": "HAEMOGLOBIN, BLOOD", "WBC": "TOTAL LEUCOCYTE COUNT"},
             "values": {"HGB": 8.9, "RBC": 4.18, "PCV": 29.6, "MCV": 70.8, "MCH": 21.3,
                        "MCHC": 30.1, "RDW": 19.4, "WBC": 7100, "NEUT_PCT": 50,
                        "LYMPH_PCT": 40, "MONO_PCT": 7, "EOS_PCT": 2, "BASO_PCT": 1,
                        "PLT": 388000}},
            {"heading": "Smear and typing",
             "row_traps": {"UR_COLOUR": "text_result"},
             "rows": [{"code": "PERIPH_SMEAR",
                       "value": "Microcytic hypochromic RBCs with anisopoikilocytosis. "
                                "Pencil cells seen. No haemoparasite."},
                      {"code": "BLOOD_GROUP", "value": "B Positive"},
                      {"label": "Reticulocyte Haemoglobin (CHr)", "value": "23.4",
                       "unit": "pg", "reference": "> 28", "flag": "L"}]},
        ],
    },
    # ---- R03 -- the wellness provider's pastel report ------------------------
    {
        "collected": "2025-01-20 10:15", "reported": "2025-01-20 19:05",
        "lab": "wellcare", "layout_style": "pastel_wellness",
        "header_style": "two_line_ribbon", "uhid_label": "Member ID",
        "doctor": BORAH, "specimen": "Whole blood (EDTA), Serum",
        "alias": 2, "traps": ["flag_as_words", "unit_in_label"],
        "note": "Issued as part of the school health programme. Not a diagnostic report.",
        "sections": [
            {"panel": "CBC", "title": 2, "drop": ["MPV", "BASO_PCT", "ANC", "ALC"],
             "labels": {"HGB": "Haemoglobin level"},
             "values": {"HGB": 10.4, "RBC": 4.44, "PCV": 33.2, "MCV": 74.8, "MCH": 23.4,
                        "MCHC": 31.3, "RDW": 16.2, "WBC": 6600, "NEUT_PCT": 52,
                        "LYMPH_PCT": 38, "MONO_PCT": 7, "EOS_PCT": 3,
                        "PLT": 344000}},
            {"panel": "VITAMIN", "title": 0,
             "labels": {"VIT_B12": "Vitamin B-12 (Cyanocobalamin)",
                        "VIT_D": "25-OH Vitamin D (Total)"},
             "values": {"VIT_D": 18.6, "VIT_B12": 286, "FOLATE": 7.4}},
        ],
    },
    # ---- R04 -- the spreadsheet export --------------------------------------
    {
        "collected": "2025-06-11 08:40", "reported": "2025-06-11 16:15",
        "lab": "brahma", "layout_style": "grid_lines",
        "header_style": "hospital_department_block", "uhid_label": "UHID",
        "doctor": BORAH, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["test_code_column", "method_sub_line",
                              "abnormal_shaded"],
        "sections": [
            {"panel": "CBC", "title": 1, "drop": ["MPV", "BASO_PCT"], "methods": True,
             "lab_codes": {"HGB": "HAE-001", "WBC": "HAE-004", "PLT": "HAE-011",
                           "MCV": "HAE-006", "RDW": "HAE-009"},
             "values": {"HGB": 11.6, "RBC": 4.62, "PCV": 35.8, "MCV": 77.5, "MCH": 25.1,
                        "MCHC": 32.4, "RDW": 14.1, "WBC": 6900, "NEUT_PCT": 54,
                        "LYMPH_PCT": 37, "MONO_PCT": 6, "EOS_PCT": 3,
                        "PLT": 312000}},
            {"panel": "IRON", "title": 0,
             "lab_codes": {"FERRITIN": "BIO-221", "IRON": "BIO-118"},
             "values": {"FERRITIN": 48.0, "IRON": 74, "TIBC": 362}},
        ],
    },
    # ---- R05 -- annual review, barcode down the spine ------------------------
    {
        "collected": "2026-02-14 09:05", "reported": "2026-02-14 17:45",
        "lab": "kamrup", "layout_style": "spine_barcode",
        "header_style": "barcode_right", "uhid_label": "Hospital No",
        "doctor": BORAH, "specimen": "Whole blood (EDTA), Serum",
        "alias": 1, "traps": ["range_split_columns", "footnote_marker"],
        "damage": ["crop-bottom"],
        "footnotes": [("1", "Haemoglobin within the 12 to 15 year female interval. "
                            "Iron stores replete. No further supplementation needed."),
                      ("2", "Variant analysis performed on request. No abnormal "
                            "haemoglobin fraction detected.")],
        "sections": [
            {"panel": "CBC", "title": 0, "drop": ["MPV", "ANC", "ALC", "BASO_PCT"],
             "labels": {"HGB": "Hb (Haemoglobin)"},
             "values": {"HGB": 12.2, "RBC": 4.71, "PCV": 37.4, "MCV": 79.4, "MCH": 25.9,
                        "MCHC": 32.6, "RDW": 13.4, "WBC": 7200, "NEUT_PCT": 56,
                        "LYMPH_PCT": 36, "MONO_PCT": 5, "EOS_PCT": 3,
                        "PLT": 286000}},
            {"heading": "Stores and variant screen",
             "rows": [{"code": "FERRITIN", "value": 62.0, "marker": "1"},
                      {"label": "Haemoglobin Variant Analysis (HPLC)",
                       "value": "Normal HbA pattern. HbA2 2.6 percent.",
                       "unit": "", "reference": "HbA2 < 3.5 percent",
                       "trap": "text_result", "marker": "2"},
                      {"label": "Serum Zinc", "value": "84", "unit": "mcg/dL",
                       "reference": "70 - 120"}]},
        ],
    },
]
