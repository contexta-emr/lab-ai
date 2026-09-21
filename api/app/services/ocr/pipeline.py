"""Turn engine geometry into the extraction contract.

This is where meaning is added, and it is deliberately all deterministic code rather than
anything a model does. The engine says "here is a table and here is where it sits"; this
module decides which column is the value and which is the reference range, using
:mod:`idp.columns`.

Still no vocabulary. Nothing here knows what a lab test is, and no canonical code is
assigned - that happens later, in SQL, and is allowed to fail without losing a row.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from html import unescape

from .columns import Role, infer_roles, role_of
from .contracts import BBox, DocumentMeta, Extraction, Header, Row, Section, UnparsedBlock
from .dates import parse_lab_date
from .base import RawBlock, RawDocument, RawPage
from .numbers import split_flag_prefix, split_reference_unit
from .synonyms import split_method_suffix
from .tables import Grid, looks_like_html_table, parse_html_tables, split_sections

__all__ = ["build_extraction", "centred_heading", "extract_header_fields", "plain_text"]

#: An engine may leave markup inside a *text* block. PaddleOCR-VL returns centred headings
#: as ``<div style="text-align: center;">KIDNEY FUNCTION TEST (KFT)</div>`` - the panel
#: name, which is the single most reliable signal there is for what a report contains,
#: wrapped in something that made it unusable. Every document in the corpus carried one.
_TAG_RE = re.compile(r"<[^>]+>")

#: A text block whose whole content is one centred block element is a heading. That is a
#: typographic fact rather than a fact about any one lab: centring is how a heading is
#: marked up. The engine labels these ``text``, so without this they are lost.
_CENTRED_RE = re.compile(
    r"^\s*<(div|p|h[1-6])[^>]*text-align:\s*center[^>]*>(?P<inner>.*?)</\1>\s*$",
    re.IGNORECASE | re.DOTALL,
)


def plain_text(content: str) -> str:
    """Strip markup an engine left inside a text block, and decode entities."""
    # `&` matters as much as `<`: an entity with no tag around it still reaches the
    # contract as `a &amp; b` and reads as garbage on screen.
    if "<" not in content and "&" not in content:
        return content
    return unescape(_TAG_RE.sub("", content)).strip()


def centred_heading(content: str) -> str | None:
    """The text of a centred heading, or ``None`` when this is not one."""
    match = _CENTRED_RE.match(content)
    if match is None:
        return None
    inner = plain_text(match.group("inner"))
    return inner or None



# Engine block labels that carry a section heading. "header" is deliberately absent:
# in PaddleOCR that means the running page header, which on a lab report is boilerplate
# like "PLEASE SCAN QR CODE TO VERIFY THE REPORT ONLINE" - not a panel name.
_TITLE_LABELS = frozenset({"title", "doc_title", "paragraph_title", "section_title"})
_TABLE_LABELS = frozenset({"table", "table_body", "form"})

# Header keys, normalised. Only the three date fields get promoted to columns; every
# other printed key is kept verbatim in raw_fields rather than being interpreted.
_COLLECTED = frozenset(
    {"collectedon", "collecteddate", "samplecollected", "collectiondate", "sampledate",
     "drawnon", "specimencollected", "collected"}
)
_TESTED = frozenset(
    {"testedon", "testeddate", "analysedon", "analyzedon", "processedon", "receivedon",
     "sampletested", "tested"}
)
_REPORTED = frozenset(
    {"reportedon", "reporteddate", "reportdate", "approvedon", "releasedon", "reported"}
)
_LAB_NAME = frozenset({"labname", "laboratory", "lab", "centre", "center", "diagnostics"})
_LAB_REF = frozenset(
    {"labno", "labid", "labreferenceno", "referenceno", "accessionno", "sampleid",
     "barcode", "sinno", "srno", "visitid", "orderid", "sampleno",
     # Seen on real Tenet Diagnostics reports.
     "reqno", "requestno", "regno", "registrationno", "tidsid", "uhid", "umr"}
)

# A sub-line under a test naming the assay, with every other cell empty.
_METHOD_RE = re.compile(r"^\s*method\s*[:\-]\s*(.+?)\s*$", re.I)

#: The same kind of sub-line naming the specimen instead - "Sample - EDTA Whole Blood".
#: Not a result, and not a method either, so it folds away without setting one.
_SPECIMEN_RE = re.compile(r"^\s*(?:sample|specimen)(?:\s*type)?\s*[:\-]", re.I)

#: What a lab prints in a field it has nothing for. Accepting "-" put a pathologist's
#: blank registration number into patient_id.
_PLACEHOLDER_RE = re.compile(r"^[\s\-.–—/]*$|^(?:n/?a|nil|none)$", re.I)

_KV_RE = re.compile(r"^\s*([A-Za-z][A-Za-z ./&()-]{1,40}?)\s*[:\-]\s*(.+?)\s*$")

#: A label with nothing after the colon. Reports often stack the pair vertically in a
#: right-aligned box - "Reported on:" on one line, the timestamp on the next - so a
#: same-line-only parser reads neither half.
_LABEL_ONLY_RE = re.compile(r"^\s*([A-Za-z][A-Za-z ./&()-]{1,40}?)\s*:\s*$")


def _key_values(block: str) -> list[tuple[str, str]]:
    """Pull ``key, value`` pairs out of a text block, however they are laid out.

    Handles both shapes seen on real reports: the pair on one line, and the pair stacked
    across two lines because the lab right-aligns it into a box.

    Args:
        block: One text block's content.

    Returns:
        The pairs found, in reading order.
    """
    lines = [line.strip() for line in block.splitlines()]
    pairs: list[tuple[str, str]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        inline = _KV_RE.match(line)
        if inline and inline.group(2).strip():
            pairs.append((inline.group(1).strip(), inline.group(2).strip()))
            index += 1
            continue
        stacked = _LABEL_ONLY_RE.match(line)
        following = lines[index + 1] if index + 1 < len(lines) else ""
        # Only take the next line when it is a value, not another label.
        if stacked and following and not _LABEL_ONLY_RE.match(following):
            pairs.append((stacked.group(1).strip(), following))
            index += 2
            continue
        index += 1
    return pairs


def _norm_key(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


#: Demographic keys, normalised. Aliases are wide on purpose - every lab names these
#: differently and the cost of a miss is a report that cannot be tied to a patient.
_PATIENT_NAME = frozenset(
    {"name", "patientname", "ptname", "patient", "nameofpatient", "patientsname"}
)
_AGE = frozenset({"age", "ageyrs", "ageyears", "ageingyears", "dob", "dateofbirth"})
_SEX = frozenset({"sex", "gender"})
_PATIENT_ID = frozenset(
    {"pid", "patientid", "uhid", "mrn", "mrno", "regno", "registrationno", "ipno",
     "opno", "opdno", "abha", "abhano", "healthid", "patientno", "idno"}
)
_DOCTOR = frozenset(
    {"refby", "referredby", "referringphysician", "referringdoctor", "refdoctor",
     "referredbydr", "consultant", "doctor", "refdby"}
)

#: Any of these appearing in a block is what marks it as the demographics area, which is
#: how a bare heading just above it is recognised as the patient name.
_DEMOGRAPHIC = _PATIENT_NAME | _AGE | _SEX | _PATIENT_ID | _DOCTOR

#: Every key the header promotes. A table whose keys are these is a header, not results.
_HEADER_KEYS = _DEMOGRAPHIC | _COLLECTED | _TESTED | _REPORTED | _LAB_NAME | _LAB_REF

#: A heading further back than this is not part of the demographics block. Two labs in
#: the corpus print the name directly above the first demographic line; the slack exists
#: for a lab that puts a barcode or a logo caption between them.
_NAME_LOOKBACK = 3


def _split_combined(raw_key: str, value: str) -> list[tuple[str, str]]:
    """Split ``Age / Sex : 27 YRS / M`` into its two real fields.

    Labs pack related fields onto one printed line to save space. Treating that as a
    single field named "Age / Sex" loses both of them. Only splits when the key and the
    value divide into the same number of parts - anything else is a value that merely
    happens to contain a slash, like a date or a ratio.
    """
    for sep in ("/", "|"):
        if sep in raw_key and sep in value:
            keys = [k.strip() for k in raw_key.split(sep)]
            values = [v.strip() for v in value.split(sep)]
            if len(keys) == len(values) and all(keys) and all(values):
                return list(zip(keys, values, strict=True))
    return [(raw_key, value)]


def _row_pairs(row: list[str]) -> list[tuple[str, str]]:
    """Read one table row as printed ``key : value`` pairs.

    Two shapes, both seen on real reports: the colon ends the key cell
    (``Collection Date :`` | ``15/09/26`` | ``15:28``), or it starts the value cell
    (``UHID`` | ``: DDCH.123``). A value may spill over several cells, so everything up to
    the next key belongs to it.
    """
    # colspan expands one printed cell into several identical ones; read it once.
    cells = [c.strip() for i, c in enumerate(row) if c.strip() and (i == 0 or c != row[i - 1])]
    pairs: list[tuple[str, str]] = []
    index = 0
    while index < len(cells):
        cell = cells[index]
        following = cells[index + 1] if index + 1 < len(cells) else ""
        if len(cell) > 1 and cell.endswith(":") and not cell.startswith(":"):
            end = index + 1
            while (
                end < len(cells)
                and not cells[end].endswith(":")
                and not (end + 1 < len(cells) and cells[end + 1].startswith(":"))
            ):
                end += 1
            value = " ".join(cells[index + 1 : end])
            if value:
                pairs.append((cell[:-1].strip(), value))
            index = end
        elif following.startswith(":") and not cell.startswith(":"):
            value = following[1:].strip()
            if value:
                pairs.append((cell, value))
            index += 2
        else:
            index += 1
    return pairs


def _is_header_key(key: str) -> bool:
    """True for a promoted header key, including packed ones like ``Age/Sex``."""
    return any(_norm_key(part) in _HEADER_KEYS for part in re.split(r"[/|]", key))


def _header_rows(grid: Grid) -> tuple[list[tuple[str, str]], Grid]:
    """Separate printed key-value rows from a table's results.

    Some labs box the demographics as a bordered table, which the engine returns as a
    table block; others run a ``Sample No : … Collection Date : …`` strip across the top
    of the results grid. Read as results, both lose the patient and the dates.

    Returns:
        The header pairs, and the grid with those rows removed. A whole table goes to the
        header only when every filled row is key-value *and* at least two keys are header
        keys - a urine table printing ``Colour :`` | ``Pale yellow`` is still results.
        A single row inside a results grid needs two pairs and one header key.
    """
    per_row = [(row, _row_pairs(row)) for row in grid]
    filled = [(row, pairs) for row, pairs in per_row if any(c.strip() for c in row)]
    known = sum(_is_header_key(k) for _, pairs in filled for k, _ in pairs)
    if filled and all(pairs for _, pairs in filled) and known >= 2:
        return [p for _, pairs in filled for p in pairs], []

    header: list[tuple[str, str]] = []
    kept: Grid = []
    for row, pairs in per_row:
        if len(pairs) >= 2 and any(_is_header_key(k) for k, _ in pairs):
            header.extend(pairs)
        else:
            kept.append(row)
    return header, kept


def extract_header_fields(blocks: Iterable[tuple[str, str]]) -> Header:
    """Pull document-level fields out of the non-table blocks.

    Two kinds of field are promoted out of ``raw_fields``: the three dates, because every
    longitudinal query orders by collection date, and the patient identifiers, because
    they are what tie a document to a record. Everything else the lab printed stays in
    ``raw_fields`` exactly as written - schema-loose on purpose, since the long tail of
    lab-specific fields is unbounded.

    **The patient name is usually not a labelled field.** Both labs in the corpus print it
    as a bare heading - `Yash M. Patel`, `Mr. Saubhik Bhaumik` - with no key beside it.
    It is recognised by *context* rather than by looking like a name: a heading sitting
    immediately above the demographic block is the patient. That rule needs no notion of
    what names look like, which matters in a country with no single naming convention.

    Args:
        blocks: ``(engine block label, text)`` in reading order. The label is what
            distinguishes a heading from body text, and without it the name is invisible.

    Returns:
        The populated header. Fields that were not printed stay ``None``; a missing date
        is never guessed at.
    """
    header = Header()
    recent_heading: str | None = None
    since_heading = 0

    for label, block in blocks:
        if label.lower() in _TABLE_LABELS:
            # A heading above a results table labels that table. It is not the patient,
            # however close the next demographic key happens to be in reading order.
            recent_heading = None
            continue
        if label.lower() in _TITLE_LABELS:
            recent_heading = " ".join(block.split())
            since_heading = 0
            continue
        since_heading += 1

        for raw_key, raw_value in _key_values(block):
            if not raw_value or len(raw_value) > 120 or _PLACEHOLDER_RE.match(raw_value):
                continue
            for key_part, value in _split_combined(raw_key, raw_value):
                key = _norm_key(key_part)

                # A heading just above the demographics is the patient. Claimed once, and
                # only when the name was not printed as a proper field.
                if (
                    key in _DEMOGRAPHIC
                    and header.patient_name is None
                    and recent_heading
                    and since_heading <= _NAME_LOOKBACK
                ):
                    header.patient_name = recent_heading
                    recent_heading = None

                if key in _PATIENT_NAME:
                    # A labelled name always wins over one inferred from a heading.
                    header.patient_name = value
                elif key in _AGE and header.patient_age is None:
                    header.patient_age = value
                elif key in _SEX and header.patient_sex is None:
                    header.patient_sex = value
                elif key in _PATIENT_ID and header.patient_id is None:
                    header.patient_id = value
                elif key in _DOCTOR and header.referring_doctor is None:
                    header.referring_doctor = value
                elif key in _COLLECTED and header.collected_at is None:
                    header.collected_at = value
                elif key in _TESTED and header.tested_at is None:
                    header.tested_at = value
                elif key in _REPORTED and header.reported_at is None:
                    header.reported_at = value
                elif key in _LAB_NAME and header.lab_name is None:
                    header.lab_name = value
                elif key in _LAB_REF and header.lab_reference_no is None:
                    header.lab_reference_no = value
                header.raw_fields.setdefault(key_part, value)

    # Parsed beside the printed text, never instead of it.
    for field_name in ("collected_at", "tested_at", "reported_at"):
        parsed = parse_lab_date(getattr(header, field_name))
        if parsed is not None:
            setattr(header, f"{field_name}_iso", parsed.isoformat())
    return header


def _cell(row: list[str], col: int | None) -> str | None:
    """Read one cell by role-assigned column index, or ``None`` when unassigned."""
    if col is None or col >= len(row):
        return None
    value = row[col].strip()
    return value or None


def _grid_to_section(
    grid: Grid, *, title: str | None, page: int, bbox: BBox | None, start_index: int
) -> Section:
    """Build one :class:`Section` from a grid, inferring what its columns mean."""
    roles = infer_roles(grid)
    label_col = role_of(roles, Role.LABEL)
    value_col = role_of(roles, Role.VALUE)
    unit_col = role_of(roles, Role.UNIT)
    ref_col = role_of(roles, Role.REFERENCE)
    flag_col = role_of(roles, Role.FLAG)

    # Drop the header row from the data, but only if inference found one.
    from .columns import detect_header_row

    header_idx = detect_header_row(grid)
    data = grid[header_idx + 1 :] if header_idx is not None else list(grid)

    rows: list[Row] = []
    for raw in data:
        cells = list(raw)
        label = _cell(cells, label_col)
        if label is None:
            # A row with no label is not a result. Keep the grid honest by skipping it
            # here; the raw block still reaches unparsed_blocks if nothing parsed.
            continue

        value = _cell(cells, value_col)
        unit = _cell(cells, unit_col)
        reference = _cell(cells, ref_col)
        flag = _cell(cells, flag_col)

        # "Method:Diazo Method" with every other cell empty is a continuation of the
        # test above it, not a result of its own. Folding it onto that row is what stops
        # a twelve-analyte panel arriving at the verification screen as twenty-four rows.
        method = _METHOD_RE.match(label)
        if method and not any((value, unit, reference, flag)) and rows:
            rows[-1].raw_method = method.group(1)
            continue
        if _SPECIMEN_RE.match(label) and not any((value, unit, reference, flag)) and rows:
            continue

        # Many labs print no unit column - the unit rides inside the reference cell as
        # "35-104 U/L". Recover it, because a value without a unit cannot be trended.
        if unit is None and reference is not None:
            _, embedded = split_reference_unit(reference)
            unit = embedded

        # Some labs print no flag column either, and glue the marker to the front of the
        # range: "High 80.00 - 200.00". That marker is the lab's own abnormality call and
        # is worth keeping - it is what a reviewer scans for first.
        if flag is None and reference is not None:
            marker, _ = split_flag_prefix(reference)
            flag = marker

        # Some labs print the assay under the test name in small type, and the reading
        # model merges the two into one cell: "Cholesterol Total Spectrophotometry".
        # raw_label stays exactly as printed; the method is recorded alongside it.
        row_method = method.group(1) if method else split_method_suffix(label)[1]

        rows.append(
            Row(
                row_index=start_index + len(rows),
                raw_label=label,
                raw_value=value,
                raw_unit=unit,
                raw_reference=reference,
                raw_flag=flag,
                raw_method=row_method,
                page=page,
                bbox=bbox,
            )
        )

    return Section(
        printed_title=title,
        rows=rows,
        column_roles={col: role.value for col, role in roles.items()},
        page=page,
        bbox=bbox,
    )


def _normalise(block: RawBlock, page: RawPage) -> BBox | None:
    """Express a block's engine-space box as fractions of the page."""
    if block.bbox is None:
        return None
    try:
        return BBox.from_pixels(block.bbox, page.width, page.height)
    except ValueError:
        return None


def build_extraction(document: RawDocument, *, document_type: str | None = None) -> Extraction:
    """Assemble the extraction JSON from one engine's output.

    Args:
        document: What the engine returned.
        document_type: Optional classification, when something upstream decided one.

    Returns:
        The contract object. Every table block becomes a :class:`Section`; every block
        that did not parse into a grid becomes an :class:`UnparsedBlock`, so nothing the
        engine saw is silently discarded.
    """
    sections: list[Section] = []
    unparsed: list[UnparsedBlock] = []
    text_blocks: list[tuple[str, str]] = []
    row_counter = 0

    for page in document.pages:
        pending_title: str | None = None
        for block in sorted(page.blocks, key=lambda b: (b.order is None, b.order or 0)):
            bbox = _normalise(block, page)
            label = block.label.lower()

            heading = centred_heading(block.content)
            if label in _TITLE_LABELS or heading is not None:
                title_text = heading or " ".join(block.content.split())
                pending_title = title_text
                text_blocks.append(("paragraph_title", title_text))
                continue

            grids = (
                parse_html_tables(block.content)
                if label in _TABLE_LABELS or looks_like_html_table(block.content)
                else []
            )
            if grids:
                for whole in grids:
                    pairs, grid = _header_rows(whole)
                    if pairs:
                        lines = [f"{key} : {value}" for key, value in pairs]
                        text_blocks.append(("text", "\n".join(lines)))
                    if not grid:
                        continue
                    # One HTML table can hold several logical ones, divided by full-width
                    # heading rows. Splitting them keeps the interpretation guide from
                    # contaminating the results grid's column inference.
                    for heading, part in split_sections(grid):
                        section = _grid_to_section(
                            part,
                            title=heading or pending_title,
                            page=page.page_number,
                            bbox=bbox,
                            start_index=row_counter,
                        )
                        row_counter += len(section.rows)
                        sections.append(section)
                    text_blocks.append(("table", ""))
                pending_title = None
                continue

            readable = plain_text(block.content)
            text_blocks.append((block.label, readable))
            unparsed.append(
                UnparsedBlock(
                    page=page.page_number,
                    text=" ".join(readable.split()),
                    bbox=bbox,
                    block_label=block.label,
                )
            )

    return Extraction(
        document=DocumentMeta(
            engine=document.engine,
            engine_version=document.engine_version,
            source_name=document.source_path.name,
            page_count=document.page_count,
            document_type=document_type,
        ),
        header=extract_header_fields(text_blocks),
        sections=sections,
        unparsed_blocks=unparsed,
    )
