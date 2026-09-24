"""A header field is not a result, whatever grid it was printed in."""
from __future__ import annotations

import pytest

from app.services.ocr.pipeline import _clean_key, _header_rows, _is_header_key

# Found on the dev set (P05-R02) via the Step 1 diagnostic: printed header fields
# that were falling through _is_header_key, which stopped the whole narrow-report
# header table from promoting (see _header_rows: every filled row must pair).
LEAKED = ["Report Released", "Specimen"]


@pytest.mark.parametrize("printed", LEAKED)
def test_known_header_keys_are_recognised(printed):
    assert _is_header_key(_clean_key(printed))


def test_specimen_does_not_supply_the_second_key_for_whole_table_promotion():
    """A urine/stool panel must not be swallowed just because Specimen pairs.

    _header_rows promotes a whole table to header when every filled row pairs
    AND two keys are recognised header keys. Specimen alone pairing with
    Collected On used to supply that second key on an ordinary results panel,
    discarding Colour, Albumin and Pus Cells silently.
    """
    grid = [
        ["Specimen :", "Urine"],
        ["Collected On :", "09/03/2022"],
        ["Colour :", "Pale yellow"],
        ["Albumin :", "++"],
        ["Pus Cells :", "8-10 /hpf"],
    ]
    header, kept = _header_rows(grid)
    assert kept == grid, "results rows must survive, not be promoted to header"
