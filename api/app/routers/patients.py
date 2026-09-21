"""Patients, their documents, and the trend a doctor actually asked for."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.auth import CurrentUserDep
from app.db import call_function, fetch_all, fetch_one
from app.schemas import PatientOut, TrendPoint, TrendResponse, parse_id

router = APIRouter(prefix="/patients", tags=["patients"])

PATIENT_SQL = """
SELECT p.id, p.uhid, p.first_name, p.last_name, p.dob, p.gender, p.city,
       (SELECT count(*) FROM lab.documents d
         WHERE d.patient_id = p.id AND d.is_deleted = FALSE) AS document_count,
       (SELECT count(*) FROM lab.results r
         WHERE r.patient_id = p.id AND r.is_deleted = FALSE) AS result_count,
       (SELECT max(r.collected_at) FROM lab.reports r
         WHERE r.patient_id = p.id AND r.is_deleted = FALSE) AS last_report_at
FROM   core.patients p
WHERE  p.practice_id = %s AND p.is_deleted = FALSE
"""


def _to_out(r: dict) -> PatientOut:
    return PatientOut(
        id=str(r["id"]),
        uhid=r["uhid"],
        full_name=f"{r['first_name']} {r['last_name']}".strip(),
        dob=r["dob"],
        gender=r["gender"],
        city=r["city"],
        document_count=r["document_count"],
        result_count=r["result_count"],
        last_report_at=r["last_report_at"],
    )


@router.get("", response_model=list[PatientOut])
def list_patients(
    user: CurrentUserDep,
    q: Annotated[str | None, Query(description="name or UHID fragment")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[PatientOut]:
    sql, params = PATIENT_SQL, [user.practice_id]
    if q:
        sql += (" AND (p.uhid ILIKE %s OR p.first_name ILIKE %s"
                "      OR p.last_name ILIKE %s)")
        like = f"%{q}%"
        params += [like, like, like]
    sql += " ORDER BY p.first_name, p.last_name LIMIT %s"
    params.append(limit)
    return [_to_out(r) for r in fetch_all(sql, tuple(params))]


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: str, user: CurrentUserDep) -> PatientOut:
    pid = parse_id(patient_id, "patient_id")
    row = fetch_one(PATIENT_SQL + " AND p.id = %s", (user.practice_id, pid))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    return _to_out(row)


@router.get("/{patient_id}/analytes")
def available_analytes(patient_id: str, user: CurrentUserDep) -> list[dict]:
    """Which tests this patient has enough of to be worth charting.

    Ordered by how many points there are: three is a line, one is a dot.
    """
    pid = parse_id(patient_id, "patient_id")
    return fetch_all(
        """
        -- Through lab.v_results_verified, not lab.results. The verified rule
        -- lives in the view; repeating it here as d.status = 'verified' means
        -- two places to change and one of them will be missed.
        SELECT v.analyte_code AS code, v.analyte_name AS display_name,
               a.default_unit, v.panel_code,
               count(*) AS point_count,
               min(v.collected_at) AS first_at,
               max(v.collected_at) AS last_at
        FROM   lab.v_results_verified v
        JOIN   lab.analytes a ON a.code = v.analyte_code
        WHERE  v.practice_id = %s AND v.patient_id = %s
          AND  v.value_numeric IS NOT NULL
        GROUP  BY v.analyte_code, v.analyte_name, a.default_unit, v.panel_code
        ORDER  BY count(*) DESC, v.analyte_name
        """,
        (user.practice_id, pid),
    )


@router.get("/{patient_id}/documents")
def patient_documents(patient_id: str, user: CurrentUserDep) -> list[dict]:
    """This patient's reports, newest first, for the timeline."""
    pid = parse_id(patient_id, "patient_id")
    return fetch_all(
        """
        SELECT d.id AS document_id, d.status, d.received_at,
               r.id AS report_id, r.lab_name, r.collected_at, r.department,
               r.referring_doctor, r.layout_hint,
               (SELECT count(*) FROM lab.results x
                 WHERE x.report_id = r.id AND x.is_deleted = FALSE) AS result_count,
               (SELECT string_agg(DISTINCT pn.code, ', ' ORDER BY pn.code)
                  FROM lab.report_sections s
                  JOIN lab.panels pn ON pn.id = s.panel_id
                 WHERE s.report_id = r.id AND s.is_deleted = FALSE) AS panels
        FROM   lab.reports   r
        JOIN   lab.documents d ON d.id = r.document_id
        WHERE  r.practice_id = %s AND r.patient_id = %s
          AND  r.is_deleted = FALSE AND d.is_deleted = FALSE
        ORDER  BY r.collected_at DESC NULLS LAST
        """,
        (user.practice_id, pid),
    )


@router.get("/{patient_id}/trend/{analyte_code}", response_model=TrendResponse)
def analyte_trend(
    patient_id: str,
    analyte_code: str,
    user: CurrentUserDep,
    date_from: date | None = None,
    date_to: date | None = None,
) -> TrendResponse:
    """Every verified point for one analyte, in date order.

    Completeness is the point. A chart that silently drops a reading is worse
    than no chart, so this reads through the function and does not paginate.
    """
    pid = parse_id(patient_id, "patient_id")
    meta = fetch_one(
        "SELECT display_name, default_unit FROM lab.analytes WHERE code = %s",
        (analyte_code,))
    if meta is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            f"'{analyte_code}' is not in the analyte master")

    rows = call_function(
        "lab.fn_get_analyte_trend",
        user.practice_id, pid, analyte_code, date_from, date_to,
        returns_table=True,
    )
    points = [
        TrendPoint(
            collected_at=r["collected_at"], value_numeric=r["value_numeric"],
            value_text=r["value_text"], value_operator=r["value_operator"],
            unit=r["unit"], reference_printed=r["reference_printed"],
            ref_low=r["ref_low"], ref_high=r["ref_high"], flag=r["flag"],
            lab_name=r["lab_name"], printed_label=r["printed_label"],
            document_id=str(r["document_id"]),
        )
        for r in rows
    ]
    return TrendResponse(
        patient_id=patient_id,
        analyte_code=analyte_code,
        analyte_name=meta["display_name"],
        unit=points[0].unit if points else meta["default_unit"],
        point_count=len(points),
        points=points,
    )
