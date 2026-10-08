"""fn_fail_document may only fail a document that is still being read (review B5).

Each test executes migration 030 itself inside db_write's transaction, which is
always rolled back. So these validate the migration as written - before anyone
has applied it, and without leaving it applied - and the database the other
tests read is untouched.
"""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

MIGRATION = "030_fail_only_what_is_in_flight.sql"


def _migration() -> str:
    for root in (Path(__file__).resolve().parents[2] / "db", Path("/work/db")):
        if (root / MIGRATION).exists():
            return (root / MIGRATION).read_text(encoding="utf-8")
    pytest.skip(f"{MIGRATION} is not reachable from here")
    return ""  # unreachable; pytest.skip raises


def _document(conn: psycopg.Connection, status: str) -> tuple[int, int]:
    row = conn.execute(
        "SELECT id, practice_id FROM lab.documents WHERE status = %s AND NOT is_deleted LIMIT 1",
        (status,),
    ).fetchone()
    if row is None:
        pytest.skip(f"no {status} document in this database")
    return row


def _status(conn: psycopg.Connection, document_id: int) -> str:
    return conn.execute(
        "SELECT status FROM lab.documents WHERE id = %s", (document_id,)
    ).fetchone()[0]


@pytest.mark.parametrize("finished", ["parsed", "needs_review", "verified"])
def test_a_late_failure_leaves_a_finished_document_alone(db_write, finished: str) -> None:
    """The losing worker's error path, after the winner completed the document."""
    db_write.execute(_migration())
    doc_id, practice_id = _document(db_write, finished)

    returned = db_write.execute(
        "SELECT lab.fn_fail_document(%s, %s, %s)",
        (practice_id, doc_id, "document is not awaiting extraction"),
    ).fetchone()[0]

    assert returned == finished
    assert _status(db_write, doc_id) == finished


def test_a_late_failure_is_recorded_not_lost(db_write) -> None:
    db_write.execute(_migration())
    doc_id, practice_id = _document(db_write, "parsed")
    db_write.execute("SELECT lab.fn_fail_document(%s, %s, %s)", (practice_id, doc_id, "late"))
    event = db_write.execute(
        "SELECT event_type FROM lab.document_events WHERE document_id = %s "
        "ORDER BY created_at DESC, id DESC LIMIT 1",
        (doc_id,),
    ).fetchone()[0]
    assert event == "ocr_failure_ignored"


def test_a_document_still_being_read_is_still_failed(db_write) -> None:
    """The guard must not stop the function doing its actual job."""
    db_write.execute(_migration())
    doc_id, practice_id = _document(db_write, "parsed")
    db_write.execute(
        "UPDATE lab.documents SET status = 'parsing', ocr_attempts = 1 WHERE id = %s", (doc_id,)
    )
    returned = db_write.execute(
        "SELECT lab.fn_fail_document(%s, %s, %s)", (practice_id, doc_id, "OpenParser 503")
    ).fetchone()[0]
    assert returned == "received"
    assert _status(db_write, doc_id) == "received"
