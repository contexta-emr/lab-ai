from __future__ import annotations

import pytest

from app.services.ocr.tables import fold_single_column

WIDE = ["P01-R01", "P02-R03", "P03-R05", "P04-R02"]


@pytest.mark.parametrize("report_id", WIDE)
def test_wide_tables_are_untouched(cached_blocks, report_id):
    """Identity, not equality: the transform must not even rebuild these."""
    from app.services.ocr.tables import looks_like_html_table, parse_html_tables

    for block in cached_blocks(report_id):
        if block["label"] != "table" and not looks_like_html_table(
            block["content"]
        ):
            continue
        for grid in parse_html_tables(block["content"]):
            assert fold_single_column(grid) is grid


def test_value_column_is_recognised_when_the_unit_is_glued_to_the_value():
    """A column of "12.9 g/dL" is a value column, not an unknown one.

    This is the defect that made narrow haematology panels extract with every
    raw_value None: infer_roles asked whether each cell was a bare number, the
    unit made the answer no, and no value column was ever claimed.
    """
    from app.services.ocr.columns import Role, infer_roles

    grid = [
        ["Hemoglobin (Hb)", "12.9 g/dL"],
        ["WBC Count", "7600 /uL"],
        ["PLATELET COUNT", "268000 /uL"],
        ["Haematocrit (PCV)", "39.1 %"],
        ["M.C.V.", "83 g/L"],
    ]
    assert infer_roles(grid) == {0: Role.LABEL, 1: Role.VALUE}
