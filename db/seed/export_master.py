"""Generate db/004_seed_analyte_master.sql from the corpus catalogue.

The analyte master and the synthetic corpus must agree on every code, alias,
unit and reference range - otherwise the fixture tests a vocabulary the parser
will never meet. Rather than maintain both, this reads corpus/generator/
catalog.py and emits the SQL. catalog.py stays the single source of truth.

    python db/seed/export_master.py

Rerun it whenever catalog.py changes; the output file is generated, not edited.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "corpus" / "generator"))

import catalog as C  # noqa: E402

OUT = ROOT / "db" / "004_seed_analyte_master.sql"

# The ten high-frequency groups from the Top 10 Lab Panels reference. The rest
# are real panels too, they are simply not in that first ten.
CORE_PANELS = ["CBC", "LIPID", "DIABETES", "LFT", "KFT", "THYROID",
               "URINE_ROUTINE", "ELECTROLYTES", "IRON", "VITAMIN"]

# Calculated rather than measured. Flagged in the master so a recomputation
# check can run against what the lab actually printed.
DERIVED = {"VLDL", "LDL", "NON_HDL", "CHOL_HDL_RATIO", "LDL_HDL_RATIO", "EAG",
           "BUN", "GLOB", "AG_RATIO", "BILI_I", "UIBC", "TSAT", "EGFR",
           "ANC", "ALC"}

DERIVATION_NOTE = {
    "VLDL": "TRIG / 5",
    "LDL": "CHOL - HDL - VLDL (Friedewald)",
    "NON_HDL": "CHOL - HDL",
    "CHOL_HDL_RATIO": "CHOL / HDL",
    "LDL_HDL_RATIO": "LDL / HDL",
    "EAG": "28.7 * HBA1C - 46.7",
    "BUN": "UREA / 2.14",
    "GLOB": "PROT_T - ALB",
    "AG_RATIO": "ALB / GLOB",
    "BILI_I": "BILI_T - BILI_D",
    "UIBC": "TIBC - IRON",
    "TSAT": "IRON / TIBC * 100",
    "EGFR": "CKD-EPI 2009 from CREAT, age and sex",
    "ANC": "WBC * NEUT_PCT / 100",
    "ALC": "WBC * LYMPH_PCT / 100",
}

PANEL_DESCRIPTION = {
    "CBC": "Complete blood count and differential",
    "LIPID": "Lipid profile with calculated fractions and ratios",
    "DIABETES": "Glycaemic profile including HbA1c and estimated average glucose",
    "LFT": "Liver function, bilirubin fractions and protein",
    "KFT": "Renal function including estimated GFR",
    "THYROID": "Thyroid function and autoantibodies",
    "URINE_ROUTINE": "Routine urine examination and microscopy",
    "ELECTROLYTES": "Serum electrolytes and minerals",
    "IRON": "Iron studies and transferrin saturation",
    "VITAMIN": "Vitamin D, B12 and folate",
    "COAGULATION": "Prothrombin time, INR, APTT and D-dimer",
    "CARDIAC": "Cardiac markers",
    "INFLAMMATION": "Acute phase reactants and arthritis markers",
    "HORMONES": "Endocrine assays",
    "SEROLOGY": "Infectious disease screening, reported as text",
    "TUMOUR_MARKERS": "Tumour markers",
}


def q(value) -> str:
    """SQL literal. None becomes NULL; quotes are doubled."""
    if value is None or value == "":
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def decimals(fmt: str) -> int:
    m = re.search(r"\.(\d)f", fmt)
    return int(m.group(1)) if m else 1


def is_text_analyte(code: str) -> bool:
    """A test whose result is words, not a number."""
    ref = C.ANALYTES[code]["ref"]
    if re.match(r"^\s*[<>]?\s*-?\d", ref):
        return False
    return not re.match(r"^\s*-?\d+(\.\d+)?\s*-\s*-?\d+(\.\d+)?\s*$", ref)


def split_range(band: str) -> tuple[str | None, str | None]:
    """'13.0 - 17.0' -> (13.0, 17.0);  '< 200' -> (None, 200);  '> 90' -> (90, None)."""
    band = (band or "").strip()
    if " - " in band:
        lo, hi = band.split(" - ", 1)
        try:
            return str(float(lo)), str(float(hi))
        except ValueError:
            return None, None
    if band.startswith("<"):
        try:
            return None, str(float(band.lstrip("<= ")))
        except ValueError:
            return None, None
    if band.startswith(">"):
        try:
            return str(float(band.lstrip(">= ")), ), None
        except ValueError:
            return None, None
    return None, None


def main() -> None:
    lines: list[str] = []
    add = lines.append

    add("-- =============================================================================")
    add("-- Contexta - Lab extraction store")
    add("-- 004  Seed: panels, analytes, aliases, reference ranges")
    add("-- =============================================================================")
    add("-- GENERATED FILE - do not edit by hand.")
    add("--   Source:    corpus/generator/catalog.py")
    add("--   Regenerate: python db/seed/export_master.py")
    add("--")
    add("-- Idempotent: every statement is ON CONFLICT DO NOTHING or keyed on a natural")
    add("-- key, so running this twice changes nothing the second time.")
    add("-- =============================================================================")
    add("")
    add("BEGIN;")
    add("")

    # ---- panels -------------------------------------------------------------
    add("-- ---------------------------------------------------------------- panels")
    add("INSERT INTO lab.panels (code, display_name, description, is_core, sort_order)")
    add("VALUES")
    rows = []
    for i, (code, panel) in enumerate(C.PANELS.items()):
        rows.append(f"    ({q(code)}, {q(panel['titles'][0])}, "
                    f"{q(PANEL_DESCRIPTION.get(code))}, "
                    f"{q(code in CORE_PANELS)}, {i * 10})")
    add(",\n".join(rows))
    add("ON CONFLICT (code) DO NOTHING;")
    add("")

    # ---- panel aliases ------------------------------------------------------
    add("-- -------------------------------------------------------- panel aliases")
    add("-- The printed titles a section heading arrives under.")
    add("INSERT INTO lab.panel_aliases (panel_id, alias, source)")
    add("SELECT p.id, v.alias, 'seed'")
    add("FROM (VALUES")
    rows = []
    for code, panel in C.PANELS.items():
        seen = set()
        for title in panel["titles"]:
            key = re.sub(r"[^a-z0-9]+", "", title.lower())
            if key in seen:
                continue
            seen.add(key)
            rows.append(f"    ({q(code)}, {q(title)})")
    add(",\n".join(rows))
    add(") AS v(panel_code, alias)")
    add("JOIN lab.panels p ON p.code = v.panel_code")
    add("WHERE NOT EXISTS (")
    add("    SELECT 1 FROM lab.panel_aliases pa")
    add("    WHERE pa.alias_normalised = regexp_replace(lower(v.alias), '[^a-z0-9]+', '', 'g')")
    add("      AND pa.practice_id IS NULL")
    add(");")
    add("")

    # ---- analytes -----------------------------------------------------------
    panel_of = {c: p for p, panel in C.PANELS.items() for c in panel["analytes"]}
    add("-- -------------------------------------------------------------- analytes")
    add("INSERT INTO lab.analytes (code, panel_id, display_name, value_type,")
    add("                          default_unit, decimals, is_derived, derivation_note,")
    add("                          sort_order)")
    add("SELECT v.code, p.id, v.display_name, v.value_type, v.default_unit,")
    add("       v.decimals, v.is_derived, v.derivation_note, v.sort_order")
    add("FROM (VALUES")
    rows = []
    order = 0
    for code, meta in C.ANALYTES.items():
        order += 10
        rows.append(
            f"    ({q(code)}, {q(panel_of.get(code))}, {q(meta['labels'][0])}, "
            f"{q('text' if is_text_analyte(code) else 'numeric')}, "
            f"{q(meta['unit'])}, {decimals(meta['fmt'])}, "
            f"{q(code in DERIVED)}, {q(DERIVATION_NOTE.get(code))}, {order})"
        )
    add(",\n".join(rows))
    add(") AS v(code, panel_code, display_name, value_type, default_unit,")
    add("       decimals, is_derived, derivation_note, sort_order)")
    add("LEFT JOIN lab.panels p ON p.code = v.panel_code")
    add("ON CONFLICT (code) DO NOTHING;")
    add("")

    # ---- analyte aliases ----------------------------------------------------
    add("-- ------------------------------------------------------ analyte aliases")
    add("-- Every spelling a lab prints. This is the table the pipeline turns on:")
    add("-- Creatinine, Serum / S. CREATININE / Sr.Creat / CREATININE (SERUM) are one")
    add("-- test, and only this table knows it.")
    add("INSERT INTO lab.analyte_aliases (analyte_id, alias, source, confidence)")
    add("SELECT a.id, v.alias, 'seed', 1.0000")
    add("FROM (VALUES")
    rows, seen_norm = [], set()
    for code, meta in C.ANALYTES.items():
        for alias in meta["labels"]:
            key = re.sub(r"[^a-z0-9]+", "", alias.lower())
            if key in seen_norm:       # one normalised spelling, one analyte
                continue
            seen_norm.add(key)
            rows.append(f"    ({q(code)}, {q(alias)})")
    add(",\n".join(rows))
    add(") AS v(analyte_code, alias)")
    add("JOIN lab.analytes a ON a.code = v.analyte_code")
    add("WHERE NOT EXISTS (")
    add("    SELECT 1 FROM lab.analyte_aliases al")
    add("    WHERE al.alias_normalised = regexp_replace(lower(v.alias), '[^a-z0-9]+', '', 'g')")
    add("      AND al.practice_id IS NULL")
    add(");")
    add("")

    # ---- reference ranges ---------------------------------------------------
    add("-- ------------------------------------------------------ reference ranges")
    add("-- Adult default, then the sex-specific and paediatric bands that override")
    add("-- it. A haemoglobin of 12.4 is normal for a woman, low for a man, and")
    add("-- normal for a six-year-old; each of those is a row.")
    add("INSERT INTO lab.reference_ranges (analyte_id, sex, age_min_years, age_max_years,")
    add("                                  range_low, range_high, range_text, unit, source)")
    add("SELECT a.id, v.sex, v.age_min, v.age_max, v.range_low, v.range_high,")
    add("       v.range_text, v.unit, v.source")
    add("FROM (VALUES")
    rows = []
    for code, meta in C.ANALYTES.items():
        lo, hi = split_range(meta["ref"])
        rows.append(f"    ({q(code)}, NULL::CHAR(1), 18::NUMERIC, NULL::NUMERIC, "
                    f"{lo or 'NULL'}::NUMERIC, {hi or 'NULL'}::NUMERIC, "
                    f"{q(meta['ref'])}, {q(meta['unit'])}, 'contexta_default')")
    for code, bands in C.SEX_REF.items():
        for sex, band in bands.items():
            lo, hi = split_range(band)
            rows.append(f"    ({q(code)}, {q(sex)}, 18::NUMERIC, NULL::NUMERIC, "
                        f"{lo or 'NULL'}::NUMERIC, {hi or 'NULL'}::NUMERIC, "
                        f"{q(band)}, {q(C.ANALYTES[code]['unit'])}, 'contexta_default_sex')")
    for code, bands in C.PAED_REF.items():
        prev = 0
        for below, band in bands:
            lo, hi = split_range(band)
            rows.append(f"    ({q(code)}, NULL::CHAR(1), {prev}::NUMERIC, {below}::NUMERIC, "
                        f"{lo or 'NULL'}::NUMERIC, {hi or 'NULL'}::NUMERIC, "
                        f"{q(band)}, {q(C.ANALYTES[code]['unit'])}, 'contexta_default_paediatric')")
            prev = below
    add(",\n".join(rows))
    add(") AS v(analyte_code, sex, age_min, age_max, range_low, range_high,")
    add("       range_text, unit, source)")
    add("JOIN lab.analytes a ON a.code = v.analyte_code")
    add("WHERE NOT EXISTS (")
    add("    SELECT 1 FROM lab.reference_ranges rr")
    add("    WHERE rr.analyte_id = a.id")
    add("      AND rr.sex IS NOT DISTINCT FROM v.sex")
    add("      AND rr.age_min_years IS NOT DISTINCT FROM v.age_min")
    add("      AND rr.age_max_years IS NOT DISTINCT FROM v.age_max")
    add("      AND rr.practice_id IS NULL")
    add(");")
    add("")
    add("COMMIT;")
    add("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    n_alias = sum(1 for m in C.ANALYTES.values() for _ in m["labels"])
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  {len(C.PANELS)} panels, {len(C.ANALYTES)} analytes, "
          f"~{n_alias} aliases, {len(lines)} lines")


if __name__ == "__main__":
    main()
