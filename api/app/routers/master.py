"""The analyte master: the vocabulary, and the gaps it knows it has."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.auth import CurrentUserDep
from app.db import fetch_all
from app.schemas import AnalyteOut, PanelOut, ResolveManyIn, UnmatchedLabelOut
from app.services.term_resolver import MAX_TERMS, resolve_terms, split_terms

router = APIRouter(prefix="/master", tags=["master"])


@router.get("/panels", response_model=list[PanelOut])
def panels(_user: CurrentUserDep, core_only: bool = False) -> list[PanelOut]:
    sql = """
        SELECT p.id, p.code, p.display_name, p.description, p.is_core,
               -- membership, not the analyte's nominal panel: an analyte
               -- belongs to several, and this count is the panel's size
               (SELECT count(*) FROM lab.panel_analytes pa
                 WHERE pa.panel_id = p.id AND pa.is_deleted = FALSE) AS analyte_count
        FROM   lab.panels p
        WHERE  p.is_deleted = FALSE
    """
    if core_only:
        sql += " AND p.is_core = TRUE"
    sql += " ORDER BY p.sort_order"
    return [
        PanelOut(
            id=str(r["id"]),
            code=r["code"],
            display_name=r["display_name"],
            description=r["description"],
            is_core=r["is_core"],
            analyte_count=r["analyte_count"],
        )
        for r in fetch_all(sql)
    ]


@router.get("/analytes", response_model=list[AnalyteOut])
def analytes(
    _user: CurrentUserDep,
    panel: str | None = None,
    q: str | None = None,
) -> list[AnalyteOut]:
    sql = """
        SELECT a.id, a.code, a.display_name, a.default_unit, a.value_type,
               a.is_derived,
               -- The FIRST panel it belongs to, by panel sort order. An analyte
               -- in three panels has no single panel_code; this field keeps the
               -- shape callers expect while the join table holds the truth.
               (SELECT p2.code FROM lab.panel_analytes pa2
                  JOIN lab.panels p2 ON p2.id = pa2.panel_id
                 WHERE pa2.analyte_id = a.id AND pa2.is_deleted = FALSE
                 ORDER BY p2.sort_order, p2.code LIMIT 1) AS panel_code,
               (SELECT count(*) FROM lab.analyte_aliases al
                 WHERE al.analyte_id = a.id AND al.is_deleted = FALSE) AS alias_count
        FROM   lab.analytes a
        WHERE  a.is_deleted = FALSE
    """
    params: list = []
    # Through lab.panel_analytes: 026 dropped analytes.panel_id, and the pn
    # alias this used to filter and sort by went with it - every call failed.
    if panel:
        sql += """ AND EXISTS (SELECT 1 FROM lab.panel_analytes pa
                                JOIN lab.panels p ON p.id = pa.panel_id
                               WHERE pa.analyte_id = a.id AND pa.is_deleted = FALSE
                                 AND p.code = %s)"""
        params.append(panel)
    if q:
        sql += " AND (a.code ILIKE %s OR a.display_name ILIKE %s)"
        params += [f"%{q}%", f"%{q}%"]
    sql += """ ORDER BY (SELECT min(p3.sort_order) FROM lab.panel_analytes pa3
                          JOIN lab.panels p3 ON p3.id = pa3.panel_id
                         WHERE pa3.analyte_id = a.id AND pa3.is_deleted = FALSE) NULLS LAST,
                      a.sort_order"""

    return [
        AnalyteOut(
            id=str(r["id"]),
            code=r["code"],
            display_name=r["display_name"],
            panel_code=r["panel_code"],
            default_unit=r["default_unit"],
            value_type=r["value_type"],
            is_derived=r["is_derived"],
            alias_count=r["alias_count"],
        )
        for r in fetch_all(sql, tuple(params) if params else None)
    ]


@router.get("/analytes/{code}/aliases")
def aliases(code: str, user: CurrentUserDep) -> list[dict]:
    """Every spelling this test is known to arrive under."""
    return fetch_all(
        """
        SELECT al.alias, al.source, al.confidence, al.practice_id
        FROM   lab.analyte_aliases al
        JOIN   lab.analytes a ON a.id = al.analyte_id
        WHERE  a.code = %s AND al.is_deleted = FALSE
          AND  (al.practice_id IS NULL OR al.practice_id = %s)
        ORDER  BY al.practice_id NULLS FIRST, al.alias
        """,
        (code, user.practice_id),
    )


@router.get("/resolve")
def resolve(
    user: CurrentUserDep,
    label: Annotated[str, Query(description="a printed test name, as it appears")],
) -> dict:
    """Try a label against the master. The quickest way to debug a bad extraction."""
    # Cast explicitly: fn_resolve_analyte takes (BIGINT, TEXT, BIGINT, REAL)
    # and psycopg sends a Python float as double precision, which PostgreSQL
    # will not resolve to real. See the note on db.call_function.
    rows = fetch_all(
        "SELECT * FROM lab.fn_resolve_analyte(%s::BIGINT, %s::TEXT, "
        "                                     %s::BIGINT, %s::REAL)",
        (user.practice_id, label, None, 0.45),
    )
    if not rows:
        return {
            "label": label,
            "matched": False,
            "note": (
                "No analyte matched. The pipeline stores NULL here, which is "
                "the correct answer for a test the vocabulary does not have."
            ),
        }
    r = rows[0]
    return {
        "label": label,
        "matched": True,
        "analyte_code": r["analyte_code"],
        "match_method": r["match_method"],
        "confidence": float(r["confidence"]),
    }


@router.post("/resolve-many")
def resolve_many(user: CurrentUserDep, body: ResolveManyIn) -> dict:
    """Resolve a typed list of tests against the master, in one round trip.

    The work is in app/services/term_resolver.py, shared with the document lists
    so the same word cannot resolve differently depending on which box it was
    typed into - both boxes are visible on the same screen.
    """
    terms = split_terms(chr(10).join(body.labels))
    return {
        "terms": resolve_terms(user.practice_id, terms),
        "truncated_at": MAX_TERMS if len(body.labels) > MAX_TERMS else None,
    }


@router.get("/unmatched", response_model=list[UnmatchedLabelOut])
def unmatched(
    user: CurrentUserDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[UnmatchedLabelOut]:
    """Printed labels the master could not name, commonest first.

    The work queue for growing the vocabulary, and the honest measure of how
    much of the real world it still misses.
    """
    rows = fetch_all(
        """
        SELECT id, printed_label, occurrence_count, sample_unit, sample_value,
               last_seen_at
        FROM   lab.unmatched_labels
        WHERE  (practice_id IS NULL OR practice_id = %s)
          AND  resolved_analyte_id IS NULL
        ORDER  BY occurrence_count DESC, last_seen_at DESC
        LIMIT  %s
        """,
        (user.practice_id, limit),
    )
    return [
        UnmatchedLabelOut(
            id=str(r["id"]),
            printed_label=r["printed_label"],
            occurrence_count=r["occurrence_count"],
            sample_unit=r["sample_unit"],
            sample_value=r["sample_value"],
            last_seen_at=r["last_seen_at"],
        )
        for r in rows
    ]
