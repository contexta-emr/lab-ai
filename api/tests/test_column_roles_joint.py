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


# --- Fix-round-2 review findings ---------------------------------------------------
#
# I2: a panel-title row ("KIDNEY FUNCTION TEST" repeated across the columns beneath it)
# was misread as a column-header row, and "TEST" matching the LABEL hint by coincidence
# handed its +0.15 header bonus to whichever column sat under it - overriding a decisive
# 0.9-versus-0.0 vocabulary gap. C2: the fraction-only serial-run measure was a cliff on
# short grids - two consecutive integers covered 100% of a two-row column exactly as an
# eleven-row S.No's run covers all of it, so VALUE was lost on a two-row grid and a
# four-row microscopy panel alike. N1: a hard-required LABEL forced itself onto a pure
# units column with nothing to resolve, fabricating a value under a unit's name.


def test_a_colspan_panel_title_row_grants_no_header_bonus():
    """Two lab panels OCR-merged into one grid, each carrying its own colspan title row
    above the real column headers. "KIDNEY FUNCTION TEST" contains "test", a LABEL hint,
    purely by coincidence - the row is a title, not a description of any one column
    beneath it. Without suppressing the bonus there, the garbled STATUS/fragment column
    (vocab_fraction 0) beat the genuine INVESTIGATION column (vocab_fraction ~0.9) by
    exactly its 0.15 margin. Real corpus regression: P08-R05, P11-R05 - rows came back
    labelled 'NORMAL' and 'LOW' instead of the actual test names."""
    grid = [
        ["HEPATIC FUNCTION PANEL", "HEPATIC FUNCTION PANEL", "HEPATIC FUNCTION PANEL",
         "KIDNEY FUNCTION TEST", "KIDNEY FUNCTION TEST"],
        ["S.NO", "INVESTIGATION", "RESULT", "STATUS", "RESULT"],
        ["1", "Bilirubin, Total", "0.50", "NOR10 Creatinine Serum", "0.54"],
        ["2", "Bilirubin, Direct", "0.10", "NORMA Urea Serum Panel", "16"],
        ["3", "SGPT (ALT)", "18", "NORMA Twelve BUN Reading", "7"],
        ["4", "SGOT (AST)", "20", "HIGH Thirteen eGFR Value", "127"],
    ]
    roles = infer_roles(grid)
    assert role_of(roles, Role.LABEL) == 1


def test_a_two_row_grid_loses_value_to_the_serial_run_floor_deliberately():
    """The absolute run-length floor is 2, calibrated against the training corpus: it
    scores the most correct values overall of 2/3/4, and it fails in the safe direction
    - a dropped row, not a fabricated one (see test_a_two_row_serial_number_fragment_
    does_not_win_value_from_a_malformed_row for what floor 3 fabricated instead). The
    cost, accepted knowingly rather than fixed: two consecutive integers climbing by
    coincidence, in a grid too short to show otherwise, now reads exactly like a
    genuine two-row S.No and loses VALUE right along with it. This pins that known,
    parked trade-off - it must fail if the floor is ever raised to stop paying this
    particular cost, so the regression is visible rather than silent."""
    grid = [["Pus Cells", "2"], ["RBC", "3"]]
    roles = infer_roles(grid)
    assert role_of(roles, Role.LABEL) == 0
    assert role_of(roles, Role.VALUE) is None


def test_a_four_row_microscopy_panel_also_loses_value_at_the_serial_run_floor():
    """Same accepted trade-off as the two-row case, one row longer: "2, 3, 0, 0" has a
    longest run of 2 covering half the column, which is enough to dampen value_score
    (1.0 * (1 - 0.5) = 0.5) below THRESHOLD. The five-row version of this same grid
    (test_urine_microscopy_counts_are_not_mistaken_for_a_serial_column) keeps its VALUE
    at 0.60 - a coincidence of exactly how much of a five-row column a two-long run
    covers, not a difference in principle. Floor 2 is a real, known-imperfect line, not
    a solved problem."""
    grid = [
        ["Pus Cells", "2"],
        ["RBC", "3"],
        ["Epithelial Cells", "0"],
        ["Casts", "0"],
    ]
    roles = infer_roles(grid)
    assert role_of(roles, Role.LABEL) == 0
    assert role_of(roles, Role.VALUE) is None


def test_a_units_only_grid_leaves_label_unassigned_rather_than_fabricate_one():
    """A pure units column ("mEq/L", "mmol/L", "g/dL") is wordy and distinct enough to
    clear label_score on shape alone, with nothing in the grid resolving against the
    vocabulary. The old hard requirement forced LABEL onto it regardless, emitting
    '"mEq/L" = 138' on a grid that has no label column at all. A dropped row is
    recoverable; a fabricated value under a unit's name is not."""
    grid = [
        ["138", "mEq/L", "135 - 145"],
        ["4.2", "mmol/L", "3.5 - 5.1"],
        ["11.6", "g/dL", "12.0 - 15.0"],
    ]
    roles = infer_roles(grid)
    assert role_of(roles, Role.LABEL) is None
    assert role_of(roles, Role.UNIT) == 1


def test_a_genuinely_spanning_reference_column_does_not_blank_a_real_value_header():
    """A per-cell fix, not a per-row one: a reference range genuinely spanning three
    identical sub-columns ("BIOLOGICAL REFERENCE INTERVAL" x3) is a real colspan and
    rightly loses its own bonus, but it sits in the same header row as a perfectly
    ordinary, non-duplicated "RESULT" column two cells over. An earlier version of the
    I2 fix suppressed the bonus for the whole row once it saw any duplicate anywhere,
    which cost RESULT its +0.15 and dropped value_score (0.50 here) back under
    THRESHOLD. Real corpus regression: P02-R06 - Blood Group and HbA1c both lost their
    values."""
    grid = [
        ["INVESTIGATION", "RESULT", "UNITS", "BIOLOGICAL REFERENCE INTERVAL",
         "BIOLOGICAL REFERENCE INTERVAL", "BIOLOGICAL REFERENCE INTERVAL"],
        ["Blood Group (ABO & Rh)", "O Positive", "O Positive", "-", "-", "-"],
        ["HbA1c", "6.0", "H %", "4.0 - 5.6", "4.0 - 5.6", "4.0 - 5.6"],
    ]
    roles = infer_roles(grid)
    assert role_of(roles, Role.LABEL) == 0
    assert role_of(roles, Role.VALUE) == 1


def test_a_three_row_serial_fragment_still_loses_to_the_real_value_column():
    """A genuine S.No column is often seen only as a short fragment mid-continuation
    ("18, 19, 20" partway down a longer panel) - three rows here, not four. An earlier
    version of the C2 fix required an absolute run length of 4, which exempted this
    fragment right along with a real three-row result column and let it win VALUE.
    Real corpus regression: P16-R08."""
    grid = [
        ["S.NO", "INVESTIGATION", "RESULT", "UNITS", "BIOLOGICAL REFERENCE INTERVAL"],
        ["18", "Alanine Transaminase", "43", "U/L", "10 - 49"],
        ["19", "S. Bilirubin (Total)", "0.80", "mg/dL", "0.3 - 1.2"],
        ["20", "Blood Group (ABO & Rh)", "O Positive", "", "-"],
    ]
    roles = infer_roles(grid)
    assert role_of(roles, Role.LABEL) == 1
    assert role_of(roles, Role.VALUE) == 2


def test_a_two_row_serial_number_fragment_does_not_win_value_from_a_malformed_row():
    """P01-R12: a two-row S.No fragment ("23", "24") beside a row where a free-text
    pathology narrative has overflowed its own column, leaving the real RESULT column
    with only one usable cell. At an absolute run-length floor of 3 or 4 this fragment
    stayed undamped, tied the malformed neighbour at value_score 1.0, and won VALUE on
    the tiebreak - emitting "ESR = 24", a serial number under a real test name. This
    task has established throughout that a wrong value under a right label is worse
    than no value at all, which is why the floor is 2 and not higher: floor 2 damps
    this fragment and the row comes back empty instead of fabricated."""
    grid = [
        ["S.NO", "INVESTIGATION", "RESULT", "UNITS", "BIOLOGICAL REFERENCE INTERVAL"],
        ["23", "Urine Culture & Sensitivity",
         "Escherichia coli, >100000 CFU/mL. Sensitive: Nitrofurantoin, Fosfomycin, "
         "Meropenem. Resistant: Ciprofloxacin, Co-trimoxazole. H", "", "No growth"],
        ["24", "ESR", "", "48 H", "mm/hr 0 - 15"],
    ]
    roles = infer_roles(grid)
    assert roles.get(0) is not Role.VALUE
