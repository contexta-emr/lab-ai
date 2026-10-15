"""Uploaded bytes live in lab.document_files, written with the upload (spec section 4, B12)."""

from __future__ import annotations

import uuid

import pytest


def _pdf() -> bytes:
    # Unique per call, so the checksum dedupe never hands back an older document.
    return b"%PDF-1.4\n% " + uuid.uuid4().hex.encode() + b"\n%%EOF\n"


def _stored(db_write, document_id: str) -> list[dict]:
    return db_write.execute(
        "SELECT f.content, f.byte_count FROM lab.document_files f "
        "JOIN lab.documents d ON d.visit_attachment_id = f.visit_attachment_id "
        "WHERE d.id = %s AND f.is_deleted = FALSE",
        (int(document_id),),
    ).fetchall()


def test_an_upload_keeps_its_bytes_in_the_database_not_on_disk(
    client, db_write, monkeypatch, tmp_path
) -> None:
    from app.config import settings

    monkeypatch.setattr(settings(), "storage_dir", tmp_path)
    blob = _pdf()
    response = client.post(
        "/documents", files={"file": ("report.pdf", blob, "application/pdf")}
    )
    assert response.status_code == 201, response.text
    document_id = response.json()["id"]

    [stored] = _stored(db_write, document_id)
    assert bytes(stored["content"]) == blob
    assert stored["byte_count"] == len(blob)
    assert list(tmp_path.iterdir()) == []

    served = client.get(f"/documents/{document_id}/file")
    assert served.status_code == 200
    assert served.content == blob


def test_the_same_file_twice_is_one_document_and_one_copy(client, db_write) -> None:
    blob = _pdf()
    first = client.post("/documents", files={"file": ("a.pdf", blob, "application/pdf")}).json()
    second = client.post(
        "/documents", files={"file": ("b.pdf", blob, "application/pdf")}
    ).json()
    assert first["id"] == second["id"]
    assert len(_stored(db_write, first["id"])) == 1


def test_a_file_over_the_cap_is_refused(client, monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings(), "max_upload_mb", 4)
    big = b"%PDF-1.4\n" + b"0" * (5 * 1024 * 1024)
    response = client.post("/documents", files={"file": ("big.pdf", big, "application/pdf")})
    assert response.status_code == 413


def test_a_name_in_any_script_is_served_without_breaking_the_header(client) -> None:
    document = client.post(
        "/documents", files={"file": ("రిపోర్ట్ रिपोर्ट.pdf", _pdf(), "application/pdf")}
    ).json()
    served = client.get(f"/documents/{document['id']}/file")
    assert served.status_code == 200
    assert served.headers["content-disposition"].startswith("inline; filename*=utf-8''")


def test_a_document_stored_before_033_is_still_read_from_disk(
    client, db_write, reviewer
) -> None:
    from app.config import settings

    rows = db_write.execute(
        "SELECT d.id, va.stored_file_name FROM lab.documents d "
        "JOIN core.visit_attachments va ON va.id = d.visit_attachment_id "
        "WHERE d.practice_id = %s AND d.is_deleted = FALSE AND NOT EXISTS "
        "  (SELECT 1 FROM lab.document_files f WHERE f.visit_attachment_id = va.id) "
        "ORDER BY d.id LIMIT 50",
        (reviewer.practice_id,),
    ).fetchall()
    on_disk = [
        r
        for r in rows
        if r["stored_file_name"] and (settings().storage_dir / r["stored_file_name"]).is_file()
    ]
    if not on_disk:
        pytest.skip("no pre-033 document with its file on disk here")
    row = on_disk[0]
    served = client.get(f"/documents/{row['id']}/file")
    assert served.status_code == 200
    assert served.content == (settings().storage_dir / row["stored_file_name"]).read_bytes()
