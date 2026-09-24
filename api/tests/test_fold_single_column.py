"""A vertical key-value table is a two-column table printed on its side."""
from __future__ import annotations

from app.services.ocr.tables import fold_single_column


def test_pairs_consecutive_rows():
    grid = [["Patient Name"], ["Devansh Choudhary"], ["Reg. No"], ["MCH/226104"]]
    assert fold_single_column(grid) == [
        ["Patient Name", "Devansh Choudhary"],
        ["Reg. No", "MCH/226104"],
    ]


def test_odd_trailing_row_keeps_a_null_value():
    """Honest blank: never borrow the next label as this row's value."""
    grid = [["Haemoglobin"], ["13.2"], ["Platelet Count"]]
    assert fold_single_column(grid) == [["Haemoglobin", "13.2"], ["Platelet Count", ""]]


def test_wide_grid_is_returned_untouched():
    grid = [["Test", "Value", "Unit"], ["HGB", "13.2", "g/dL"]]
    assert fold_single_column(grid) is grid


def test_mixed_grid_below_majority_is_untouched():
    """Two of five rows single-celled is not a vertical table.

    The boundary matters: a wide table with a couple of spanning rows must not
    be folded.
    """
    grid = [["A", "1"], ["B", "2"], ["C"], ["D"], ["E", "5"]]
    assert fold_single_column(grid) is grid


def test_exact_half_does_not_fold():
    """Strict majority: two single-celled rows of four is a tie, and a tie stays put."""
    grid = [["A"], ["B"], ["C", "1"], ["D", "2"]]
    assert fold_single_column(grid) is grid


def test_all_blank_rows_return_the_grid():
    """No cell has content, so there is nothing to pair and nothing to change."""
    grid = [[""], ["   "]]
    assert fold_single_column(grid) is grid


def test_blank_rows_are_ignored_not_paired():
    grid = [["Sodium"], [""], ["140"]]
    assert fold_single_column(grid) == [["Sodium", "140"]]


def test_empty_grid():
    assert fold_single_column([]) == []
