"""A person adds a row the reading missed (2026-10-15).

Two ways in, one function: fill in a test the panel expected and the page
printed but the reading lost (Albumin on Ashwini's report), or add any line by
hand. Either way it goes through lab.fn_add_result, is marked as entered by a
person, and is recorded in document_events - the same footing as a correction.
"""

from __future__ import annotations

import uuid

import pytest


@pytest.fixture
def document(client, db_write, reviewer) -> str:
    """A read document of this practice with at least one section."""
    row = db_write.execute(
        "SELECT d.id FROM lab.documents d "
        "WHERE d.practice_id = %s AND d.status IN ('parsed', 'needs_review') "
        "AND d.is_deleted = FALSE AND EXISTS (SELECT 1 FROM lab.report_sections s "
        "  JOIN lab.reports r ON r.id = s.report_id WHERE r.document_id = d.id) "
        "ORDER BY d.id LIMIT 1",
        (reviewer.practice_id,),
    ).fetchone()
    if row is None:
        pytest.skip("no read document with a section in this database")
    return str(row["id"])


def _stored(db_write, result_id: str) -> dict:
    return db_write.execute(
        "SELECT r.printed_label, r.value_text, r.value_numeric, r.unit_printed, r.flag, "
        "r.ref_low, r.ref_high, r.match_method, r.is_reviewed, r.reviewed_by, a.code "
        "FROM lab.results r LEFT JOIN lab.analytes a ON a.id = r.analyte_id WHERE r.id = %s",
        (int(result_id),),
    ).fetchone()


def test_a_test_the_reading_missed_can_be_filled_in(
    client, db_write, document, reviewer
) -> None:
    response = client.post(
        f"/documents/{document}/results",
        json={
            "analyte_code": "ALB",
            "value": "4.2",
            "unit": "g/dL",
            "reference": "3.5 - 5.2",
            "flag": "",
        },
    )
    assert response.status_code == 201, response.text
    stored = _stored(db_write, response.json()["id"])
    assert stored["code"] == "ALB"
    assert stored["printed_label"]  # named after the test when no label was typed
    assert float(stored["value_numeric"]) == 4.2
    assert (float(stored["ref_low"]), float(stored["ref_high"])) == (3.5, 5.2)
    assert stored["match_method"] == "manual"
    assert stored["is_reviewed"] is True
    assert stored["reviewed_by"] == reviewer.user_id


def test_a_line_we_have_no_code_for_is_kept_as_printed(client, db_write, document) -> None:
    label = f"In-house marker {uuid.uuid4().hex[:6]}"
    response = client.post(
        f"/documents/{document}/results", json={"label": label, "value": "12", "flag": "High"}
    )
    assert response.status_code == 201, response.text
    stored = _stored(db_write, response.json()["id"])
    assert stored["printed_label"] == label
    assert stored["code"] is None  # an honest blank, never a guessed code
    assert stored["flag"] == "H"


@pytest.mark.parametrize(
    "body",
    [
        {"analyte_code": "NOT_A_TEST", "value": "1"},
        {"label": "Something", "value": "  "},
        {"value": "3"},
        {"label": "Something", "value": "3", "colour": "red"},
    ],
)
def test_a_line_that_cannot_be_stored_is_refused(client, document, body: dict) -> None:
    assert client.post(f"/documents/{document}/results", json=body).status_code == 400


def test_a_report_still_being_read_cannot_take_lines(client) -> None:
    blob = b"%PDF-1.4\n% " + uuid.uuid4().hex.encode() + b"\n%%EOF\n"
    waiting = client.post(
        "/documents", files={"file": ("w.pdf", blob, "application/pdf")}
    ).json()
    response = client.post(
        f"/documents/{waiting['id']}/results", json={"label": "Albumin", "value": "4"}
    )
    assert response.status_code == 400
