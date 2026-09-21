"""Turn an uploaded file into the payload lab.fn_ingest_lab_document expects.

WHAT THIS IS
    A geometry-driven reader for PDFs that carry a text layer. It does not read
    lines of text; it reads the positions of words and rebuilds the table they
    were printed in.

WHY IT HAD TO BE REWRITTEN
    The first version matched lines with a regex that wanted a label and a value
    on one line separated by run of spaces:

        Glucose, Fasting    214 H    mg/dL    70 - 100

    PyMuPDF never produces that. A table cell is its own text block, so the same
    row arrives as four separate lines:

        Glucose, Fasting / 214 H / mg/dL / 70 - 100

    Measured over the 300-report corpus, the line-matching version recovered
    0 of 3,591 printed rows, and what it did emit was header text misread as
    results - printed_label "Sanjeevani Diagnostics", value "Pune". It was
    written against a shape of text it never receives.

HOW THIS ONE WORKS, AND WHY IT IS NOT TUNED TO ONE LAB
    Nothing here keys on a lab name, a layout name or a specific heading. Four
    steps, each using the page's own proportions rather than fixed pixel sizes,
    so a report printed at any font size or page scale behaves the same:

    1. Rows.    Words are clustered by vertical midpoint, with the tolerance
                taken from the median word height on that page. Bigger type
                means a bigger tolerance, automatically.

    2. Cells.   Within a row, a horizontal gap wider than a fraction of the
                line height starts a new cell. That is what the eye uses to
                see a column boundary, and it needs no ruled lines.

    3. Columns. If the page prints a header row - INVESTIGATION, RESULT, UNITS,
                REFERENCE and the many synonyms labs use - its cell positions
                give real column boundaries and cells are assigned by x. This
                is a HINT, not a requirement. A report with no header row is
                read by step 4 alone.

    4. Meaning. Without column geometry: the label is the text before the first
                cell that looks like a result, the result is that cell, and what
                follows is sorted into unit and reference by shape. A reference
                looks like a range or a bound; a unit does not.

    A row that yields no plausible value is not a result and is dropped. A short
    line with no value may be a section heading. Both decisions are made on
    shape, never on a word list from this corpus.

WHAT IT STILL CANNOT DO
    A page with no text layer is an image. This stores the document, records
    ocr_engine "none", and invents nothing - 61 of the 300 corpus PDFs are in
    that state by construction. Reading those needs OCR: paddle_vl on our own
    hardware, or openparser hosted. Either produces this same payload, and
    extract_document() is the only function that changes.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# A UHID is letters, a separator, then digits: SRV/207431. Labs label it UHID,
# MRN, Patient ID, Reg. No or Hospital No; the label varies, the value does not.
UHID_LABELLED = re.compile(
    r"(?:UHID|MRN|Patient\s*ID|Reg\.?\s*No|Hospital\s*No|Registration\s*No)"
    r"\s*[:\-]?\s*([A-Z]{2,5}[/.\-]?\d{4,8})",
    re.IGNORECASE)
UHID_BARE = re.compile(r"\b([A-Z]{3,4}[/.]\d{5,6})\b")

DATE_PATTERNS = [
    (re.compile(r"\b(\d{2})[/-](\d{2})[/-](\d{4})\b"), "%d/%m/%Y"),   # Indian DD/MM/YYYY
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "%Y-%m-%d"),
]

# A number, optionally with an operator in front: 214, 9.6, <0.01, >60, 1,200.
NUMERIC = re.compile(r"^[<>≤≥]?\s*=?\s*-?\d[\d,]*\.?\d*$")

# Results that are words rather than numbers. Deliberately generic clinical
# vocabulary - absent, trace, reactive - and not a list mined from this corpus.
QUALITATIVE = {
    "absent", "present", "trace", "nil", "none", "negative", "positive",
    "reactive", "nonreactive", "detected", "notdetected", "normal", "abnormal",
    "clear", "turbid", "hazy", "pale", "yellow", "colourless", "colorless",
    "nad", "nogrowth", "sterile", "seen", "notseen", "few", "occasional",
    "plenty", "numerous", "moderate", "mild", "marked",
}
# Dipstick grades: +, ++, +++, +/-, 1+, 2+.
GRADE = re.compile(r"^(?:\+{1,4}|-|\+/-|[1-4]\+)$")

# A counted range, which microscopy reports as a result: "2-4" pus cells per
# field. Distinct from a reference range only by which column it sits in.
COUNT_RANGE = re.compile(r"^\d+\s*[-–—]\s*\d+$")

# A printed reference range: 13.0 - 17.0, < 200, 70-100, up to 5.
REFERENCE = re.compile(
    r"^(?:[<>≤≥]?\s*=?\s*-?[\d.,]+\s*(?:[-–—]\s*-?[\d.,]+)?|up\s*to\s*[\d.,]+)$",
    re.IGNORECASE)

# Flags a lab prints beside a value. Uppercase only, so the word "L" in a unit
# is not mistaken for "low".
FLAGS = {"H", "L", "HH", "LL", "A", "N", "AB", "CRIT"}

# Header-row vocabulary. Each tuple is one logical column and the spellings labs
# print for it. Used only to locate columns when a header row exists.
HEADER_WORDS = {
    "label": ("investigation", "investigations", "test", "tests", "testname",
              "parameter", "parameters", "analyte", "description", "examination",
              "particulars"),
    "value": ("result", "results", "value", "observedvalue", "observation",
              "reading", "found"),
    "unit": ("unit", "units", "uom"),
    "reference": ("reference", "referencerange", "range", "normal", "normalrange",
                  "biologicalreferenceinterval", "interval", "bioref", "refrange",
                  "normalvalue", "expected"),
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


@dataclass(slots=True)
class Cell:
    text: str
    x0: float
    x1: float

    @property
    def mid(self) -> float:
        return (self.x0 + self.x1) / 2


@dataclass(slots=True)
class Row:
    cells: list[Cell]
    top: float

    @property
    def text(self) -> str:
        return " ".join(c.text for c in self.cells)


def _rows_from_page(page) -> list[Row]:
    """Words on a page, clustered into rows and then into cells.

    Both tolerances scale with the median word height, so the same code reads a
    thermal slip printed at 7pt and a glossy report printed at 12pt.
    """
    words = page.get_text("words")          # x0, y0, x1, y1, text, block, line, n
    if not words:
        return []

    heights = [w[3] - w[1] for w in words if w[3] > w[1]]
    line_h = statistics.median(heights) if heights else 10.0
    row_tol = line_h * 0.6                  # same row if midpoints are this close

    # (mid_y, x0, x1, text, block, line)
    items = sorted(((w[1] + w[3]) / 2, w[0], w[2], str(w[4]), w[5], w[6])
                   for w in words)

    bands: list[list[tuple]] = []
    for item in items:
        if bands and abs(item[0] - bands[-1][0][0]) <= row_tol:
            bands[-1].append(item)
        else:
            bands.append([item])
    for band in bands:
        band.sort(key=lambda it: it[1])     # left to right

    # The gap that separates columns. A fraction of the line height, which
    # scales with font size and page scale, so a thermal slip at 7pt and a
    # glossy report at 12pt behave the same.
    #
    # Deriving this from the page's own gap distribution was tried and is
    # worse: measured over the corpus it cost 4 points of recall (81.5% ->
    # 77.1%). Most cells hold a single word, so there are too few within-cell
    # gaps for their median to estimate a space width - it ends up measuring
    # column gaps instead and merges columns that should split.
    cell_gap = line_h * 0.45

    rows: list[Row] = []
    for band in bands:
        cells: list[Cell] = []
        prev_key: tuple | None = None
        for _mid, x0, x1, text, block, line in band:
            # A change of (block, line) is the PDF saying these words were laid
            # out as separate pieces of text - which for a table is exactly a
            # cell boundary, and is stronger evidence than any gap. The gap
            # test still runs, because some generators put a whole row in one
            # block and then only spacing shows the columns.
            key = (block, line)
            same_cell = bool(cells) and prev_key == key and x0 - cells[-1].x1 <= cell_gap
            if same_cell:
                cells[-1].text += " " + text
                cells[-1].x1 = x1
            else:
                cells.append(Cell(text, x0, x1))
            prev_key = key
        cells = [c for c in cells if c.text.strip()]
        if cells:
            rows.append(Row(cells, band[0][0]))
    return rows


def _header_columns(row: Row) -> dict[str, tuple[float, float]] | None:
    """If this row is a column header, where each known column sits.

    Needs at least a label column and a value column to count, so a section
    title that happens to contain the word "Result" is not mistaken for one.
    """
    found: dict[str, tuple[float, float]] = {}
    for cell in row.cells:
        n = _norm(cell.text)
        for role, words in HEADER_WORDS.items():
            if role in found:
                continue
            if n in words or any(n.startswith(w) or w in n for w in words):
                found[role] = (cell.x0, cell.x1)
                break
    return found if {"label", "value"} <= found.keys() else None


def _looks_like_value(text: str) -> bool:
    """Does this cell hold a result?

    Three shapes, all of them things a lab prints as a result rather than
    peculiar to any one report:

      a number          214, 9.6, <0.01, 1,200
      a counted range   2-4, 0-2       microscopy reports counts per field
      a word            Absent, Pale Yellow, Non Reactive, ++
    """
    t = text.strip()
    if not t:
        return False
    core = t.rsplit(" ", 1)[0] if t.rsplit(" ", 1)[-1] in FLAGS else t
    core = core.strip()
    if NUMERIC.match(core) or GRADE.match(t) or COUNT_RANGE.match(core):
        return True
    if _norm(t) in QUALITATIVE:
        return True
    # Multi-word qualitative results - "Pale Yellow", "Not Detected", "No
    # Growth" - count when every word is one of the vocabulary words.
    tokens = [_norm(w) for w in re.split(r"[\s/,]+", t) if _norm(w)]
    return bool(tokens) and len(tokens) <= 3 and all(w in QUALITATIVE for w in tokens)


def _split_flag(text: str) -> tuple[str, str | None]:
    parts = text.strip().rsplit(" ", 1)
    if len(parts) == 2 and parts[1] in FLAGS:
        return parts[0].strip(), parts[1]
    return text.strip(), None


def _by_columns(row: Row, cols: dict[str, tuple[float, float]]) -> dict | None:
    """Assign cells to the header's columns by horizontal position."""
    out: dict[str, list[str]] = {}
    for cell in row.cells:
        role = min(cols, key=lambda r: abs(cell.mid - sum(cols[r]) / 2))
        # A cell left of the value column always belongs to the label, however
        # wide the label column was printed.
        if cell.x1 <= cols["value"][0]:
            role = "label"
        out.setdefault(role, []).append(cell.text)

    label = " ".join(out.get("label", [])).strip(" .:-")
    value = " ".join(out.get("value", [])).strip()
    if not label or not value or not _looks_like_value(value):
        return None
    return {
        "label": label,
        "value": value,
        "unit": " ".join(out.get("unit", [])).strip() or None,
        "reference": " ".join(out.get("reference", [])).strip() or None,
    }


def _by_shape(row: Row) -> dict | None:
    """No header row: find the value, then read outwards from it."""
    texts = [c.text for c in row.cells]
    idx = next((i for i in range(1, len(texts)) if _looks_like_value(texts[i])), None)
    if idx is None:
        return None

    label = " ".join(texts[:idx]).strip(" .:-")
    if not label or len(label) < 2:
        return None

    unit, reference = None, None
    for rest in texts[idx + 1:]:
        t = rest.strip()
        if REFERENCE.match(t) or re.match(r"^[<>≤≥]", t):
            reference = f"{reference} {t}".strip() if reference else t
        elif unit is None and not _looks_like_value(t):
            unit = t
    return {"label": label, "value": texts[idx], "unit": unit, "reference": reference}


def _is_heading(row: Row) -> bool:
    """A section title: one short run of words, no value anywhere in it."""
    if len(row.cells) > 2:
        return False
    text = row.text.strip()
    if not (2 < len(text) <= 60):
        return False
    if any(_looks_like_value(c.text) for c in row.cells):
        return False
    return bool(re.search(r"[A-Za-z]", text))


def _parse_page(page, sections: list[dict]) -> None:
    """Read one page into sections, appending to what earlier pages produced."""
    _read_rows(_rows_from_page(page), sections)


ROW_NUMBER = re.compile(r"^\d{1,3}[.)]?$")


def _drop_row_number(cells: list[Cell]) -> list[Cell]:
    """Discard a leading serial number, which is not part of the test name.

    Plenty of labs number the lines on a report - Sr. No., S.No, or a bare
    column of 1, 2, 3. Left in place it becomes part of the printed label,
    "1 Creatinine, Serum" never matches the alias "Creatinine, Serum", and the
    row is lost with no sign that anything went wrong.

    Only when the row has something after the number and a label following it,
    so a genuine two-cell row whose label happens to be a number survives.
    """
    if len(cells) >= 3 and ROW_NUMBER.match(cells[0].text.strip()) \
            and re.search(r"[A-Za-z]", cells[1].text):
        return cells[1:]
    return cells


def _read_rows(rows: list[Row], sections: list[dict]) -> None:
    """Turn a run of rows into sections and results.

    Separate from _parse_page because it is the half that decides what a row
    MEANS, and that is identical whether the rows came from a PDF's text layer
    or from an OCR engine's table. app/services/ocr_ingest.py builds the same
    Row objects out of the HTML an engine returns and calls straight into
    here, so there is one definition of a result row rather than two that
    drift apart.
    """
    cols: dict[str, tuple[float, float]] | None = None

    def current() -> dict:
        if not sections:
            sections.append({"heading_printed": None, "results": []})
        return sections[-1]

    for row in rows:
        row = Row(_drop_row_number(row.cells), row.top)
        header = _header_columns(row)
        if header:
            cols = header                   # columns hold until the next header
            continue

        parsed = (_by_columns(row, cols) if cols else None) or _by_shape(row)
        if parsed is None:
            if _is_heading(row):
                # A heading resets the columns: the next block may be laid out
                # differently, and stale boundaries are worse than none.
                sections.append({"heading_printed": row.text.strip(), "results": []})
                cols = None
            continue

        value, flag = _split_flag(parsed["value"])
        sec = current()
        sec["results"].append({
            "printed_label": parsed["label"][:255],
            "value_text": value[:255],
            "unit_printed": (parsed["unit"] or None) and parsed["unit"][:40],
            "reference_printed": (parsed["reference"] or None) and parsed["reference"][:160],
            "flag": flag,
            "is_text_result": not NUMERIC.match(value.strip()),
            "sequence": len(sec["results"]) + 1,
        })


def _read(path: Path):
    try:
        import pymupdf
    except ImportError:                     # pragma: no cover
        try:
            import fitz as pymupdf
        except ImportError:
            return None
    if path.suffix.lower() != ".pdf":
        return None
    return pymupdf.open(path)


def _find_uhid(text: str) -> str | None:
    m = UHID_LABELLED.search(text)
    if m:
        return m.group(1).strip()
    m = UHID_BARE.search(text)
    return m.group(1).strip() if m else None


def _find_date(text: str) -> datetime | None:
    for pattern, fmt in DATE_PATTERNS:
        for m in pattern.finditer(text):
            try:
                return datetime.strptime(m.group(0), fmt)
            except ValueError:
                continue
    return None


def extract_document(path: Path, *, checksum: str,
                     visit_attachment_id: int | None = None) -> dict:
    """Build the ingest payload. Always returns something, even for an image."""
    doc = _read(path)
    if doc is None:
        return _no_text_payload(checksum, visit_attachment_id, 1)

    with doc:
        pages = len(doc)
        text = "".join(page.get_text() for page in doc)
        if len(text.strip()) <= 40:
            return _no_text_payload(checksum, visit_attachment_id, pages)
        sections: list[dict] = []
        for page in doc:
            _parse_page(page, sections)

    sections = [s for s in sections if s["results"]]
    for s in sections:
        for i, r in enumerate(s["results"], 1):
            r["sequence"] = i

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    lab_name = lines[0][:255] if lines else None
    uhid = _find_uhid(text)
    collected = _find_date(text)
    n_results = sum(len(s["results"]) for s in sections)

    # Confidence is a statement about this parse, not a decoration. No UHID or
    # no rows means a reviewer should look before anything is trusted.
    confidence = 0.9
    if not uhid:
        confidence -= 0.35
    if not n_results:
        confidence -= 0.4
    elif n_results < 4:
        confidence -= 0.15

    return {
        "source": "emr_upload",
        "visit_attachment_id": visit_attachment_id,
        "checksum_sha256": checksum,
        "page_count": pages,
        "has_text_layer": True,
        "ocr_engine": "pdf-text",
        "engine_version": "geometry-text-layer-0.2",
        "extraction_confidence": round(max(confidence, 0.05), 4),
        "reports": [{
            "lab_name": lab_name,
            "uhid_printed": uhid,
            "uhid_label_printed": "UHID" if uhid else None,
            "collected_text": collected.strftime("%d/%m/%Y") if collected else None,
            "collected_at": collected.isoformat() if collected else None,
            "layout_hint": "text_layer",
            "sections": sections,
            "notes": [],
        }],
    }


def _no_text_payload(checksum: str, visit_attachment_id: int | None,
                     pages: int) -> dict:
    """No text layer: a scan or a photograph. Record it, invent nothing."""
    return {
        "source": "emr_upload",
        "visit_attachment_id": visit_attachment_id,
        "checksum_sha256": checksum,
        "page_count": pages or 1,
        "has_text_layer": False,
        "ocr_engine": "none",
        "engine_version": "geometry-text-layer-0.2",
        "extraction_confidence": 0.0,
        "reports": [{
            "lab_name": None,
            "uhid_printed": None,
            "sections": [],
            "notes": [{
                "note_type": "remark",
                "note_text": ("No text layer. This document needs OCR - "
                              "paddle_vl on our own hardware, or openparser "
                              "hosted - before it can be read."),
            }],
        }],
    }
