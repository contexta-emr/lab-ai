"""Patient 31 - BENCHMARK FIXTURE. Urosepsis: culture, coagulation, serology.

Female, 67, Pune. Admitted febrile and confused with an E. coli urinary sepsis.
Six reports over ten days: the urine that grew the organism, the blood culture
that grew it too, a coagulation screen as she becomes septic, the pre-transfusion
group and screen, and the admission viral serology every Indian hospital runs.

WHY THIS PATIENT EXISTS
    Not to tell a clinical story - P01 to P23 already do that. This one exists to
    print the result types nothing else in the corpus prints:

        organism        Escherichia coli
        susceptibility  S / I / R
        reactive        Non-reactive
        detected        Not detected
        coded           B Positive
        ordinal         Many / 3+
        narrative       a culture interpretation

    Every one of those is legal in lab.analytes.value_type only since migration
    021. Before that the schema could hold 'numeric' or 'text' and nothing else,
    so a susceptibility had to be stored as prose or thrown away.

    If this patient extracts and resolves correctly, the 30-panel vocabulary is
    reachable end to end: printed label -> alias -> canonical code -> a row a
    clinician can read. That is the only claim it is making.
"""

from __future__ import annotations

BENCHMARK = True

PATIENT = {
    "number": 31,
    "name": "Shalini Kulkarni",
    "sex": "F",
    "dob": "1959-02-11",
    "uhid": "DCH/880471",
    "department": "Internal Medicine",
    "city": "Pune",
    "age_at_first": 67,
    "tracked": ["CRP"],
    "brief": "Urosepsis - culture, coagulation and serology fixtures",
}


def check_arc(series):
    crp = [v for _, v in series["CRP"]]
    fails = []
    if not crp[0] > 100:
        fails.append(f"should present septic, CRP {crp[0]}")
    if not crp[-1] < 30:
        fails.append(f"should settle on antibiotics, final CRP {crp[-1]}")
    return fails


RANE = "Dr. Meenakshi Rane"

LABS = {
    "deccan": {
        "abbr": "DCH", "acc_style": 1,
        "name": "Deccan City Hospital Laboratory",
        "name_local": "डेक्कन सिटी हॉस्पिटल प्रयोगशाळा",
        "addr": "Deccan Gymkhana, Pune 411004",
        "addr_local": "डेक्कन जिमखाना, पुणे 411004",
        "city": "Pune",
        "phone": "020 2567 1180",
        "accred": "NABL MC-2214 | Microbiology and Transfusion Medicine",
        "path": {"name": "Dr. Sadanand Kelkar", "qual": "MD (Microbiology)",
                 "regn": "MMC 2002/07/14418", "scrawl": "S Kelkar"},
    },
    "mula": {
        "abbr": "MUL", "acc_style": 0,
        "name": "Mula Riverside Diagnostics",
        "name_local": "मुळा रिव्हरसाइड डायग्नोस्टिक्स",
        "addr": "Shivajinagar, Pune 411005",
        "addr_local": "शिवाजीनगर, पुणे 411005",
        "city": "Pune",
        "phone": "020 2553 7742",
        "accred": "ISO 15189:2022",
        "path": {"name": "Dr. Harshada Pethe", "qual": "MD (Pathology)",
                 "regn": "MMC 2009/03/26617", "scrawl": "H Pethe"},
    },
    "sahyadri": {
        "abbr": "SHY", "acc_style": 3,
        "name": "Sahyadri Collection Point",
        "name_local": "सह्याद्री संकलन केंद्र",
        "addr": "Kothrud, Pune 411038",
        "addr_local": "कोथरूड, पुणे 411038",
        "city": "Pune",
        "phone": "020 2546 9930",
        "accred": "Collection centre. Processed at the Deccan Gymkhana hub.",
        "path": {"name": "Dr. Ajinkya Phadke", "qual": "MBBS, DCP",
                 "regn": "MMC 2016/01/44702", "scrawl": "A Phadke"},
    },
}

HEIGHT_CM = 156.0

VITALS = {
    1: {"weight_kg": 61.2, "bp": "96/58", "spo2": 94, "temp_f": 103.1,
        "context": "Admitted febrile and confused. Dysuria for four days."},
    2: {"weight_kg": 60.8, "bp": "102/62", "spo2": 95, "temp_f": 101.4,
        "context": "Day 2. IV meropenem started on the culture report."},
    3: {"weight_kg": 60.4, "bp": "110/68", "spo2": 97, "temp_f": 99.6,
        "context": "Day 4. Afebrile 24 hours. Coagulation screen repeated."},
    4: {"weight_kg": 60.6, "bp": "116/72", "spo2": 98, "temp_f": 98.6,
        "context": "Day 6. Grouped and screened before a planned transfusion."},
    5: {"weight_kg": 61.0, "bp": "118/74", "spo2": 98, "temp_f": 98.4,
        "context": "Day 8. Admission serology reported. Stepping down to oral."},
    6: {"weight_kg": 61.8, "bp": "120/76", "spo2": 99, "temp_f": 98.2,
        "context": "Day 10. Discharged. Repeat urine culture clear."},
}

REPORTS = [
    # ---- R01 -- the urine that grew it -----------------------------------
    {
        "collected": "2026-03-02 06:40", "reported": "2026-03-04 11:20",
        "lab": "deccan", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "IP No",
        "doctor": RANE, "specimen": "Urine, midstream",
        "alias": 0, "traps": ["abnormal_shaded", "interpretation_block"],
        "interpretation": "Significant growth of Escherichia coli at more than "
                          "10^5 CFU/mL with pyuria. Sensitive to meropenem and "
                          "nitrofurantoin, resistant to ciprofloxacin.",
        "sections": [
            {"panel": "URINE_ROUTINE", "title": 0,
             "drop": ["UR_CASTS", "UR_CRYSTALS", "UR_YEAST", "UR_MUCUS",
                      "UR_UROBIL", "UR_BILI"],
             "row_traps": {"UR_COLOUR": "text_result", "UR_APPEARANCE": "text_result",
                           "UR_PROT": "text_result", "UR_GLU": "text_result",
                           "UR_KET": "text_result", "UR_BLOOD": "text_result",
                           "UR_NITRITE": "text_result", "UR_LE": "text_result",
                           "UR_BACTERIA": "text_result"},
             "values": {"UR_COLOUR": "Hazy yellow", "UR_APPEARANCE": "Turbid",
                        "UR_SPGR": 1.018, "UR_PH": 6.5, "UR_PROT": "1+",
                        "UR_GLU": "Negative", "UR_KET": "Negative",
                        "UR_BLOOD": "2+", "UR_NITRITE": "Positive",
                        "UR_LE": "3+", "UR_RBC": 12, "UR_PUS": 88,
                        "UR_EPITH": 4, "UR_BACTERIA": "Many"}},
            {"panel": "URINE_CULT", "title": 0,
             "row_traps": {"CULT_STATUS": "text_result", "CULT_ORGANISM": "text_result",
                           "CULT_QUANTITY": "text_result", "CULT_ANTIBIOTIC": "text_result",
                           "CULT_SIR": "text_result", "CULT_COMMENT": "text_result"},
             "values": {"CULT_STATUS": "Positive - significant growth",
                        "CULT_ORGANISM": "Escherichia coli",
                        "CULT_COLONY": 100000,
                        "CULT_QUANTITY": "Many",
                        "CULT_ANTIBIOTIC": "Meropenem, Nitrofurantoin, Ciprofloxacin",
                        "CULT_SIR": "S / S / R",
                        "CULT_MIC": 0.5,
                        "CULT_COMMENT": "Pure growth. Repeat after treatment."}},
        ],
    },
    # ---- R02 -- blood culture, the same organism -------------------------
    {
        "collected": "2026-03-03 05:50", "reported": "2026-03-06 09:10",
        "lab": "deccan", "layout_style": "minimal_lines",
        "header_style": "minimal_text_top", "uhid_label": "Hospital No",
        "doctor": RANE, "specimen": "Blood culture, aerobic and anaerobic",
        "alias": 1, "traps": ["no_reference_column"],
        "note": "Two sets drawn from separate sites before antibiotics.",
        "sections": [
            {"panel": "BLOOD_CULT", "title": 0,
             "row_traps": {"CULT_STATUS": "text_result", "CULT_BOTTLE": "text_result",
                           "CULT_ORGANISM": "text_result", "CULT_SIR": "text_result",
                           "CULT_COMMENT": "text_result"},
             "values": {"CULT_STATUS": "Positive",
                        "CULT_BOTTLE": "Aerobic bottle, set 1",
                        "CULT_TTP": 14,
                        "CULT_ORGANISM": "Escherichia coli",
                        "CULT_SIR": "Sensitive to meropenem",
                        "CULT_MIC": 0.25,
                        "CULT_COMMENT": "Same organism as the urine isolate."}},
            {"heading": "Inflammatory markers",
             "rows": [{"code": "CRP", "value": 186.0, "flag": "H"},
                      {"code": "ESR", "value": 68, "flag": "H"},
                      {"code": "WBC", "value": 19200, "flag": "H"}]},
        ],
    },
    # ---- R03 -- coagulation as she becomes septic ------------------------
    {
        "collected": "2026-03-05 07:15", "reported": "2026-03-05 13:40",
        "lab": "mula", "layout_style": "boxed_panels",
        "header_style": "two_line_ribbon", "uhid_label": "Patient ID",
        "doctor": RANE, "specimen": "Citrated plasma",
        "alias": 0, "traps": ["method_sub_line", "abnormal_shaded"],
        "sections": [
            {"panel": "COAGULATION", "title": 0,
             "values": {"PT": 18.4, "INR": 1.62, "APTT": 41.0,
                        "FIBRINOGEN": 520, "THROMBIN_T": 17.2, "D_DIMER": 2.9}},
            {"panel": "PT_INR", "title": 0, "drop": ["PT", "INR"],
             "row_traps": {},
             "values": {"PT_ACTIVITY": 54, "PT_CONTROL": 12.8, "ISI": 1.05}},
        ],
    },
    # ---- R04 -- group and screen before transfusion ----------------------
    {
        "collected": "2026-03-07 10:05", "reported": "2026-03-07 12:30",
        "lab": "deccan", "layout_style": "kv_header_table",
        "header_style": "centred_classic", "uhid_label": "Reg. No",
        "doctor": RANE, "specimen": "Whole blood (EDTA)",
        "alias": 0, "traps": ["no_reference_column"],
        "sections": [
            {"panel": "BLOOD_GROUP_RH", "title": 0,
             "row_traps": {"BLOOD_GROUP": "text_result", "RH_D": "text_result",
                           "AB_SCREEN": "text_result", "AB_ID": "text_result"},
             "values": {"BLOOD_GROUP": "B", "RH_D": "Positive",
                        "AB_SCREEN": "Negative",
                        "AB_ID": "Not required - screen negative"}},
            {"panel": "CBC", "title": 1,
             "drop": ["RDW_SD", "IG_PCT", "NRBC", "PDW", "PLATELETCRIT",
                      "PERIPH_SMEAR", "ANC", "ALC", "MPV"],
             "values": {"HGB": 8.4, "RBC": 3.21, "PCV": 26.8, "MCV": 83.5,
                        "MCH": 26.2, "MCHC": 31.3, "RDW": 15.1, "WBC": 12400,
                        "NEUT_PCT": 78, "LYMPH_PCT": 14, "MONO_PCT": 6,
                        "EOS_PCT": 1, "BASO_PCT": 1, "PLT": 142000}},
        ],
    },
    # ---- R05 -- admission serology ---------------------------------------
    {
        "collected": "2026-03-09 07:00", "reported": "2026-03-09 16:45",
        "lab": "sahyadri", "layout_style": "glossy_marketing",
        "header_style": "logo_left_banner", "uhid_label": "UHID",
        "doctor": RANE, "specimen": "Serum",
        "alias": 0, "traps": ["flag_as_words"],
        "note": "Pre-transfusion screening. Reactive results are repeated in "
                "duplicate before reporting.",
        "sections": [
            {"panel": "HBSAG_PANEL", "title": 0,
             "row_traps": {"HBSAG": "text_result"},
             "values": {"HBSAG": "Non-reactive", "HBSAG_INDEX": 0.12}},
            {"panel": "HIV_PANEL", "title": 0,
             "row_traps": {"HIV_SCREEN": "text_result", "HIV1_AG": "text_result",
                           "HIV1_AB": "text_result", "HIV2_AB": "text_result"},
             "values": {"HIV_SCREEN": "Non-reactive", "HIV1_AG": "Non-reactive",
                        "HIV1_AB": "Non-reactive", "HIV2_AB": "Non-reactive",
                        "HIV_SCO": 0.08}},
            {"panel": "HCV_PANEL", "title": 0,
             "row_traps": {"ANTI_HCV": "text_result", "HCV_RNA": "text_result"},
             "values": {"ANTI_HCV": "Non-reactive", "HCV_INDEX": 0.21,
                        "HCV_RNA": "Not detected"}},
        ],
    },
    # ---- R06 -- discharge, settling --------------------------------------
    {
        "collected": "2026-03-11 06:30", "reported": "2026-03-11 14:10",
        "lab": "mula", "layout_style": "two_column",
        "header_style": "barcode_right", "uhid_label": "Registration No",
        "doctor": RANE, "specimen": "Serum, Urine",
        "alias": 1, "traps": ["sno_column"],
        "sections": [
            {"heading": "Response to treatment",
             "rows": [{"code": "CRP", "value": 18.0},
                      {"code": "ESR", "value": 34, "flag": "H"},
                      {"code": "WBC", "value": 8100}]},
            {"panel": "URINE_CULT", "title": 1,
             "drop": ["CULT_ANTIBIOTIC", "CULT_SIR", "CULT_MIC", "CULT_QUANTITY"],
             "row_traps": {"CULT_STATUS": "text_result", "CULT_ORGANISM": "text_result",
                           "CULT_COMMENT": "text_result"},
             "values": {"CULT_STATUS": "No growth after 48 hours",
                        "CULT_ORGANISM": "No organism isolated",
                        "CULT_COLONY": 0,
                        "CULT_COMMENT": "Sterile. Treatment response confirmed."}},
        ],
    },
]
