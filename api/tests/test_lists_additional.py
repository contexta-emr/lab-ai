"""Panels on the page the doctor did not ask for.

Ordered CBC; the page has CBC and a lipid profile: the lipid profile is
additional - extra, not missing - and is listed with how much of it was read.
"""

from __future__ import annotations

from app.services.lists import additional_panels

ON_THE_PAGE = {
    "CBC": {
        "panel_name": "Complete Blood Count (CBC)",
        "read": 21,
        "accounted": 23,
        "expected": 23,
    },
    "LIPID": {"panel_name": "Lipid Profile", "read": 7, "accounted": 7, "expected": 8},
}


def test_a_panel_on_the_page_that_was_not_ordered_is_additional() -> None:
    extra = additional_panels(ON_THE_PAGE, [{"kind": "panel", "panel_code": "CBC"}])
    assert [x["panel_code"] for x in extra] == ["LIPID"]
    assert (extra[0]["accounted"], extra[0]["expected"], extra[0]["complete"]) == (7, 8, False)


def test_an_ordered_panel_is_not_additional() -> None:
    ordered = [{"kind": "panel", "panel_code": "CBC"}, {"kind": "panel", "panel_code": "LIPID"}]
    assert additional_panels(ON_THE_PAGE, ordered) == []


def test_ordering_one_test_does_not_cover_the_rest_of_its_panel() -> None:
    """Asked for cholesterol; the lab ran the whole lipid profile - the rest is extra."""
    ordered = [{"kind": "analyte", "analytes": [{"analyte_code": "CHOL"}]}]
    assert {x["panel_code"] for x in additional_panels(ON_THE_PAGE, ordered)} == {
        "CBC",
        "LIPID",
    }


def test_a_whole_panel_reads_as_complete() -> None:
    extra = additional_panels(ON_THE_PAGE, [{"kind": "panel", "panel_code": "LIPID"}])
    assert extra[0]["complete"] is True
