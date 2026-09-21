"""Turn an OCR engine's output into the payload lab.fn_ingest_lab_document wants.

THE SEAM
    An engine in app/services/ocr/ returns a RawDocument: pages of blocks, each
    block carrying a label the engine chose (table, text, paragraph_title) and
    its content. Tables arrive as HTML. That contract is deliberately
    open-vocabulary - it has no idea what a lab test is - and this module is
    where it becomes something the database can store.

WHY THE MEANING LOGIC IS NOT DUPLICATED HERE
    Deciding that a row says "Creatinine, 1.4, mg/dL, 0.7 - 1.3" is the same
    problem whether the row came from a PDF's text layer or from OCR. So this
    builds the same Row and Cell objects extract.py builds and calls the same
    _read_rows. One definition of what a result looks like, two sources of
    rows. If the qualitative vocabulary or the header synonyms improve, both
    engines improve together, and a scoring difference between them is a
    difference in the engine rather than in two divergent parsers.

    The only thing invented here is x coordinates. An HTML table has columns by
    index, not by position, so column i is placed at a nominal x. Column
    assignment only ever compares positions to each other, so nominal is enough.

RESIDENCY
    openparser uploads the whole document to api.openparser.dev in the United
    States. Permitted for this service by Karthik's decision of 2026-09-21,
    recorded in CLAUDE.md section 2, with no allow-remote guard. The engine's
    own refusal for anything under a directory named fixtures still applies and
    is not overridden here - that guard exists because those are real patient
    reports from a real clinic.

    lab.documents.ocr_engine records which engine read each document, so a
    stored result can always be traced back to how it was read and to whether
    it left the network.
"""

from __future__ import annotations

from pathlib import Path

from app.services.extract import (
    Cell,
    Row,
    _find_date,
    _find_uhid,
    _read_rows,
)
from app.services.ocr.base import RawDocument
from app.services.ocr.tables import parse_html_tables, to_rectangular

# Block labels the engines use for a heading. PaddleOCR-VL says
# paragraph_title; others say title or section_header. Anything not listed is
# treated as ordinary text, which is the safe default - a missed heading costs
# panel context, a wrongly detected one starts a section in the wrong place.
TITLE_LABELS = {"paragraph_title", "title", "section_header", "header", "heading"}
TABLE_LABELS = {"table", "table_body"}

# Nominal column spacing. Any consistent value works: _read_rows compares cell
# positions to each other and never to an absolute page size.
COLUMN_PITCH = 100.0


def _grid_to_rows(grid: list[list[str]]) -> list[Row]:
    """One HTML table to the Row objects the shared reader expects.

    The column index becomes the x position, so a cell that was in the third
    column stays to the right of one that was in the second.
    """
    rows: list[Row] = []
    for y, cells in enumerate(to_rectangular(grid)):
        placed = [
            Cell(text=text.strip(), x0=i * COLUMN_PITCH, x1=i * COLUMN_PITCH + 90.0)
            for i, text in enumerate(cells)
            if text and text.strip()
        ]
        if placed:
            rows.append(Row(placed, float(y)))
    return rows


def payload_from_raw(doc: RawDocument, *, checksum: str,
                     visit_attachment_id: int | None = None,
                     source: str = "emr_upload") -> dict:
    """A RawDocument from any engine to one ingest payload."""
    sections: list[dict] = []
    prose: list[str] = []

    for page in doc.pages:
        for block in sorted(page.blocks, key=lambda b: (b.order is None, b.order or 0)):
            label = (block.label or "").lower()
            content = block.content or ""
            if not content.strip():
                continue

            if label in TABLE_LABELS:
                for grid in parse_html_tables(content):
                    _read_rows(_grid_to_rows(grid), sections)
            elif label in TITLE_LABELS:
                # Start a section here. The rows of the next table land in it,
                # which is what gives fn_resolve_analyte its panel context -
                # and panel context is what tells urine albumin from serum.
                sections.append({"heading_printed": content.strip()[:255],
                                 "results": []})
                prose.append(content)
            else:
                prose.append(content)

    sections = [s for s in sections if s["results"]]
    for s in sections:
        for i, result in enumerate(s["results"], 1):
            result["sequence"] = i

    text = "\n".join(prose)
    uhid = _find_uhid(text)
    collected = _find_date(text)
    n_results = sum(len(s["results"]) for s in sections)

    # Same confidence rule as the text-layer reader, for the same reason: this
    # is a statement about the parse, and a reviewer needs to know when to look.
    confidence = 0.9
    if not uhid:
        confidence -= 0.35
    if not n_results:
        confidence -= 0.4
    elif n_results < 4:
        confidence -= 0.15

    first_line = next((line.strip() for line in text.splitlines() if line.strip()), None)

    return {
        "source": source,
        "visit_attachment_id": visit_attachment_id,
        "checksum_sha256": checksum,
        "page_count": doc.page_count or 1,
        "has_text_layer": False,
        "ocr_engine": _engine_key(doc.engine),
        "engine_version": doc.engine_version or "",
        "extraction_confidence": round(max(confidence, 0.05), 4),
        "reports": [{
            "lab_name": first_line[:255] if first_line else None,
            "uhid_printed": uhid,
            "uhid_label_printed": "UHID" if uhid else None,
            "collected_text": collected.strftime("%d/%m/%Y") if collected else None,
            "collected_at": collected.isoformat() if collected else None,
            "layout_hint": "ocr",
            "sections": sections,
            "notes": [],
        }],
    }


def _engine_key(engine: str) -> str:
    """The engine names the database expects, from the engines' own names.

    lab.documents.ocr_engine is a small vocabulary - pdf-text, paddle_vl,
    openparser, none - because it is what a scoring table groups on. The
    engines call themselves OPENPARSER and PADDLEOCR-VL.
    """
    name = (engine or "").strip().lower()
    if "openparser" in name:
        return "openparser"
    if "paddle" in name:
        return "paddle_vl"
    return name[:30] or "unknown"
