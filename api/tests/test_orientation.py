# api/tests/test_orientation.py
"""Some reports lay a panel out as cards: one analyte per column.

P22-R01 (card_grid) returns each analyte as a column and each attribute as a
row. Read row-major it produces nothing usable; read column-major it is an
ordinary result grid.
"""
from __future__ import annotations

from app.services.ocr.columns import Role, assignment_strength, infer_roles, role_of
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


def test_a_tie_prefers_the_printed_orientation():
    """Review Focus 4. Almost every report is row-major; a coin toss that
    sometimes transposes is worse than one that never does."""
    square = [["a", "b"], ["c", "d"]]
    assert assignment_strength(square) >= assignment_strength(transpose(square))


def test_a_card_grid_under_a_spanning_heading_is_not_labelled_with_it():
    """Review Focus 5. The heading spans the cards and is not an analyte."""
    with_heading = [["COMPLETE BLOOD COUNT (CBC)", "", ""]] + CARDS
    roles = infer_roles(transpose(with_heading))
    label_col = role_of(roles, Role.LABEL)
    assert label_col is not None
    assert transpose(with_heading)[0][label_col] != "COMPLETE BLOOD COUNT (CBC)"
