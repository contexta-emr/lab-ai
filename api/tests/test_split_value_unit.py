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
    ("cell", "value", "unit"),
    [
        ("12.9 g/dL", "12.9", "g/dL"),
        ("7600 /uL", "7600", "/uL"),
        ("268000 /uL", "268000", "/uL"),
        ("39.1 %", "39.1", "%"),
        ("83 g/L", "83", "g/L"),
        ("1.2 mg/dL", "1.2", "mg/dL"),
        ("12.9g/dL", "12.9", "g/dL"),
        # eGFR is per 1.73 m² of body surface; the superscript failed every pattern.
        ("54 mL/min/1.73m²", "54", "mL/min/1.73m²"),
    ],
)
def test_splits_a_value_from_its_unit(cell, value, unit):
    assert split_value_unit(cell) == (value, unit)


@pytest.mark.parametrize(
    "cell",
    [
        "13.2",  # already bare - nothing to split
        "Negative",  # categorical result
        "<0.01",  # below detection limit, not a number with a unit
        "35 - 104",  # a reference range, not a value
        "35-104 U/L",  # a reference range WITH a unit - split_reference_unit's job
        "Pale yellow",  # free text
        "",
    ],
)
def test_leaves_everything_else_alone(cell):
    """Anything that is not a bare number followed by a unit comes back unchanged."""
    assert split_value_unit(cell) == (cell.strip(), None)


@pytest.mark.parametrize(
    ("cell", "value", "flag"),
    [("214 H", "214", "H"), ("34 L", "34", "L"), ("9.6 HH", "9.6", "HH"), ("12 N", "12", "N")],
)
def test_an_abnormality_flag_is_not_a_unit(cell, value, flag):
    """ "214 H" is a high result, not 214 hectares.

    The unit shape heuristic accepts a bare letter, and H/L/M are the commonest
    abnormality markers on an Indian lab report - 515 cells in the corpus. Treating
    one as a unit records the marker in the unit field and loses the flag entirely.
    Callers that strip the flag first never see this; a caller that does not, does.
    """
    from app.services.ocr.numbers import split_flag_suffix

    assert split_value_unit(cell) == (cell, None)
    # and the flag splitter, which owns this shape, still handles it
    assert split_flag_suffix(cell) == (value, flag)


@pytest.mark.parametrize("cell", ["22.4 M", "102 M", "5 X", "7 K"])
def test_a_lone_letter_is_not_a_unit(cell):
    """A single bare letter is a marker, an initial or noise - not a measurement.

    The shape heuristic accepts one letter, which lets stray column markers become
    units. Every real unit in UNIT_LEXICON is either multi-character or "%", so
    requiring lexicon membership for a one-letter unit closes the whole class rather
    than the particular letters that happen to appear in this corpus.
    """
    assert split_value_unit(cell) == (cell, None)


def test_a_known_one_character_unit_still_works():
    """% is a real unit and one character long; the rule must not catch it."""
    assert split_value_unit("39.1 %") == ("39.1", "%")
