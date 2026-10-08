"""confirm-all confirms only what a reviewer would find nothing outstanding on (review B2).

The judgement is tested on real stored documents, each broken one way it was not
broken before, so a test fails if the gate stops seeing that kind of gap. The
endpoint then runs for real through the API in-process: documents are verified
inside db_write's transaction and are back as they were when it rolls back.
"""

from __future__ import annotations

import pytest

from app.services.coverage import NEEDS_A_PERSON, merged_rows, needs_a_person, panel_templates

BY_SIZE = """
SELECT d.id FROM lab.documents d
WHERE  d.practice_id = %s AND d.status = 'verified'
  AND  d.is_deleted = FALSE AND d.patient_id IS NOT NULL
ORDER  BY (SELECT count(*) FROM lab.results r
           WHERE r.document_id = d.id AND r.is_deleted = FALSE) {order}, d.id
LIMIT  %s
"""


@pytest.fixture(scope="module")
def templates(db):
    return panel_templates()


@pytest.fixture(scope="module")
def largest(db) -> list[list[dict]]:
    """The stored rows of the largest verified documents - the ones with panels to check."""
    from app.services.coverage import stored_rows

    practice = db.execute("SELECT min(practice_id) FROM lab.documents").fetchone()[0]
    ids = [r[0] for r in db.execute(BY_SIZE.format(order="DESC"), (practice, 80)).fetchall()]
    rows = stored_rows(practice, ids)
    return [rows[i] for i in ids]


def _core_found(rows: list[dict], templates) -> list[int]:
    """Result ids of the rows coverage counts as a core test, read with its value."""
    return [
        int(r["result_id"])
        for r in merged_rows(rows, templates)["rows"]
        if r["required"] == "core" and r["status"] == "found"
    ]


def _lacking(largest, templates, state: str) -> tuple[list[dict], list[int]]:
    """A document with three or more core tests read and no `state` flagged yet."""
    for rows in largest:
        if NEEDS_A_PERSON[state] in needs_a_person(rows, templates):
            continue
        core = _core_found(rows, templates)
        if len(core) >= 3:
            return rows, core
    pytest.skip(f"no document here without {NEEDS_A_PERSON[state]!r} to break")
    return [], []  # unreachable; pytest.skip raises


def test_a_document_with_nothing_read_is_held(templates) -> None:
    assert needs_a_person([], templates) == ["nothing was read from it"]


def test_an_unread_value_holds_it(largest, templates) -> None:
    rows, core = _lacking(largest, templates, "no_value")
    broken = [{**r, "value_text": ""} if r["id"] == core[0] else r for r in rows]
    assert NEEDS_A_PERSON["no_value"] in needs_a_person(broken, templates)


def test_a_missing_core_test_holds_it(largest, templates) -> None:
    """The only signal for a row lost whole: nothing was stored, so nothing is blank."""
    rows, core = _lacking(largest, templates, "missing")
    broken = [r for r in rows if r["id"] != core[0]]
    assert NEEDS_A_PERSON["missing"] in needs_a_person(broken, templates)


def test_confirm_all_confirms_the_clean_and_holds_the_rest(
    client, db_write, reviewer, templates
) -> None:
    from app.services.coverage import stored_rows

    small = [
        r["id"]
        for r in db_write.execute(
            BY_SIZE.format(order="ASC"), (reviewer.practice_id, 60)
        ).fetchall()
    ]
    rows = stored_rows(reviewer.practice_id, small)
    clean = next((i for i in small if rows[i] and not needs_a_person(rows[i], templates)), None)
    empty = next((i for i in small if not rows[i]), None)
    if clean is None or empty is None:
        pytest.skip("this database has no clean or no empty verified document to re-queue")
    # Both back in the queue, as if just read and matched to their patient.
    db_write.execute(
        "UPDATE lab.documents SET status = 'parsed' WHERE id = ANY(%s)", ([clean, empty],)
    )

    response = client.post("/review/confirm-all")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["confirmed"] >= 1
    assert body["held_because"].get("nothing was read from it", 0) >= 1
    status = {
        r["id"]: r["status"]
        for r in db_write.execute(
            "SELECT id, status FROM lab.documents WHERE id = ANY(%s)", ([clean, empty],)
        ).fetchall()
    }
    assert status == {clean: "verified", empty: "parsed"}
