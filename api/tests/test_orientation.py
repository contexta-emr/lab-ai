# api/tests/test_orientation.py
"""Some reports lay a panel out as cards: one analyte per column.

P22-R01 (card_grid) returns each analyte as a column and each attribute as a
row. Read row-major it produces nothing usable; read column-major it is an
ordinary result grid.
"""

from __future__ import annotations

from app.services.ocr.columns import Role, assignment_strength, infer_roles, role_of
from app.services.ocr.pipeline import _grid_to_section
from app.services.ocr.tables import transpose

# P22-R01, card_grid layout
CARDS = [
    ["HB (HAEMOGLOBIN)", "RBC COUNT", "HCT / PCV"],
    ["7.8", "3.96", "26.4"],
    ["g/dL", "mil/uL", "%"],
    ["11.5 - 15.5", "4.0 - 5.2", "35 - 45"],
]


def test_transpose_turns_cards_into_rows():
    assert transpose(CARDS) == [
        ["HB (HAEMOGLOBIN)", "7.8", "g/dL", "11.5 - 15.5"],
        ["RBC COUNT", "3.96", "mil/uL", "4.0 - 5.2"],
        ["HCT / PCV", "26.4", "%", "35 - 45"],
    ]


def test_transpose_pads_ragged_rows():
    assert transpose([["a", "b"], ["c"]]) == [["a", "c"], ["b", ""]]


def test_the_transposed_card_grid_assigns_real_roles():
    roles = infer_roles(transpose(CARDS))
    assert role_of(roles, Role.LABEL) == 0
    assert role_of(roles, Role.VALUE) == 1
    assert role_of(roles, Role.UNIT) == 2
    assert role_of(roles, Role.REFERENCE) == 3


ORDINARY = [
    ["INVESTIGATION", "RESULT", "UNITS", "BIOLOGICAL REFERENCE INTERVAL"],
    ["Haemoglobin", "11.6", "g/dL", "11.5 - 15.5"],
    ["RBC Count", "4.62", "mil/uL", "4.0 - 5.2"],
    ["PCV", "35.8", "%", "35 - 45"],
]


def test_a_card_grid_scores_better_transposed():
    assert assignment_strength(transpose(CARDS)) > assignment_strength(CARDS)


def test_an_ordinary_grid_scores_better_as_printed():
    assert assignment_strength(ORDINARY) > assignment_strength(transpose(ORDINARY))


def test_a_column_with_no_vocabulary_match_is_never_the_label():
    """assignment_strength's vocab_fraction guard (columns.py:620): a LABEL column
    that resolves against nothing in the analyte vocabulary must not count, even
    when its shape alone clears THRESHOLD.

    Neither column here names a real analyte - both are fabricated wordy,
    distinct strings - but one is exactly as wordy and distinct as a genuine
    test-name column, and the other is a clean numeric column. Shape alone
    hands LABEL and VALUE to them (see the measured scores below), which is
    precisely the false positive the guard exists to catch: the training
    corpus measured this losing 44 rows across 11 non-card reports, none of
    them an actual card layout, all of them a wrongly-transposed reading whose
    LABEL column resolved zero analyte names. Deleting the guard leaves every
    other test in this suite green.
    """
    grid = [
        ["Foo Bar Baz", "214"],
        ["Quux Corge Grault", "58"],
        ["Wibble Wobble Flob", "97"],
    ]
    roles = infer_roles(grid)
    assert role_of(roles, Role.LABEL) == 0
    assert role_of(roles, Role.VALUE) == 1
    assert assignment_strength(grid) == 0.0


def test_a_near_tie_does_not_flip_a_genuinely_printed_grid():
    """`_FLIP_MARGIN` (pipeline.py:38), exercised through `_grid_to_section` -
    the only place it is ever reached. Review measured two real training
    reports (two_column, boxed_panels) where the wrongly transposed reading
    outscored the correct one by as little as 0.05 and 0.10, both readings
    having found a real LABEL column - too close for a bare `>` to be safe,
    which is exactly why `_FLIP_MARGIN` exists and had no test of its own.

    This grid reproduces that shape: a haemoglobin trend printed alongside
    several serology panels, tracked across many visits. Printed (row-major)
    it is correct. Transposed, each visit becomes a "card" whose name column
    is wordy and mostly non-numeric (a serology result column) or cleanly
    numeric (the haemoglobin trend) - close enough in shape to the genuine
    card layout in `test_the_transposed_card_grid_assigns_real_roles` that it
    narrowly outscores the printed reading. `_FLIP_MARGIN` must hold the line
    anyway.
    """
    serology_terms = ["Negative", "Trace", "Nil", "Reactive", "Present"]
    serology_tests = ["Widal Test", "Dengue NS1 Antigen", "Scrub Typhus IgM", "HIV I & II"]
    visits = 10
    grid = [["Haemoglobin"] + [str(round(11.5 + 0.1 * i, 1)) for i in range(visits)]]
    for offset, name in enumerate(serology_tests):
        grid.append(
            [name] + [serology_terms[(offset + i) % len(serology_terms)] for i in range(visits)]
        )

    printed = assignment_strength(grid)
    transposed = assignment_strength(transpose(grid))
    # The near tie this fixture is built to reproduce: transposed edges out
    # printed, but by less than _FLIP_MARGIN (0.25).
    assert 0.0 < transposed - printed < 0.25

    section = _grid_to_section(grid, title=None, page=1, bbox=None, start_index=0)
    assert [row.raw_label for row in section.rows] == ["Haemoglobin", *serology_tests]
    assert section.rows[0].raw_value == "11.5"


def test_a_card_grid_under_a_spanning_heading_is_not_labelled_with_it():
    """Review Focus 5. The heading spans the cards and is not an analyte."""
    with_heading = [["COMPLETE BLOOD COUNT (CBC)", "", ""]] + CARDS
    roles = infer_roles(transpose(with_heading))
    label_col = role_of(roles, Role.LABEL)
    assert label_col is not None
    assert transpose(with_heading)[0][label_col] != "COMPLETE BLOOD COUNT (CBC)"
