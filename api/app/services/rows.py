"""What a row of a lab report table means.

Engine-agnostic on purpose. Give it cells and it tells you which is the test
name, which is the result, which is the unit and which is the printed
reference range. It does not know or care whether those cells came from a
PDF's text layer, from OpenParser's HTML, or from anywhere else - and it never
decides what a test IS. "S. CREATININE" stays "S. CREATININE"; turning that
into CREAT happens in SQL, in fn_resolve_analyte, where a miss costs one
uncharted value instead of the whole report.

Two ways to read a row, tried in order:

    by columns  When the page printed a header row - INVESTIGATION, TEST,
                PARAMETER, RESULT, VALUE, UNITS, REFERENCE and the usual
                synonyms - its cell positions give real column boundaries and
                cells are assigned by x. A hint, never a requirement.

    by shape    Otherwise: the result is the first cell that LOOKS like one,
                the label is everything before it, and what follows is sorted
                into unit and reference by shape. A reference looks like a
                range or a bound; a unit does not.

A row with no plausible result is not a result and is dropped.

MEASURED HISTORY - these are not arbitrary choices
    Every constant here was measured over the 300-report synthetic corpus,
    and two plausible-sounding alternatives were tried and rejected:

    * Deriving the cell gap from each page's own gap distribution sounds more
      principled than a fraction of the line height. It cost 4 points of
      recall (81.5% -> 77.1%), because most cells hold a single word and there
      are too few within-cell gaps for their median to estimate a space width.

    * Dropping a leading serial number is worth 4.3 points (82.0% -> 86.3%).
      "1 Creatinine, Serum" never matches the alias "Creatinine, Serum" and
      the row vanishes with no sign anything went wrong. OpenParser found this
      for us; idp's columns.py had it documented all along.

    Both numbers are on the synthetic corpus. Say so whenever quoting them -
    that corpus came out of one PDF producer, and a high score on it is not
    by itself evidence about a real clinic's reports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

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


