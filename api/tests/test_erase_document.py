"""Deleting a report erases it for good (2026-10-15, Karthik's call).

The report, its results, its notes, its lists, its history and the uploaded
file itself are removed from the database - a real patient's report uploaded
by mistake must be able to leave completely. One line stays in
lab.document_deletions: which document, who, when, what state it was in. No
file name, no label, no value: file names are often the patient's name.
"""

from __future__ import annotations

import uuid

import pytest


def _upload(client) -> str:
    blob = b"%PDF-1.4\n% " + uuid.uuid4().hex.encode() + b"\n%%EOF\n"
    response = client.post(
        "/documents", files={"file": ("Mr X report.pdf", blob, "application/pdf")}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _left(db_write, document_id: str) -> dict[str, int]:
    doc = int(document_id)
    counts = db_write.execute(
        """
        SELECT
          (SELECT count(*) FROM lab.documents WHERE id = %(d)s) AS documents,
          (SELECT count(*) FROM lab.reports WHERE document_id = %(d)s) AS reports,
          (SELECT count(*) FROM lab.results WHERE document_id = %(d)s) AS results,
          (SELECT count(*) FROM lab.document_events WHERE document_id = %(d)s) AS events
        """,
        {"d": doc},
    ).fetchone()
    return dict(counts)


def test_a_deleted_report_is_gone_with_its_file(client, db_write, reviewer) -> None:
    uploaded = _upload(client)
    attachment = db_write.execute(
        "SELECT visit_attachment_id FROM lab.documents WHERE id = %s", (int(uploaded),)
    ).fetchone()["visit_attachment_id"]

    response = client.delete(f"/documents/{uploaded}")

    assert response.status_code == 204, response.text
    assert _left(db_write, uploaded) == {
        "documents": 0,
        "reports": 0,
        "results": 0,
        "events": 0,
    }
    files = db_write.execute(
        "SELECT count(*) AS n FROM lab.document_files WHERE visit_attachment_id = %s",
        (attachment,),
    ).fetchone()["n"]
    attachments = db_write.execute(
        "SELECT count(*) AS n FROM core.visit_attachments WHERE id = %s", (attachment,)
    ).fetchone()["n"]
    assert files == 0
    assert attachments == 0
    assert client.get(f"/documents/{uploaded}").status_code == 404


def test_the_deletion_is_recorded_without_the_report(client, db_write, reviewer) -> None:
    uploaded = _upload(client)
    client.delete(f"/documents/{uploaded}")
    row = db_write.execute(
        "SELECT * FROM lab.document_deletions WHERE document_id = %s", (int(uploaded),)
    ).fetchone()
    assert row is not None
    assert row["deleted_by"] == reviewer.user_id
    assert row["practice_id"] == reviewer.practice_id
    # Nothing that could name the patient: no file name, label or value column at all.
    assert not {"file_name", "original_file_name", "printed_label", "value_text"} & set(row)


def test_the_same_file_can_be_uploaded_again_after_deleting(client) -> None:
    blob = b"%PDF-1.4\n% " + uuid.uuid4().hex.encode() + b"\n%%EOF\n"
    file = {"file": ("again.pdf", blob, "application/pdf")}
    first = client.post("/documents", files=file).json()
    assert client.delete(f"/documents/{first['id']}").status_code == 204
    second = client.post("/documents", files=file)
    assert second.status_code == 201
    assert second.json()["id"] != first["id"]


def test_a_read_and_checked_report_can_be_deleted_too(client, db_write, reviewer) -> None:
    row = db_write.execute(
        "SELECT id FROM lab.documents WHERE practice_id = %s AND status = 'verified' "
        "AND is_deleted = FALSE ORDER BY id LIMIT 1",
        (reviewer.practice_id,),
    ).fetchone()
    if row is None:
        pytest.skip("no verified document here")
    assert client.delete(f"/documents/{row['id']}").status_code == 204
    assert _left(db_write, str(row["id"]))["results"] == 0


def test_a_report_of_another_practice_cannot_be_deleted(client, db_write, reviewer) -> None:
    other = db_write.execute(
        "SELECT id FROM lab.documents WHERE practice_id <> %s AND is_deleted = FALSE LIMIT 1",
        (reviewer.practice_id,),
    ).fetchone()
    if other is None:
        pytest.skip("no other practice's document here")
    assert client.delete(f"/documents/{other['id']}").status_code == 404
    assert _left(db_write, str(other["id"]))["documents"] == 1
