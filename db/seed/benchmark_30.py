"""The 30-panel laboratory benchmark, as data.

SOURCE OF TRUTH
    VectorDB_Analysis/Contexta_Lab_30_Panels_Full_Tabular_Benchmark.md, v1.1,
    September 2026. Where this disagrees with anything already in the master,
    this file wins - that was the explicit call. Nothing here is invented: every
    analyte, synonym, unit, result type and panel role is read off that document.

WHY IT IS NOT IN catalog.py
    catalog.py is the corpus vocabulary AND the seed source, and those two jobs
    only coexist while the lists are identical. build.py renders a declared panel
    by iterating PANELS[code]["analytes"] - so adding RDW-SD to CBC there would
    print a new row on all 300 corpus reports and invalidate the sealed answer
    key. The corpus is a fixed measurement; it does not move because the
    vocabulary grew.

    So the DB master is the UNION of the two: catalog.py for what the corpus
    prints, this file for everything the benchmark says we should recognise.
    db/seed/export_master.py merges them.

PANEL MEMBERSHIP IS MANY-TO-MANY
    Section 11 rule 2: one analyte may belong to multiple panels. Sodium is in
    Electrolytes and in RFT; PT is in Coagulation Profile and in PT/INR. So
    membership lives in MEMBERS below, keyed by (panel, analyte), each with its
    own role - an analyte can be core to one panel and optional in another.

ROLE, AND WHY IT MATTERS
    The benchmark states Core / Common / Optional / Derived per analyte per
    panel. We previously computed is_core mechanically as NOT is_derived, which
    called LDL optional because it is calculated - though every lipid report
    prints it. The stated role replaces that guess.

    Mapping: core and common -> is_core TRUE (worth flagging when absent)
             optional and derived -> is_core FALSE.
"""

from __future__ import annotations

# --------------------------------------------------------------------- panels
#: (code, display_name, benchmark section number, is_core)
#: is_core here marks the panel as one of the high-frequency groups, which is a
#: different question from whether an ANALYTE is core to it.
PANELS: list[tuple[str, str, int, bool]] = [
    ("CBC",             "Complete Blood Count (CBC)",        1,  True),
    ("LFT",             "Liver Function Test (LFT)",         2,  True),
    ("KFT",             "Renal Function Test (RFT)",         3,  True),
    ("LIPID",           "Lipid Profile",                     4,  True),
    ("HBA1C_PANEL",     "HbA1c",                             5,  True),
    ("GLUCOSE",         "Blood Glucose",                     6,  True),
    ("URINE_ROUTINE",   "Urine Routine & Microscopy",        7,  True),
    ("THYROID",         "Thyroid Profile",                   8,  True),
    ("ELECTROLYTES",    "Serum Electrolytes",                9,  True),
    ("CRP_PANEL",       "C-Reactive Protein",               10,  True),
    ("ESR_PANEL",       "ESR",                              11,  True),
    ("IRON",            "Iron Profile",                     12,  True),
    ("B12_PANEL",       "Vitamin B12",                      13,  True),
    ("VIT_D_PANEL",     "Vitamin D",                        14,  True),
    ("CALCIUM_PANEL",   "Calcium",                          15,  True),
    ("URIC_ACID_PANEL", "Uric Acid",                        16,  True),
    ("AMYLASE_LIPASE",  "Amylase / Lipase",                 17,  False),
    ("COAGULATION",     "Coagulation Profile",              18,  False),
    ("PT_INR",          "PT / INR",                         19,  False),
    ("APTT_PANEL",      "aPTT",                             20,  False),
    ("BLOOD_GROUP_RH",  "Blood Group & Rh",                 21,  True),
    ("PSA_PANEL",       "PSA",                              22,  False),
    ("HCG_PANEL",       "Pregnancy / Beta hCG",             23,  False),
    ("TROPONIN",        "Cardiac Troponin",                 24,  False),
    ("FERRITIN_PANEL",  "Ferritin",                         25,  False),
    ("URINE_CULT",      "Urine Culture",                    26,  False),
    ("BLOOD_CULT",      "Blood Culture",                    27,  False),
    ("HBSAG_PANEL",     "HBsAg",                            28,  False),
    ("HIV_PANEL",       "HIV 1/2",                          29,  False),
    ("HCV_PANEL",       "HCV Antibody",                     30,  False),
]

#: Titles a panel arrives under, beyond its display name.
PANEL_ALIASES: dict[str, list[str]] = {
    "HBA1C_PANEL":     ["HbA1c", "Glycated Haemoglobin", "Glycosylated Hemoglobin", "A1c"],
    "GLUCOSE":         ["Blood Glucose", "Blood Sugar", "Glucose Studies", "OGTT",
                        "Glucose Tolerance Test"],
    "CRP_PANEL":       ["CRP", "C Reactive Protein", "C-Reactive Protein Test"],
    "ESR_PANEL":       ["ESR", "Erythrocyte Sedimentation Rate", "Sed Rate"],
    "B12_PANEL":       ["Vitamin B12", "B12", "Cobalamin"],
    "VIT_D_PANEL":     ["Vitamin D", "Vitamin D Test", "25 OH Vitamin D"],
    "CALCIUM_PANEL":   ["Calcium", "Serum Calcium", "Calcium Studies"],
    "URIC_ACID_PANEL": ["Uric Acid", "Serum Uric Acid"],
    "AMYLASE_LIPASE":  ["Amylase", "Lipase", "Amylase and Lipase", "Pancreatic Profile"],
    "PT_INR":          ["PT INR", "PT/INR", "Prothrombin Time with INR", "PT with INR"],
    "APTT_PANEL":      ["aPTT", "APTT", "PTT", "Activated Partial Thromboplastin Time"],
    "BLOOD_GROUP_RH":  ["Blood Group", "Blood Grouping", "ABO and Rh", "Blood Group and Rh Typing",
                        "Type and Screen"],
    "PSA_PANEL":       ["PSA", "Prostate Specific Antigen"],
    "HCG_PANEL":       ["Beta hCG", "BHCG", "Pregnancy Test", "Serum Pregnancy Test", "UPT"],
    "TROPONIN":        ["Troponin", "Cardiac Troponin", "Trop I", "Trop T", "hs Troponin"],
    "FERRITIN_PANEL":  ["Ferritin", "Serum Ferritin"],
    "URINE_CULT":      ["Urine Culture", "Urine C/S", "Urine Culture and Sensitivity",
                        "Urine C and S"],
    "BLOOD_CULT":      ["Blood Culture", "Blood C/S", "Blood Culture and Sensitivity"],
    "HBSAG_PANEL":     ["HBsAg", "Hepatitis B Surface Antigen", "Australia Antigen"],
    "HIV_PANEL":       ["HIV", "HIV 1 and 2", "HIV Ag Ab", "HIV Screening"],
    "HCV_PANEL":       ["Anti HCV", "HCV Antibody", "Hepatitis C Antibody"],
    "COAGULATION":     ["Coagulation Profile", "Coagulogram", "Clotting Profile"],
}

# ------------------------------------------------------------------- analytes
#: (code, display_name, [synonyms], unit, result_type, is_calculated, specimen)
#:
#: result_type is the benchmark's own vocabulary (section 1), widened from the
#: numeric/text pair the schema allowed before. Only analytes NOT already in
#: catalog.py appear here - export_master.py unions the two and the existing
#: definition wins on code, so nothing already seeded is restated or changed.
ANALYTES: list[tuple[str, str, list[str], str, str, bool, str]] = [
    # --- 1. CBC additions -------------------------------------------------
    ("RDW_SD",      "RDW-SD", ["RDW SD", "Red Cell Distribution Width SD"],
                    "fL", "numeric", False, "Whole blood"),
    ("IG_PCT",      "Immature Granulocytes", ["IG", "Immature Granulocyte Percentage"],
                    "%", "numeric", False, "Whole blood"),
    ("NRBC",        "Nucleated RBC", ["NRBC", "Nucleated Red Blood Cells"],
                    "%", "numeric", False, "Whole blood"),
    ("PDW",         "Platelet Distribution Width", ["PDW"],
                    "fL", "numeric", False, "Whole blood"),
    ("PLATELETCRIT", "Plateletcrit", ["PCT", "Plateletcrit"],
                    "%", "numeric", False, "Whole blood"),

    # --- 2. LFT additions -------------------------------------------------
    ("LDH",         "Lactate Dehydrogenase", ["LDH", "Lactate dehydrogenase", "LD"],
                    "U/L", "numeric", False, "Serum/plasma"),

    # --- 3. RFT additions -------------------------------------------------
    ("HCO3",        "Bicarbonate", ["HCO3", "Bicarbonate", "Total CO2", "TCO2", "CO2"],
                    "mmol/L", "numeric", False, "Serum/plasma"),
    ("ANION_GAP",   "Anion Gap", ["AG", "Anion Gap"],
                    "mmol/L", "numeric", True, "Serum/plasma"),

    # --- 5/6. Glycaemic ---------------------------------------------------
    ("HBA1C_IFCC",  "HbA1c (IFCC)", ["HbA1c IFCC", "A1c IFCC"],
                    "mmol/mol", "numeric", False, "Whole blood"),
    ("OGTT_F",      "OGTT Fasting Glucose", ["OGTT Fasting", "GTT Fasting"],
                    "mg/dL", "numeric", False, "Plasma"),
    ("OGTT_1H",     "OGTT 1-hour Glucose", ["OGTT 1 hr", "1 hour glucose", "GTT 1 hour"],
                    "mg/dL", "numeric", False, "Plasma"),
    ("OGTT_2H",     "OGTT 2-hour Glucose", ["OGTT 2 hr", "2 hour glucose", "GTT 2 hour"],
                    "mg/dL", "numeric", False, "Plasma"),
    ("OGTT_3H",     "OGTT 3-hour Glucose", ["OGTT 3 hr", "3 hour glucose", "GTT 3 hour"],
                    "mg/dL", "numeric", False, "Plasma"),

    # --- 7. Urinalysis: chemistry then microscopy -------------------------
    ("UR_APPEARANCE", "Urine Appearance", ["Appearance", "Turbidity", "Clarity"],
                    "", "coded", False, "Urine"),
    ("UR_BLOOD",    "Urine Blood", ["Blood", "Occult Blood", "Haemoglobin (urine)"],
                    "", "ordinal", False, "Urine"),
    ("UR_BILI",     "Urine Bilirubin", ["Bilirubin (urine)", "Urine Bilirubin"],
                    "", "qualitative", False, "Urine"),
    ("UR_UROBIL",   "Urobilinogen", ["Urobilinogen", "Uro"],
                    "mg/dL", "numeric", False, "Urine"),
    ("UR_NITRITE",  "Urine Nitrite", ["Nitrite", "Nitrites"],
                    "", "qualitative", False, "Urine"),
    ("UR_LE",       "Leukocyte Esterase", ["LE", "Leucocyte Esterase", "Leukocyte Esterase"],
                    "", "ordinal", False, "Urine"),
    ("UR_BACTERIA", "Urine Bacteria", ["Bacteria"],
                    "", "ordinal", False, "Urine"),
    ("UR_CASTS",    "Urine Casts", ["Casts", "Hyaline Casts", "Granular Casts"],
                    "/LPF", "structured", False, "Urine"),
    ("UR_CRYSTALS", "Urine Crystals", ["Crystals", "Calcium Oxalate Crystals"],
                    "", "structured", False, "Urine"),
    ("UR_YEAST",    "Urine Yeast", ["Yeast", "Yeast Cells", "Budding Yeast"],
                    "", "qualitative", False, "Urine"),
    ("UR_MUCUS",    "Urine Mucus", ["Mucus", "Mucus Threads"],
                    "", "qualitative", False, "Urine"),

    # --- 8. Thyroid additions ---------------------------------------------
    ("ANTI_TG",     "Anti-Thyroglobulin Antibody", ["TgAb", "Anti TG", "Anti-Thyroglobulin",
                                                    "Thyroglobulin Antibody"],
                    "IU/mL", "numeric", False, "Serum"),
    ("TRAB",        "TSH Receptor Antibody", ["TRAb", "TSH Receptor Antibody", "TSH-R Ab"],
                    "IU/L", "numeric", False, "Serum"),

    # --- 12. Iron addition -------------------------------------------------
    ("TRANSFERRIN", "Transferrin", ["Transferrin", "Serum Transferrin"],
                    "mg/dL", "numeric", False, "Serum"),

    # --- 14/15. Vitamin D and calcium --------------------------------------
    ("VIT_D_125",   "1,25-Dihydroxy Vitamin D", ["1,25 (OH)2 D", "1,25-Dihydroxy Vitamin D",
                                                 "Calcitriol"],
                    "pg/mL", "numeric", False, "Serum"),
    ("CA_CORRECTED", "Corrected Calcium", ["Corrected Calcium", "Albumin-corrected Calcium"],
                    "mg/dL", "numeric", True, "Serum"),

    # --- 16. Uric acid -----------------------------------------------------
    ("UA_URINE",    "Urine Uric Acid", ["Urinary Uric Acid", "Urine Urate", "24 hr Uric Acid"],
                    "mg/24h", "numeric", False, "Urine"),

    # --- 17. Amylase / lipase ----------------------------------------------
    ("AMYLASE_T",   "Total Amylase", ["Amylase", "Serum Amylase", "Total Amylase"],
                    "U/L", "numeric", False, "Serum"),
    ("AMYLASE_P",   "Pancreatic Amylase", ["P-Amylase", "Pancreatic Amylase"],
                    "U/L", "numeric", False, "Serum"),
    ("AMYLASE_S",   "Salivary Amylase", ["S-Amylase", "Salivary Amylase"],
                    "U/L", "numeric", False, "Serum"),
    ("LIPASE",      "Lipase", ["Lipase", "Serum Lipase"],
                    "U/L", "numeric", False, "Serum"),

    # --- 18/19/20. Coagulation --------------------------------------------
    ("FIBRINOGEN",  "Fibrinogen", ["Fibrinogen", "Factor I"],
                    "mg/dL", "numeric", False, "Citrated plasma"),
    ("THROMBIN_T",  "Thrombin Time", ["TT", "Thrombin Time"],
                    "seconds", "numeric", False, "Citrated plasma"),
    ("PT_ACTIVITY", "PT Activity", ["Prothrombin Activity", "PT Activity"],
                    "%", "numeric", True, "Citrated plasma"),
    ("PT_CONTROL",  "PT Control", ["Control PT", "PT Control", "Normal Control"],
                    "seconds", "numeric", False, "Citrated plasma"),
    ("ISI",         "ISI", ["ISI", "International Sensitivity Index"],
                    "", "numeric", False, "Assay metadata"),
    ("APTT_RATIO",  "aPTT Ratio", ["aPTT Ratio", "APTT Ratio", "Patient/Control Ratio"],
                    "", "numeric", True, "Citrated plasma"),
    ("APTT_CONTROL", "aPTT Control", ["Control aPTT", "APTT Control"],
                    "seconds", "numeric", False, "Citrated plasma"),

    # --- 21. Blood group ---------------------------------------------------
    ("RH_D",        "Rh(D) Type", ["Rh Type", "Rh Factor", "Rh(D)", "RhD"],
                    "", "coded", False, "Whole blood"),
    ("AB_SCREEN",   "Antibody Screen", ["Red Cell Antibody Screen", "Antibody Screening",
                                        "Indirect Coombs"],
                    "", "qualitative", False, "Plasma/serum"),
    ("AB_ID",       "Antibody Identification", ["Antibody Identification", "Antibody ID"],
                    "", "coded", False, "Plasma/serum"),

    # --- 22. PSA -----------------------------------------------------------
    ("PSA_FREE",    "Free PSA", ["fPSA", "Free PSA"],
                    "ng/mL", "numeric", False, "Serum"),
    ("PSA_PCT_FREE", "Percent Free PSA", ["%fPSA", "Percent Free PSA", "Free/Total PSA"],
                    "%", "numeric", True, "Serum"),

    # --- 23. hCG -----------------------------------------------------------
    ("HCG_QUAL",    "hCG (Qualitative)", ["Pregnancy Test", "UPT", "Urine Pregnancy Test",
                                          "Qualitative hCG"],
                    "", "qualitative", False, "Urine or serum"),
    ("HCG_QUANT",   "Beta hCG (Quantitative)", ["Beta hCG", "BHCG", "Quantitative hCG",
                                                "Serum Beta hCG"],
                    "mIU/mL", "numeric", False, "Serum"),

    # --- 24. Troponin ------------------------------------------------------
    ("TROP_I_HS",   "High-sensitivity Troponin I", ["hs-cTnI", "hs Troponin I",
                                                    "High sensitivity Troponin I"],
                    "ng/L", "numeric", False, "Serum/plasma"),
    ("TROP_T",      "Troponin T", ["cTnT", "Troponin T"],
                    "ng/L", "numeric", False, "Serum/plasma"),
    ("TROP_T_HS",   "High-sensitivity Troponin T", ["hs-cTnT", "hs Troponin T",
                                                    "High sensitivity Troponin T"],
                    "ng/L", "numeric", False, "Serum/plasma"),
    ("TROP_99TH",   "Assay 99th Percentile", ["99th Percentile", "Upper Reference Limit",
                                              "Decision Limit"],
                    "", "numeric", False, "Assay metadata"),

    # --- 26/27. Microbiology ----------------------------------------------
    # Stored as observations now so a culture report can be read at all. The
    # structured isolate/susceptibility tables of benchmark section 7 are a
    # separate pass; these are deliberately the flat form of the same facts.
    ("CULT_STATUS", "Culture Status", ["Culture", "Growth", "Culture Result",
                                       "No Growth", "Culture Status"],
                    "", "qualitative", False, "Culture"),
    ("CULT_ORGANISM", "Organism Isolated", ["Organism", "Isolate", "Organism Isolated",
                                            "Organism Identification"],
                    "", "organism", False, "Culture"),
    ("CULT_COLONY", "Colony Count", ["Colony Count", "CFU Count", "CFU/mL"],
                    "CFU/mL", "numeric", False, "Urine"),
    ("CULT_QUANTITY", "Organism Quantity", ["Growth Quantity", "Organism Quantity"],
                    "", "ordinal", False, "Culture"),
    ("CULT_ANTIBIOTIC", "Antibiotic Tested", ["Antibiotic", "Drug Tested", "Antimicrobial"],
                    "", "coded", False, "Culture isolate"),
    ("CULT_SIR",    "Susceptibility", ["Sensitivity", "S/I/R", "Susceptibility",
                                       "Sensitive/Intermediate/Resistant"],
                    "", "susceptibility", False, "Culture isolate"),
    ("CULT_MIC",    "MIC", ["MIC", "Minimum Inhibitory Concentration"],
                    "mcg/mL", "numeric", False, "Culture isolate"),
    ("CULT_COMMENT", "Culture Comment", ["Culture Comment", "Interpretive Comment"],
                    "", "narrative", False, "Culture"),
    ("CULT_BOTTLE", "Bottle / Set", ["Aerobic Bottle", "Anaerobic Bottle", "Bottle", "Set"],
                    "", "coded", False, "Blood culture"),
    ("CULT_TTP",    "Time to Positivity", ["TTP", "Time to Positivity"],
                    "hours", "numeric", False, "Blood culture"),

    # --- 28/29/30. Serology, with the assay indices the benchmark insists on
    ("HBSAG_INDEX", "HBsAg Index (S/CO)", ["HBsAg Index", "S/CO", "COI", "Signal to Cutoff"],
                    "", "numeric", False, "Serum/plasma"),
    ("HIV_SCREEN",  "HIV Ag/Ab Screen", ["HIV Ag Ab", "HIV 1 and 2 Screen", "HIV Combo",
                                         "HIV Ag/Ab"],
                    "", "reactive", False, "Serum/plasma"),
    ("HIV1_AG",     "HIV-1 Antigen", ["p24 Antigen", "HIV-1 Ag", "HIV 1 Antigen"],
                    "", "reactive", False, "Serum/plasma"),
    ("HIV1_AB",     "HIV-1 Antibody", ["HIV-1 Ab", "HIV 1 Antibody"],
                    "", "reactive", False, "Serum/plasma"),
    ("HIV2_AB",     "HIV-2 Antibody", ["HIV-2 Ab", "HIV 2 Antibody"],
                    "", "reactive", False, "Serum/plasma"),
    ("HIV_SCO",     "HIV Signal/Cutoff Index", ["HIV S/CO", "HIV COI", "HIV Index"],
                    "", "numeric", False, "Serum/plasma"),
    ("HCV_INDEX",   "HCV Ab Index (S/CO)", ["HCV Index", "HCV S/CO", "HCV COI"],
                    "", "numeric", False, "Serum/plasma"),
    ("HCV_RNA",     "HCV RNA", ["HCV RNA", "HCV PCR", "HCV NAT", "HCV Viral Load"],
                    "IU/mL", "detected", False, "Plasma/serum"),
]

# ----------------------------------------------------------------- membership
#: (panel_code, analyte_code, role) where role is the benchmark's Panel Role.
#: core | common -> is_core TRUE.  optional | derived -> is_core FALSE.
#:
#: Many-to-many on purpose: Sodium appears under ELECTROLYTES and KFT, PT under
#: COAGULATION and PT_INR, Ferritin under IRON and FERRITIN_PANEL. Section 3 of
#: the benchmark lists exactly these cross-panel observations.
MEMBERS: list[tuple[str, str, str]] = []


def _add(panel: str, rows: str) -> None:
    """rows is "CODE:role, CODE:role" - compact because there are 300 of them."""
    for item in rows.replace("\n", " ").split(","):
        item = item.strip()
        if not item:
            continue
        code, _, role = item.partition(":")
        MEMBERS.append((panel, code.strip(), (role or "core").strip()))


_add("CBC", """
    HGB:core, RBC:core, PCV:core, MCV:core, MCH:core, MCHC:core, RDW:common,
    RDW_SD:optional, WBC:core, NEUT_PCT:core, LYMPH_PCT:core, MONO_PCT:core,
    EOS_PCT:core, BASO_PCT:core, IG_PCT:optional, NRBC:optional, PLT:core,
    MPV:common, PDW:optional, PLATELETCRIT:optional, PERIPH_SMEAR:optional,
    ANC:optional, ALC:optional""")

_add("LFT", """
    BILI_T:core, BILI_D:core, BILI_I:common, AST:core, ALT:core, ALP:core,
    PROT_T:core, ALB:core, GLOB:common, AG_RATIO:common, GGT:common,
    LDH:optional""")

_add("KFT", """
    CREAT:core, UREA:core, BUN:common, NA:core, K:core, CL:core, HCO3:common,
    CA:common, EGFR:common, PHOS:optional, ALB:optional, UA:optional,
    ANION_GAP:derived""")

_add("LIPID", """
    CHOL:core, HDL:core, LDL:core, TRIG:core, VLDL:common, NON_HDL:common,
    CHOL_HDL_RATIO:optional, LDL_HDL_RATIO:optional""")

_add("HBA1C_PANEL", "HBA1C:core, HBA1C_IFCC:optional, EAG:derived")

_add("GLUCOSE", """
    GLU_F:core, GLU_R:core, GLU_PP:core, OGTT_F:optional, OGTT_1H:optional,
    OGTT_2H:optional, OGTT_3H:optional""")

_add("URINE_ROUTINE", """
    UR_COLOUR:core, UR_APPEARANCE:core, UR_SPGR:core, UR_PH:core, UR_PROT:core,
    UR_GLU:core, UR_KET:common, UR_BLOOD:common, UR_BILI:common,
    UR_UROBIL:common, UR_NITRITE:common, UR_LE:common, UR_RBC:core,
    UR_PUS:core, UR_EPITH:common, UR_BACTERIA:optional, UR_CASTS:optional,
    UR_CRYSTALS:optional, UR_YEAST:optional, UR_MUCUS:optional""")

_add("THYROID", """
    TSH:core, FT4:core, FT3:common, T3_TOTAL:optional, T4_TOTAL:optional,
    ANTI_TPO:optional, ANTI_TG:optional, TRAB:optional""")

_add("ELECTROLYTES", """
    NA:core, K:core, CL:core, HCO3:common, ANION_GAP:derived, CA:optional,
    MG:optional, PHOS:optional""")

_add("CRP_PANEL", "CRP:core, HS_CRP:optional")
_add("ESR_PANEL", "ESR:core")

_add("IRON", """
    IRON:core, TIBC:core, TRANSFERRIN:common, TSAT:common, UIBC:common,
    FERRITIN:common""")

_add("B12_PANEL", "VIT_B12:core")
_add("VIT_D_PANEL", "VIT_D:core, VIT_D_125:optional")
_add("CALCIUM_PANEL", "CA:core, CA_ION:optional, CA_CORRECTED:derived")
_add("URIC_ACID_PANEL", "UA:core, UA_URINE:optional")
_add("AMYLASE_LIPASE", "AMYLASE_T:core, LIPASE:core, AMYLASE_P:optional, AMYLASE_S:optional")

_add("COAGULATION", """
    PT:core, INR:core, APTT:core, FIBRINOGEN:common, THROMBIN_T:optional,
    D_DIMER:optional""")

_add("PT_INR", """
    PT:core, INR:core, PT_ACTIVITY:optional, PT_CONTROL:optional, ISI:optional""")

_add("APTT_PANEL", "APTT:core, APTT_RATIO:optional, APTT_CONTROL:optional")

_add("BLOOD_GROUP_RH", """
    BLOOD_GROUP:core, RH_D:core, AB_SCREEN:optional, AB_ID:optional""")

_add("PSA_PANEL", "PSA:core, PSA_FREE:optional, PSA_PCT_FREE:derived")
_add("HCG_PANEL", "HCG_QUAL:core, HCG_QUANT:core")

_add("TROPONIN", """
    TROP_I:core, TROP_I_HS:core, TROP_T:core, TROP_T_HS:core, TROP_99TH:optional""")

_add("FERRITIN_PANEL", "FERRITIN:core")

_add("URINE_CULT", """
    CULT_STATUS:core, CULT_ORGANISM:common, CULT_COLONY:common,
    CULT_QUANTITY:optional, CULT_ANTIBIOTIC:optional, CULT_SIR:optional,
    CULT_MIC:optional, CULT_COMMENT:optional""")

_add("BLOOD_CULT", """
    CULT_STATUS:core, CULT_BOTTLE:common, CULT_TTP:optional,
    CULT_ORGANISM:common, CULT_SIR:optional, CULT_MIC:optional,
    CULT_COMMENT:optional""")

_add("HBSAG_PANEL", "HBSAG:core, HBSAG_INDEX:optional")

_add("HIV_PANEL", """
    HIV_SCREEN:core, HIV1_AG:optional, HIV1_AB:optional, HIV2_AB:optional,
    HIV_SCO:optional""")

_add("HCV_PANEL", "ANTI_HCV:core, HCV_INDEX:optional, HCV_RNA:optional")


#: Roles the benchmark uses, and how they land on the schema's boolean.
CORE_ROLES = frozenset({"core", "common"})


def is_core(role: str) -> bool:
    """Core and Common are worth flagging when absent; Optional and Derived are not.

    This replaces is_core = NOT is_derived, which called LDL optional because it
    is calculated - though every lipid report prints it. The benchmark states
    the role per panel, so an analyte can be core to one panel and optional in
    another, which the mechanical rule could never express.
    """
    return role in CORE_ROLES
