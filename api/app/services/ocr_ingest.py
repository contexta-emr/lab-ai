"""Extraction to the payload lab.fn_ingest_lab_document expects.

THE SEAM, AND WHY IT IS THIS SHORT
    app/services/ocr/ is the extraction pipeline from the idp workspace,
    copied in. An engine returns a RawDocument - pages of blocks, tables as
    HTML - and pipeline.build_extraction turns it into an Extraction: sections
    of rows, every field a raw printed string, no canonical codes anywhere.

    That contract was designed against fn_ingest_lab_document. Section
    .printed_title is documented there as "the panel hint passed to
    fn_resolve_panel later - never a panel code", and Row carries raw_label,
    raw_value, raw_unit, raw_reference, raw_flag and raw_method. So this file
    is a rename, not a translation:

        Row.raw_label      -> printed_label
        Row.raw_value      -> value_text
        Row.raw_unit       -> unit_printed
        Row.raw_reference  -> reference_printed
        Row.raw_flag       -> flag
        Row.raw_method     -> method_printed
        Section.printed_title -> heading_printed
        Header.patient_id  -> uhid_printed     (the UHID matcher's input)

    The division of labour it implies is the one this project already chose:
    extraction is open-vocabulary and knows nothing about lab tests;
    resolution is a separate pass, in SQL, allowed to fail without losing the
    row.

WHAT THIS REPLACED
    A hand-written reader built here over three days: geometry clustering,
    header-word matching, a value-shape heuristic. It reached 86.3% recall on
    the corpus. The pipeline it gives way to was already written, already
    tested, and infers column roles from what the cells contain rather than
    from what the header says - which is the more robust way round, and
    already handles the serial-number column that cost this project an
    afternoon and an OpenParser run to rediscover.

ENGINES
    textlayer   pdfplumber, no model, no network, milliseconds. The fast path
                for a PDF that already contains its characters.
    openparser  hosted, ~6s and ~Rs 0.09 a page, and the document leaves the
                country. Permitted here by Karthik's decision of 2026-09-21.
    paddle_vl   the same model locally, ~20 min a page, nothing leaves.

    lab.documents.ocr_engine records which one ran, so a stored result can
    always be traced back to how it was read.
"""

from __future__ import annotations

from pathlib import Path

from app.services.ocr.contracts import Extraction
from app.services.ocr.pipeline import build_extraction

#: What lab.documents.ocr_engine is allowed to hold. A small vocabulary,
#: because it is what the scoring table groups on.
ENGINE_KEYS = {
    "textlayer": "pdf-text",
    "pdfplumber": "pdf-text",
    "openparser": "openparser",
    "paddleocrvl": "paddle_vl",
    "paddle": "paddle_vl",
}


def engine_key(engine: str) -> str:
    name = (engine or "").strip().lower().replace("-", "").replace("_", "")
    for needle, key in ENGINE_KEYS.items():
        if needle in name:
            return key
    return name[:30] or "unknown"


def payload_from_extraction(ex: Extraction, *, checksum: str,
                            engine: str, engine_version: str,
                            has_text_layer: bool,
                            visit_attachment_id: int | None = None,
                            source: str = "emr_upload") -> dict:
    """One Extraction to one ingest payload."""
    sections = []
    for section in ex.sections:
        results = []
        for row in section.rows:
            if not (row.raw_label or "").strip():
                continue
            value = (row.raw_value or "").strip()
            if not value:
                # A label with no value is not a result. It is usually a
                # sub-heading the grid carried, and storing it would put a
                # blank reading on a patient's chart.
                continue
            results.append({
                "printed_label": row.raw_label.strip()[:255],
                "value_text": value[:255],
                "unit_printed": _clip(row.raw_unit, 40),
                "reference_printed": _clip(row.raw_reference, 160),
                "method_printed": _clip(row.raw_method, 160),
                "flag": _clip(row.raw_flag, 4),
                "is_text_result": not _is_number(value),
                "sequence": len(results) + 1,
            })
        if results:
            sections.append({
                "heading_printed": _clip(section.printed_title, 255),
                "results": results,
            })

    header = ex.header
    n_results = sum(len(s["results"]) for s in sections)

    # Confidence is a statement about this parse, not a decoration. No patient
    # identifier or no rows means a reviewer should look before anything here
    # is treated as clinical fact.
    confidence = 0.9
    if not (header and header.patient_id):
        confidence -= 0.35
    if not n_results:
        confidence -= 0.4
    elif n_results < 4:
        confidence -= 0.15

    return {
        "source": source,
        "visit_attachment_id": visit_attachment_id,
        "checksum_sha256": checksum,
        "page_count": ex.document.page_count or 1,
        "has_text_layer": has_text_layer,
        "ocr_engine": engine_key(engine),
        "engine_version": engine_version or "",
        "extraction_confidence": round(max(confidence, 0.05), 4),
        "reports": [{
            "lab_name": _clip(getattr(header, "lab_name", None), 255),
            "uhid_printed": _clip(getattr(header, "patient_id", None), 20),
            "uhid_label_printed": "UHID" if getattr(header, "patient_id", None) else None,
            "patient_name_printed": _clip(getattr(header, "patient_name", None), 255),
            "age_printed": _clip(getattr(header, "patient_age", None), 20),
            "sex_printed": _clip(getattr(header, "patient_sex", None), 10),
            "collected_text": _clip(getattr(header, "collected_at", None), 60),
            "referring_doctor": _clip(getattr(header, "referring_doctor", None), 255),
            "layout_hint": engine_key(engine),
            "sections": sections,
            "notes": [],
        }],
    }


def extract_with(engine, path: Path, *, checksum: str,
                 visit_attachment_id: int | None = None,
                 source: str = "emr_upload") -> dict:
    """Run one engine over one file and return the ingest payload."""
    raw = engine.extract(path)
    ex = build_extraction(raw)
    return payload_from_extraction(
        ex,
        checksum=checksum,
        engine=getattr(engine, "name", "") or raw.engine,
        engine_version=raw.engine_version,
        has_text_layer=engine_key(raw.engine) == "pdf-text",
        visit_attachment_id=visit_attachment_id,
        source=source,
    )


def _clip(value, length: int) -> str | None:
    text = (value or "").strip() if isinstance(value, str) else None
    return text[:length] if text else None


def _is_number(text: str) -> bool:
    from app.services.ocr.numbers import is_numeric
    return is_numeric(text)
