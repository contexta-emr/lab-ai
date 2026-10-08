"""The fixture purge removes everything under a document, document_lists included.

Migration 031. Before it, a document carrying a doctor's order could not be
purged: the foreign key from lab.document_lists stopped the whole function, and
bench/run.ps1 went on to score the old run as a new one. Each test executes the
migration inside db_write's transaction, which is always rolled back.
"""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

MIGRATION = "031_purge_reaches_document_lists.sql"


def _migration() -> str:
    for root in (Path(__file__).resolve().parents[2] / "db", Path("/work/db")):
        if (root / MIGRATION).exists():
            return (root / MIGRATION).read_text(encoding="utf-8")
    pytest.skip(f"{MIGRATION} is not reachable from here")
    return ""  # unreachable; pytest.skip raises


def _document_with_a_list(conn: psycopg.Connection) -> tuple[int, int, str]:
    """A synthetic document carrying a doctor's order, made so in the transaction."""
    row = conn.execute(
        "SELECT id, practice_id, checksum_sha256 FROM lab.documents ORDER BY id LIMIT 1"
    ).fetchone()
    if row is None:
        pytest.skip("no document in this database")
    doc_id, practice_id, checksum = row
    conn.execute("UPDATE lab.documents SET is_synthetic = TRUE WHERE id = %s", (doc_id,))
    # Not ON CONFLICT: the unique index is partial, over live lists only.
    conn.execute(
        "INSERT INTO lab.document_lists (document_id, practice_id, kind, raw_text) "
        "SELECT %s, %s, 'doctor_order', 'HbA1c, lipid profile' "
        "WHERE NOT EXISTS (SELECT 1 FROM lab.document_lists "
        "                  WHERE document_id = %s AND kind = 'doctor_order' AND NOT is_deleted)",
        (doc_id, practice_id, doc_id),
    )
    return doc_id, practice_id, checksum


def test_a_document_with_a_doctors_order_can_be_purged(db_write) -> None:
    db_write.execute(_migration())
    doc_id, practice_id, checksum = _document_with_a_list(db_write)

    removed = db_write.execute(
        "SELECT documents_removed FROM lab.fn_purge_synthetic(%s, %s)", (practice_id, checksum)
    ).fetchone()[0]

    assert removed >= 1
    for table, column in (("lab.documents", "id"), ("lab.document_lists", "document_id")):
        left = db_write.execute(
            f"SELECT count(*) FROM {table} WHERE {column} = %s",  # noqa: S608 - fixed names
            (doc_id,),
        ).fetchone()[0]
        assert left == 0, f"{table} still holds document {doc_id}"
