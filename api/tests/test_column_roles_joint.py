# api/tests/test_column_roles_joint.py
"""Role assignment must read content, not column position.

Both grids below are transcribed from holdout documents that currently
extract zero usable rows. P22-R04 prints an internal test code to the LEFT
of the test name; P21-R02 prints its columns in reverse order. The old
implementation claimed LABEL as the leftmost text-like column and then
contested every other role only to its right, so both were unrecoverable.
"""
from __future__ import annotations

from app.services.ocr.columns import Role, infer_roles, role_of

# P22-R04, grid_lines layout, trap: test_code_column
CODE_FIRST = [
    ["TEST CODE", "INVESTIGATION", "RESULT", "UNITS", "BIOLOGICAL REFERENCE INTERVAL"],
    ["HAE-001", "Haemoglobin", "11.6", "g/dL", "11.5 - 15.5"],
    ["", "RBC Count", "4.62", "mil/uL", "4.0 - 5.2"],
    ["", "PCV", "35.8", "%", "35 - 45"],
    ["HAE-006", "MCV", "77.5", "fL", "77 - 95"],
]


def test_analyte_column_wins_label_over_a_test_code_column():
    roles = infer_roles(CODE_FIRST)
    assert role_of(roles, Role.LABEL) == 1, (
        f"expected INVESTIGATION (column 1) as the label, got {roles}")


def test_the_test_code_column_is_recognised_not_ignored():
    """CODE exists so the code column has somewhere to go. Without a role of
    its own it competes for LABEL, which is exactly how this bug started."""
    roles = infer_roles(CODE_FIRST)
    assert roles[0] is Role.CODE


# P21-R02, rtl_columns layout, trap: sno_column
REVERSED = [
    ["BIOLOGICAL REFERENCE INTERVAL", "UNITS", "RESULT", "INVESTIGATION", "S.NO"],
    ["0.7 - 1.3", "mg/dL", "1.74", "Creatinine - Serum", "1"],
    ["17 - 43", "mg/dL", "58", "Blood Urea", "2"],
    ["8 - 20", "mg/dL", "27", "Blood Urea Nitrogen", "3"],
    ["3.5 - 7.2", "mg/dL", "7.9", "Uric Acid, Serum", "4"],
]


def test_columns_printed_right_to_left_still_resolve():
    roles = infer_roles(REVERSED)
    assert role_of(roles, Role.LABEL) == 3
    assert role_of(roles, Role.VALUE) == 2
    assert role_of(roles, Role.UNIT) == 1
    assert role_of(roles, Role.REFERENCE) == 0


def test_a_serial_number_column_never_becomes_the_value():
    """The old positional rule existed to stop exactly this. Removing the rule
    must not bring the failure back: S.NO is numeric and would score as a value
    if the real RESULT column were not a better joint fit."""
    roles = infer_roles(REVERSED)
    assert roles.get(4) is not Role.VALUE


def test_two_vocabulary_columns_do_not_both_win_label():
    """A previous-result column repeats the analyte names. Only one column can
    be the label, and it must be the one paired with the current result."""
    grid = [
        ["INVESTIGATION", "PREVIOUS", "RESULT", "UNITS"],
        ["Haemoglobin", "10.2", "11.6", "g/dL"],
        ["RBC Count", "4.10", "4.62", "mil/uL"],
        ["PCV", "33.0", "35.8", "%"],
    ]
    roles = infer_roles(grid)
    assert sum(1 for r in roles.values() if r is Role.LABEL) == 1
    assert role_of(roles, Role.LABEL) == 0


def test_a_two_column_grid_leaves_the_absent_roles_unassigned():
    """Forcing every role onto some column is how a number ends up in raw_unit."""
    grid = [["Haemoglobin", "11.6"], ["RBC Count", "4.62"], ["PCV", "35.8"]]
    roles = infer_roles(grid)
    assert role_of(roles, Role.LABEL) == 0
    assert role_of(roles, Role.VALUE) == 1
    assert role_of(roles, Role.UNIT) is None
    assert role_of(roles, Role.REFERENCE) is None
