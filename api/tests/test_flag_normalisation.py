"""The flag column is a closed domain, and these are the values that may enter it.

lab.results.flag is VARCHAR(4) with a CHECK allowing exactly H, L, HH, LL, A
and N. Anything else aborts the INSERT and loses the whole document - which is
how four reports died, each after three OpenParser calls, when a misread column
turned "Interpretation" into "Inte". These pin the normaliser that stops it.

Moved here from a self-check that lived inside ocr_ingest.py and only ran when
someone remembered to execute the module by hand.
"""

from __future__ import annotations

import pytest

from app.services.ocr_ingest import _FLAGS, _flag

DOMAIN = {"H", "L", "HH", "LL", "A", "N"}


@pytest.mark.parametrize(
    ("printed", "stored"),
    [
        ("H", "H"),
        (" high ", "H"),
        ("↑", "H"),
        ("LL", "LL"),
        ("↓↓", "LL"),
        ("*", "A"),
        ("**", "A"),
        ("normal", "N"),
    ],
)
def test_printed_spellings_map_to_the_canonical_flag(printed, stored):
    assert _flag(printed) == stored


@pytest.mark.parametrize("printed", ["Interpretation", "Inte", "3+", "", None])
def test_anything_outside_the_domain_is_dropped_rather_than_forced_in(printed):
    """Prose, prose cut to four characters, and nothing at all."""
    assert _flag(printed) is None


@pytest.mark.parametrize("printed", [*list(_FLAGS), "Interpretation", "3+", "", None])
def test_whatever_comes_back_is_insertable(printed):
    out = _flag(printed)
    assert out is None or out in DOMAIN
    assert out is None or len(out) <= 4
