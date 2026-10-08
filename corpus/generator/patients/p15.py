"""Patient 15 of 20 - Rheumatology. Rheumatoid arthritis, inflammatory markers responding.

Female, 44 at the first report, Guwahati. Seropositive rheumatoid arthritis: CRP 68,
ESR 82, RA factor 186 and swollen hands at presentation. Methotrexate and a short steroid
course bring CRP under 6 within a year. The setback is mid-2024, a flare after
methotrexate was stopped for a dental extraction and never restarted - CRP back to 54 -
settled by adding a biologic.

This is the first patient whose reports have been handled the way patients actually handle
them. Nine of the fifteen carry physical damage: old paper kept folded in a file, a tea
ring, a torn corner, staple holes, pages photographed on a phone in poor light, and two
where the right edge was cropped out of the picture altogether. R09 is deliberately
illegible - a dark, blurred photograph with a thumb across the corner, the kind of thing a
clinic receives and has to ask the patient to send again. The answer key still records
what the page says, so the scorer can separate "the parser failed" from "the image was
unreadable".
"""

from __future__ import annotations

PATIENT = {
    "number": 15,
    "name": "Anjali Bhattacharyya",
    "sex": "F",
    "dob": "1977-09-06",
    "uhid": "BRH/649238",
    "department": "Rheumatology",
    "city": "Guwahati",
    "age_at_first": 44,
    "tracked": ["CRP"],
    "brief": "Rheumatoid arthritis, inflammatory markers responding",
}


def check_arc(series):
    crp = [v for _, v in series["CRP"]]
    fails = []
    if not crp[0] > 40:
        fails.append(f"should present with a high CRP, got {crp[0]}")
    if not min(crp) < 6:
        fails.append(f"treatment never controls the inflammation, best {min(crp)}")
    if not any(crp[j] > min(crp[:j]) + 30 for j in range(1, len(crp))):
        fails.append("no flare after methotrexate was stopped")
    if not crp[-1] < 10:
        fails.append(f"should end controlled, CRP {crp[-1]}")
    return fails


LABS = {
    "brahmaputra": {
        "abbr": "BRH", "acc_style": 1,
        "name": "Brahmaputra Referral Hospital Laboratory",
        "name_local": "ব্ৰহ্মপুত্ৰ ৰেফাৰেল হস্পিটেল পৰীক্ষাগাৰ",
        "addr": "GS Road, Guwahati 781005",
        "addr_local": "জি এছ ৰোড, গুৱাহাটী 781005",
        "city": "Guwahati",
        "phone": "0361 246 8800",
        "accred": "Department of Laboratory Medicine, Rheumatology Services",
        "path": {"name": "Dr. Nabanita Sarma", "qual": "MD, DNB (Pathology)",
                 "regn": "ACMR 2004/08/1147", "scrawl": "N Sarma"},
    },
    "kamakhya": {
        "abbr": "KDL", "acc_style": 0,
        "name": "Kamakhya Diagnostic Labs",
        "name_local": "কামাখ্যা ডায়েগনষ্টিক লেবছ",
        "addr": "Zoo Road Tiniali, Guwahati 781024",
        "addr_local": "চিৰিয়াখানা ৰোড তিনিআলি, গুৱাহাটী 781024",
        "city": "Guwahati",
        "phone": "0361 235 4417",
        "accred": "NABL Accredited (MC-5529) | ISO 15189:2012",
        "path": {"name": "Dr. Pranab Deka", "qual": "MD (Pathology)",
                 "regn": "ACMR 2009/12/6638", "scrawl": "P Deka"},
    },
    "dispur": {
        "abbr": "DPC", "acc_style": 3,
        "name": "Dispur Path Corner",
        "name_local": "দিছপুৰ পেথ কৰ্ণাৰ",
        "addr": "Last Gate, Dispur, Guwahati 781006",
        "addr_local": "লাষ্ট গেট, দিছপুৰ, গুৱাহাটী 781006",
        "city": "Guwahati",
        "phone": "0361 222 9930",
        "accred": "NABL Accredited (M-7783)",
        "path": {"name": "Dr. Rituparna Das", "qual": "MBBS, MD (Path.)",
                 "regn": "ACMR 2015/03/9924", "scrawl": "R Das"},
    },
}

BARUAH = "Dr. Hiren Baruah, MBBS, MD, DM (Rheumatology)"
GOSWAMI = "Dr. Mridula Goswami, MBBS, MD (Medicine)"
HAZARIKA = "Dr. Pankaj Hazarika, MBBS, MD (General Medicine)"

CRP_LEGEND = [
    ("C-reactive protein - interpretation", "CRP mg/L"),
    ("Below 6", "Normal"),
    ("6 - 40", "Mild to moderate inflammation"),
    ("Above 40", "Marked inflammation, correlate clinically"),
]

# Steroids put weight on in the first year and it comes off slowly.
# The 2024 flare is the only visit with a low-grade temperature.
HEIGHT_CM = 155.0

VITALS = {
    1: {"weight_kg": 54.6, "bp": "118/76", "spo2": 98, "temp_f": 99.2,
        "context": "Swollen painful hands for four months, morning stiffness two hours."},
    2: {"weight_kg": 57.8, "bp": "124/80", "spo2": 98, "temp_f": 98.4,
        "context": "Six weeks on prednisolone and methotrexate. Much less pain."},
    3: {"weight_kg": 59.4, "bp": "126/82", "spo2": 98, "temp_f": 98.2,
        "context": "Steroid being tapered. Weight up from the steroids."},
    4: {"weight_kg": 58.2, "bp": "122/78", "spo2": 99, "temp_f": 98.6,
        "context": "Off steroids, methotrexate alone. Hands much better."},
    5: {"weight_kg": 56.8, "bp": "120/78", "spo2": 98, "temp_f": 98.4,
        "context": "Annual review. Inflammation controlled."},
    6: {"weight_kg": 56.2, "bp": "118/76", "spo2": 98, "temp_f": 98.2,
        "context": "In remission by clinical and laboratory criteria."},
    7: {"weight_kg": 56.6, "bp": "120/78", "spo2": 98, "temp_f": 98.4,
        "context": "Methotrexate stopped for a dental extraction, not restarted."},
    8: {"weight_kg": 57.4, "bp": "126/82", "spo2": 97, "temp_f": 99.8,
        "context": "Flare. Both wrists swollen, stiffness back, low-grade temperature."},
    9: {"weight_kg": 57.0, "bp": "124/80", "spo2": 98, "temp_f": 99.1,
        "context": "Flare settling on restarted methotrexate and a steroid burst."},
    10: {"weight_kg": 57.8, "bp": "122/78", "spo2": 98, "temp_f": 98.6,
         "context": "Biologic added after the second flare in six months."},
    11: {"weight_kg": 57.2, "bp": "120/78", "spo2": 98, "temp_f": 98.4,
         "context": "Responding well to the combination."},
    12: {"weight_kg": 56.4, "bp": "118/76", "spo2": 99, "temp_f": 98.2,
         "context": "Back in remission. Monitoring bloods three-monthly."},
    13: {"weight_kg": 56.0, "bp": "118/76", "spo2": 98, "temp_f": 98.4,
         "context": "Single confirmatory CRP before the annual review."},
    14: {"weight_kg": 55.8, "bp": "116/74", "spo2": 98, "temp_f": 98.6,
         "context": "Annual review. Sustained remission on the combination."},
    15: {"weight_kg": 55.4, "bp": "116/74", "spo2": 99, "temp_f": 98.2,
         "context": "Well. Biologic interval being extended."},
}

REPORTS = [
    # ---- R01 -- presentation, an old page kept folded in the file ------------
    {
        "collected": "2021-10-30 09:20", "reported": "2021-10-30 18:40",
        "lab": "brahmaputra", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": BARUAH, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["legend_lines"],
        "damage": ["aged", "fold"],
        "interpretation": "Seropositive inflammatory arthritis with markedly raised acute "
                          "phase reactants. Anti-CCP is strongly positive, which carries a "
                          "worse prognosis and supports early disease-modifying therapy.",
        "sections": [
            {"panel": "INFLAMMATION", "title": 0, "legend": CRP_LEGEND,
             "values": {"CRP": 68.4, "HS_CRP": 12.60, "RA_FACTOR": 186.0, "ASO": 94}},
            {"heading": "Haematology and Serology",
             "rows": [{"code": "ESR", "value": 82, "flag": "H"},
                      {"code": "HGB", "value": 10.6, "flag": "L"},
                      {"label": "Anti-CCP Antibody", "value": "248", "unit": "U/mL",
                       "reference": "< 17", "flag": "H"},
                      {"label": "ANA (IFA, Hep-2)", "value": "Positive, 1:80 speckled",
                       "unit": "", "reference": "Negative", "flag": "H",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R02 -- six weeks on treatment --------------------------------------
    {
        "collected": "2021-12-18 08:50", "reported": "2021-12-18 16:20",
        "lab": "kamakhya", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Patient ID",
        "doctor": BARUAH, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 1, "traps": ["unit_in_label"],
        "sections": [
            {"panel": "LFT", "title": 0, "drop": ["GGT", "BILI_I"],
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 32, "AST": 28, "ALP": 82,
                        "PROT_T": 7.0, "ALB": 3.8}},
            {"heading": "Inflammatory Markers",
             "rows": [{"code": "CRP", "value": 28.6, "flag": "H"},
                      {"code": "ESR", "value": 48, "flag": "H"},
                      {"code": "HGB", "value": 11.0, "flag": "L"}]},
        ],
    },
    # ---- R03 -- steroid taper, photographed on a phone -----------------------
    {
        "collected": "2022-05-14 09:05", "reported": "2022-05-14 17:10",
        "lab": "dispur", "layout_style": "kv_header_table",
        "header_style": "bilingual_header", "uhid_label": "Reg. No",
        "doctor": GOSWAMI, "specimen": "Serum, Urine (midstream)",
        "alias": 2, "traps": ["sample_type_row"],
        "damage": ["dark", "fold"],
        "note": "Copy photographed by the patient; original with the rheumatology clinic.",
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 1, "sample_row": "Urine, Midstream",
             "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.0, "UR_SPGR": 1.016,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 3, "UR_RBC": 1, "UR_EPITH": 4}},
            {"heading": "Inflammatory Markers",
             "rows": [{"code": "CRP", "value": 14.2, "flag": "H"},
                      {"code": "ESR", "value": 32, "flag": "H"}]},
        ],
    },
    # ---- R04 -- methotrexate alone -------------------------------------------
    {
        "collected": "2022-10-22 08:40", "reported": "2022-10-22 16:50",
        "lab": "kamakhya", "layout_style": "ledger_ruled",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": BARUAH, "specimen": "Whole blood (EDTA), Serum",
        "alias": 3, "traps": ["range_split_columns"],
        "damage": ["aged"],
        "sections": [
            {"panel": "CBC", "title": 0, "drop": ["ANC", "ALC", "MPV"],
             "values": {"HGB": 11.6, "RBC": 4.02, "PCV": 35.4, "MCV": 88.1, "MCH": 28.9,
                        "MCHC": 32.8, "RDW": 14.2, "WBC": 6200, "NEUT_PCT": 58,
                        "LYMPH_PCT": 32, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 286000}},
            {"heading": "Inflammatory Markers",
             "rows": [{"code": "CRP", "value": 8.4, "flag": "H"},
                      {"code": "ESR", "value": 24, "flag": "H"}]},
        ],
    },
    # ---- R05 -- annual review -------------------------------------------------
    {
        "collected": "2023-04-08 07:55", "reported": "2023-04-08 19:20",
        "lab": "brahmaputra", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Hospital No",
        "doctor": BARUAH, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 0, "traps": ["merged_panel_heading", "text_result", "method_sub_line"],
        "note": "Annual review package with methotrexate monitoring bloods.",
        "sections": [
            {"panel": "LIPID", "title": 0, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 194, "TRIG": 138, "HDL": 52}},
            {"panels": ["LFT", "KFT"], "heading": "Methotrexate Monitoring",
             "trap": "merged_panel_heading",
             "drop": ["GGT", "AG_RATIO", "GLOB", "BILI_I", "BUN"],
             "values": {"BILI_T": 0.6, "BILI_D": 0.2, "ALT": 38, "AST": 32, "ALP": 78,
                        "PROT_T": 7.1, "ALB": 4.0,
                        "CREAT": 0.68, "UREA": 22, "UA": 4.6}},
            {"panel": "THYROID", "title": 0, "drop": ["FT3", "ANTI_TPO"],
             "values": {"TSH": 2.84, "T3_TOTAL": 118, "T4_TOTAL": 8.8, "FT4": 1.20}},
            {"panel": "IRON", "title": 4, "drop": ["UIBC"], "methods": True,
             "values": {"FERRITIN": 46, "IRON": 72, "TIBC": 358}},
            {"panel": "VITAMIN", "title": 0,
             "values": {"VIT_D": 17.6, "VIT_B12": 298, "FOLATE": 6.2}},
            {"heading": "Inflammation and Other",
             "rows": [{"code": "CRP", "value": 5.2},
                      {"code": "ESR", "value": 18},
                      {"code": "BLOOD_GROUP", "value": "A Positive",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R06 -- remission, on a tea-stained page ------------------------------
    {
        "collected": "2023-09-26 09:10", "reported": "2023-09-26 16:30",
        "lab": "dispur", "layout_style": "clean_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Reg. No",
        "doctor": GOSWAMI, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 1, "traps": ["flag_as_words"],
        "damage": ["stain", "aged"],
        "sections": [
            {"panel": "INFLAMMATION", "title": 1,
             "values": {"CRP": 3.4, "HS_CRP": 1.80, "RA_FACTOR": 96.0, "ASO": 88}},
            {"panel": "DIABETES", "title": 1, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 90, "GLU_PP": 122, "HBA1C": 5.3}},
            {"heading": "Haematology",
             "rows": [{"code": "ESR", "value": 14}, {"code": "HGB", "value": 12.2}]},
        ],
    },
    # ---- R07 -- methotrexate stopped for dental work -------------------------
    {
        "collected": "2024-02-15 09:30", "reported": "2024-02-15 14:50",
        "lab": "kamakhya", "layout_style": "thermal_slip",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": HAZARIKA, "specimen": "Serum",
        "alias": 2, "traps": ["no_reference_column"],
        "sections": [
            {"heading": "C-Reactive Protein",
             "rows": [{"code": "CRP", "value": 6.8, "flag": "H"}]},
        ],
    },
    # ---- R08 -- the flare, right edge cropped out of the photograph ----------
    {
        "collected": "2024-07-19 10:40", "reported": "2024-07-19 18:15",
        "lab": "brahmaputra", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": BARUAH, "specimen": "Whole blood (EDTA), Serum",
        "alias": 3, "traps": ["abnormal_shaded", "legend_lines"],
        "damage": ["crop-right", "dark"],
        "note": "Flare of disease activity six months after stopping methotrexate.",
        "sections": [
            {"panel": "INFLAMMATION", "title": 2, "legend": CRP_LEGEND,
             "values": {"CRP": 54.2, "HS_CRP": 9.80, "RA_FACTOR": 168.0, "ASO": 102}},
            {"heading": "Haematology",
             "rows": [{"code": "ESR", "value": 68, "flag": "H"},
                      {"code": "HGB", "value": 11.2, "flag": "L"},
                      {"code": "PLT", "value": 428000, "flag": "H"}]},
        ],
    },
    # ---- R09 -- the photograph the clinic had to reject ----------------------
    {
        "collected": "2024-09-04 09:00", "reported": "2024-09-04 15:40",
        "lab": "dispur", "layout_style": "kv_header_table",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": HAZARIKA, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 0, "traps": ["method_sub_line"],
        "damage": ["blur", "dark", "thumb", "fold"], "illegible": True,
        "note": "Image supplied by the patient. Quality poor; a fresh copy was requested.",
        "sections": [
            {"panel": "LFT", "title": 3, "methods": True, "drop": ["GGT", "BILI_I"],
             "values": {"BILI_T": 0.7, "BILI_D": 0.2, "ALT": 44, "AST": 36, "ALP": 84,
                        "PROT_T": 7.0, "ALB": 3.9}},
            {"heading": "Inflammatory Markers",
             "rows": [{"code": "CRP", "value": 22.4, "flag": "H"},
                      {"code": "ESR", "value": 44, "flag": "H"}]},
        ],
    },
    # ---- R10 -- biologic added, torn corner and staple holes -----------------
    {
        "collected": "2025-01-31 08:45", "reported": "2025-01-31 17:25",
        "lab": "brahmaputra", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Hospital No",
        "doctor": BARUAH, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 1, "traps": ["text_result", "test_code_column"],
        "damage": ["torn", "stain", "aged"],
        "interpretation": "Screening before starting a biologic agent. Viral serology and "
                          "tuberculosis screening are negative, so treatment may proceed.",
        "sections": [
            {"panel": "SEROLOGY", "title": 0, "drop": ["WIDAL", "DENGUE_NS1",
                                                       "DENGUE_IGM", "MP"],
             "lab_codes": {"HBSAG": "S-10", "ANTI_HCV": "S-11", "HIV": "S-12",
                           "VDRL": "S-13"},
             "values": {"HBSAG": "Non Reactive", "ANTI_HCV": "Non Reactive",
                        "HIV": "Non Reactive", "VDRL": "Non Reactive"},
             "row_traps": {"HBSAG": "text_result"}},
            {"heading": "Pre-biologic Screen",
             "lab_codes": {"CRP": "I-01", "ESR": "I-02"},
             "rows": [{"code": "CRP", "value": 18.6, "flag": "H"},
                      {"code": "ESR", "value": 38, "flag": "H"},
                      {"label": "Interferon Gamma Release Assay (TB)", "value": "Negative",
                       "unit": "", "reference": "Negative", "trap": "text_result"}]},
        ],
    },
    # ---- R11 -- responding ----------------------------------------------------
    {
        "collected": "2025-06-13 09:15", "reported": "2025-06-13 16:40",
        "lab": "kamakhya", "layout_style": "landscape_wide",
        "header_style": "barcode_header", "uhid_label": "Patient ID",
        "doctor": BARUAH, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["prev_value_column"],
        "damage": ["fold"],
        "sections": [
            {"panel": "CBC", "title": 3, "drop": ["ANC", "ALC", "MPV", "MCHC"],
             "prev": {"HGB": "11.2 (19/07/2024)", "PLT": "428000 (19/07/2024)"},
             "values": {"HGB": 12.0, "RBC": 4.18, "PCV": 36.6, "MCV": 87.6, "MCH": 28.7,
                        "RDW": 13.6, "WBC": 5800, "NEUT_PCT": 56, "LYMPH_PCT": 34,
                        "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 312000}},
            {"heading": "Inflammatory Markers",
             "prev": {"CRP": "18.6 (31/01/2025)", "ESR": "38 (31/01/2025)"},
             "rows": [{"code": "CRP", "value": 7.2, "flag": "H"},
                      {"code": "ESR", "value": 22, "flag": "H"}]},
        ],
    },
    # ---- R12 -- remission again, bottom of the page cropped off --------------
    {
        "collected": "2025-11-07 08:55", "reported": "2025-11-07 17:00",
        "lab": "dispur", "layout_style": "glossy_marketing",
        "header_style": "letterhead_logo_left", "uhid_label": "Reg. No",
        "doctor": GOSWAMI, "specimen": "Serum",
        "alias": 3, "traps": ["method_sub_line"],
        "damage": ["crop-bottom", "blur"],
        "sections": [
            {"panel": "INFLAMMATION", "title": 3, "methods": True,
             "values": {"CRP": 3.8, "HS_CRP": 1.40, "RA_FACTOR": 74.0, "ASO": 82}},
            {"panel": "ELECTROLYTES", "title": 0, "drop": ["CA_ION", "MG"],
             "values": {"NA": 140, "K": 4.2, "CL": 103, "CA": 9.2, "PHOS": 3.4}},
            {"panel": "URINE_ROUTINE", "title": 4, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.5, "UR_SPGR": 1.018,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 2, "UR_RBC": 0, "UR_EPITH": 3}},
        ],
    },
    # ---- R13 -- one CRP -------------------------------------------------------
    {
        "collected": "2026-03-11 09:40", "reported": "2026-03-11 13:20",
        "lab": "kamakhya", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Patient ID",
        "doctor": GOSWAMI, "specimen": "Serum",
        "alias": 0, "traps": ["no_header_row"],
        "damage": ["aged", "scanborder"],
        "sections": [
            {"heading": "C-Reactive Protein",
             "rows": [{"code": "CRP", "value": 4.6}]},
        ],
    },
    # ---- R14 -- annual review, two pages -------------------------------------
    {
        "collected": "2026-06-23 07:50", "reported": "2026-06-23 20:10",
        "lab": "brahmaputra", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "Hospital No",
        "doctor": BARUAH, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["ratio_no_code", "footnote_marker"],
        "page_break_after": 3,
        "footnotes": [("1", "Methotrexate monitoring bloods: full blood count, liver and "
                            "renal function every three months.")],
        "sections": [
            {"panel": "CBC", "title": 5,
             "values": {"HGB": 12.4, "RBC": 4.28, "PCV": 37.6, "MCV": 87.9, "MCH": 29.0,
                        "MCHC": 33.0, "RDW": 13.2, "WBC": 5600, "NEUT_PCT": 55,
                        "LYMPH_PCT": 35, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 288000, "MPV": 9.6}},
            {"panel": "LIPID", "title": 5,
             "values": {"CHOL": 188, "TRIG": 124, "HDL": 56}},
            {"panel": "DIABETES", "title": 5, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 92, "GLU_PP": 126, "HBA1C": 5.4}},
            {"heading": "Liver Function - Monitoring",
             "rows": [{"code": "BILI_T", "value": 0.6},
                      {"code": "ALT", "value": 34, "marker": "1"},
                      {"code": "AST", "value": 30}, {"code": "ALP", "value": 76},
                      {"code": "GGT", "value": 22}, {"code": "ALB", "value": 4.2}]},
            {"panel": "THYROID", "title": 4, "drop": ["T3_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel",
             "values": {"TSH": 2.96, "T4_TOTAL": 9.0, "FT4": 1.22}},
            {"panel": "KFT", "title": 5,
             "values": {"CREAT": 0.66, "UREA": 21, "UA": 4.4}},
            {"heading": "Inflammation and Derived",
             "rows": [{"code": "CRP", "value": 3.2}, {"code": "ESR", "value": 16},
                      {"label": "Neutrophil - Lymphocyte Ratio", "value": "1.6",
                       "unit": "", "reference": "1.0 - 3.0", "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R15 -- sustained remission ------------------------------------------
    {
        "collected": "2026-09-13 08:40", "reported": "2026-09-13 16:25",
        "lab": "kamakhya", "layout_style": "mixed_print_hand",
        "header_style": "stamp_and_signature", "uhid_label": "Patient ID",
        "doctor": BARUAH, "specimen": "Serum", "stamp": "RHEUMATOLOGY<br>REVIEWED",
        "alias": 2, "traps": ["method_sub_line"],
        "damage": ["fold", "stain"],
        "sections": [
            {"panel": "IRON", "title": 1, "methods": True,
             "values": {"FERRITIN": 62, "IRON": 86, "TIBC": 342}},
            {"panel": "VITAMIN", "title": 2, "methods": True,
             "values": {"VIT_D": 30.4, "VIT_B12": 344, "FOLATE": 9.6}},
            {"panel": "ELECTROLYTES", "title": 4, "drop": ["CA_ION", "PHOS"],
             "values": {"NA": 141, "K": 4.4, "CL": 104, "CA": 9.4, "MG": 2.0}},
            {"heading": "Noted at the clinic", "hand_addendum": True,
             "rows": [{"code": "CRP", "value": 2.8}, {"code": "ESR", "value": 12}]},
        ],
    },
]
