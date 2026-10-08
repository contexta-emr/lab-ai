"""The review queue: a human settles what the machine was unsure about.

Every decision goes through lab.fn_review_lab_document, which cascades the
patient down to reports and results and writes a row to lab.document_events.
Nothing here updates a table directly, so there is exactly one code path by
which a document becomes clinical fact.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.auth import CurrentUserDep, ReviewerDep
from app.db import fetch_all, fetch_one
from app.schemas import ReviewRequest, ReviewResponse, parse_id

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue")
def queue(
    user: CurrentUserDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    status: Annotated[str | None, Query(description="needs_review | parsed")] = None,
) -> dict:
    """What is waiting, and why each one is waiting.

    Returns ``total`` alongside ``items`` because the list is capped. Counting 300
    documents in the headline and silently showing 50 of them is how a reviewer
    concludes 259 documents have vanished - which is exactly what happened.
    """
    wanted = ("needs_review", "parsed") if status is None else (status,)
    rows = fetch_all(
        """
        SELECT d.id, d.status, d.detected_uhid, d.detected_patient_name,
               d.patient_match_method, d.patient_match_confidence,
               d.extraction_confidence, d.received_at, d.ocr_engine,
               va.original_file_name AS file_name,
               (SELECT r.lab_name FROM lab.reports r
                 WHERE r.document_id = d.id AND r.is_deleted = FALSE
                 ORDER BY r.sequence LIMIT 1) AS lab_name,
               (SELECT count(*) FROM lab.results x
                 WHERE x.document_id = d.id AND x.is_deleted = FALSE) AS result_count,
               (SELECT count(*) FROM lab.results x
                 WHERE x.document_id = d.id AND x.is_deleted = FALSE
                   AND x.analyte_id IS NULL) AS unmatched_count
        FROM   lab.documents d
        LEFT   JOIN core.visit_attachments va ON va.id = d.visit_attachment_id
        WHERE  d.practice_id = %s
          AND  d.is_deleted = FALSE
          AND  d.status = ANY(%s)
        ORDER  BY (d.status = 'needs_review') DESC, d.received_at
        LIMIT  %s
        """,
        (user.practice_id, list(wanted), limit),
    )

    for r in rows:
        r["id"] = str(r["id"])
        if r["patient_match_method"] in (None, "none"):
            r["reason"] = "No patient matched the UHID on the page"
        elif r["status"] == "needs_review":
            r["reason"] = (
                f"UHID matched only approximately "
                f"({float(r['patient_match_confidence'] or 0):.0%})"
            )
        elif (r["extraction_confidence"] or 1) < 0.5:
            r["reason"] = "Extraction confidence is low; the image may be unreadable"
        else:
            r["reason"] = "Matched, awaiting confirmation"

    counts = fetch_one(
        """
        SELECT count(*) FILTER (WHERE status = 'needs_review') AS needs_review,
               count(*) FILTER (WHERE status = 'parsed')       AS awaiting_confirm,
               count(*) FILTER (WHERE status = 'verified')     AS verified,
               count(*) FILTER (WHERE status = 'rejected')     AS rejected
        FROM   lab.documents
        WHERE  practice_id = %s AND is_deleted = FALSE
        """,
        (user.practice_id,),
    )
    total = fetch_one(
        """
        SELECT count(*) AS n FROM lab.documents
        WHERE  practice_id = %s AND is_deleted = FALSE AND status = ANY(%s)
        """,
        (user.practice_id, list(wanted)),
    )
    return {"counts": counts, "items": rows, "total": total["n"], "showing": len(rows)}


@router.post("/confirm-all")
def confirm_all(user: ReviewerDep, note: str | None = None) -> dict:
    """Confirm every document already matched to a patient and waiting.

    Only touches status 'parsed' - documents where the UHID found somebody and the
    only thing missing is a person agreeing. Documents in 'needs_review' matched
    nobody, so there is nothing to agree with and they are left alone.

    This turns readings into clinical fact in bulk, which is the whole reason the
    confirmation exists, so the caller is expected to have asked first. Each row goes
    through fn_review_lab_document, so the audit trail and the patient cascade are
    identical to confirming them one at a time - no shortcut write.
    """
    rows = fetch_all(
        """
        SELECT lab.fn_review_lab_document(%s, d.id, NULL, %s, 'verify', %s) AS status
        FROM   lab.documents d
        WHERE  d.practice_id = %s
          AND  d.status = 'parsed'
          AND  d.patient_id IS NOT NULL
          AND  d.is_deleted = FALSE
        """,
        (
            user.practice_id,
            user.user_id,
            note or "confirmed in bulk from the queue",
            user.practice_id,
        ),
    )
    return {"confirmed": len(rows)}


# DECLARED BEFORE THE "/{document_id}" ROUTE BELOW, AND IT MUST STAY THERE.
#
# Routes match in declaration order. With this one second, a POST to
# /review/confirm-all matched /review/{document_id} with document_id set to
# the literal string "confirm-all", and that route requires a ReviewIn body -
# so the button returned 422 "body: field required" and confirmed nothing. A
# literal path segment has to come before the wildcard that would swallow it.
@router.post("/{document_id}", response_model=ReviewResponse)
def review_document(
    document_id: str,
    body: ReviewRequest,
    user: ReviewerDep,
) -> ReviewResponse:
    doc_id = parse_id(document_id, "document_id")
    patient_id = parse_id(body.patient_id, "patient_id") if body.patient_id else None

    # No patient means "confirm the match already on the document". The function
    # resolves it and refuses if there is nobody there, so the check that used to
    # live here would only reject a legitimate confirmation.

    row = fetch_one(
        "SELECT lab.fn_review_lab_document(%s, %s, %s, %s, %s, %s) AS status",
        (user.practice_id, doc_id, patient_id, user.user_id, body.decision, body.note),
    )
    return ReviewResponse(
        document_id=document_id,
        status=row["status"],
        patient_id=body.patient_id,
    )


@router.get("/{document_id}/events")
def document_events(document_id: str, user: CurrentUserDep) -> list[dict]:
    """The audit trail. Append-only, and the answer when something goes wrong."""
    doc_id = parse_id(document_id, "document_id")
    rows = fetch_all(
        """
        SELECT e.event_type, e.from_status, e.to_status, e.detail, e.created_at,
               u.email AS actor_email
        FROM   lab.document_events e
        LEFT   JOIN core.users u ON u.id = e.actor_user_id
        WHERE  e.document_id = %s AND e.practice_id = %s
        ORDER  BY e.created_at
        """,
        (doc_id, user.practice_id),
    )
    return rows
