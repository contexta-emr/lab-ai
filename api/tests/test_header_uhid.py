# api/tests/test_header_uhid.py
"""The patient identifier decides which record a report joins.

Both header grids below are transcribed from holdout documents whose UHID is
printed plainly on the page and was not recovered. One uses a label nobody had
listed; the other prints the value to the LEFT of its key.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

from app.services.ocr.base import RawBlock, RawDocument, RawPage
from app.services.ocr.pipeline import build_extraction


def _cells_to_html(grid: list[list[str]]) -> str:
    """Render a plain ``list[list[str]]`` grid as the ``<table>`` HTML the pipeline's
    ``parse_html_tables`` reconstructs a grid from.

    ``openparser.cells_to_html`` takes an OpenParser element dict (``row_index`` /
    ``column_index`` cells), not a bare grid, so it does not fit here - this is the
    grid-shaped equivalent the tests need.
    """
    rows = "".join(
        "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>"
        for row in grid
    )
    return f"<table>{rows}</table>"


def _doc(grid: list[list[str]]) -> RawDocument:
    """A one-page document whose only block is this header table."""
    return RawDocument(
        source_path=Path("test.pdf"),
        engine="OPENPARSER",
        engine_version="paddleocr-vl-1.6",
        pages=[RawPage(page_number=1, width=1240.0, height=1754.0,
                       blocks=[RawBlock(label="table", content=_cells_to_html(grid),
                                        bbox=(0.0, 0.0, 1240.0, 300.0), order=0)])],
    )


def test_member_id_is_a_patient_identifier():
    """P22-R03. A wellness lab calls it a Member ID; it is still the UHID."""
    header = build_extraction(_doc([
        ["Patient Name", "Ankita Bhuyan", "Accession No.", "WCP25-042739"],
        ["Member ID", "BRM/730914", "Sample Collected", "20/01/2025 10:15 AM"],
    ])).header
    assert header.patient_id == "BRM/730914"


def test_a_header_printed_value_first_still_yields_the_uhid():
    """P21-R02. The whole grid is right to left, keys in the rightmost column."""
    header = build_extraction(_doc([
        ["VDB/24/002032", "Accession No.", "Prabhakar Deshmukh", "Patient Name"],
        ["14/08/2024 9:05 AM", "Sample Collected", "ORG/451207", "Registration No"],
    ])).header
    assert header.patient_id == "ORG/451207"
    assert header.patient_name == "Prabhakar Deshmukh"


def test_a_left_to_right_header_is_not_broken_by_the_change():
    header = build_extraction(_doc([
        ["Patient Name", "Devansh Choudhary", "Accession No.", "MCH23-047304"],
        ["Hospital No", "MCH/226104", "Sample Collected", "16/09/2023 8:20 AM"],
    ])).header
    assert header.patient_id == "MCH/226104"
    assert header.patient_name == "Devansh Choudhary"


def test_a_value_that_is_itself_a_known_key_is_not_read_backwards():
    """The forward/backward vote that decides which way a headerless row reads
    is deliberately narrower than the set of keys that get *promoted* once a
    direction is chosen (`_ALL_HEADER_KEYS` excludes `_SPECIMEN` and
    `_LAB_NAME` - see pipeline.py:264). "Specimen" and a lab's own name are
    printed constantly, including as filler values beside fields this module
    does not otherwise recognise, so counting them toward the vote would make
    them tip it.

    Widening `_ALL_HEADER_KEYS` with `_SPECIMEN | _LAB_NAME` does exactly
    that here: "Specimen" and "Diagnostics" sit in the two backward-vote
    positions of a row whose only genuine key is "Patient Name" at the front.
    Narrow, the vote stays forward (1 to 0) and "Patient Name" : "A B" reads
    correctly. Widened, backward wins (2 to 1), the row is walked from the
    right instead, and "Patient Name" is consumed as a *value* under the key
    "Specimen" - the patient's name is lost, not just misfiled.
    """
    header = build_extraction(_doc([
        ["Patient Name", "A B", "Bed No", "Specimen", "Ward", "Diagnostics"],
        ["UHID", "XYZ/1"],
    ])).header
    assert header.patient_name == "A B"
    assert header.patient_id == "XYZ/1"
