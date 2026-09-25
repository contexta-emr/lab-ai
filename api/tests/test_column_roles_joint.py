# api/tests/test_column_roles_joint.py
"""Role assignment must read content, not column position.

Both grids below are transcribed from holdout documents that currently
extract zero usable rows. P22-R04 prints an internal test code to the LEFT
of the test name; P21-R02 prints its columns in reverse order. The old
implementation claimed LABEL as the leftmost text-like column and then
contested every other role only to its right, so both were unrecoverable.
"""
from __future__ import annotations

from app.services.ocr.columns import Role, infer_roles, profile_columns, role_of

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
    """A previous-result column repeats the *same analyte names* as the current one, so
    both columns fully resolve against the vocabulary and both are genuine LABEL
    candidates. (An earlier version of this fixture put plain numbers in the second
    column, which can never be a label candidate at all - alpha_fraction is 0 - so the
    assertion below could not have failed no matter what infer_roles did with LABEL.
    Only one column can be LABEL, and it must be the one the header calls the test name.
    """
    grid = [
        ["INVESTIGATION", "PREVIOUS", "RESULT", "UNITS"],
        ["Haemoglobin", "Haemoglobin", "11.6", "g/dL"],
        ["RBC Count", "RBC Count", "4.62", "mil/uL"],
        ["PCV", "PCV", "35.8", "%"],
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


# --- Fix-round-1 review findings -------------------------------------------------
#
# C1: a serial column whose numbers run 3+ digits escaped the old mean-length damping
# and tied the real result column at value_score 1.0; the tie was then broken by lowest
# column index. C2: the same damping deleted VALUE on legitimate short-integer columns
# (a WBC differential, urine microscopy counts, a short panel) that the old positional
# rule got right. C3: an unweighted objective let a false-positive UNIT match outbid a
# genuine LABEL column for the same cell, and pipeline.py drops any row with no label.
# I1: an optional separator in _CODE_RE let real analyte shorthand ("CA125", "VITD3")
# read as an internal test code instead of a label.


def test_a_wide_serial_number_column_never_becomes_the_value():
    """A three-digit S.No is still a running count - width must not exempt it, and the
    real result column must win outright, not by a tie the lowest index happens to
    settle."""
    grid = [
        ["101", "Sodium", "138", "mEq/L"],
        ["102", "Potassium", "4.2", "mEq/L"],
        ["103", "Chloride", "101", "mEq/L"],
        ["104", "Bicarbonate", "24", "mEq/L"],
    ]
    roles = infer_roles(grid)
    assert role_of(roles, Role.LABEL) == 1
    assert role_of(roles, Role.VALUE) == 2
    assert roles.get(0) is not Role.VALUE


def test_a_short_non_ascending_numeric_column_is_not_dampened_at_all():
    """A lone value, or a pair that does not climb by exactly one, is not evidence of
    seriality - only an actual +1 step is. Pins a real training-corpus regression: TLC
    4400 and Platelets 198000 in the same two-row column, with no ascending pair between
    them, were losing VALUE entirely to a phantom "run of length one" that any non-empty
    numeric column trivially has."""
    grid = [["TLC", "4400", "/uL"], ["Platelets", "198000", "/uL"]]
    roles = infer_roles(grid)
    assert role_of(roles, Role.LABEL) == 0
    assert role_of(roles, Role.VALUE) == 1


def test_a_wbc_differential_is_not_mistaken_for_a_serial_column():
    grid = [
        ["Neutrophils", "62", "%"],
        ["Lymphocytes", "30", "%"],
        ["Eosinophils", "4", "%"],
        ["Monocytes", "3", "%"],
        ["Basophils", "1", "%"],
    ]
    roles = infer_roles(grid)
    assert role_of(roles, Role.LABEL) == 0
    assert role_of(roles, Role.VALUE) == 1


def test_urine_microscopy_counts_are_not_mistaken_for_a_serial_column():
    grid = [
        ["Pus Cells", "2", "/hpf"],
        ["Red Blood Cells", "3", "/hpf"],
        ["Epithelial Cells", "0", "/hpf"],
        ["Casts", "0", "/hpf"],
        ["Crystals", "1", "/hpf"],
    ]
    roles = infer_roles(grid)
    assert role_of(roles, Role.LABEL) == 0
    assert role_of(roles, Role.VALUE) == 1


def test_a_short_panel_is_not_mistaken_for_a_serial_column():
    grid = [
        ["Platelet Count", "250", "x10^3/uL"],
        ["WBC Count", "9", "x10^3/uL"],
        ["ESR", "8", "mm/hr"],
    ]
    roles = infer_roles(grid)
    assert role_of(roles, Role.LABEL) == 0
    assert role_of(roles, Role.VALUE) == 1


def test_serial_run_fraction_reads_the_longest_run_not_the_cell_width():
    """Pins the signal itself, not just an end-to-end outcome: a genuine counter scores
    high regardless of digit width, and a column that merely contains short integers
    scores low because it never sustains a +1 run."""
    counter = profile_columns([["7"], ["8"], ["9"], ["10"]])
    assert counter[0].serial_run_fraction == 1.0

    wide_counter = profile_columns([["101"], ["102"], ["103"], ["104"]])
    assert wide_counter[0].serial_run_fraction == 1.0

    differential = profile_columns([["62"], ["30"], ["4"], ["3"], ["1"]])
    assert differential[0].serial_run_fraction < 0.5


def test_a_label_candidate_does_not_lose_to_a_unit_false_positive():
    """looks_like_unit false-positives on short test-name words like "pH". LABEL must
    still win that column - the alternative is UNIT taking it and the row being dropped
    outright for having no label at all."""
    grid = [["pH", "6"], ["Nitrite", "0"], ["Ketone", "0"]]
    roles = infer_roles(grid)
    assert role_of(roles, Role.LABEL) == 0
    assert role_of(roles, Role.VALUE) == 1


def test_real_analyte_shorthand_is_not_mistaken_for_an_internal_code():
    """CA125, VITD3 and CEA2 are real test-name shorthand with letters glued straight to
    digits and no separator, unlike an internal code such as HAE-001. None of them
    resolve against the vocabulary, so an optional separator let them read as CODE and
    drop the whole grid."""
    grid = [
        ["CA125", "35", "U/mL"],
        ["VITD3", "22", "ng/mL"],
        ["CEA2", "2.1", "ng/mL"],
    ]
    roles = infer_roles(grid)
    assert role_of(roles, Role.LABEL) == 0
    assert role_of(roles, Role.VALUE) == 1
    assert roles.get(0) is not Role.CODE
