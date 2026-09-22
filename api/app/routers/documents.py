"""Upload a document, watch it parse, read what came out.

The upload path is deliberately boring: store the file, record it as a
visit_attachment, hand the extracted payload to lab.fn_ingest_lab_document, and
let the function decide whether the result is attached or quarantined. The API
makes no clinical judgement of its own.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Body, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.auth import CurrentUserDep
from app.config import settings
from app.db import call_function, fetch_all, fetch_one, transaction
from app.services.coverage import coverage_for
from app.schemas import (DocumentDetail, DocumentSummary, PatientCandidate,
                         ReportOut, ResultOut, SectionOut, parse_id)

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif"}

LIST_SQL = """
SELECT d.id, d.status, d.source, d.detected_uhid, d.detected_uhid_label,
       d.detected_patient_name, d.patient_id, d.patient_match_method,
       d.patient_match_confidence, d.page_count, d.ocr_engine,
       d.extraction_confidence, d.received_at, d.is_synthetic,
       p.first_name || ' ' || p.last_name AS patient_name,
       p.uhid AS patient_uhid,
       va.original_file_name AS file_name,
       (SELECT r.lab_name FROM lab.reports r
         WHERE r.document_id = d.id AND r.is_deleted = FALSE
         ORDER BY r.sequence LIMIT 1) AS lab_name,
       (SELECT min(r.collected_at) FROM lab.reports r
         WHERE r.document_id = d.id AND r.is_deleted = FALSE) AS collected_at,
       (SELECT count(*) FROM lab.results x
         WHERE x.document_id = d.id AND x.is_deleted = FALSE) AS result_count,
       (SELECT count(*) FROM lab.results x
         WHERE x.document_id = d.id AND x.is_deleted = FALSE
           AND x.analyte_id IS NULL) AS unmatched_count
FROM   lab.documents d
LEFT   JOIN core.patients p ON p.id = d.patient_id
LEFT   JOIN core.visit_attachments va ON va.id = d.visit_attachment_id
WHERE  d.practice_id = %s
  AND  d.is_deleted = FALSE
"""


def _row_to_summary(row: dict) -> DocumentSummary:
    return DocumentSummary(
        id=str(row["id"]),
        status=row["status"],
        source=row["source"],
        detected_uhid=row["detected_uhid"],
        detected_uhid_label=row["detected_uhid_label"],
        detected_patient_name=row["detected_patient_name"],
        patient_id=str(row["patient_id"]) if row["patient_id"] else None,
        patient_name=row.get("patient_name"),
        patient_uhid=row.get("patient_uhid"),
        patient_match_method=row["patient_match_method"],
        patient_match_confidence=row["patient_match_confidence"],
        page_count=row["page_count"],
        ocr_engine=row["ocr_engine"],
        extraction_confidence=row["extraction_confidence"],
        result_count=row["result_count"],
        unmatched_count=row["unmatched_count"],
        lab_name=row["lab_name"],
        collected_at=row["collected_at"],
        received_at=row["received_at"],
        is_synthetic=row["is_synthetic"],
        file_name=row.get("file_name"),
    )


@router.get("", response_model=list[DocumentSummary])
def list_documents(
    user: CurrentUserDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    patient_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DocumentSummary]:
    sql, params = LIST_SQL, [user.practice_id]

    if status_filter:
        # The review queue is two statuses, not one.
        if status_filter == "pending":
            sql += " AND d.status IN ('parsed', 'needs_review')"
        else:
            sql += " AND d.status = %s"
            params.append(status_filter)
    if patient_id:
        sql += " AND d.patient_id = %s"
        params.append(parse_id(patient_id, "patient_id"))

    sql += " ORDER BY d.received_at DESC LIMIT %s OFFSET %s"
    params += [limit, offset]
    return [_row_to_summary(r) for r in fetch_all(sql, tuple(params))]


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, user: CurrentUserDep) -> DocumentDetail:
    doc_id = parse_id(document_id, "document_id")

    head = fetch_one(LIST_SQL + " AND d.id = %s", (user.practice_id, doc_id))
    if head is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    rows = fetch_all(
        """
        SELECT rep.id AS report_id, rep.lab_name, rep.accession_no, rep.uhid_printed,
               rep.patient_name_printed, rep.age_printed, rep.sex_printed,
               rep.collected_at, rep.reported_at, rep.referring_doctor, rep.layout_hint,
               s.id AS section_id, s.heading_printed, s.panel_match_method,
               pn.code AS panel_code,
               res.id AS result_id, res.printed_label, res.match_method,
               res.match_confidence, res.value_text, res.value_numeric,
               res.value_operator, COALESCE(res.unit_canonical, res.unit_printed) AS unit,
               res.reference_printed, res.flag, res.is_text_result, res.is_derived,
               res.sequence,
               a.code AS analyte_code, a.display_name AS analyte_name
        FROM   lab.reports rep
        LEFT   JOIN lab.report_sections s ON s.report_id = rep.id AND s.is_deleted = FALSE
        LEFT   JOIN lab.panels pn ON pn.id = s.panel_id
        LEFT   JOIN lab.results res ON res.section_id = s.id AND res.is_deleted = FALSE
        LEFT   JOIN lab.analytes a ON a.id = res.analyte_id
        WHERE  rep.document_id = %s AND rep.practice_id = %s AND rep.is_deleted = FALSE
        ORDER  BY rep.sequence, s.sequence, res.sequence
        """,
        (doc_id, user.practice_id),
    )

    reports: dict[int, ReportOut] = {}
    sections: dict[int, SectionOut] = {}
    for r in rows:
        rep = reports.get(r["report_id"])
        if rep is None:
            rep = ReportOut(
                id=str(r["report_id"]), lab_name=r["lab_name"],
                accession_no=r["accession_no"], uhid_printed=r["uhid_printed"],
                patient_name_printed=r["patient_name_printed"],
                age_printed=r["age_printed"], sex_printed=r["sex_printed"],
                collected_at=r["collected_at"], reported_at=r["reported_at"],
                referring_doctor=r["referring_doctor"], layout_hint=r["layout_hint"],
            )
            reports[r["report_id"]] = rep
        if r["section_id"] is None:
            continue
        sec = sections.get(r["section_id"])
        if sec is None:
            sec = SectionOut(
                id=str(r["section_id"]), heading_printed=r["heading_printed"],
                panel_code=r["panel_code"], panel_match_method=r["panel_match_method"],
            )
            sections[r["section_id"]] = sec
            rep.sections.append(sec)
        if r["result_id"] is not None:
            sec.results.append(ResultOut(
                id=str(r["result_id"]), printed_label=r["printed_label"],
                analyte_code=r["analyte_code"], analyte_name=r["analyte_name"],
                panel_code=r["panel_code"], match_method=r["match_method"],
                match_confidence=r["match_confidence"], value_text=r["value_text"],
                value_numeric=r["value_numeric"], value_operator=r["value_operator"],
                unit=r["unit"], reference_printed=r["reference_printed"],
                flag=r["flag"], is_text_result=r["is_text_result"],
                is_derived=r["is_derived"],
            ))

    for rep_id, rep in reports.items():
        rep.notes = fetch_all(
            "SELECT note_type, marker, note_text FROM lab.report_notes "
            "WHERE report_id = %s AND is_deleted = FALSE ORDER BY sequence",
            (int(rep_id),))

    detail = DocumentDetail(**_row_to_summary(head).model_dump(),
                            reports=list(reports.values()))

    # A quarantined document gets suggestions rather than a decision.
    if head["patient_id"] is None and head["detected_uhid"]:
        detail.candidates = _candidates(user.practice_id, head["detected_uhid"])
    return detail


def _candidates(practice_id: int, uhid: str) -> list[PatientCandidate]:
    rows = call_function("lab.fn_match_patient_by_uhid", practice_id, uhid, 0.45,
                         returns_table=True)
    out = []
    for r in rows:
        p = fetch_one(
            "SELECT first_name, last_name, dob FROM core.patients WHERE id = %s",
            (r["patient_id"],))
        out.append(PatientCandidate(
            patient_id=str(r["patient_id"]), uhid=r["matched_uhid"],
            full_name=f"{p['first_name']} {p['last_name']}" if p else "",
            dob=p["dob"] if p else None,
            match_method=r["match_method"], confidence=r["confidence"],
        ))
    return out


@router.post("", response_model=DocumentSummary, status_code=status.HTTP_201_CREATED)
async def upload_document(
    user: CurrentUserDep,
    file: Annotated[UploadFile, File(description="PDF or image of a lab report")],
) -> DocumentSummary:
    cfg = settings()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            f"{suffix or 'that file type'} is not accepted. "
                            f"Allowed: {', '.join(sorted(ALLOWED))}")

    blob = await file.read()
    if len(blob) > cfg.max_upload_mb * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"File is larger than {cfg.max_upload_mb} MB")
    if not blob:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is empty")

    checksum = hashlib.sha256(blob).hexdigest()

    # Same bytes, same document. Return the original rather than making a
    # reviewer reconcile two rows that say the same thing.
    existing = fetch_one(
        LIST_SQL + " AND d.checksum_sha256 = %s", (user.practice_id, checksum))
    if existing:
        return _row_to_summary(existing)

    stored_name = f"{checksum[:16]}_{datetime.utcnow():%Y%m%d%H%M%S}{suffix}"
    target = cfg.storage_dir / stored_name
    target.write_bytes(blob)

    with transaction() as conn:
        attachment = conn.execute(
            """
            INSERT INTO core.visit_attachments (
                practice_id, uploaded_by, original_file_name, stored_file_name,
                file_extension, mime_type, file_size_bytes, storage_provider,
                azure_blob_path, source, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'local', %s, 'emr_user', %s)
            RETURNING id
            """,
            (user.practice_id, user.user_id, file.filename, stored_name, suffix,
             file.content_type, len(blob), str(target), user.user_id),
        ).fetchone()

        # A placeholder, and then the doctor's browser is released.
        #
        # Reading is done by OpenParser, which is hosted and slow: measured
        # over the full corpus run, 38.9 seconds a document sustained, with
        # roughly 2% transient failures. Calling it here would block the
        # upload for the best part of a minute and lose it outright when the
        # network hiccups. scripts/ocr_worker.py claims this document, reads
        # it, and replaces it through lab.fn_complete_document.
        #
        # The row exists immediately and on purpose: the reviewer sees the
        # upload arrive in 'received' rather than wondering whether it landed.
        payload = {
            "source": "emr_upload",
            "visit_attachment_id": attachment["id"],
            "checksum_sha256": checksum,
            "page_count": 1,
            "has_text_layer": False,
            "ocr_engine": "none",
            "engine_version": "",
            "extraction_confidence": 0.0,
            "reports": [{
                "lab_name": None,
                "uhid_printed": None,
                "sections": [],
                "notes": [{"note_type": "remark",
                           "note_text": "Queued for extraction."}],
            }],
        }
        doc_id = conn.execute(
            "SELECT lab.fn_ingest_lab_document(%s, %s::jsonb, %s) AS id",
            (user.practice_id, json.dumps(payload), user.user_id),
        ).fetchone()["id"]
        conn.execute(
            "UPDATE lab.documents SET status = 'received' WHERE id = %s", (doc_id,))

    row = fetch_one(LIST_SQL + " AND d.id = %s", (user.practice_id, doc_id))
    return _row_to_summary(row)

@router.get("/{document_id}/file")
def get_document_file(document_id: str, user: CurrentUserDep):
    """The uploaded file itself, so the console can show the page.

    Served through the API rather than from a static directory because the
    file is a patient's lab report: it has to be scoped to the practice on the
    way out, exactly like every other read here. A static mount would hand out
    any document to anyone who guessed a filename.

    inline, not attachment - the point is to display it beside the extracted
    values, not to download it.
    """
    doc_id = parse_id(document_id, "document_id")
    row = fetch_one(
        """
        SELECT va.stored_file_name, va.original_file_name, va.mime_type
        FROM   lab.documents d
        JOIN   core.visit_attachments va ON va.id = d.visit_attachment_id
        WHERE  d.id = %s AND d.practice_id = %s AND d.is_deleted = FALSE
        """,
        (doc_id, user.practice_id),
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "No stored file for that document")

    # Resolved from the configured storage directory and the stored NAME, never
    # from a path in the database. A path column is a value someone could set.
    target = settings().storage_dir / Path(row["stored_file_name"]).name
    if not target.is_file():
        raise HTTPException(status.HTTP_410_GONE,
                            "The file is no longer in storage")

    return FileResponse(
        target,
        media_type=row["mime_type"] or "application/pdf",
        filename=row["original_file_name"] or target.name,
        content_disposition_type="inline",
    )


@router.get("/{document_id}/coverage")
def get_document_coverage(document_id: str, user: CurrentUserDep) -> dict:
    """What this document should have contained, against what it did.

    found / missing / extra. The only way to notice a dropped row on a real
    report, where there is no answer key to score against.
    """
    doc_id = parse_id(document_id, "document_id")
    rows = fetch_all(
        """
        SELECT res.printed_label, res.value_text, res.reference_printed, res.flag,
               COALESCE(res.unit_canonical, res.unit_printed) AS unit,
               s.id AS section_id, s.heading_printed
        FROM   lab.results res
        LEFT   JOIN lab.report_sections s ON s.id = res.section_id
        WHERE  res.document_id = %s AND res.practice_id = %s
          AND  res.is_deleted = FALSE
        ORDER  BY res.section_id NULLS FIRST, res.sequence
        """,
        (doc_id, user.practice_id),
    )
    return coverage_for(rows)


@router.patch("/{document_id}/results/{result_id}")
def correct_result(document_id: str, result_id: str, user: CurrentUserDep,
                   body: dict = Body(...)) -> dict:
    """A reviewer fixes one row.

    Only the fields present in the body change; anything omitted is left
    alone, so editing one cell cannot quietly blank the others. An empty
    string is a real value and clears the field - that is how a reviewer says
    "there is no unit here" as opposed to "I did not touch the unit".

    Goes through lab.fn_correct_result, which records what the machine thought
    in corrected_from_analyte_id and writes the whole change to
    document_events. A corrected label is the most valuable thing this system
    produces: a real spelling a real lab printed, mapped by a human to a real
    code, which is exactly what the alias master cannot invent for itself.
    """
    doc_id = parse_id(document_id, "document_id")
    res_id = parse_id(result_id, "result_id")

    allowed = {"label", "value", "unit", "reference", "flag", "analyte_code"}
    unknown = set(body) - allowed
    if unknown:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"cannot edit {', '.join(sorted(unknown))}")

    owned = fetch_one(
        "SELECT 1 FROM lab.results WHERE id = %s AND document_id = %s "
        "AND practice_id = %s AND is_deleted = FALSE",
        (res_id, doc_id, user.practice_id))
    if owned is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such row on that document")

    try:
        with transaction() as conn:
            conn.execute(
                "SELECT lab.fn_correct_result(%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (user.practice_id, res_id, user.user_id,
                 body.get("label"), body.get("value"), body.get("unit"),
                 body.get("reference"), body.get("flag"), body.get("analyte_code")))
    except Exception as exc:                                  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc).strip()) from exc

    return _result_row(res_id, user.practice_id)


@router.delete("/{document_id}/results/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_result(document_id: str, result_id: str, user: CurrentUserDep) -> None:
    """Remove a row the engine should not have produced.

    Soft, and recorded. A row invented out of a footer is evidence of what the
    extractor gets wrong, and a reviewer who removes the wrong one has to be
    able to get it back.
    """
    doc_id = parse_id(document_id, "document_id")
    res_id = parse_id(result_id, "result_id")

    owned = fetch_one(
        "SELECT 1 FROM lab.results WHERE id = %s AND document_id = %s "
        "AND practice_id = %s AND is_deleted = FALSE",
        (res_id, doc_id, user.practice_id))
    if owned is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such row on that document")

    with transaction() as conn:
        conn.execute("SELECT lab.fn_remove_result(%s, %s, %s)",
                     (user.practice_id, res_id, user.user_id))


def _result_row(result_id: int, practice_id: int) -> dict:
    """One row as the console shows it, after a correction."""
    row = fetch_one(
        """
        SELECT res.id, res.printed_label, res.value_text, res.value_numeric,
               res.value_operator, res.flag, res.reference_printed,
               res.match_method, res.match_confidence, res.is_text_result,
               res.is_derived, res.is_reviewed,
               COALESCE(res.unit_canonical, res.unit_printed) AS unit,
               a.code AS analyte_code, a.display_name AS analyte_name,
               was.code AS corrected_from
        FROM   lab.results res
        LEFT   JOIN lab.analytes a   ON a.id = res.analyte_id
        LEFT   JOIN lab.analytes was ON was.id = res.corrected_from_analyte_id
        WHERE  res.id = %s AND res.practice_id = %s
        """,
        (result_id, practice_id))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Row not found")
    row["id"] = str(row["id"])
    for key in ("value_numeric", "match_confidence"):
        if row[key] is not None:
            row[key] = float(row[key])
    return row
