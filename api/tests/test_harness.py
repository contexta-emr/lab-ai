"""The harness reads real engine output, so tests run against real shapes."""
from __future__ import annotations

import pytest


def test_cached_blocks_reads_a_known_document(cached_blocks):
    blocks = cached_blocks("P05-R02")
    assert blocks, "expected cached OpenParser blocks for P05-R02"
    assert any(b["label"] == "table" for b in blocks)


def test_dev_set_constant_contains_required_documents():
    """Dev-set constant must contain the pairing rule development documents."""
    from tests import conftest

    # The dev-set constant must have exactly these four documents.
    assert conftest.DEV_SET == {"P05-R02", "P05-R08", "P06-R11", "P12-R04"}
