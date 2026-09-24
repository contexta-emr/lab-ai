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
