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

from app.services.ocr.labels import _is_unit, split_label
from app.services.ocr.numbers import UNIT_LEXICON
from app.services.ocr.synonyms import load_synonyms, normalise_label


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
    """ "(Sr.)" is the LOINC SYSTEM axis, not a unit, and stripping it would
    merge serum and plasma creatinine into one series."""
    parts = split_label("Creatinine (Sr.)")
    assert parts.name == "Creatinine (Sr.)"
    assert parts.unit is None


def test_a_bare_bracketed_unit_with_no_name_before_it_is_kept_whole():
    """Review Focus 3. _TRAILING_GROUP_RE requires a test name before the
    bracket (`.*\\S`), so "(mg/dL)" has nowhere to produce an empty stem -
    there is genuinely nothing left to call the test, and the text is kept
    exactly as printed rather than emitting a nameless row."""
    parts = split_label("(mg/dL)")
    assert parts.name == "(mg/dL)"
    assert parts.unit is None
    assert parts.method is None


def test_ordering_unit_before_method_not_method_before_unit():
    """The unit must come off before split_method_suffix runs. Swapped, the
    fallback sees "Cholesterol Total Spectrophotometry (mg/dL)" whole:
    "(mg/dL)" is not a known method word, "Spectrophotometry (mg/dL)" is not
    either, and nothing before that resolves with the unit still attached -
    so the swapped order returns method=None. Every other test in this file
    still passes under that swap; this is the one that does not, because
    test_a_method_sub_line_is_separated_from_the_name gets its method from
    the "Method:" line regex, never from this fallback."""
    parts = split_label("Cholesterol Total Spectrophotometry (mg/dL)")
    assert parts.name == "Cholesterol Total"
    assert parts.unit == "mg/dL"
    assert parts.method == "Spectrophotometry"


def test_a_bracketed_method_is_recorded_without_losing_the_printed_label():
    """ "TSH (CLIA)" is not a unit and not a specimen qualifier - it is the
    analyte's own printed form with a real assay method attached. Unlike a
    unit, a bracketed method does not block resolution (synonyms.resolve
    already calls split_method_suffix itself), so there is no need to choose
    between keeping the label and keeping the method: both are kept."""
    parts = split_label("TSH (CLIA)")
    assert parts.name == "TSH (CLIA)"
    assert parts.method == "CLIA"


def test_only_ph_collides_with_the_analyte_seed():
    """``_is_unit`` (labels.py:62) excludes any ``UNIT_LEXICON`` entry that is
    also a resolvable analyte synonym, because a word that names an analyte is
    a label, not a unit - "pH" is a genuine blood-gas unit but also
    UR_PH's own synonym, printed as "Reaction (pH)", and treating it as a
    unit corpus-wide turned 17 correctly-labelled rows into "Reaction".

    That exclusion is coupled to the seed, not just to "pH": the comment
    above ``_is_unit`` says "ratio", "index", "score" and "titre" are each
    one seed row away from the same collision. This pins the current,
    checked state - exactly one collision - so the next synonym added for
    any other ``UNIT_LEXICON`` entry fails this test instead of silently
    disabling unit-stripping for it.
    """
    colliding = {u for u in UNIT_LEXICON if load_synonyms().get(normalise_label(u))}
    assert colliding == {"ph"}
    assert all(_is_unit(u) for u in UNIT_LEXICON if u != "ph")
    assert _is_unit("ph") is False


@pytest.mark.parametrize("text", [None, "", "   "])
def test_empty_or_missing_input_is_tolerated(text):
    """``text`` is typed ``str``, but a caller upstream can still hand this a
    bare ``None`` - a cell an OCR engine returned nothing for. ``(text or
    "").strip()`` is what keeps that from raising: with the `or ""` removed,
    ``None.strip()`` raises ``AttributeError`` and this fails for the
    ``None`` case specifically. "" and "   " do not add coverage beyond
    that - ``str.strip()`` already tolerates them either way - but they
    pin the boundary result (an empty name, no unit, no method) that
    callers are entitled to rely on for a blank cell.
    """
    parts = split_label(text)
    assert parts.name == (text or "").strip()
    assert parts.unit is None and parts.method is None
