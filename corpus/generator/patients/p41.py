"""Patient 41 - DEMO. Three reports built to show the product, not to measure it.

Male, 54, Pune. A diabetic health check in March, a single follow-up HbA1c in
June, and an old-looking typed report from the September review. HbA1c runs
8.2 -> 7.4 -> 6.8 across the three, so the trend chart has a real line with a
real clinical meaning: control improving.

WHAT EACH ONE IS FOR
    R01  multi-panel. Five panels on one page, so the coverage chips have
         something to show. It deliberately does NOT contain a thyroid profile
         and is missing MCHC and MPV from the CBC - the gap is the point. Order a
         thyroid profile in the drawer and the system says the lab never reported
         it, which is the whole argument for the feature.

    R02  single panel. One small clean report, everything present, every chip
         green. The contrast with R01 is the demonstration.

         kv_header_table and not boxed_panels or minimal_lines: on a five-row
         report those two let the signature block - "Tested by: A. Jadhav
         (DMLT)" - be read as two more results, because it is the largest
         text block left on the page. Measured, not guessed: 7 rows with 2
         uncoded against 5 with 0.

    R03  old-looking. A ruled ledger, the shape a clinic register has had for
         decades, still carrying a text layer. It LOOKS like the worst thing a
         clinic will hand you and reads perfectly, which is the point.

         ledger_ruled and not typewriter_manual, carbon_copy or
         dot_matrix_pinfeed: measured, those three return the diabetes block with
         no values at all - four rows recognised and empty. ledger_ruled returns
         twelve rows, every one coded, every one with its number.

WHY NOT DAMAGED
    Any CSS filter makes the browser rasterise the page, and a rasterised page has
    no text layer at all - it can only be read by OCR. Impressive, and it needs
    the worker, an API key, the internet and six seconds in front of an audience.
    An old TYPEFACE costs none of that and looks the same on a projector.

DISPOSABLE
    Demo data. Nothing measures against it and nothing should: the layouts were
    chosen because they score well, which is exactly the bias a benchmark exists
    to avoid. Delete the tree and the seed when the presentation is over.
"""

from __future__ import annotations

DEMO = True

PATIENT = {
    "number": 41,
    "name": "Ramesh Iyer",
    "sex": "M",
    "dob": "1972-04-18",
    "uhid": "DEM/100245",
    "department": "General Medicine",
    "city": "Pune",
    "age_at_first": 53,
    "tracked": ["HBA1C"],
    "brief": "Type 2 diabetes - control improving over three visits",
}


def check_arc(series):
    a1c = [v for _, v in series["HBA1C"]]
    fails = []
    if not a1c == sorted(a1c, reverse=True):
        fails.append(f"HbA1c should improve across the three visits: {a1c}")
    if not a1c[0] > 8.0:
        fails.append(f"should open poorly controlled, HbA1c {a1c[0]}")
    if not a1c[-1] < 7.0:
        fails.append(f"should end near target, HbA1c {a1c[-1]}")
    return fails


DESAI = "Dr. Anjali Desai"

LABS = {
    "sahyadri": {
        "abbr": "SPL", "acc_style": 1,
        "name": "Sahyadri Pathology Laboratory",
        "name_local": "सह्याद्री पॅथॉलॉजी प्रयोगशाळा",
        "addr": "Erandwane, Pune 411004",
        "addr_local": "एरंडवणे, पुणे 411004",
        "city": "Pune",
        "phone": "020 2541 7700",
        "accred": "NABL MC-5521 | ISO 15189:2022",
        "path": {"name": "Dr. Vikram Joshi", "qual": "MD (Pathology)",
                 "regn": "MMC 2006/05/21184", "scrawl": "V Joshi"},
    },
    "shivaji": {
        "abbr": "SNL", "acc_style": 0,
        "name": "Shivajinagar Diagnostic Centre",
        "name_local": "शिवाजीनगर डायग्नोस्टिक सेंटर",
        "addr": "Shivajinagar, Pune 411005",
        "addr_local": "शिवाजीनगर, पुणे 411005",
        "city": "Pune",
        "phone": "020 2553 1142",
        "accred": "ISO 15189:2022",
        "path": {"name": "Dr. Sneha Kulkarni", "qual": "MD, DNB (Pathology)",
                 "regn": "MMC 2011/02/33907", "scrawl": "S Kulkarni"},
    },
}

HEIGHT_CM = 172.0

VITALS = {
    1: {"weight_kg": 84.6, "bp": "142/88", "spo2": 97, "temp_f": 98.4,
        "context": "Annual health check. Diabetic six years, control slipping."},
    2: {"weight_kg": 81.2, "bp": "134/84", "spo2": 98, "temp_f": 98.2,
        "context": "Three months on the revised regimen. Walking daily."},
    3: {"weight_kg": 78.4, "bp": "126/80", "spo2": 98, "temp_f": 98.6,
        "context": "Six-month review. Weight down six kilos, HbA1c at target."},
}

REPORTS = [
    # ---- R01 -- the multi-panel health check ---------------------------------
    {
        "collected": "2026-03-10 08:20", "reported": "2026-03-10 17:40",
        "lab": "sahyadri", "layout_style": "clean_table",
        "header_style": "hospital_department_block", "uhid_label": "UHID",
        "doctor": DESAI, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 0, "traps": ["abnormal_shaded", "interpretation_block"],
        "interpretation": "Poorly controlled type 2 diabetes with dyslipidaemia. "
                          "Intensify therapy, repeat HbA1c in three months.",
        "sections": [
            # MCHC and MPV deliberately absent, so the CBC chip is amber and the
            # drawer can name exactly which two tests did not come back.
            {"panel": "CBC", "title": 0,
             # MCHC and MPV withheld on purpose - the gap is the demonstration.
             # Everything else core or common is printed, so the panel reads as
             # a real complete blood count with two tests the lab did not report.
             "drop": ["MCHC", "MPV", "RDW_SD", "IG_PCT", "NRBC", "PDW",
                      "PLATELETCRIT", "PERIPH_SMEAR", "ANC", "ALC"],
             "values": {"HGB": 14.2, "RBC": 4.86, "PCV": 43.1, "MCV": 88.7,
                        "MCH": 29.2, "RDW": 13.4, "WBC": 7800, "NEUT_PCT": 58,
                        "LYMPH_PCT": 32, "MONO_PCT": 6, "EOS_PCT": 3,
                        "BASO_PCT": 1, "PLT": 262000}},
            {"panel": "DIABETES", "title": 0, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 168, "GLU_PP": 254, "HBA1C": 8.2}},
            {"panel": "LIPID", "title": 0,
             "values": {"CHOL": 238, "TRIG": 265, "HDL": 36}},
        ],
    },
    # ---- R02 -- the single panel, everything present -------------------------
    {
        "collected": "2026-06-15 08:05", "reported": "2026-06-15 14:20",
        "lab": "shivaji", "layout_style": "kv_header_table",
        "header_style": "two_line_ribbon", "uhid_label": "Patient ID",
        "doctor": DESAI, "specimen": "Whole blood (EDTA), Serum",
        "alias": 1, "traps": ["abnormal_shaded"],
        "sections": [
            {"panel": "DIABETES", "title": 1, "drop": ["INSULIN_F"],
             "values": {"GLU_F": 132, "GLU_PP": 186, "GLU_R": 149, "HBA1C": 7.4}},
        ],
    },
    # ---- R03 -- the old-looking one, text layer intact -----------------------
    {
        "collected": "2026-09-16 07:50", "reported": "2026-09-16 16:10",
        "lab": "shivaji", "layout_style": "ledger_ruled",
        "header_style": "minimal_text_top", "uhid_label": "Reg. No",
        "doctor": DESAI, "specimen": "Serum, Whole blood (EDTA)",
        "alias": 2, "traps": ["no_reference_column"],
        "note": "Typed copy issued at the collection counter. Carbon retained "
                "at the laboratory.",
        "sections": [
            {"panel": "DIABETES", "title": 0, "drop": ["GLU_R", "INSULIN_F"],
             "values": {"GLU_F": 108, "GLU_PP": 142, "HBA1C": 6.8}},
            {"panel": "LIPID", "title": 1,
             "values": {"CHOL": 176, "TRIG": 148, "HDL": 46}},
        ],
    },
]
