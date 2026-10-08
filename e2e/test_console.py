"""The review console, driven through a real browser.

Written from what explore.py found rather than from what the components say they
do. Tests marked xfail(strict=True) pin bugs that are confirmed and listed in
docs/review-2026-10-08.md: they pass while the bug is present, and the moment
someone fixes it they turn red, so the marker cannot outlive the bug.

    docker compose --profile e2e run --rm e2e
"""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

import pytest
from conftest import API, WEB, Problems, all_documents, api
from playwright.sync_api import Page, expect

SCREENS = ["/", "/upload", "/queue", "/patients"]


@pytest.mark.parametrize("path", SCREENS)
@pytest.mark.usefixtures("clean")
def test_every_screen_loads_without_an_error(page: Page, path: str) -> None:
    page.goto(WEB + path, wait_until="networkidle")
    expect(page.locator("h1").first).to_be_visible()


@pytest.mark.parametrize("status", ["parsed", "needs_review", "verified"])
@pytest.mark.usefixtures("clean")
def test_the_review_screen_opens_for_each_status(page: Page, status: str) -> None:
    documents = [d for d in all_documents() if d["status"] == status]
    if not documents:
        pytest.skip(f"no {status} document in this database")
    page.goto(f"{WEB}/review?doc={documents[0]['id']}", wait_until="networkidle")
    expect(page.get_by_role("heading", name="Results")).to_be_visible()
    # The page itself is offered, inline or - in headless Chromium, which has no PDF
    # plugin - as a link that opens it.
    expect(page.locator("object[type='application/pdf']")).to_be_attached()


@pytest.mark.usefixtures("clean")
def test_a_reupload_returns_the_document_already_held(page: Page) -> None:
    """The duplicate check: same bytes, same document, nothing read twice.

    Self-guarding. The stored file is downloaded and compared byte for byte
    before anything is uploaded; if the corpus was regenerated since, the bytes
    differ, a new document would be created and the worker would bill a call -
    so the test skips instead.
    """
    local = Path("/corpus/P05/P05-R05.pdf")
    held = [d for d in all_documents() if d.get("file_name") == local.name]
    if not local.exists() or not held:
        pytest.skip("P05-R05.pdf is not both on disk and held by the service")
    with urllib.request.urlopen(f"{API}/documents/{held[0]['id']}/file", timeout=30) as r:
        if r.read() != local.read_bytes():
            pytest.skip(
                "the corpus file differs from the stored one - uploading would read it again"
            )

    before = len(all_documents())
    page.goto(WEB + "/upload", wait_until="networkidle")
    page.locator("input[type='file']").set_input_files(str(local))
    expect(page.locator(".chip").first).to_be_visible(timeout=30_000)
    assert len(all_documents()) == before


# ------------------------------------------------------------ pinned bugs
PATIENT_WITH_AN_UNDATED_READING = "Aadhya Menon"


def _patient_page(page: Page, name: str) -> None:
    found = api("/patients?q=" + name.split(maxsplit=1)[0])
    if not found:
        pytest.skip(f"{name} is not in this database")
    page.goto(f"{WEB}/patients/{found[0]['id']}", wait_until="networkidle")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="review B4: /patients/{id}/analytes groups by the section's panel, so one "
    "analyte appears once per panel-or-none and React sees duplicate keys",
)
def test_the_patient_screen_renders_without_a_duplicate_key_warning(
    page: Page, problems: Problems
) -> None:
    _patient_page(page, PATIENT_WITH_AN_UNDATED_READING)
    duplicates = [p for p in problems if "same key" in p]
    assert not duplicates, f"{len(duplicates)} duplicate-key warnings"


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="review B4: the same grouping lists Haemoglobin twice, each chip with a "
    "partial count, so the picker under-reports the patient's history",
)
def test_each_analyte_appears_once_in_the_trend_picker(page: Page) -> None:
    _patient_page(page, PATIENT_WITH_AN_UNDATED_READING)
    labels = page.locator("button").all_inner_texts()
    haemoglobin = [t for t in labels if re.match(r"^\s*Haemoglobin\b", t)]
    assert len(haemoglobin) == 1, haemoglobin


def test_the_trend_axis_starts_at_the_first_real_reading(page: Page) -> None:
    """Review B3: an undated reading used to be plotted at 1 January 1970."""
    _patient_page(page, PATIENT_WITH_AN_UNDATED_READING)
    axis_years = [
        int(t)
        for t in page.locator("svg text").all_text_contents()  # SVG has no innerText
        if re.fullmatch(r"\d{4}", t.strip())
    ]
    assert axis_years, "no year labels on the trend axis"
    assert min(axis_years) >= 2000, f"axis starts in {min(axis_years)}"


def test_an_undated_reading_is_announced_not_silently_dropped(page: Page) -> None:
    """Review B3's other half. The undated reading cannot sit on a date axis, and
    a chart that quietly drops a reading is worse than no chart - so it says so."""
    _patient_page(page, PATIENT_WITH_AN_UNDATED_READING)
    expect(page.get_by_text(re.compile(r"no date and (is|are) not plotted"))).to_be_visible()
