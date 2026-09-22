"""OpenParser output to the payload lab.fn_ingest_lab_document expects.

A HYBRID, AND THE MEASUREMENTS THAT CHOSE IT
    Two halves of this job were measured separately and the winners came from
    different codebases.

    Rows, on OpenParser output over five image-only corpus reports:

        our rows.py logic         67.2% recall   83.7% precision   100.0% value
        idp build_extraction      49.2%          78.9%              60.0% value

    Header fields, over the thirteen real vendor PDFs in the idp workspace -
    Drlogy and LabSmart reports, not our synthetic corpus:

        our regex                 patient id found on  0 of 13
        idp extract_header_fields patient id found on 10 of 13

    So: rows from here, header from there. The patient id is not a detail. A
    document with no identifier cannot be filed automatically at all, and
    every upload lands in a human queue - that is a different product, not a
    slightly worse one. Our regex looked for three or four letters, a
    separator and five or six digits, which is the format our own generator
    invented; real labs number patients differently.

    idp's version recognises the patient name by CONTEXT - a heading sitting
    immediately above the demographic block - rather than by looking like a
    name, which is what makes it work in a country with no single naming
    convention.

WHAT THIS DOES NOT DO
    It never decides what a test is. Every field here is a printed string.
    "S. CREATININE" reaches the database as "S. CREATININE"; resolving it to
    CREAT happens in fn_resolve_analyte, and a miss costs one uncharted value
    rather than the row.

RESIDENCY
    openparser uploads the whole document to api.openparser.dev in the United
    States. Permitted for this service by Karthik's decision of 2026-09-21,
    recorded in CLAUDE.md section 2. lab.documents.ocr_engine records which
    engine read each document, so a stored result can always be traced back to
    how it was read.
"""

from __future__ import annotations

from pathlib import Path

from app.services.ocr.base import RawDocument
from app.services.ocr.pipeline import extract_header_fields
from app.services.ocr.tables import parse_html_tables, to_rectangular
from app.services.rows import NUMERIC, Cell, Row, _read_rows

#: Block labels the engines use for a heading. PaddleOCR-VL says
#: paragraph_title; others say title or section_header. Anything unlisted is
#: ordinary text - the safe default, since a missed heading costs panel
#: context while a wrongly detected one starts a section in the wrong place.
TITLE_LABELS = {"paragraph_title", "title", "section_header", "header", "heading"}
TABLE_LABELS = {"table", "table_body"}

#: Nominal column spacing for HTML cells. Any consistent value works: the row
#: reader compares cell positions to each other, never to a page size.
COLUMN_PITCH = 100.0

ENGINE_KEYS = {
    "openparser": "openparser",
    "paddleocrvl": "paddle_vl",
    "paddle": "paddle_vl",
    "textlayer": "pdf-text",
}


def engine_key(engine: str) -> str:
    """The small vocabulary lab.documents.ocr_engine holds, from an engine name."""
    name = (engine or "").strip().lower().replace("-", "").replace("_", "")
    for needle, key in ENGINE_KEYS.items():
        if needle in name:
            return key
    return name[:30] or "unknown"


def _grid_to_rows(grid: list[list[str]]) -> list[Row]:
    """One HTML table to the Row objects rows.py expects.

    The column index becomes the x position, so a cell printed in the third
    column stays to the right of one from the second.
    """
    out: list[Row] = []
    for y, cells in enumerate(to_rectangular(grid)):
        placed = [
            Cell(text=text.strip(), x0=i * COLUMN_PITCH, x1=i * COLUMN_PITCH + 90.0)
            for i, text in enumerate(cells)
            if text and text.strip()
        ]
        if placed:
            out.append(Row(placed, float(y)))
    return out


def payload_from_raw(doc: RawDocument, *, checksum: str,
                     visit_attachment_id: int | None = None,
                     source: str = "emr_upload") -> dict:
    """One engine's RawDocument to one ingest payload."""
    sections: list[dict] = []
    prose: list[tuple[str, str]] = []        # (block label, text), for the header

    for page in doc.pages:
        ordered = sorted(page.blocks, key=lambda b: (b.order is None, b.order or 0))
        for block in ordered:
            label = (block.label or "").lower()
            content = block.content or ""
            if not content.strip():
                continue
            if label in TABLE_LABELS:
                for grid in parse_html_tables(content):
                    _read_rows(_grid_to_rows(grid), sections)
            else:
                prose.append((block.label or "text", content))
                if label in TITLE_LABELS:
                    # Start a section here so the next table's rows land in it.
                    # That heading is what gives fn_resolve_panel its context,
                    # and panel context is what tells urine albumin from serum.
                    sections.append({"heading_printed": content.strip()[:255],
                                     "results": []})

    sections = [s for s in sections if s["results"]]
    for section in sections:
        for i, result in enumerate(section["results"], 1):
            result["sequence"] = i

    header = extract_header_fields(prose)
    n_results = sum(len(s["results"]) for s in sections)

    # Confidence is a statement about this parse, not a decoration. No patient
    # identifier or no rows means a reviewer should look before any of this is
    # treated as clinical fact.
    confidence = 0.9
    if not header.patient_id:
        confidence -= 0.35
    if not n_results:
        confidence -= 0.4
    elif n_results < 4:
        confidence -= 0.15

    return {
        "source": source,
        "visit_attachment_id": visit_attachment_id,
        "checksum_sha256": checksum,
        "page_count": doc.page_count or 1,
        "has_text_layer": False,
        "ocr_engine": engine_key(doc.engine),
        "engine_version": doc.engine_version or "",
        "extraction_confidence": round(max(confidence, 0.05), 4),
        "reports": [{
            "lab_name": _clip(header.lab_name, 255),
            "accession_no": _clip(header.lab_reference_no, 60),
            "uhid_printed": _clip(header.patient_id, 20),
            "uhid_label_printed": "UHID" if header.patient_id else None,
            "patient_name_printed": _clip(header.patient_name, 255),
            "age_printed": _clip(header.patient_age, 20),
            "sex_printed": _clip(header.patient_sex, 10),
            "collected_text": _clip(header.collected_at, 60),
            "referring_doctor": _clip(header.referring_doctor, 255),
            "layout_hint": engine_key(doc.engine),
            "sections": sections,
            "notes": [],
        }],
    }


def extract_with(engine, path: Path, *, checksum: str,
                 visit_attachment_id: int | None = None,
                 source: str = "emr_upload") -> dict:
    """Run one engine over one file and return the ingest payload."""
    return payload_from_raw(engine.extract(path), checksum=checksum,
                            visit_attachment_id=visit_attachment_id, source=source)


def _clip(value, length: int) -> str | None:
    text = value.strip() if isinstance(value, str) else None
    return text[:length] if text else None
