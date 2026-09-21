"""Patient 19 of 20 - Pulmonology. Recurrent chest infections in a smoker, inflammation.

Male, 63 at the first report, Kanpur. Forty pack-years, three or four chest infections a
winter, CRP that never quite returns to normal between them, and a slow decline the
numbers only hint at. He stops smoking in 2024 after the worst admission and the
inflammatory markers finally settle - the record ends better than it starts, which is the
point of the case.

The setback is January 2024: community acquired pneumonia with CRP 246, admitted for five
days, the sickest he has been.

Five of these fifteen are not lab reports at all in the usual sense. R03 is a photograph
of the lab register book with four other patients' entries on the same page. R06 is a
screenshot of the lab sending values over chat. R08 and R09 are the discharge summary
from the pneumonia admission, labs buried in a section between the treatment and the
advice. R12 is the modern chain-lab format where every value sits on a range bar instead
of beside a printed interval.
"""

from __future__ import annotations

PATIENT = {
    "number": 19,
    "name": "Ramakant Dwivedi",
    "sex": "M",
    "dob": "1958-03-08",
    "uhid": "LMH/704628",
    "department": "Pulmonology",
    "city": "Kanpur",
    "age_at_first": 63,
    "tracked": ["CRP"],
    "brief": "Recurrent chest infections in a smoker, inflammation",
}


def check_arc(series):
    crp = [v for _, v in series["CRP"]]
    fails = []
    if not max(crp) > 150:
        fails.append(f"the pneumonia admission never shows, peak CRP {max(crp)}")
    if not crp[-1] < 10:
        fails.append(f"stopping smoking should settle it, ends {crp[-1]}")
    if len([v for v in crp if v > 20]) < 3:
        fails.append("not enough infective episodes for a recurrent case")
    return fails


LABS = {
    "ganges": {
        "abbr": "GDK", "acc_style": 0,
        "name": "Ganges Diagnostics Kanpur",
        "name_local": "गंगा डायग्नोस्टिक्स कानपुर",
        "addr": "Mall Road, Kanpur 208001",
        "addr_local": "मॉल रोड, कानपुर 208001",
        "city": "Kanpur",
        "phone": "0512 233 7740",
        "accred": "NABL Accredited (MC-2286) | ISO 15189:2012",
        "path": {"name": "Dr. Alka Tripathi", "qual": "MD (Pathology)",
                 "regn": "UPMC 2006/04/5521", "scrawl": "A Tripathi"},
    },
    "lakshmi": {
        "abbr": "LMH", "acc_style": 1,
        "name": "Lakshmi Memorial Hospital Laboratory",
        "name_local": "लक्ष्मी मेमोरियल हॉस्पिटल प्रयोगशाला",
        "addr": "Swaroop Nagar, Kanpur 208002",
        "addr_local": "स्वरूप नगर, कानपुर 208002",
        "city": "Kanpur",
        "phone": "0512 255 9000",
        "accred": "Department of Laboratory Medicine, Respiratory Unit",
        "path": {"name": "Dr. Mahesh Chandra Pal", "qual": "MD, DNB (Pathology)",
                 "regn": "UPMC 1997/12/0648", "scrawl": "M C Pal"},
    },
    "chowk": {
        "abbr": "CPL", "acc_style": 3,
        "name": "Chowk Path Lab",
        "name_local": "चौक पैथ लैब",
        "addr": "Naya Ganj, Kanpur 208001",
        "addr_local": "नया गंज, कानपुर 208001",
        "city": "Kanpur",
        "phone": "0512 241 6612",
        "accred": "Clinical Laboratory, Reg. No. KNP/DL/2016/2290",
        "path": {"name": "Dr. Sanjay Nigam", "qual": "MBBS, DCP",
                 "regn": "UPMC 2009/06/7714", "scrawl": "S Nigam"},
    },
}

AGARWAL = "Dr. Praveen Agarwal, MBBS, MD (Pulmonary Medicine)"
SINGH = "Dr. Ritu Singh, MBBS, MD (General Medicine)"
YADAV = "Dr. O. P. Yadav, MBBS, MD (Medicine)"

CRP_LEGEND = [
    ("C-reactive protein in respiratory infection", "CRP mg/L"),
    ("Below 6", "Normal"),
    ("6 - 40", "Mild inflammation or resolving infection"),
    ("40 - 100", "Significant bacterial infection likely"),
    ("Above 100", "Severe infection, assess for admission"),
]

# A smoker who loses weight through the bad years and puts some back after quitting.
# Saturation is the vital that tells the story: 94-96 through the winters, 88 on the
# day of the pneumonia admission, back to 96 once he stops.
HEIGHT_CM = 167.0

VITALS = {
    1: {"weight_kg": 62.4, "bp": "138/84", "spo2": 95, "temp_f": 99.6,
        "context": "Third chest infection this winter. Smoking 20 a day for forty years."},
    2: {"weight_kg": 61.8, "bp": "136/84", "spo2": 96, "temp_f": 98.4,
        "context": "Between episodes. Inhalers started, told again to stop smoking."},
    3: {"weight_kg": 61.0, "bp": "138/86", "spo2": 94, "temp_f": 100.2,
        "context": "Another infection. Treated at the local lab and clinic."},
    4: {"weight_kg": 60.2, "bp": "140/86", "spo2": 95, "temp_f": 98.6,
        "context": "Recovered. Spirometry shows moderate obstruction."},
    5: {"weight_kg": 59.6, "bp": "138/84", "spo2": 95, "temp_f": 98.4,
        "context": "Annual review. Still smoking, now 15 a day."},
    6: {"weight_kg": 59.0, "bp": "136/84", "spo2": 94, "temp_f": 99.8,
        "context": "Winter cough with green sputum. Results sent over the phone."},
    7: {"weight_kg": 58.2, "bp": "134/82", "spo2": 94, "temp_f": 98.8,
        "context": "Slow to clear. Second course of antibiotics."},
    8: {"weight_kg": 56.4, "bp": "118/70", "spo2": 88, "temp_f": 103.2,
        "context": "Admitted with community acquired pneumonia. Oxygen started."},
    9: {"weight_kg": 56.8, "bp": "126/76", "spo2": 93, "temp_f": 99.4,
        "context": "Fifth hospital day, for discharge. Oxygen stopped yesterday."},
    10: {"weight_kg": 58.6, "bp": "130/80", "spo2": 94, "temp_f": 98.4,
         "context": "Six weeks after discharge. Stopped smoking on the ward."},
    11: {"weight_kg": 60.4, "bp": "132/82", "spo2": 95, "temp_f": 98.2,
         "context": "Six months smoke free. Cough much less."},
    12: {"weight_kg": 62.0, "bp": "130/80", "spo2": 96, "temp_f": 98.6,
         "context": "Annual review. No infection this winter, the first in years."},
    13: {"weight_kg": 62.8, "bp": "128/80", "spo2": 96, "temp_f": 98.4,
         "context": "Single repeat CRP after a mild cold."},
    14: {"weight_kg": 63.6, "bp": "128/78", "spo2": 96, "temp_f": 98.2,
         "context": "Annual review. Weight and saturation both better than 2021."},
    15: {"weight_kg": 64.2, "bp": "126/78", "spo2": 96, "temp_f": 98.4,
         "context": "Two years smoke free. Inhalers continue."},
}

REPORTS = [
    # ---- R01 -- third infection of the winter --------------------------------
    {
        "collected": "2021-12-09 10:30", "reported": "2021-12-09 18:10",
        "lab": "ganges", "layout_style": "clean_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Patient ID",
        "doctor": SINGH, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["legend_lines", "abnormal_shaded"],
        "damage": ["aged", "fold"],
        "sections": [
            {"panel": "CBC", "title": 0, "drop": ["ANC", "ALC", "MPV"],
             "values": {"HGB": 14.2, "RBC": 4.86, "PCV": 43.8, "MCV": 90.1, "MCH": 29.2,
                        "MCHC": 32.4, "RDW": 13.8, "WBC": 13800, "NEUT_PCT": 79,
                        "LYMPH_PCT": 14, "MONO_PCT": 5, "EOS_PCT": 1, "BASO_PCT": 1,
                        "PLT": 296000}},
            {"panel": "INFLAMMATION", "title": 0, "legend": CRP_LEGEND,
             "drop": ["RA_FACTOR", "ASO"],
             "values": {"CRP": 86.4, "HS_CRP": 14.20}},
        ],
    },
    # ---- R02 -- between episodes ----------------------------------------------
    {
        "collected": "2022-04-21 09:00", "reported": "2022-04-21 16:40",
        "lab": "chowk", "layout_style": "ledger_ruled",
        "header_style": "bilingual_header", "uhid_label": "Reg. No",
        "doctor": AGARWAL, "specimen": "Serum, Urine (midstream)",
        "alias": 1, "traps": ["unit_in_label"],
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 0, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Yellow", "UR_PH": 6.0, "UR_SPGR": 1.022,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 3, "UR_RBC": 1, "UR_EPITH": 3}},
            {"panel": "KFT", "title": 0,
             "values": {"CREAT": 1.04, "UREA": 32, "UA": 6.6}},
            {"panel": "DIABETES", "title": 0, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 104, "GLU_PP": 142, "HBA1C": 5.9}},
            {"heading": "Inflammation",
             "rows": [{"code": "CRP", "value": 12.4, "flag": "H"},
                      {"code": "ESR", "value": 28, "flag": "H"}]},
        ],
    },
    # ---- R03 -- the register book page ---------------------------------------
    {
        "collected": "2022-11-30 11:10", "reported": "2022-11-30 15:20",
        "lab": "chowk", "layout_style": "register_page",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": SINGH, "specimen": "Whole blood (EDTA), Serum",
        "alias": 2, "traps": [],
        "damage": ["dark", "fold"],
        "sections": [
            {"heading": "Register Entries",
             "rows": [{"code": "WBC", "value": 12600, "flag": "H"},
                      {"code": "CRP", "value": 64.8, "flag": "H"},
                      {"code": "HGB", "value": 14.0}]},
        ],
    },
    # ---- R04 -- recovered, spirometry ----------------------------------------
    {
        "collected": "2023-03-17 08:50", "reported": "2023-03-17 17:30",
        "lab": "lakshmi", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Hospital No",
        "doctor": AGARWAL, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 3, "traps": ["method_sub_line"],
        "interpretation": "Inflammatory markers have not returned to normal between "
                          "infections, which is usual in a smoker with chronic "
                          "bronchitis. Smoking cessation remains the single most useful "
                          "intervention.",
        "sections": [
            {"panel": "LFT", "title": 0, "methods": True, "drop": ["BILI_I"],
             "values": {"BILI_T": 0.8, "BILI_D": 0.2, "ALT": 38, "AST": 42, "ALP": 96,
                        "GGT": 88, "PROT_T": 7.0, "ALB": 3.9}},
            {"panel": "THYROID", "title": 2, "drop": ["T3_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel",
             "values": {"TSH": 2.94, "T4_TOTAL": 8.4, "FT4": 1.14}},
            {"heading": "Inflammation",
             "rows": [{"code": "CRP", "value": 9.6, "flag": "H"},
                      {"code": "ESR", "value": 24, "flag": "H"}]},
        ],
    },
    # ---- R05 -- annual review --------------------------------------------------
    {
        "collected": "2023-08-10 07:50", "reported": "2023-08-10 19:20",
        "lab": "ganges", "layout_style": "dense_multipanel",
        "header_style": "banner_with_qr", "uhid_label": "Patient ID",
        "doctor": AGARWAL, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 0, "traps": ["merged_panel_heading", "text_result", "method_sub_line"],
        "note": "Annual respiratory review package.",
        "sections": [
            {"panel": "CBC", "title": 2, "drop": ["ANC", "ALC", "MPV", "MCHC", "RDW"],
             "values": {"HGB": 15.4, "RBC": 5.16, "PCV": 46.8, "MCV": 90.7, "MCH": 29.8,
                        "WBC": 8600, "NEUT_PCT": 64, "LYMPH_PCT": 26, "MONO_PCT": 6,
                        "EOS_PCT": 3, "BASO_PCT": 1, "PLT": 262000}},
            {"panel": "LIPID", "title": 2, "drop": ["NON_HDL", "LDL_HDL_RATIO"],
             "values": {"CHOL": 196, "TRIG": 172, "HDL": 38}},
            {"panels": ["LFT", "ELECTROLYTES"], "heading": "Biochemistry Screen",
             "trap": "merged_panel_heading",
             "drop": ["GGT", "AG_RATIO", "GLOB", "BILI_I", "CA_ION", "MG"],
             "values": {"BILI_T": 0.7, "BILI_D": 0.2, "ALT": 34, "AST": 38, "ALP": 92,
                        "PROT_T": 7.1, "ALB": 4.0,
                        "NA": 139, "K": 4.3, "CL": 103, "CA": 9.2, "PHOS": 3.4}},
            {"panel": "VITAMIN", "title": 2, "methods": True,
             "values": {"VIT_D": 14.6, "VIT_B12": 288, "FOLATE": 6.8}},
            {"heading": "Other",
             "rows": [{"code": "CRP", "value": 11.2, "flag": "H"},
                      {"code": "BLOOD_GROUP", "value": "B Positive",
                       "trap": "text_result"},
                      {"code": "HBA1C", "value": 5.8}]},
        ],
    },
    # ---- R06 -- results sent over chat ----------------------------------------
    {
        "collected": "2023-12-28 09:40", "reported": "2023-12-28 19:05",
        "lab": "chowk", "layout_style": "chat_screenshot",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": SINGH, "specimen": "Whole blood (EDTA), Serum",
        "alias": 1, "traps": [],
        "note": "Screenshot forwarded to the clinic by the patient's son.",
        "sections": [
            {"heading": "Reports ready sir",
             "rows": [{"code": "WBC", "value": 14200, "flag": "H"},
                      {"code": "CRP", "value": 92.6, "flag": "H"},
                      {"code": "HGB", "value": 14.6}]},
            {"heading": "Sputum",
             "rows": [{"label": "Sputum Gram Stain", "value": "Gram positive diplococci "
                       "seen, plenty of pus cells", "unit": "", "reference": "",
                       "trap": "text_result"}]},
        ],
    },
    # ---- R07 -- slow to clear --------------------------------------------------
    {
        "collected": "2024-01-08 09:20", "reported": "2024-01-08 16:10",
        "lab": "ganges", "layout_style": "thermal_slip",
        "header_style": "centred_title_only", "uhid_label": "Patient ID",
        "doctor": SINGH, "specimen": "Serum",
        "alias": 2, "traps": ["no_reference_column"],
        "sections": [
            {"heading": "C-Reactive Protein",
             "rows": [{"code": "CRP", "value": 58.4, "flag": "H"}]},
        ],
    },
    # ---- R08 -- the pneumonia admission, discharge summary -------------------
    {
        "collected": "2024-01-22 04:10", "reported": "2024-01-22 07:40",
        "lab": "lakshmi", "layout_style": "discharge_summary",
        "header_style": "hospital_department_block", "uhid_label": "Hospital No",
        "doctor": AGARWAL, "specimen": "Whole blood (EDTA), Serum, Sputum",
        "alias": 3, "traps": ["text_result", "abnormal_shaded"],
        "page_break_after": 2,
        "discharge": {
            "diagnosis": "Community acquired pneumonia, right lower lobe. Chronic "
                         "obstructive pulmonary disease, moderate. Current smoker.",
            "history": "Admitted through casualty with four days of fever, productive "
                       "cough and increasing breathlessness. Saturation 88 per cent on "
                       "room air at presentation. Forty pack-year smoking history, three "
                       "to four chest infections each winter for the past five years.",
            "examination": "Febrile at 39.5 C, respiratory rate 28, bronchial breathing "
                           "at the right base with coarse crackles. No signs of cardiac "
                           "failure. Chest radiograph confirmed right lower lobe "
                           "consolidation.",
            "course": "Started on intravenous antibiotics and controlled oxygen. Fever "
                      "settled by the third day and oxygen was weaned by the fourth. "
                      "Inflammatory markers fell steadily, as below. Counselled at length "
                      "on smoking cessation and started on nicotine replacement on the "
                      "ward, which he accepted for the first time.",
            "treatment": "Injection Ceftriaxone 1 g twice daily for five days, "
                         "Azithromycin 500 mg daily for five days, nebulised "
                         "bronchodilators, controlled oxygen, nicotine patches.",
            "advice": "Complete the oral antibiotic course. Continue inhalers. Do not "
                      "resume smoking. Review in the chest clinic in six weeks with a "
                      "repeat CRP and chest radiograph. Return earlier if fever or "
                      "breathlessness returns.",
        },
        "sections": [
            {"heading": "On Admission (22/01/2024)",
             "rows": [{"code": "WBC", "value": 21400, "flag": "H"},
                      {"code": "NEUT_PCT", "value": 89, "flag": "H"},
                      {"code": "CRP", "value": 246.0, "flag": "H"},
                      {"code": "HGB", "value": 13.4, "flag": "L"},
                      {"code": "NA", "value": 131, "flag": "L"},
                      {"code": "UREA", "value": 52, "flag": "H"},
                      {"code": "CREAT", "value": 1.24}]},
            {"heading": "Microbiology",
             "rows": [{"label": "Sputum Culture", "value": "Streptococcus pneumoniae, "
                       "moderate growth. Sensitive to Ceftriaxone, Amoxicillin.",
                       "unit": "", "reference": "No growth", "flag": "H",
                       "trap": "text_result"},
                      {"label": "Procalcitonin", "value": "4.62", "unit": "ng/mL",
                       "reference": "< 0.50", "flag": "H"}]},
        ],
    },
    # ---- R09 -- fifth hospital day, discharge bloods -------------------------
    {
        "collected": "2024-01-26 06:20", "reported": "2024-01-26 09:50",
        "lab": "lakshmi", "layout_style": "fax_header",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": AGARWAL, "specimen": "Whole blood (EDTA), Serum",
        "alias": 0, "traps": ["no_reference_column"],
        "note": "Faxed to the chest clinic with the discharge papers.",
        "sections": [
            {"heading": "Discharge Bloods",
             "rows": [{"code": "WBC", "value": 9800},
                      {"code": "CRP", "value": 42.6, "flag": "H"},
                      {"code": "HGB", "value": 13.2, "flag": "L"},
                      {"code": "NA", "value": 137},
                      {"code": "CREAT", "value": 1.06}]},
        ],
    },
    # ---- R10 -- six weeks after discharge -------------------------------------
    {
        "collected": "2024-03-06 09:10", "reported": "2024-03-06 16:30",
        "lab": "lakshmi", "layout_style": "kv_header_table",
        "header_style": "letterhead_logo_left", "uhid_label": "Hospital No",
        "doctor": AGARWAL, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 1, "traps": ["prev_value_column", "flag_as_words"],
        "damage": ["crop-right", "aged"],
        "sections": [
            {"panel": "HORMONES", "title": 0, "drop": ["PROLACTIN", "PTH"],
             "values": {"CORTISOL_AM": 16.4, "TESTO_T": 312}},
            {"heading": "Inflammation",
             "prev": {"CRP": "42.6 (26/01/2024)", "ESR": "58 (22/01/2024)"},
             "rows": [{"code": "CRP", "value": 14.8, "flag": "H"},
                      {"code": "ESR", "value": 32, "flag": "H"}]},
        ],
    },
    # ---- R11 -- six months smoke free ------------------------------------------
    {
        "collected": "2024-08-19 08:40", "reported": "2024-08-19 17:00",
        "lab": "ganges", "layout_style": "typewriter_manual",
        "header_style": "minimal_text_top", "uhid_label": "Patient ID",
        "doctor": AGARWAL, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["no_reference_column"],
        "damage": ["fold", "stain"],
        "sections": [
            {"panel": "IRON", "title": 0, "drop": ["UIBC"],
             "values": {"FERRITIN": 148, "IRON": 88, "TIBC": 336}},
            {"heading": "Inflammation",
             "rows": [{"code": "CRP", "value": 8.2, "flag": "H"},
                      {"code": "ESR", "value": 20}]},
        ],
    },
    # ---- R12 -- the chain lab with range bars ---------------------------------
    {
        "collected": "2025-02-15 08:30", "reported": "2025-02-15 16:50",
        "lab": "ganges", "layout_style": "range_bar",
        "header_style": "two_line_ribbon", "uhid_label": "Patient ID",
        "doctor": AGARWAL, "specimen": "Whole blood (EDTA), Serum",
        "alias": 3, "traps": ["method_sub_line"],
        "interpretation": "First winter in six years without a chest infection. "
                          "Inflammatory markers are near normal and the blood count has "
                          "settled.",
        "sections": [
            {"heading": "Haemogram",
             "rows": [{"code": "HGB", "value": 14.8}, {"code": "PCV", "value": 44.2},
                      {"code": "MCV", "value": 89.5}, {"code": "WBC", "value": 7600},
                      {"code": "NEUT_PCT", "value": 60},
                      {"code": "PLT", "value": 248000}]},
            {"panel": "IRON", "title": 3, "drop": ["UIBC"],
             "values": {"FERRITIN": 132, "IRON": 92, "TIBC": 330}},
            {"panel": "INFLAMMATION", "title": 3, "drop": ["RA_FACTOR", "ASO"],
             "methods": True,
             "values": {"CRP": 5.4, "HS_CRP": 2.60}},
        ],
    },
    # ---- R13 -- one CRP after a cold -------------------------------------------
    {
        "collected": "2025-09-23 09:45", "reported": "2025-09-23 13:20",
        "lab": "chowk", "layout_style": "handwritten_values",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": SINGH, "specimen": "Serum",
        "alias": 0, "traps": ["no_header_row"],
        "damage": ["scanborder", "aged"],
        "sections": [
            {"heading": "C-Reactive Protein",
             "rows": [{"code": "CRP", "value": 7.6, "flag": "H"}]},
        ],
    },
    # ---- R14 -- annual review, two pages ---------------------------------------
    {
        "collected": "2026-03-24 07:45", "reported": "2026-03-24 19:50",
        "lab": "lakshmi", "layout_style": "continuation",
        "header_style": "letterhead_logo_left", "uhid_label": "Hospital No",
        "doctor": AGARWAL, "specimen": "Whole blood (EDTA), Serum, Fluoride plasma",
        "alias": 1, "traps": ["footnote_marker", "ratio_no_code"],
        "page_break_after": 3,
        "footnotes": [("1", "Two years smoke free. Spirometry stable compared with 2023.")],
        "sections": [
            {"panel": "CBC", "title": 5,
             "values": {"HGB": 14.6, "RBC": 4.88, "PCV": 43.6, "MCV": 89.3, "MCH": 29.9,
                        "MCHC": 33.5, "RDW": 13.0, "WBC": 7200, "NEUT_PCT": 58,
                        "LYMPH_PCT": 32, "MONO_PCT": 6, "EOS_PCT": 3, "BASO_PCT": 1,
                        "PLT": 244000, "MPV": 9.4}},
            {"panel": "LIPID", "title": 5,
             "values": {"CHOL": 186, "TRIG": 148, "HDL": 44}},
            {"panel": "DIABETES", "title": 5, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 100, "GLU_PP": 136, "HBA1C": 5.7}},
            {"panel": "KFT", "title": 5,
             "values": {"CREAT": 1.02, "UREA": 30, "UA": 6.2},
             "row_traps": {"CREAT": "footnote_marker"}},
            {"panel": "THYROID", "title": 5, "drop": ["T3_TOTAL", "FT3", "ANTI_TPO"],
             "trap": "sparse_panel",
             "values": {"TSH": 2.62, "T4_TOTAL": 8.8, "FT4": 1.18}},
            {"heading": "Inflammation and Derived",
             "rows": [{"code": "CRP", "value": 4.8}, {"code": "ESR", "value": 16},
                      {"label": "Neutrophil - Lymphocyte Ratio", "value": "1.8",
                       "unit": "", "reference": "1.0 - 3.0", "trap": "ratio_no_code"}]},
        ],
    },
    # ---- R15 -- two years smoke free --------------------------------------------
    {
        "collected": "2026-09-08 08:50", "reported": "2026-09-08 16:20",
        "lab": "ganges", "layout_style": "mixed_print_hand",
        "header_style": "stamp_and_signature", "uhid_label": "Patient ID",
        "doctor": AGARWAL, "specimen": "Serum, Whole blood (EDTA), Urine",
        "alias": 2, "traps": ["method_sub_line"], "stamp": "CHEST CLINIC<br>REVIEWED",
        "damage": ["fold"],
        "sections": [
            {"panel": "VITAMIN", "title": 4, "methods": True,
             "values": {"VIT_D": 26.4, "VIT_B12": 332, "FOLATE": 8.8}},
            {"panel": "ELECTROLYTES", "title": 4, "drop": ["CA_ION", "MG"],
             "values": {"NA": 140, "K": 4.2, "CL": 104, "CA": 9.4, "PHOS": 3.2}},
            {"panel": "URINE_ROUTINE", "title": 4, "drop": ["MICROALB", "ACR"],
             "values": {"UR_COLOUR": "Pale Yellow", "UR_PH": 6.5, "UR_SPGR": 1.018,
                        "UR_PROT": "Absent", "UR_GLU": "Absent", "UR_KET": "Absent",
                        "UR_PUS": 2, "UR_RBC": 0, "UR_EPITH": 3}},
            {"heading": "Noted at the clinic", "hand_addendum": True,
             "rows": [{"code": "CRP", "value": 4.2}, {"code": "ESR", "value": 14}]},
        ],
    },
]
