"""A patient identifier must look like one before it is believed.

The header pairer can mis-associate a key with the wrong cell on a crowded page,
and it was handing back "WBC Count" - an analyte name off the results table - and
bare patient names as the patient id. Those then go to fn_match_patient_by_uhid,
which either finds nobody or, worse, fuzzy-matches somebody else's record.

A wrong identifier is the expensive failure. An honest blank quarantines the
document and a human sorts it out, which is the outcome the whole pipeline is
built to prefer.
"""

from __future__ import annotations

import pytest

from app.services.ocr.pipeline import _is_identifier


@pytest.mark.parametrize(
    "value",
    [
        "SRV/207431",  # the corpus house format
        "MRN/558240",
        "ABCD.12345",  # a dot rather than a slash
        "APMC/FMR/78102",  # three segments
        "555",  # bare number - implausible, but not disprovable
        "P 12345",  # one alphabetic token plus digits
        "ORG/451207",
        "BRM/730914",
    ],
)
def test_accepts_things_that_could_be_identifiers(value: str) -> None:
    assert _is_identifier(value)


@pytest.mark.parametrize(
    "value",
    [
        "WBC Count",  # an analyte name from the table below the header
        "RMakamant Dwivedi",  # a patient name
        "Vijayalakshmi Appala",  # another
        "Ward 4 Bed 12",  # has digits, still prose
        "Complete Blood Count",
        "",
        "   ",
        None,
    ],
)
def test_rejects_things_that_are_not(value: str | None) -> None:
    assert not _is_identifier(value)


def test_rejects_something_far_too_long() -> None:
    """A whole sentence paired with an id key. Length is the last guard, not the
    first: real identifiers are short, and nothing legitimate is 40 characters."""
    assert not _is_identifier("Sample collected at 08:40 on 11/03/2025 by A. Jadhav")


def test_permissive_about_form_on_purpose() -> None:
    """The rule is "contains a digit", not a pattern for the shape of a UHID.

    There is no such shape - every lab invents its own - and a pattern tight
    enough to reject a name would also reject the next format we have not seen.
    That failure mode is worse, because it is silent: a document that could have
    been matched quarantines instead, and nobody knows a rule caused it.
    """
    for invented in ["X1", "2024-ABC-9", "ID#4471", "स/12345"]:
        assert _is_identifier(invented), invented
