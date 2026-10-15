"""GET /master/analytes lists the vocabulary - "Add a line" searches it (2026-10-15).

It sorted and filtered by a panel alias, pn, that the query stopped joining when
026 dropped analytes.panel_id, so every call failed: unnoticed until the review
screen needed the list.
"""

from __future__ import annotations


def test_every_test_we_know_is_listed(client) -> None:
    response = client.get("/master/analytes")
    assert response.status_code == 200, response.text
    codes = {a["code"] for a in response.json()}
    assert {"ALB", "HGB", "WBC", "RBC"} <= codes


def test_a_panel_narrows_the_list_to_its_members(client) -> None:
    response = client.get("/master/analytes", params={"panel": "LFT"})
    assert response.status_code == 200, response.text
    codes = {a["code"] for a in response.json()}
    assert "ALB" in codes
    assert "HGB" not in codes
