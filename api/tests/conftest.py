"""Fixtures backed by recorded engine output.

The dumps in bench/results are OpenParser's blocks before any interpretation.
Testing against them means testing against shapes a real lab actually printed,
not against a hand-written approximation of one.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


def _dumps_dir() -> Path:
    """Where the recorded blocks are, from wherever the suite is being run.

    From a host checkout the tests sit two levels under the repo root. Inside
    the api container they sit at /app/tests, so parents[2] is "/" and the
    dumps are on their compose mount instead. Finding neither is not guessed
    at - the fixtures fail or skip on a missing file, loudly, as they did.
    """
    override = os.environ.get("LABIDP_DUMPS")
    if override:
        return Path(override)
    checkout = Path(__file__).resolve().parents[2] / "bench" / "results"
    if checkout.is_dir():
        return checkout
    return Path("/work/bench/results")


RESULTS = _dumps_dir()

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
                pytest.fail(f"missing required dev-set dump: {path.name}")
            else:
                pytest.skip(f"no cached dump for {report_id}; run bench/run.ps1 first")
        document = json.loads(path.read_text(encoding="utf-8"))
        return [block for page in document["pages"] for block in page["blocks"]]

    return _read


@pytest.fixture(scope="session")
def db():
    """A connection to the service's own database, or a skip when there is none.

    The Postgres functions are the product - alias resolution, patient matching and the
    ingest transaction all live in SQL - so testing them means running them. Everything
    that does not need the database stays runnable anywhere.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("no DATABASE_URL; run inside the api container to exercise the functions")
    try:
        import psycopg
    except ImportError:  # pragma: no cover - environment without the driver
        pytest.skip("psycopg is not installed here")
    with psycopg.connect(url) as conn:
        conn.read_only = True
        yield conn


@pytest.fixture
def db_write():
    """A connection whose work is always rolled back.

    Creating a patient is a write, and a test suite that leaves records behind stops
    being repeatable: the second run hits the unique index the first run satisfied.
    Everything here happens inside one transaction that is discarded, so the seed the
    other tests read is exactly as it was.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("no DATABASE_URL; run with the service's database to exercise writes")
    try:
        import psycopg
    except ImportError:  # pragma: no cover - environment without the driver
        pytest.skip("psycopg is not installed here")
    conn = psycopg.connect(url)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()
