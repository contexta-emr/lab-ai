"""Each result keeps the page it was printed on, and each panel says which pages it spans.

Testers on the team console (2026-10-19) asked where a panel sits in the report:
a CBC that starts at the foot of page one and finishes on page two was shown as
one chip with no hint of either page. The reader always knew the page of every
row; the payload dropped it and no column held it (migration 038).
"""

from __future__ import annotations

import json

import pytest

from app.services.coverage import merged_rows, panel_templates
from app.services.ocr.contracts import DocumentMeta, Extraction, Row, Section
from app.services.ocr.grounded import merge
from app.services.ocr.outputs import read_raw
from app.services.ocr.pipeline import build_extraction
from app.services.ocr_ingest import payload_from_extraction
from tests import conftest

#: A two-page corpus report, as OpenParser returned it.
TWO_PAGES = "P01-R14.OPENPARSER.raw.json"


def _results(payload: dict) -> list[dict]:
    return [
        result
        for report in payload["reports"]
        for section in report["sections"]
        for result in section["results"]
    ]


def test_every_result_in_the_payload_carries_the_page_it_was_read_from() -> None:
    ex = build_extraction(read_raw(conftest.RESULTS / TWO_PAGES))
    results = _results(payload_from_extraction(ex, checksum="0" * 64))

    assert results
    assert all(isinstance(r["page"], int) and r["page"] >= 1 for r in results)
    # Both pages of the report contribute rows, so neither is lost.
    assert {r["page"] for r in results} == {1, 2}


def test_a_row_pass_b_recovers_keeps_the_page_of_the_block_it_quoted() -> None:
    ex = Extraction(
        document=DocumentMeta(engine="openparser", engine_version="", source_name=""),
        sections=[Section(printed_title="CBC", rows=[Row(0, "Haemoglobin", "13")])],
    )
    kept = [{"label_ref": "b4", "value_ref": "b5", "label": "TSH", "value": "2.1", "page": 3}]

    merged = merge(ex, kept)

    recovered = merged.sections[-1].rows[0]
    assert (recovered.raw_label, recovered.page) == ("TSH", 3)


@pytest.fixture(scope="module")
def templates(db):
    return panel_templates()


def _row(i: int, label: str, value: str, code: str, page: int | None) -> dict:
    return {
        "id": i,
        "section_id": 1,
        "heading_printed": "Complete Blood Count (CBC)",
        "printed_label": label,
        "value_text": value,
        "unit": None,
        "flag": None,
        "reference_printed": None,
        "analyte_code": code,
        "analyte_name": None,
        "match_method": "exact_alias",
        "is_reviewed": False,
        "corrected_from": None,
        "page_number": page,
    }


def test_a_panel_lists_every_page_its_rows_were_printed_on(templates) -> None:
    rows = [
        _row(1, "Haemoglobin", "14.2", "HGB", 1),
        _row(2, "Total WBC Count", "11800", "WBC", 2),
        _row(3, "Platelet Count", "245000", "PLT", 2),
        _row(4, "MCV", "87.4", "MCV", 2),
    ]
    cbc = next(p for p in merged_rows(rows, templates)["panels"] if p["panel_code"] == "CBC")
    assert cbc["pages"] == [1, 2]


def test_a_document_read_before_pages_were_stored_shows_none(templates) -> None:
    rows = [
        _row(1, "Haemoglobin", "14.2", "HGB", None),
        _row(2, "Total WBC Count", "11800", "WBC", None),
        _row(3, "Platelet Count", "245000", "PLT", None),
    ]
    cbc = next(p for p in merged_rows(rows, templates)["panels"] if p["panel_code"] == "CBC")
    assert cbc["pages"] == []


def test_ingest_stores_the_page_and_refuses_one_that_is_not_a_page(db_write) -> None:
    practice = db_write.execute("SELECT id FROM core.practices ORDER BY id LIMIT 1").fetchone()[
        0
    ]
    results = [
        {"printed_label": "Haemoglobin", "value_text": "14.2", "sequence": 1, "page": 1},
        {"printed_label": "MCV", "value_text": "87.4", "sequence": 2, "page": 2},
        {"printed_label": "MCH", "value_text": "29.2", "sequence": 3, "page": "two"},
        {"printed_label": "MCHC", "value_text": "33.4", "sequence": 4},
    ]
    payload = {
        "source": "emr_upload",
        "checksum_sha256": "e" * 64,
        "page_count": 2,
        "reports": [{"sections": [{"heading_printed": "CBC", "results": results}]}],
    }
    doc_id = db_write.execute(
        "SELECT lab.fn_ingest_lab_document(%s, %s::jsonb)", (practice, json.dumps(payload))
    ).fetchone()[0]

    stored = dict(
        db_write.execute(
            "SELECT printed_label, page_number FROM lab.results WHERE document_id = %s",
            (doc_id,),
        ).fetchall()
    )
    assert stored == {"Haemoglobin": 1, "MCV": 2, "MCH": None, "MCHC": None}
