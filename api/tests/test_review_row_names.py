"""A review row's name describes the code beside it (review B26).

Coverage re-matches printed labels with its own fuzzy dictionary. Where that guess
differed from the code the database stored, the row showed the guess's name next
to the stored code - "NON-HDL CHOL." as HDL Cholesterol, code NON_HDL - on a
screen whose job is to make a wrong mapping obvious.
"""

from __future__ import annotations

import pytest

from app.services.coverage import merged_rows, panel_templates


@pytest.fixture(scope="module")
def templates(db):
    return panel_templates()


def _row(i: int, label: str, code: str | None, name: str | None) -> dict:
    return {
        "id": i,
        "printed_label": label,
        "value_text": "150",
        "reference_printed": None,
        "flag": None,
        "is_reviewed": False,
        "unit": "mg/dL",
        "section_id": 1,
        "heading_printed": "LIPID PROFILE",
        "analyte_code": code,
        "analyte_name": name,
        "corrected_from": None,
    }


# No HDL row, so HDL is still wanted when the fuzzy pass reaches NON-HDL CHOL.
LIPIDS = [
    _row(1, "Total Cholesterol", "CHOL", "Total Cholesterol"),
    _row(2, "Triglycerides", "TG", "Triglycerides"),
    _row(3, "LDL Cholesterol", "LDL", "LDL Cholesterol"),
]


def _shown(rows: list[dict], templates, label: str) -> dict:
    return next(r for r in merged_rows(rows, templates)["rows"] if r["printed_label"] == label)


def test_the_stored_mapping_is_what_the_row_shows(templates) -> None:
    rows = [*LIPIDS, _row(4, "NON-HDL CHOL.", "NON_HDL", "Non-HDL Cholesterol")]
    shown = _shown(rows, templates, "NON-HDL CHOL.")
    assert (shown["analyte_name"], shown["analyte_code"]) == ("Non-HDL Cholesterol", "NON_HDL")


def test_with_nothing_stored_the_guess_is_still_offered(templates) -> None:
    rows = [*LIPIDS, _row(4, "NON-HDL CHOL.", None, None)]
    shown = _shown(rows, templates, "NON-HDL CHOL.")
    assert shown["analyte_code"] is None
    assert shown["analyte_name"]  # the suggestion, marked "confirm?" on screen
    assert shown["status"] == "confirm"
