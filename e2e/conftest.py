"""Fixtures for browser tests against the running stack.

Every test gets a page whose console errors, uncaught exceptions and failed
network calls are collected, and the `clean` fixture fails the test if any
occurred. That is the class of fault a reviewer sees as "Failed to fetch" with
no further explanation - the 500 that skipped its CORS headers, the endpoint
that returned null - and it is invisible to every API-level test.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Page

WEB = "http://localhost:3000"
API = "http://localhost:8000"


@pytest.fixture(scope="session", autouse=True)
def _forwarder() -> Iterator[None]:
    """localhost:3000 and :8000 inside this container reach the compose services."""
    process = subprocess.Popen([sys.executable, str(Path(__file__).parent / "forward.py")])
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:  # the console compiles on first request
        try:
            urllib.request.urlopen(API + "/health", timeout=5).close()
            urllib.request.urlopen(WEB + "/", timeout=60).close()
            break
        except OSError:
            time.sleep(1)
    else:
        process.terminate()
        pytest.fail("the stack never answered on :3000 and :8000 - is it up?")
    yield
    process.terminate()


def api(path: str) -> object:
    """A read straight from the API, for picking real ids to test against."""
    with urllib.request.urlopen(API + path, timeout=30) as response:
        return json.loads(response.read())


def all_documents() -> list[dict]:
    """Every live document, paging past the endpoint's 200-row ceiling.

    One page is not "all": with 329 documents a single limit=200 read silently
    drops the oldest 129, and a count taken from it is capped at 200 - so a test
    comparing two such counts passes whether or not anything changed.
    """
    out: list[dict] = []
    while True:
        page = api(f"/documents?limit=200&offset={len(out)}")
        out += page
        if len(page) < 200:
            return out


class Problems(list[str]):
    """What went wrong on the page while a test ran."""


@pytest.fixture
def problems(page: Page) -> Problems:
    found = Problems()
    page.on(
        "console",
        lambda m: found.append(f"console {m.type}: {m.text}") if m.type == "error" else None,
    )
    page.on("pageerror", lambda e: found.append(f"uncaught: {e}"))
    # ERR_ABORTED is a request the page cancelled on purpose: the review screen
    # aborts its fetch in an effect cleanup so a stale response cannot overwrite
    # a newer one, and React's development StrictMode runs every effect, cleans
    # it up, and runs it again. Counting that as a failure would fail every
    # review test on correct behaviour.
    page.on(
        "requestfailed",
        lambda r: (
            found.append(f"{r.method} {r.url} failed: {r.failure}")
            if "ERR_ABORTED" not in (r.failure or "")
            else None
        ),
    )
    page.on(
        "response",
        lambda r: (
            found.append(f"{r.request.method} {r.url} -> {r.status}")
            if r.status >= 400
            else None
        ),
    )
    return found


@pytest.fixture
def clean(problems: Problems) -> Iterator[Problems]:
    """Fail the test if the page logged an error or a request failed."""
    yield problems
    assert not problems, "the page was not clean:\n  " + "\n  ".join(problems)
