"""Fixtures backed by recorded engine output.

The dumps in bench/results are OpenParser's blocks before any interpretation.
Testing against them means testing against shapes a real lab actually printed,
not against a hand-written approximation of one.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

RESULTS = Path(__file__).resolve().parents[2] / "bench" / "results"


@pytest.fixture
def cached_blocks():
    """Every block the engine returned for a corpus document, in page order."""

    def _read(report_id: str) -> list[dict]:
        path = RESULTS / f"{report_id}.OPENPARSER.raw.json"
        if not path.exists():
            pytest.skip(f"no cached dump for {report_id}; run bench/run.ps1 first")
        document = json.loads(path.read_text(encoding="utf-8"))
        return [block for page in document["pages"] for block in page["blocks"]]

    return _read
