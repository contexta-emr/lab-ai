"""The harness reads real engine output, so tests run against real shapes."""
from __future__ import annotations


def test_cached_blocks_reads_a_known_document(cached_blocks):
    blocks = cached_blocks("P05-R02")
    assert blocks, "expected cached OpenParser blocks for P05-R02"
    assert any(b["label"] == "table" for b in blocks)
