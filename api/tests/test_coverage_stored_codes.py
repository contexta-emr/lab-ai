"""Coverage counts the code the database stored, when the database was sure (review B26).

The panel check re-matched printed labels against its own static dictionary and
never read lab.results.analyte_id. "Albumin" is ambiguous there - serum albumin
and urine albumin share the spelling - so on Ashwini's report (2026-10-15)
Albumin 4.2, stored as ALB by an exact alias match, sat under the liver panel
as "missing". A stored code now counts when it was matched exactly or set by a
person. A FUZZY stored code does not: "Total RBC Count" stored as WBC by a
near-miss must not make WBC look found with the red cell count's value.
"""

from __future__ import annotations

import pytest

from app.services.coverage import merged_rows, panel_templates

LFT = "LIVER FUNCTION TEST - A (LFT-A)"
CBP = "COMPLETE BLOOD PICTURE (CBP)"


def _row(i: int, section: str, label: str, value: str, code: str | None, method: str) -> dict:
    return {
        "id": i,
        "section_id": 1 if section == CBP else 2,
        "heading_printed": section,
        "printed_label": label,
        "value_text": value,
        "unit": None,
        "flag": None,
        "reference_printed": None,
        "analyte_code": code,
        "analyte_name": None,
        "match_method": method,
        "is_reviewed": False,
        "corrected_from": None,
    }


# Ashwini's liver section, as stored.
LIVER = [
    _row(1, LFT, "Total Bilirubin", "0.5", "BILI_T", "exact_alias"),
    _row(2, LFT, "Direct Bilirubin", "0.1", "BILI_D", "exact_alias"),
    _row(3, LFT, "Indirect Bilirubin", "0.4", "BILI_I", "exact_alias"),
    _row(4, LFT, "ALT/SGPT", "10", "ALT", "exact_alias"),
    _row(5, LFT, "AST/SGOT", "19", "AST", "exact_alias"),
    _row(6, LFT, "Alkaline Phosphatase", "97", "ALP", "exact_alias"),
    _row(7, LFT, "Total Protein (TP)", "7.4", "PROT_T", "exact_alias"),
    _row(8, LFT, "Albumin", "4.2", "ALB", "exact_alias"),
    _row(9, LFT, "Globulin", "3.2", "GLOB", "exact_alias"),
    _row(10, LFT, "Albumin / Globulin (A/G) Ratio", "1.3", "AG_RATIO", "fuzzy_alias"),
    _row(11, LFT, "Gamma-Glutamyl Transferase (GGT)", "16", "GGT", "exact_alias"),
]

# Ashwini's blood count, with the near-miss the database made.
BLOOD = [
    _row(20, CBP, "Haemoglobin", "11.5", "HGB", "exact_alias"),
    _row(21, CBP, "Total RBC Count", "4.36", "WBC", "fuzzy_alias"),
    _row(22, CBP, "MCV", "80.40", "MCV", "exact_alias"),
    _row(23, CBP, "MCH", "26.40", "MCH", "exact_alias"),
    _row(24, CBP, "MCHC", "32.90", "MCHC", "exact_alias"),
    _row(25, CBP, "RDW", "16.1", "RDW", "exact_alias"),
    _row(26, CBP, "Total WBC Count", "6800", "WBC", "exact_alias"),
    _row(27, CBP, "Neutrophils", "57", "NEUT_PCT", "exact_alias"),
    _row(28, CBP, "Lymphocytes", "30", "LYMPH_PCT", "exact_alias"),
    _row(29, CBP, "Eosinophils", "5", "EOS_PCT", "exact_alias"),
    _row(30, CBP, "Monocytes", "7", "MONO_PCT", "exact_alias"),
    _row(31, CBP, "Basophils", "1", "BASO_PCT", "exact_alias"),
    _row(32, CBP, "Platelet Count", "246000", "PLT", "exact_alias"),
]


@pytest.fixture(scope="module")
def templates(db):
    return panel_templates()


def _by_label(out: dict) -> dict[str, dict]:
    return {r["printed_label"]: r for r in out["rows"] if r.get("printed_label")}


def test_a_test_the_database_matched_exactly_counts_as_found(templates) -> None:
    out = merged_rows(LIVER, templates)
    assert _by_label(out)["Albumin"]["status"] == "found"
    still_missing = [
        r for r in out["rows"] if r["status"] == "missing" and r.get("analyte_code") == "ALB"
    ]
    assert not still_missing


def test_a_fuzzy_stored_code_never_makes_another_test_look_found(templates) -> None:
    rows = _by_label(merged_rows(BLOOD, templates))
    assert rows["Total WBC Count"]["status"] == "found"
    assert rows["Total RBC Count"]["status"] != "found"
