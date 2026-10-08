"""The harness reads real engine output, so tests run against real shapes."""

from __future__ import annotations

import pytest
from _pytest.outcomes import Failed, Skipped


def test_cached_blocks_reads_a_known_document(cached_blocks):
    blocks = cached_blocks("P05-R02")
    assert blocks, "expected cached OpenParser blocks for P05-R02"
    assert any(b["label"] == "table" for b in blocks)


def test_missing_dev_set_dump_fails_hard(cached_blocks, monkeypatch, tmp_path):
    """A dev-set dump is load-bearing: its absence must stop the suite, not skip it.

    A Skipped outcome here would mean the DEV_SET guard broke silently: pytest
    reports a skip as green ("N passed, 1 skipped"), not as a failure, so a
    broken guard would let CI through unnoticed. Skipped is caught explicitly
    and turned into a hard failure naming what went wrong, instead of letting
    it escape this test and be reported as a mere skip.
    """
    from tests import conftest

    monkeypatch.setattr(conftest, "RESULTS", tmp_path)
    try:
        with pytest.raises(Failed, match="P05-R02"):
            cached_blocks("P05-R02")
    except Skipped:
        pytest.fail(
            "cached_blocks skipped instead of failing hard for a dev-set "
            "report (P05-R02) - the DEV_SET guard in conftest.py is broken"
        )


def test_missing_other_dump_skips(cached_blocks, monkeypatch, tmp_path):
    """Anything outside the dev set is an optional probe and may skip."""
    from tests import conftest

    monkeypatch.setattr(conftest, "RESULTS", tmp_path)
    with pytest.raises(Skipped):
        cached_blocks("P99-R99")
