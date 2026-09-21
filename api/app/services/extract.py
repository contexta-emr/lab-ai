"""Turn an uploaded file into the payload lab.fn_ingest_lab_document expects.

WHAT THIS IS TODAY
    A real but deliberately simple extractor: it pulls the text layer out of a
    PDF, finds the UHID and the lab name in the header, and reads table-ish
    lines into results. It handles the clean, text-layer half of the corpus.

WHAT IT IS NOT
    It is not the production engine. Scanned and photographed pages have no text
    layer at all - 52 of the 300 corpus reports are images - and those need OCR.
    Two engines already exist and are tested in the idp/ workspace:

        paddle_vl   PaddleOCR-VL 1.6 on our own hardware. About 20 minutes a
                    page on CPU, free, and nothing leaves the network.
        openparser  The same model on OpenParser hosted GPU. About 6 seconds and
                    roughly 0.09 rupees a page - but the whole PDF is uploaded
                    to api.openparser.dev in the United States.

    That 200x speed difference is why OpenParser exists. It is also why it is not
    the default: the idp workspace gates it behind an explicit allow-remote flag
    and restricts it to synthetic and vendor sample documents, never a real
    patient report, because sending PHI abroad is a DPDPA question rather than a
    latency one. Keep that rule when wiring either engine in here.

    When one lands, replace extract_document() and nothing else changes: the
    payload shape is the contract, and it is documented on
    lab.fn_ingest_lab_document. Set ocr_engine to the engine key that ran, so a
    stored result can always be traced back to how it was read.

    Where this extractor is unsure it says so in extraction_confidence rather
    than guessing, because a confident wrong reading is the expensive failure.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

# A UHID is 3-4 uppercase letters, a dot or slash, then 5-6 digits: SRV/207431.
# Labs label it UHID, MRN, Patient ID, Reg. No or Hospital No; the label varies,
# the value does not.
UHID_LABELLED = re.compile(
    r"(?:UHID|MRN|Patient\s*ID|Reg\.?\s*No|Hospital\s*No|Registration\s*No)"
    r"\s*[:\-]?\s*([A-Z]{2,5}[/.\-]?\d{4,8})",
    re.IGNORECASE)
UHID_BARE = re.compile(r"\b([A-Z]{3,4}[/.]\d{5,6})\b")

DATE_PATTERNS = [
    (re.compile(r"(\d{2})[/-](\d{2})[/-](\d{4})"), "%d/%m/%Y"),   # Indian DD/MM/YYYY
    (re.compile(r"(\d{4})-(\d{2})-(\d{2})"), "%Y-%m-%d"),
]

# label ....  value  unit  range
RESULT_LINE = re.compile(
    r"^(?P<label>[A-Za-z][A-Za-z0-9 ,.()%/&+-]{2,60}?)\s{2,}"
    r"(?P<value>[<>]?\s?-?[\d.,]+|[A-Za-z][A-Za-z ]{2,40})\s*"
    r"(?P<unit>[a-zA-Z/%^0-9.\-]{1,15})?\s*"
    r"(?P<ref>[\d.<>\- ]{3,25})?\s*$")


def _read_text(path: Path) -> tuple[str, int, bool]:
    """Text, page count, and whether there was a text layer at all."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return "", 0, False

    if path.suffix.lower() != ".pdf":
        return "", 1, False

    with fitz.open(path) as doc:
        pages = [page.get_text() for page in doc]
        text = "\n".join(pages)
        return text, len(pages), len(text.strip()) > 40


def _find_uhid(text: str) -> str | None:
    m = UHID_LABELLED.search(text)
    if m:
        return m.group(1).strip()
    m = UHID_BARE.search(text)
    return m.group(1).strip() if m else None


def _find_date(text: str) -> datetime | None:
    for pattern, fmt in DATE_PATTERNS:
        m = pattern.search(text)
        if m:
            try:
                return datetime.strptime(m.group(0), fmt)
            except ValueError:
                continue
    return None


def _parse_results(text: str) -> list[dict]:
    """Lines that look like a result row. Anything ambiguous is skipped, not guessed."""
    results: list[dict] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if len(line) < 8 or line.count(" ") < 2:
            continue
        m = RESULT_LINE.match(line)
        if not m:
            continue
        label = m.group("label").strip(" .:-")
        value = (m.group("value") or "").strip()
        if not label or not value:
            continue
        if label.lower() in ("investigation", "test", "parameter", "result", "units"):
            continue  # that is the header row, not a result
        results.append({
            "printed_label": label,
            "value_text": value,
            "unit_printed": (m.group("unit") or "").strip() or None,
            "reference_printed": (m.group("ref") or "").strip() or None,
            "is_text_result": not re.match(r"^[<>]?\s?-?[\d.,]+$", value),
            "sequence": len(results) + 1,
        })
    return results


def extract_document(path: Path, *, checksum: str,
                     visit_attachment_id: int | None = None) -> dict:
    """Build the ingest payload. Always returns something, even for an image."""
    text, pages, has_text = _read_text(path)

    if not has_text:
        # No text layer: this is a scan or a photograph and needs OCR. Record
        # the document so it exists and can be queued, with nothing invented.
        return {
            "source": "emr_upload",
            "visit_attachment_id": visit_attachment_id,
            "checksum_sha256": checksum,
            "page_count": pages or 1,
            "has_text_layer": False,
            "ocr_engine": "none",
            "engine_version": "text-layer-extractor-0.1",
            "extraction_confidence": 0.0,
            "reports": [{
                "lab_name": None,
                "uhid_printed": None,
                "sections": [],
                "notes": [{
                    "note_type": "remark",
                    "note_text": ("No text layer. This document needs OCR - "
                                  "paddle_vl on our own hardware, or openparser "
                                  "hosted if the document is not real patient "
                                  "data - before it can be read."),
                }],
            }],
        }

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    lab_name = lines[0][:255] if lines else None
    uhid = _find_uhid(text)
    collected = _find_date(text)
    results = _parse_results(text)

    # Confidence is a statement about this parse, not a decoration. No UHID or
    # no results means a reviewer should look before anything is trusted.
    confidence = 0.9
    if not uhid:
        confidence -= 0.35
    if not results:
        confidence -= 0.4
    elif len(results) < 4:
        confidence -= 0.15

    return {
        "source": "emr_upload",
        "visit_attachment_id": visit_attachment_id,
        "checksum_sha256": checksum,
        "page_count": pages,
        "has_text_layer": True,
        "ocr_engine": "pdf-text",
        "engine_version": "text-layer-extractor-0.1",
        "extraction_confidence": round(max(confidence, 0.05), 4),
        "reports": [{
            "lab_name": lab_name,
            "uhid_printed": uhid,
            "uhid_label_printed": "UHID" if uhid else None,
            "collected_text": collected.strftime("%d/%m/%Y") if collected else None,
            "collected_at": collected.isoformat() if collected else None,
            "layout_hint": "text_layer",
            "sections": [{
                "heading_printed": "Investigations",
                "results": results,
            }] if results else [],
            "notes": [],
        }],
    }
