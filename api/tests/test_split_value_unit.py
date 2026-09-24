"""A value printed with its unit in the same cell is still a value.

Indian labs frequently print "12.9 g/dL" in one cell rather than splitting the
unit into its own column. The column profiler tested cells for being a bare
number, so a whole column of these scored zero and was typed UNKNOWN - no value
column was recognised and every reading on the panel was dropped.
"""
from __future__ import annotations

import pytest

from app.services.ocr.numbers import split_value_unit


@pytest.mark.parametrize(
    "cell, value, unit",
    [
        ("12.9 g/dL", "12.9", "g/dL"),
        ("7600 /uL", "7600", "/uL"),
        ("268000 /uL", "268000", "/uL"),
        ("39.1 %", "39.1", "%"),
        ("83 g/L", "83", "g/L"),
        ("1.2 mg/dL", "1.2", "mg/dL"),
        ("12.9g/dL", "12.9", "g/dL"),
    ],
)
def test_splits_a_value_from_its_unit(cell, value, unit):
    assert split_value_unit(cell) == (value, unit)


@pytest.mark.parametrize(
    "cell",
    [
        "13.2",           # already bare - nothing to split
        "Negative",       # categorical result
        "<0.01",          # below detection limit, not a number with a unit
        "35 - 104",       # a reference range, not a value
        "35-104 U/L",     # a reference range WITH a unit - split_reference_unit's job
        "Pale yellow",    # free text
        "",
    ],
)
def test_leaves_everything_else_alone(cell):
    """Anything that is not a bare number followed by a unit comes back unchanged."""
    assert split_value_unit(cell) == (cell.strip(), None)
