"""A near-miss must not swap one test for another (2026-10-15).

"Total RBC Count" is not a spelling the alias master holds, and the fuzzy tier
found "Total WBC Count" at 0.65 similarity - so Ashwini's red cell count was
stored as a white cell count. One letter apart is exactly what fuzzy matching
is for, unless that letter IS the test: when a word of the printed label is,
by itself, another test's name ("rbc"), and the candidate does not contain it,
the match is refused and the row is left for a person. A blank beats a guess.
"""

from __future__ import annotations


def _resolve(db, label: str) -> str | None:
    practice = db.execute("SELECT min(id) FROM core.practices").fetchone()[0]
    row = db.execute(
        "SELECT analyte_code FROM lab.fn_resolve_analyte(%s, %s)", (practice, label)
    ).fetchone()
    return row[0] if row else None


def test_a_red_cell_count_is_never_stored_as_a_white_cell_count(db) -> None:
    assert _resolve(db, "Total RBC Count") != "WBC"


def test_an_honest_near_miss_still_resolves(db) -> None:
    """The guard refuses swaps, not typos: a misspelt name of the same test still lands."""
    assert _resolve(db, "Haemoglobn") == "HGB"
