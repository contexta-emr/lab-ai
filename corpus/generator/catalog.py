"""Analyte vocabulary, printed-label aliases, reference ranges and derived maths.

The printed label is deliberately *not* the code: a lab prints "S. CREATININE" where
Contexta calls it CREAT, and matching those spellings is what the corpus tests. Every
analyte therefore carries several aliases, rotated by report index so the same patient's
15 reports spell the same test at least three ways.

Derived values are computed here from the already-rounded printed numbers, so that
VLDL = TRIG/5 and the rest hold exactly as printed rather than only before rounding.
"""

from __future__ import annotations

INT = "{:.0f}"


def A(labels: str, unit: str, ref: str, fmt: str = "{:.1f}") -> dict:
    return {"labels": [s.strip() for s in labels.split("|")], "unit": unit, "ref": ref, "fmt": fmt}


ANALYTES: dict[str, dict] = {
    # --- CBC -------------------------------------------------------------------
    "HGB": A("Haemoglobin | Hemoglobin (Hb) | HAEMOGLOBIN | Hb", "g/dL", "13.0 - 17.0"),
    "RBC": A("RBC Count | Total RBC | Red Blood Cell Count | R.B.C.", "mil/uL", "4.5 - 5.5", "{:.2f}"),
    "PCV": A("PCV | Haematocrit (PCV) | HCT | Packed Cell Volume", "%", "40 - 50"),
    "MCV": A("MCV | M.C.V. | Mean Corpuscular Volume", "fL", "83 - 101"),
    "MCH": A("MCH | M.C.H. | Mean Corpuscular Hb", "pg", "27 - 32"),
    "MCHC": A("MCHC | M.C.H.C. | Mean Corp. Hb Concn.", "g/dL", "31.5 - 34.5"),
    "RDW": A("RDW-CV | RDW | R.D.W.", "%", "11.6 - 14.0"),
    "WBC": A("Total WBC Count | WBC Count | TLC | Total Leucocyte Count", "/uL", "4000 - 10000", INT),
    "NEUT_PCT": A("Neutrophils | NEUTROPHILS | Polymorphs | Neutrophil %", "%", "40 - 80", INT),
    "LYMPH_PCT": A("Lymphocytes | LYMPHOCYTES | Lymphocyte % | Lymph", "%", "20 - 40", INT),
    "MONO_PCT": A("Monocytes | MONOCYTES | Monocyte %", "%", "2 - 10", INT),
    "EOS_PCT": A("Eosinophils | EOSINOPHILS | Eosinophil %", "%", "1 - 6", INT),
    "BASO_PCT": A("Basophils | BASOPHILS | Basophil %", "%", "0 - 2", INT),
    "ANC": A("Absolute Neutrophil Count | ANC | Abs. Neutrophil Count", "/uL", "2000 - 7000", INT),
    "ALC": A("Absolute Lymphocyte Count | ALC | Abs. Lymphocyte Count", "/uL", "1000 - 3000", INT),
    "PLT": A("Platelet Count | PLATELET COUNT | Platelets | Plt Count", "/uL", "150000 - 410000", INT),
    "MPV": A("MPV | M.P.V. | Mean Platelet Volume", "fL", "6.5 - 12.0"),
    # --- LIPID -----------------------------------------------------------------
    "CHOL": A("Total Cholesterol | Cholesterol, Total | CHOLESTEROL - TOTAL | S. Cholesterol", "mg/dL", "< 200", INT),
    "TRIG": A("Triglycerides | TRIGLYCERIDES | Triglyceride, Serum | S. Triglycerides", "mg/dL", "< 150", INT),
    "HDL": A("HDL Cholesterol | HDL - Cholesterol | H.D.L. Cholesterol | Cholesterol, HDL", "mg/dL", "40 - 60", INT),
    "LDL": A("LDL Cholesterol | LDL - Cholesterol (Calc.) | L.D.L. Cholesterol | Cholesterol, LDL", "mg/dL", "< 100", INT),
    "VLDL": A("VLDL Cholesterol | VLDL - Cholesterol (Calc.) | V.L.D.L. Cholesterol", "mg/dL", "5 - 40", INT),
    "NON_HDL": A("Non-HDL Cholesterol | Non HDL Cholesterol (Calc.) | NON-HDL CHOL.", "mg/dL", "< 130", INT),
    "CHOL_HDL_RATIO": A("CHOL / HDL Ratio | Total Chol. / HDL Ratio | TC : HDL Ratio", "", "< 4.5"),
    "LDL_HDL_RATIO": A("LDL / HDL Ratio | LDL : HDL Ratio | L.D.L./H.D.L. Ratio", "", "< 3.5"),
    # --- DIABETES --------------------------------------------------------------
    "GLU_F": A("Glucose, Fasting | Fasting Blood Sugar (FBS) | BLOOD SUGAR - FASTING | Plasma Glucose Fasting", "mg/dL", "70 - 100", INT),
    "GLU_PP": A("Glucose, Post Prandial | Post Prandial Blood Sugar | BLOOD SUGAR - PP | PPBS (2 hr)", "mg/dL", "70 - 140", INT),
    "GLU_R": A("Glucose, Random | Random Blood Sugar (RBS) | BLOOD SUGAR - RANDOM", "mg/dL", "70 - 140", INT),
    "HBA1C": A("HbA1c | Glycosylated Haemoglobin (HbA1c) | HBA1C - GLYCATED HB | Glycated Hemoglobin A1c", "%", "4.0 - 5.6"),
    "EAG": A("Estimated Average Glucose (eAG) | eAG | Mean Blood Glucose (Calc.)", "mg/dL", "68 - 114", INT),
    "INSULIN_F": A("Insulin, Fasting | Fasting Insulin | S. INSULIN (FASTING)", "uIU/mL", "2.6 - 24.9"),
    # --- LFT -------------------------------------------------------------------
    "BILI_T": A("Bilirubin, Total | Total Bilirubin | BILIRUBIN - TOTAL | S. Bilirubin (Total)", "mg/dL", "0.3 - 1.2", "{:.2f}"),
    "BILI_D": A("Bilirubin, Direct | Direct Bilirubin | BILIRUBIN - DIRECT | Conjugated Bilirubin", "mg/dL", "0.0 - 0.3", "{:.2f}"),
    "BILI_I": A("Bilirubin, Indirect | Indirect Bilirubin (Calc.) | BILIRUBIN - INDIRECT", "mg/dL", "0.1 - 0.9", "{:.2f}"),
    "ALT": A("SGPT (ALT) | ALT (SGPT) | S.G.P.T. | Alanine Transaminase", "U/L", "10 - 49", INT),
    "AST": A("SGOT (AST) | AST (SGOT) | S.G.O.T. | Aspartate Transaminase", "U/L", "10 - 40", INT),
    "ALP": A("Alkaline Phosphatase | ALP | ALKALINE PHOSPHATASE (ALP) | S. Alk. Phosphatase", "U/L", "35 - 104", INT),
    "GGT": A("Gamma GT (GGT) | GGT | Gamma Glutamyl Transferase", "U/L", "10 - 71", INT),
    "PROT_T": A("Total Protein | Protein, Total | TOTAL PROTEINS | S. Protein (Total)", "g/dL", "6.4 - 8.3"),
    "ALB": A("Albumin | S. Albumin | ALBUMIN, SERUM | Alb", "g/dL", "3.5 - 5.2"),
    "GLOB": A("Globulin | Globulin (Calc.) | GLOBULIN, SERUM", "g/dL", "2.0 - 3.5"),
    "AG_RATIO": A("A / G Ratio | Albumin / Globulin Ratio | A:G RATIO (Calc.)", "", "1.0 - 2.1"),
    # --- KFT -------------------------------------------------------------------
    "CREAT": A("Creatinine, Serum | S. CREATININE | Sr.Creat | CREATININE (SERUM) | Serum Creatinine", "mg/dL", "0.7 - 1.3", "{:.2f}"),
    "UREA": A("Urea, Serum | S. UREA | Blood Urea | UREA (SERUM)", "mg/dL", "17 - 43", INT),
    "BUN": A("BUN | Blood Urea Nitrogen | B.U.N. (Calc.)", "mg/dL", "8 - 20", INT),
    "UA": A("Uric Acid | S. URIC ACID | Uric Acid, Serum | URIC ACID (SERUM)", "mg/dL", "3.5 - 7.2"),
    "EGFR": A("eGFR | eGFR (CKD-EPI) | Est. GFR | GFR, Estimated", "mL/min/1.73m2", "> 90", INT),
    # --- THYROID ---------------------------------------------------------------
    "TSH": A("TSH | TSH - Ultrasensitive | S. T.S.H. | Thyroid Stimulating Hormone", "uIU/mL", "0.55 - 4.78", "{:.2f}"),
    "T3_TOTAL": A("T3 - Total | Total Tri-iodothyronine (T3) | T3 (TOTAL)", "ng/dL", "60 - 200", INT),
    "T4_TOTAL": A("T4 - Total | Total Thyroxine (T4) | T4 (TOTAL)", "ug/dL", "4.6 - 12.0"),
    "FT3": A("Free T3 | FT3 | F.T.3 (Free Tri-iodothyronine)", "pg/mL", "2.3 - 4.2"),
    "FT4": A("Free T4 | FT4 | F.T.4 (Free Thyroxine)", "ng/dL", "0.89 - 1.76", "{:.2f}"),
    "ANTI_TPO": A("Anti-TPO Antibody | Anti Thyroid Peroxidase Ab | TPO ANTIBODIES", "IU/mL", "< 34"),
    # --- URINE ROUTINE ---------------------------------------------------------
    "UR_COLOUR": A("Colour | COLOUR | Color", "", "Pale Yellow"),
    "UR_PH": A("pH | Reaction (pH) | PH", "", "5.0 - 7.5"),
    "UR_SPGR": A("Specific Gravity | Sp. Gravity | SPECIFIC GRAVITY", "", "1.005 - 1.030", "{:.3f}"),
    "UR_PROT": A("Protein (Albumin) | Proteins | ALBUMIN | Protein", "", "Absent"),
    "UR_GLU": A("Glucose | Sugar | GLUCOSE (Urine)", "", "Absent"),
    "UR_KET": A("Ketone Bodies | Ketones | ACETONE", "", "Absent"),
    "UR_PUS": A("Pus Cells (WBC) | Pus Cells | WBC / Pus Cells", "/hpf", "0 - 5", INT),
    "UR_RBC": A("RBCs | Red Blood Cells | R.B.C. (Urine)", "/hpf", "0 - 2", INT),
    "UR_EPITH": A("Epithelial Cells | Epith. Cells | EPITHELIAL CELLS", "/hpf", "0 - 5", INT),
    "MICROALB": A("Microalbumin, Urine | Urine Microalbumin | MICROALBUMIN (SPOT)", "mg/L", "< 20", INT),
    "ACR": A("Albumin / Creatinine Ratio | Urine ACR | ACR (Spot Urine)", "mg/g", "< 30", INT),
    # --- ELECTROLYTES ----------------------------------------------------------
    "NA": A("Sodium | S. SODIUM | Sodium (Na+) | Na", "mmol/L", "136 - 145", INT),
    "K": A("Potassium | S. POTASSIUM | Potassium (K+) | K", "mmol/L", "3.5 - 5.1"),
    "CL": A("Chloride | S. CHLORIDE | Chloride (Cl-) | Cl", "mmol/L", "98 - 107", INT),
    "CA": A("Calcium, Total | S. CALCIUM | Total Calcium | Calcium", "mg/dL", "8.6 - 10.2"),
    "CA_ION": A("Ionised Calcium | Calcium, Ionized | IONIC CALCIUM", "mg/dL", "4.5 - 5.3"),
    "PHOS": A("Phosphorus | S. PHOSPHORUS | Inorganic Phosphate", "mg/dL", "2.5 - 4.5"),
    "MG": A("Magnesium | S. MAGNESIUM | Magnesium, Serum", "mg/dL", "1.6 - 2.6"),
    # --- IRON ------------------------------------------------------------------
    "FERRITIN": A("Ferritin | S. FERRITIN | Ferritin, Serum", "ng/mL", "22 - 322", INT),
    "IRON": A("Iron | S. IRON | Serum Iron | IRON (SERUM)", "ug/dL", "65 - 175", INT),
    "TIBC": A("TIBC | Total Iron Binding Capacity | T.I.B.C.", "ug/dL", "250 - 425", INT),
    "UIBC": A("UIBC | Unsaturated Iron Binding Capacity | U.I.B.C. (Calc.)", "ug/dL", "125 - 350", INT),
    "TSAT": A("Transferrin Saturation | % Saturation | TRANSFERRIN SAT. (Calc.)", "%", "20 - 50"),
    # --- VITAMIN ---------------------------------------------------------------
    "VIT_D": A("Vitamin D (25-OH) | 25-Hydroxy Vitamin D | VITAMIN D3 (25-OH)", "ng/mL", "30 - 100"),
    "VIT_B12": A("Vitamin B12 | S. VITAMIN B-12 | Cyanocobalamin (B12)", "pg/mL", "211 - 911", INT),
    "FOLATE": A("Folate | Folic Acid | S. FOLATE", "ng/mL", "3.1 - 20.5"),
    # --- COAGULATION -----------------------------------------------------------
    "PT": A("Prothrombin Time (PT) | PT | P.T. (Patient)", "sec", "11.0 - 14.0"),
    "INR": A("INR | I.N.R. | International Normalised Ratio", "", "0.8 - 1.2", "{:.2f}"),
    "APTT": A("APTT | A.P.T.T. | Activated Partial Thromboplastin Time", "sec", "26.0 - 37.0"),
    "D_DIMER": A("D-Dimer | D DIMER | D-Dimer, Quantitative", "ng/mL", "< 500", INT),
    # --- misc extras -----------------------------------------------------------
    "ESR": A("ESR | E.S.R. (Westergren) | Erythrocyte Sedimentation Rate", "mm/hr", "0 - 15", INT),
    "PERIPH_SMEAR": A("Peripheral Smear | P.S. Examination | Peripheral Blood Smear", "", "Normal morphology"),
    "BLOOD_GROUP": A("Blood Group (ABO & Rh) | ABO Grouping & Rh | BLOOD GROUP", "", "-"),
    "URINE_CULTURE": A("Urine Culture & Sensitivity | URINE C/S | Culture, Urine", "", "No growth"),
    "RETIC": A("Reticulocyte Count | Retic Count | RETICULOCYTES", "%", "0.5 - 2.5"),
    # --- CARDIAC ---------------------------------------------------------------
    "TROP_I": A("Troponin I | Trop I (Quantitative) | CARDIAC TROPONIN-I", "ng/mL", "< 0.04", "{:.3f}"),
    "CPK_MB": A("CPK-MB | CK-MB | Creatine Kinase MB", "U/L", "< 25", INT),
    "NT_PROBNP": A("NT-proBNP | NT pro BNP | N-Terminal pro BNP", "pg/mL", "< 125", INT),
    # --- INFLAMMATION ----------------------------------------------------------
    "CRP": A("CRP | C-Reactive Protein | C REACTIVE PROTEIN (CRP)", "mg/L", "< 6"),
    "HS_CRP": A("hs-CRP | High Sensitivity CRP | HS-CRP (Cardio)", "mg/L", "< 3", "{:.2f}"),
    "RA_FACTOR": A("RA Factor | Rheumatoid Factor | RA FACTOR (Quantitative)", "IU/mL", "< 14"),
    "ASO": A("ASO Titre | Anti Streptolysin O | ASLO", "IU/mL", "< 200", INT),
    # --- HORMONES --------------------------------------------------------------
    "PTH": A("PTH (Intact) | Parathyroid Hormone | INTACT PTH", "pg/mL", "15 - 65"),
    "TESTO_T": A("Testosterone, Total | Total Testosterone | S. TESTOSTERONE", "ng/dL", "249 - 836", INT),
    "PROLACTIN": A("Prolactin | S. PROLACTIN | PRL", "ng/mL", "4.0 - 15.2"),
    "CORTISOL_AM": A("Cortisol (8 AM) | Morning Cortisol | CORTISOL - AM SAMPLE", "ug/dL", "6.2 - 19.4"),
    # --- SEROLOGY (all text results) -------------------------------------------
    "HBSAG": A("HBsAg | Hepatitis B Surface Antigen | HBSAG (ELISA)", "", "Non Reactive"),
    "ANTI_HCV": A("Anti-HCV | HCV Antibody | ANTI HCV (ELISA)", "", "Non Reactive"),
    "HIV": A("HIV I & II Antibody | HIV (I & II) | HIV 1 AND 2 ANTIBODY", "", "Non Reactive"),
    "WIDAL": A("Widal Test | WIDAL (Slide Agglutination) | Widal", "", "Non Reactive"),
    "DENGUE_NS1": A("Dengue NS1 Antigen | NS1 Antigen | DENGUE NS1 (ELISA)", "", "Negative"),
    "DENGUE_IGM": A("Dengue IgM Antibody | Dengue IgM | DENGUE IGM (ELISA)", "", "Negative"),
    "MP": A("Malaria Parasite | MP (Smear) | MALARIAL PARASITE", "", "Not Detected"),
    "VDRL": A("VDRL | VDRL (RPR) | Syphilis (VDRL)", "", "Non Reactive"),
    # --- TUMOUR MARKERS --------------------------------------------------------
    "PSA": A("PSA, Total | Prostate Specific Antigen | TOTAL PSA", "ng/mL", "< 4.0", "{:.2f}"),
}

# Reference ranges that differ by sex. Everything else uses the range above.
SEX_REF: dict[str, dict[str, str]] = {
    "HGB": {"F": "12.0 - 15.0"},
    "RBC": {"F": "3.8 - 4.8"},
    "PCV": {"F": "36 - 46"},
    "CREAT": {"F": "0.6 - 1.1"},
    "UA": {"F": "2.6 - 6.0"},
    "FERRITIN": {"F": "10 - 291"},
    "IRON": {"F": "50 - 170"},
    "ESR": {"F": "0 - 20"},
    "HDL": {"F": "50 - 75"},
    "TESTO_T": {"F": "10 - 55"},
    "PROLACTIN": {"F": "4.8 - 23.3"},
}

# Paediatric ranges: (age below which the range applies, range). Checked in order.
PAED_REF: dict[str, list[tuple[int, str]]] = {
    "HGB": [(7, "11.0 - 13.5"), (13, "11.5 - 15.5"), (18, "12.0 - 16.0")],
    "RBC": [(7, "4.0 - 5.2"), (13, "4.0 - 5.2"), (18, "4.2 - 5.4")],
    "PCV": [(7, "33 - 40"), (13, "35 - 45"), (18, "37 - 47")],
    "MCV": [(7, "75 - 87"), (13, "77 - 95"), (18, "78 - 98")],
    "MCH": [(13, "24 - 30"), (18, "25 - 32")],
    "WBC": [(7, "5000 - 15000"), (13, "4500 - 13500"), (18, "4500 - 11000")],
    "NEUT_PCT": [(7, "30 - 60"), (13, "35 - 65"), (18, "40 - 75")],
    "LYMPH_PCT": [(7, "35 - 65"), (13, "30 - 55"), (18, "25 - 45")],
    "PLT": [(18, "150000 - 450000")],
    "ALP": [(7, "150 - 380"), (13, "130 - 420"), (18, "50 - 560")],
    "CREAT": [(7, "0.30 - 0.70"), (13, "0.40 - 0.80"), (18, "0.50 - 1.00")],
    "UREA": [(13, "10 - 38"), (18, "12 - 40")],
    "UA": [(13, "2.0 - 5.5"), (18, "2.5 - 6.5")],
    "PROT_T": [(13, "6.0 - 8.0"), (18, "6.2 - 8.2")],
    "ALB": [(18, "3.8 - 5.4")],
    "CA": [(18, "8.8 - 10.8")],
    "PHOS": [(7, "4.0 - 6.5"), (13, "3.7 - 5.6"), (18, "2.9 - 5.4")],
    "TSH": [(7, "0.70 - 5.70"), (18, "0.50 - 4.90")],
    "T4_TOTAL": [(18, "5.5 - 12.8")],
    "FT4": [(18, "0.95 - 1.80")],
    "CHOL": [(18, "< 170")],
    "TRIG": [(10, "< 75"), (18, "< 90")],
    "LDL": [(18, "< 110")],
    "HDL": [(18, "> 45")],
    "FERRITIN": [(18, "7 - 140")],
    "ESR": [(18, "0 - 13")],
    "VIT_B12": [(18, "200 - 900")],
}


def ref(code: str, sex: str = "M", age: int = 40) -> str:
    """The reference range this lab would print for this patient."""
    if age < 18 and code in PAED_REF:
        for below, band in PAED_REF[code]:
            if age < below:
                return band
    if sex == "F" and code in SEX_REF:
        return SEX_REF[code].get("F", ANALYTES[code]["ref"])
    return ANALYTES[code]["ref"]

# Panel code -> printed titles to rotate, and full analyte membership.
PANELS: dict[str, dict] = {
    "CBC": {
        "titles": ["Complete Blood Count (CBC)", "COMPLETE HEMOGRAM", "Haemogram", "Complete Haemogram", "CBC", "Hemogram"],
        "analytes": ["HGB", "RBC", "PCV", "MCV", "MCH", "MCHC", "RDW", "WBC", "NEUT_PCT",
                     "LYMPH_PCT", "MONO_PCT", "EOS_PCT", "BASO_PCT", "ANC", "ALC", "PLT", "MPV"],
    },
    "LIPID": {
        "titles": ["Lipid Profile", "LIPID PANEL", "Lipidogram", "Lipid Screen", "Dyslipidemia Profile", "Cholesterol Profile"],
        "analytes": ["CHOL", "TRIG", "HDL", "LDL", "VLDL", "NON_HDL", "CHOL_HDL_RATIO", "LDL_HDL_RATIO"],
    },
    "DIABETES": {
        "titles": ["Diabetes Profile", "DIABETIC PROFILE", "Sugar Profile", "Blood Sugar Profile", "Glycemic Profile", "Glucose Profile"],
        "analytes": ["GLU_F", "GLU_PP", "GLU_R", "HBA1C", "EAG", "INSULIN_F"],
    },
    "LFT": {
        "titles": ["Liver Function Test (LFT)", "LIVER FUNCTION PROFILE", "Liver Profile", "Hepatic Function Panel", "Liver Panel", "LFT"],
        "analytes": ["BILI_T", "BILI_D", "BILI_I", "ALT", "AST", "ALP", "GGT", "PROT_T", "ALB", "GLOB", "AG_RATIO"],
    },
    "KFT": {
        "titles": ["Renal Function Test (RFT)", "KIDNEY FUNCTION TEST", "Renal Profile", "KFT", "Kidney Profile", "Renal Panel"],
        "analytes": ["CREAT", "UREA", "BUN", "UA", "EGFR"],
    },
    "THYROID": {
        "titles": ["Thyroid Profile", "THYROID FUNCTION TEST (TFT)", "TFT", "Thyroid Panel", "Thyroid Function Profile"],
        "analytes": ["TSH", "T3_TOTAL", "T4_TOTAL", "FT3", "FT4", "ANTI_TPO"],
    },
    "URINE_ROUTINE": {
        "titles": ["Urine Routine & Microscopy", "URINE R/M", "Complete Urine Examination (CUE)", "Urinalysis", "Routine Urine Examination", "Urine Routine"],
        "analytes": ["UR_COLOUR", "UR_PH", "UR_SPGR", "UR_PROT", "UR_GLU", "UR_KET",
                     "UR_PUS", "UR_RBC", "UR_EPITH", "MICROALB", "ACR"],
    },
    "ELECTROLYTES": {
        "titles": ["Serum Electrolytes", "ELECTROLYTE PANEL", "Electrolytes", "Electrolyte Profile", "Mineral Profile"],
        "analytes": ["NA", "K", "CL", "CA", "CA_ION", "PHOS", "MG"],
    },
    "IRON": {
        "titles": ["Iron Profile", "IRON STUDIES", "Iron Panel", "Iron Status", "Anaemia Profile", "Anemia Profile"],
        "analytes": ["FERRITIN", "IRON", "TIBC", "UIBC", "TSAT"],
    },
    "VITAMIN": {
        "titles": ["Vitamin Profile", "VITAMIN PANEL", "Nutritional Profile", "Vitamin Screening", "Bone Health Profile", "Nutrition Profile"],
        "analytes": ["VIT_D", "VIT_B12", "FOLATE"],
    },
    "COAGULATION": {
        "titles": ["Coagulation Profile", "COAGULATION SCREEN", "Pre-operative Coagulation Panel"],
        "analytes": ["PT", "INR", "APTT", "D_DIMER"],
    },
    "CARDIAC": {
        "titles": ["Cardiac Profile", "CARDIAC MARKERS", "Cardiac Marker Panel", "Cardiac Enzymes"],
        "analytes": ["TROP_I", "CPK_MB", "NT_PROBNP"],
    },
    "INFLAMMATION": {
        "titles": ["Inflammatory Markers", "INFLAMMATION PANEL", "Acute Phase Reactants",
                   "Arthritis Profile"],
        "analytes": ["CRP", "HS_CRP", "RA_FACTOR", "ASO"],
    },
    "HORMONES": {
        "titles": ["Hormone Profile", "HORMONE PANEL", "Endocrine Profile", "Hormone Assay"],
        "analytes": ["CORTISOL_AM", "PROLACTIN", "PTH", "TESTO_T"],
    },
    "SEROLOGY": {
        "titles": ["Serology", "SEROLOGY PANEL", "Infectious Disease Screen",
                   "Viral Markers", "Pre-procedure Viral Screen"],
        "analytes": ["HBSAG", "ANTI_HCV", "HIV", "VDRL", "WIDAL", "DENGUE_NS1",
                     "DENGUE_IGM", "MP"],
    },
    "TUMOUR_MARKERS": {
        "titles": ["Tumour Markers", "TUMOUR MARKER PANEL", "Oncology Markers", "Tumor Markers"],
        "analytes": ["PSA"],
    },
}

METHODS = {
    "HBA1C": "HPLC, NGSP certified",
    "TSH": "CLIA",
    "FT4": "CLIA",
    "CREAT": "Modified Jaffe, kinetic",
    "CHOL": "CHOD - PAP",
    "TRIG": "GPO - Trinder",
    "HGB": "SLS - Haemoglobin",
    "VIT_D": "CLIA",
    "FERRITIN": "CLIA",
    "MICROALB": "Immunoturbidimetry",
    "PT": "Photo-optical clot detection",
    "URINE_CULTURE": "Semi-quantitative culture, CLSI M100",
    "UA": "Uricase - POD",
    "ALP": "IFCC, pNPP - AMP buffer",
}


def fmt(code: str, value) -> str:
    """Format a value the way the analyte is usually printed."""
    if isinstance(value, str):
        return value
    return ANALYTES[code]["fmt"].format(value)


def flag(code: str, value, sex: str = "M", age: int = 40) -> str:
    """H / L against the range this patient's report prints, blank if it cannot be judged."""
    if isinstance(value, str):
        return ""
    band = ref(code, sex, age)
    try:
        if band.startswith("<"):
            return "H" if value > float(band.lstrip("< ")) else ""
        if band.startswith(">"):
            return "L" if value < float(band.lstrip("> ")) else ""
        low, high = (float(p) for p in band.split(" - "))
    except ValueError:
        return ""
    if value < low:
        return "L"
    if value > high:
        return "H"
    return ""


def egfr(creat: float, age: int, sex: str) -> float:
    """CKD-EPI 2009, the equation Indian labs print alongside creatinine."""
    k = 0.7 if sex == "F" else 0.9
    a = -0.329 if sex == "F" else -0.411
    ratio = creat / k
    val = 141 * min(ratio, 1) ** a * max(ratio, 1) ** -1.209 * 0.993**age
    return val * 1.018 if sex == "F" else val


def derive(v: dict, age: int, sex: str) -> dict:
    """Fill in every calculated analyte from the printed (already rounded) inputs.

    Each derived value is computed from the rounded number the report shows, so a scorer
    recomputing VLDL = TRIG/5 off the PDF gets exactly the printed VLDL back.
    """
    v = dict(v)

    def has(*codes):
        return all(c in v for c in codes)

    if "TRIG" in v:
        v.setdefault("VLDL", round(v["TRIG"] / 5))
    if has("CHOL", "HDL", "VLDL"):
        v.setdefault("LDL", round(v["CHOL"] - v["HDL"] - v["VLDL"]))
    if has("CHOL", "HDL"):
        v.setdefault("NON_HDL", round(v["CHOL"] - v["HDL"]))
        v.setdefault("CHOL_HDL_RATIO", round(v["CHOL"] / v["HDL"], 1))
    if has("LDL", "HDL"):
        v.setdefault("LDL_HDL_RATIO", round(v["LDL"] / v["HDL"], 1))
    if "UREA" in v:
        v.setdefault("BUN", round(v["UREA"] / 2.14))
    if has("PROT_T", "ALB"):
        v.setdefault("GLOB", round(v["PROT_T"] - v["ALB"], 1))
        v.setdefault("AG_RATIO", round(v["ALB"] / v["GLOB"], 1))
    if has("BILI_T", "BILI_D"):
        v.setdefault("BILI_I", round(v["BILI_T"] - v["BILI_D"], 2))
    if "HBA1C" in v:
        v.setdefault("EAG", round(28.7 * v["HBA1C"] - 46.7))
    if has("IRON", "TIBC"):
        v.setdefault("UIBC", round(v["TIBC"] - v["IRON"]))
        v.setdefault("TSAT", round(v["IRON"] / v["TIBC"] * 100, 1))
    if "CREAT" in v and age >= 18:
        v.setdefault("EGFR", round(egfr(v["CREAT"], age, sex)))
    if has("WBC", "NEUT_PCT"):
        v.setdefault("ANC", round(v["WBC"] * v["NEUT_PCT"] / 100))
    if has("WBC", "LYMPH_PCT"):
        v.setdefault("ALC", round(v["WBC"] * v["LYMPH_PCT"] / 100))
    return v


def check_derived(v: dict, age: int, sex: str) -> list[str]:
    """Return the derived values that disagree with what they are computed from."""
    bad: list[str] = []

    def near(a, b, t=1.0):
        return abs(a - b) <= t

    k = v.keys()
    if {"TRIG", "VLDL"} <= k and not near(v["VLDL"], v["TRIG"] / 5):
        bad.append("VLDL != TRIG/5")
    if {"CHOL", "HDL", "VLDL", "LDL"} <= k and not near(v["LDL"], v["CHOL"] - v["HDL"] - v["VLDL"]):
        bad.append("LDL != CHOL-HDL-VLDL")
    if {"CHOL", "HDL", "NON_HDL"} <= k and not near(v["NON_HDL"], v["CHOL"] - v["HDL"]):
        bad.append("NON_HDL != CHOL-HDL")
    if {"UREA", "BUN"} <= k and not near(v["BUN"], v["UREA"] / 2.14):
        bad.append("BUN != UREA/2.14")
    if {"PROT_T", "ALB", "GLOB"} <= k and not near(v["GLOB"], v["PROT_T"] - v["ALB"], 0.11):
        bad.append("GLOB != PROT_T-ALB")
    if {"ALB", "GLOB", "AG_RATIO"} <= k and not near(v["AG_RATIO"], v["ALB"] / v["GLOB"], 0.06):
        bad.append("AG_RATIO != ALB/GLOB")
    if {"BILI_T", "BILI_D", "BILI_I"} <= k and not near(v["BILI_I"], v["BILI_T"] - v["BILI_D"], 0.011):
        bad.append("BILI_I != BILI_T-BILI_D")
    if {"HBA1C", "EAG"} <= k and not near(v["EAG"], 28.7 * v["HBA1C"] - 46.7):
        bad.append("EAG != 28.7*HbA1c-46.7")
    if {"IRON", "TIBC", "TSAT"} <= k and not near(v["TSAT"], v["IRON"] / v["TIBC"] * 100, 0.6):
        bad.append("TSAT != IRON/TIBC")
    if {"CREAT", "EGFR"} <= k and age >= 18 and not near(v["EGFR"], egfr(v["CREAT"], age, sex), 2.0):
        bad.append("EGFR inconsistent with creatinine")
    pcts = [v[c] for c in ("NEUT_PCT", "LYMPH_PCT", "MONO_PCT", "EOS_PCT", "BASO_PCT") if c in v]
    if len(pcts) == 5 and sum(pcts) != 100:
        bad.append(f"differential sums to {sum(pcts)}")
    return bad
