"""A header field is not a result, whatever grid it was printed in."""
from __future__ import annotations

import pytest

from app.services.ocr.pipeline import _clean_key, _is_header_key

# Found on the dev set (P05-R02) via the Step 1 diagnostic: printed header fields
# that were falling through _is_header_key, which stopped the whole narrow-report
# header table from promoting (see _header_rows: every filled row must pair).
LEAKED = ["Report Released", "Specimen"]


@pytest.mark.parametrize("printed", LEAKED)
def test_known_header_keys_are_recognised(printed):
    assert _is_header_key(_clean_key(printed))
