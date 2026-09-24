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

# Documents the pairing rule is developed against. Missing dumps for these are failures.
DEV_SET = {"P05-R02", "P05-R08", "P06-R11", "P12-R04"}


@pytest.fixture
def cached_blocks():
    """Every block the engine returned for a corpus document, in page order."""

    def _read(report_id: str) -> list[dict]:
        path = RESULTS / f"{report_id}.OPENPARSER.raw.json"
        if not path.exists():
            # Dev-set dumps are load-bearing; missing one means a corrupted repo state.
            # Optional probes (anything outside the dev set) skip instead.
            if report_id in DEV_SET:
                pytest.fail(
                    f"missing required dev-set dump: {path.name}"
                )
            else:
                pytest.skip(f"no cached dump for {report_id}; run bench/run.ps1 first")
        document = json.loads(path.read_text(encoding="utf-8"))
        return [block for page in document["pages"] for block in page["blocks"]]

    return _read
