"""Patient 23 - HELD OUT. Hepatology: alcohol-related hepatitis, recovering on abstinence.

Male, 41 at the first report, Kochi. Admitted jaundiced with an ALT of 186, an AST
above it in the ratio that points at alcohol rather than a virus, and a bilirubin of
4.8. He stops drinking. Over eighteen months the transaminases come down to 38, the
bilirubin normalises, and the albumin recovers last, as albumin does.

The falling curve matters here: most of the training corpus climbs or oscillates, and
a trend chart that only ever renders deterioration is not proven to render recovery.

This patient is NOT part of the training corpus. See p21 for the rule on spellings:
nothing printed here may be added to catalog.py afterwards.
"""

from __future__ import annotations

HOLDOUT = True

PATIENT = {
    "number": 23,
    "name": "Thomas Varghese",
    "sex": "M",
    "dob": "1983-06-20",
    "uhid": "MRN/558240",
    "department": "Gastroenterology",
    "city": "Kochi",
    "age_at_first": 41,
    "tracked": ["ALT"],
    "brief": "Alcohol-related hepatitis, recovering with abstinence",
}


def check_arc(series):
    alt = [v for _, v in series["ALT"]]
    fails = []
    if not alt[0] > 150:
        fails.append(f"should present with a hepatitic ALT, got {alt[0]}")
    if not alt == sorted(alt, reverse=True):
        fails.append(f"ALT should fall steadily on abstinence: {alt}")
    if not alt[-1] < 50:
        fails.append(f"should end near normal, final ALT {alt[-1]}")
    return fails


JOSEPH = "Dr. Cyriac Joseph"

LABS = {
    "marine": {
        "abbr": "MRN", "acc_style": 1,
        "name": "Marine Drive Liver Institute Laboratory",
        "name_local": "മറൈൻ ഡ്രൈവ് ലിവർ ഇൻസ്റ്റിറ്റ്യൂട്ട് ലാബ്",
        "addr": "Marine Drive, Ernakulam, Kochi 682031",
        "addr_local": "മറൈൻ ഡ്രൈവ്, എറണാകുളം, കൊച്ചി 682031",
        "city": "Kochi",
        "phone": "0484 237 6600",
        "accred": "NABL MC-3308 | Hepatology and Transplant Laboratory",
        "path": {"name": "Dr. Sunitha Menon", "qual": "MD, DNB (Pathology)",
                 "regn": "TCMC 2004/12/8817", "scrawl": "S Menon"},
    },
    "backwater": {
        "abbr": "BWD", "acc_style": 0,
        "name": "Backwater Diagnostics",
        "name_local": "ബാക്ക്‌വാട്ടർ ഡയഗ്നോസ്റ്റിക്സ്",
        "addr": "Vyttila, Kochi 682019",
        "addr_local": "വൈറ്റില, കൊച്ചി 682019",
        "city": "Kochi",
        "phone": "0484 230 9944",
        "accred": "ISO 15189:2022 | NABL application pending",
        "path": {"name": "Dr. Ranjith Pillai", "qual": "MD (Pathology)",
                 "regn": "TCMC 2011/05/26640", "scrawl": "R Pillai"},
    },
    "fortcochin": {
        "abbr": "FCL", "acc_style": 3,
        "name": "Fort Cochin Clinical Lab",
        "name_local": "ഫോർട്ട് കൊച്ചി ക്ലിനിക്കൽ ലാബ്",
        "addr": "Napier Street, Fort Kochi 682001",
        "addr_local": "നേപ്പിയർ സ്ട്രീറ്റ്, ഫോർട്ട് കൊച്ചി 682001",
        "city": "Kochi",
        "phone": "0484 221 5570",
        "accred": "Neighbourhood laboratory. Reports issued same day.",
        "path": {"name": "Dr. Liji Antony", "qual": "MBBS, DCP",
                 "regn": "TCMC 2015/03/38812", "scrawl": "L Antony"},
    },
}

LFT_LEGEND = [
    ("AST to ALT ratio, interpretation", "Ratio"),
    ("Below 1.0", "Usual in viral and metabolic liver disease"),
    ("1.0 to 2.0", "Non-specific. Correlate clinically"),
    ("Above 2.0", "Suggestive of alcohol-related liver injury"),
]

# Ascites drained on admission, so the weight falls before it rises with recovery.
HEIGHT_CM = 174.0

VITALS = {
    1: {"weight_kg": 82.6, "bp": "126/78", "spo2": 97, "temp_f": 99.4,
        "context": "Admitted jaundiced. Ascites present. Last drink four days ago."},
    2: {"weight_kg": 74.8, "bp": "118/74", "spo2": 98, "temp_f": 98.6,
        "context": "Ascites drained and diuresed. Abstinent eight weeks."},
    3: {"weight_kg": 71.2, "bp": "116/72", "spo2": 98, "temp_f": 98.4,
        "context": "Abstinent six months. Attending the de-addiction programme."},
    4: {"weight_kg": 72.6, "bp": "118/74", "spo2": 99, "temp_f": 98.2,
        "context": "Well. Appetite back, weight recovering as muscle."},
    5: {"weight_kg": 74.4, "bp": "120/76", "spo2": 99, "temp_f": 98.4,
        "context": "Eighteen months abstinent. Discharged to annual review."},
}

REPORTS = [
    # ---- R01 -- presentation, printed as peel-off ward labels ----------------
    {
        "collected": "2025-01-15 07:30", "reported": "2025-01-15 13:10",
        "lab": "marine", "layout_style": "sticker_sheet",
        "header_style": "minimal_text_top", "uhid_label": "IP No",
        "doctor": JOSEPH, "specimen": "Serum",
        "alias": 0, "traps": ["abnormal_shaded", "no_reference_column"],
        "note": "Printed for the case file. Formal report issued separately.",
        "sections": [
            {"panel": "LFT", "title": 0, "drop": ["GGT"],
             "labels": {"ALT": "SGPT (ALT)", "AST": "SGOT (AST)",
                        "BILI_T": "BILIRUBIN - TOTAL"},
             "values": {"BILI_T": 4.82, "BILI_D": 3.16, "ALT": 186, "AST": 412,
                        "ALP": 168, "PROT_T": 6.4, "ALB": 2.6}},
        ],
    },
    # ---- R02 -- the wide ledger ---------------------------------------------
    {
        "collected": "2025-05-08 08:15", "reported": "2025-05-08 16:40",
        "lab": "backwater", "layout_style": "ledger_landscape",
        "header_style": "two_line_ribbon", "uhid_label": "Patient ID",
        "doctor": JOSEPH, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 1, "traps": ["sno_column", "test_code_column"],
        "sections": [
            {"panel": "LFT", "title": 1,
             "lab_codes": {"ALT": "LFT-104", "AST": "LFT-105", "GGT": "LFT-108",
                           "BILI_T": "LFT-101", "ALB": "LFT-110"},
             "labels": {"ALT": "Alanine Aminotransferase", "GGT": "Gamma GT",
                        "ALB": "Albumin, Serum (BCG)"},
             "values": {"BILI_T": 2.64, "BILI_D": 1.48, "ALT": 142, "AST": 268,
                        "ALP": 144, "GGT": 286, "PROT_T": 6.6, "ALB": 3.0}},
            {"panel": "CBC", "title": 0, "drop": ["ANC", "ALC", "BASO_PCT"],
             "values": {"HGB": 11.8, "RBC": 3.86, "PCV": 35.4, "MCV": 101.8,
                        "MCH": 30.6, "MCHC": 33.3, "RDW": 15.6, "WBC": 8900,
                        "NEUT_PCT": 68, "LYMPH_PCT": 22, "MONO_PCT": 8, "EOS_PCT": 2,
                        "PLT": 128000, "MPV": 10.8},
             "extra_rows": [{"code": "PERIPH_SMEAR",
                             "value": "Macrocytosis with target cells. Mild "
                                      "thrombocytopenia confirmed. No blasts."}]},
        ],
    },
    # ---- R03 -- six months abstinent, the accredited format ------------------
    {
        "collected": "2025-09-22 08:45", "reported": "2025-09-22 18:00",
        "lab": "marine", "layout_style": "nabl_ulr",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": JOSEPH, "specimen": "Serum",
        "alias": 2, "traps": ["footnote_marker", "interpretation_block",
                              "legend_lines"],
        "damage": ["fold", "stain"],
        "footnotes": [("1", "AST to ALT ratio 1.6, down from 2.2 in January. "
                            "Consistent with sustained abstinence."),
                      ("2", "Assay standardised to IFCC. Results are not comparable "
                            "with the pre-2024 method.")],
        "interpretation": "Marked improvement on abstinence. Transaminases roughly a "
                          "third of the admission values, bilirubin normal, albumin "
                          "recovering. Continue abstinence and repeat in six months.",
        "sections": [
            {"panel": "LFT", "title": 0, "legend": LFT_LEGEND,
             "labels": {"ALT": "S.G.P.T.", "AST": "S.G.O.T."},
             "values": {"BILI_T": 1.24, "BILI_D": 0.42, "ALT": 88, "AST": 141,
                        "ALP": 122, "GGT": 148, "PROT_T": 6.9, "ALB": 3.6}},
            {"heading": "Fibrosis markers",
             "rows": [{"code": "PLT", "value": 164000, "marker": "1"},
                      {"label": "Prothrombin Time (INR)", "value": "1.18",
                       "unit": "", "reference": "0.9 - 1.2"},
                      {"label": "Transient Elastography (kPa)", "value": "9.4",
                       "unit": "kPa", "reference": "< 7.0", "flag": "H",
                       "marker": "2"}]},
        ],
    },
    # ---- R04 -- this visit beside the last, both in bold ---------------------
    {
        "collected": "2026-02-10 08:20", "reported": "2026-02-10 17:15",
        "lab": "backwater", "layout_style": "dual_period",
        "header_style": "logo_left_banner", "uhid_label": "UHID",
        "doctor": JOSEPH, "specimen": "Serum",
        "alias": 0, "traps": ["prev_value_column", "abnormal_shaded"],
        "sections": [
            {"panel": "LFT", "title": 1,
             "sub": "Current column is 10/02/2026. Previous column is 22/09/2025.",
             "prev": {"BILI_T": "1.24", "BILI_D": "0.42", "BILI_I": "0.82",
                      "ALT": "88", "AST": "141", "ALP": "122", "GGT": "148",
                      "PROT_T": "6.9", "ALB": "3.6", "GLOB": "3.3",
                      "AG_RATIO": "1.1"},
             "labels": {"ALT": "SGPT (ALT)", "AST": "SGOT (AST)"},
             "values": {"BILI_T": 0.94, "BILI_D": 0.28, "ALT": 54, "AST": 66,
                        "ALP": 108, "GGT": 82, "PROT_T": 7.1, "ALB": 4.0}},
        ],
    },
    # ---- R05 -- discharged to annual review, results as cards ----------------
    {
        "collected": "2026-07-30 09:10", "reported": "2026-07-30 16:30",
        "lab": "fortcochin", "layout_style": "card_grid",
        "header_style": "centred_classic", "uhid_label": "Reg. No",
        "doctor": JOSEPH, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 1, "traps": ["unit_in_value_cell", "abnormal_shaded"],
        "damage": ["blur"],
        "sections": [
            {"panel": "LFT", "title": 1, "drop": ["GGT"],
             "labels": {"ALT": "Alanine Transaminase (ALT/SGPT)"},
             "values": {"BILI_T": 0.78, "BILI_D": 0.22, "ALT": 38, "AST": 41,
                        "ALP": 96, "PROT_T": 7.3, "ALB": 4.3}},
            {"heading": "Screening",
             "row_traps": {"UR_COLOUR": "text_result"},
             "rows": [{"code": "UR_COLOUR", "value": "Straw"},
                      {"code": "BLOOD_GROUP", "value": "O Positive"},
                      {"code": "HBA1C", "value": 5.6},
                      {"label": "Alpha Fetoprotein (AFP)", "value": "4.2",
                       "unit": "ng/mL", "reference": "< 10.0"}]},
        ],
    },
]
