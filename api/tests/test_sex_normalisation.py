"""The sex column is a closed domain too: M, F or O, or nothing.

lab.reports.sex_printed has a CHECK allowing exactly M, F and O. A redacted
report prints "Age / Sex : XXXXX / XXXXX", the reader took "X", and the CHECK
aborted the insert - losing 29 values that had been read perfectly, three
times over, at the price of an OpenParser read each time (a redacted vendor report, 2026-10-15).
The same failure the flag column had; the same rule fixes it.
"""

from __future__ import annotations

import pytest

from app.services.ocr_ingest import _sex


@pytest.mark.parametrize(
    ("printed", "stored"),
    [
        ("M", "M"),
        ("Male", "M"),
        (" male ", "M"),
        ("F", "F"),
        ("FEMALE", "F"),
        ("O", "O"),
        ("Other", "O"),
    ],
)
def test_a_printed_sex_is_stored_as_its_code(printed: str, stored: str) -> None:
    assert _sex(printed) == stored


@pytest.mark.parametrize("printed", ["X", "XXXXX", "", "Mrs", "32 Y", None])
def test_anything_else_is_stored_as_nothing(printed: str | None) -> None:
    """Redacted, misread or missing: an honest blank, never a value the CHECK refuses."""
    assert _sex(printed) is None
