"""A method printed on its own line belongs to the test above it (2026-10-15).

Vijaya's blood count prints each test's method underneath it, with no
"Method:" prefix and nothing in the other columns:

    Haemoglobin                  11.5   g/dL   12.0 - 15.0
    Photometric measurement
    Total RBC Count              4.36   ...
    Coulter Principle

Each method line came back as a test of its own, with no value - eight fake
rows on one report, each shown to a reviewer as "no value". They fold onto
the test above as its method, the way "Method: Diazo" lines already do. And a
trailing "Calculated" is the method too, not part of the name: "Packed Cell
Volume / Hematocrit Calculated" was a name nothing could resolve.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from app.services.ocr.base import RawBlock, RawDocument, RawPage
from app.services.ocr.pipeline import build_extraction


def _doc(grid: list[list[str]]) -> RawDocument:
    rows = "".join(
        "<tr>" + "".join(f"<td>{escape(c)}</td>" for c in row) + "</tr>" for row in grid
    )
    return RawDocument(
        source_path=Path("test.pdf"),
        engine="OPENPARSER",
        engine_version="test",
        pages=[
            RawPage(
                page_number=1,
                width=1240.0,
                height=1754.0,
                blocks=[
                    RawBlock(
                        label="table",
                        content=f"<table>{rows}</table>",
                        bbox=(0.0, 300.0, 1240.0, 900.0),
                        order=0,
                    )
                ],
            )
        ],
    )


GRID = [
    ["Test Name", "Result", "Units", "Biological Reference Interval"],
    ["Haemoglobin", "11.5", "g/dL", "12.0 - 15.0"],
    ["Photometric measurement", "", "", ""],
    ["Total RBC Count", "4.36", "millions/cumm", "3.8 - 4.8"],
    ["Coulter Principle", "", "", ""],
    ["Packed Cell Volume / Hematocrit Calculated", "35.00", "%", "36 - 46"],
    ["MCV", "80.40", "fL", "83 - 101"],
    ["Derived from RBC Histogram", "", "", ""],
    ["Neutrophils", "57", "%", "40 - 80"],
    ["VCSn Technology / Microscopy", "", "", ""],
    ["Peripheral Smear", "", "", ""],
]


def _rows():
    extraction = build_extraction(_doc(GRID))
    return [row for section in extraction.sections for row in section.rows]


def test_a_method_line_is_the_method_of_the_test_above() -> None:
    by_label = {row.raw_label: row for row in _rows()}
    assert "Photometric measurement" not in by_label
    assert "Coulter Principle" not in by_label
    assert "Derived from RBC Histogram" not in by_label
    assert "VCSn Technology / Microscopy" not in by_label
    assert by_label["Haemoglobin"].raw_method == "Photometric measurement"
    assert by_label["Total RBC Count"].raw_method == "Coulter Principle"
    assert by_label["Neutrophils"].raw_method == "VCSn Technology / Microscopy"


def test_a_trailing_calculated_is_the_method_not_the_name() -> None:
    labels = [row.raw_label for row in _rows()]
    assert "Packed Cell Volume / Hematocrit" in labels


def test_a_valueless_line_that_is_not_a_method_stays_a_row() -> None:
    """A test the lab prints without a number is still a test - never folded away."""
    assert "Peripheral Smear" in [row.raw_label for row in _rows()]
