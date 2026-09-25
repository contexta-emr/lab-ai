# api/tests/test_label_parts.py
"""A printed label carries more than the test name.

LOINC models a lab observation on six axes; three of them show up glued into
one cell on real reports - the COMPONENT (the test), the SYSTEM (the specimen,
"Sr."), and the METHOD. A label still carrying its unit resolves against
nothing, so the unit has to come off before the method split will fire.

Both cases below are transcribed from holdout documents.
"""
from __future__ import annotations

import pytest

from app.services.ocr.labels import split_label


def test_a_unit_in_brackets_is_taken_off_the_name():
    """P22-R03, pastel_wellness, trap: unit_in_label."""
    parts = split_label("Haemoglobin level (g/dL)")
    assert parts.name == "Haemoglobin level"
    assert parts.unit == "g/dL"
    assert parts.method is None


def test_a_method_sub_line_is_separated_from_the_name():
    """P21-R04, form_boxes. The newline arrives as two literal characters."""
    parts = split_label("Creatinine (Sr.) (mg/dL)\\nMethod: Modified Jaffe, kinetic")
    assert parts.name == "Creatinine (Sr.)"
    assert parts.unit == "mg/dL"
    assert parts.method == "Modified Jaffe, kinetic"


def test_a_specimen_qualifier_is_not_mistaken_for_a_unit():
    """"(Sr.)" is the LOINC SYSTEM axis, not a unit, and stripping it would
    merge serum and plasma creatinine into one series."""
    parts = split_label("Creatinine (Sr.)")
    assert parts.name == "Creatinine (Sr.)"
    assert parts.unit is None


def test_a_label_that_is_only_a_unit_keeps_its_text():
    """Review Focus 3. Reducing a label to "" emits a nameless row."""
    parts = split_label("mg/dL")
    assert parts.name == "mg/dL"
    assert parts.unit is None


@pytest.mark.parametrize("text", ["", "   "])
def test_empty_input_is_tolerated(text):
    parts = split_label(text)
    assert parts.name == text.strip()
    assert parts.unit is None and parts.method is None
