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


@pytest.mark.usefixtures("clean")
def test_home_offers_the_drop_area_and_the_tabs(page: Page) -> None:
    page.goto(WEB + "/", wait_until="networkidle")
    expect(page.get_by_text("Drop lab reports here")).to_be_visible()
    expect(page.get_by_role("tab", name=re.compile("Needs checking"))).to_be_visible()


@pytest.mark.usefixtures("clean")
def test_a_patient_can_be_added_from_the_patients_page(page: Page) -> None:
    page.goto(WEB + "/patients", wait_until="networkidle")
    page.get_by_role("button", name="+ Add patient").click()
    expect(page.get_by_role("heading", name="Add a patient")).to_be_visible()
    page.get_by_role("button", name="Cancel").click()
    expect(page.get_by_role("heading", name="Add a patient")).to_be_hidden()


@pytest.mark.parametrize("status", ["parsed", "needs_review", "verified"])
@pytest.mark.usefixtures("clean")
def test_the_review_screen_opens_for_each_status(page: Page, status: str) -> None:
    documents = [d for d in all_documents() if d["status"] == status]
    if not documents:
        pytest.skip(f"no {status} document in this database")
    page.goto(f"{WEB}/review?doc={documents[0]['id']}", wait_until="networkidle")
    # Either designed state: the results, or - for a page nothing was read from,
    # which after a fresh run is often the first one waiting - the empty state.
    results = page.get_by_role("heading", name="Results")
    nothing_read = page.get_by_text("No rows came out of this page")
    expect(results.or_(nothing_read)).to_be_visible()
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
    page.goto(WEB + "/", wait_until="networkidle")
    page.locator("input[type='file']").set_input_files(str(local))
    # The card for THIS upload, not any card already on Home.
    expect(page.locator(".report-card.live .chip").first).to_be_visible(timeout=30_000)
    assert len(all_documents()) == before


# ------------------------------------------------------------ pinned bugs
PATIENT_WITH_AN_UNDATED_READING = "Aadhya Menon"


def _patient_page(page: Page, name: str) -> None:
    found = api("/patients?q=" + name.split(maxsplit=1)[0])
    if not found:
        pytest.skip(f"{name} is not in this database")
    # Every test that opens this page is about the trend picker and the chart,
    # which read verified results only. Straight after a fresh benchmark nothing
    # is verified, and these would pass or fail on an empty page.
    if not api(f"/patients/{found[0]['id']}/analytes"):
        pytest.skip(f"nothing of {name}'s is verified yet, so there is no trend to test")
    page.goto(f"{WEB}/patients/{found[0]['id']}", wait_until="networkidle")


def test_the_patient_screen_renders_without_a_duplicate_key_warning(
    page: Page, problems: Problems
) -> None:
    """Review B4: /patients/{id}/analytes grouped by the section's panel as well as
    the analyte, so one analyte came back once per panel-or-none and React warned
    about duplicate keys 48 times on one page."""
    _patient_page(page, PATIENT_WITH_AN_UNDATED_READING)
    duplicates = [p for p in problems if "same key" in p]
    assert not duplicates, f"{len(duplicates)} duplicate-key warnings"


def test_each_analyte_appears_once_in_the_trend_picker(page: Page) -> None:
    """Review B4's clinical half: Haemoglobin was listed twice, as 8 readings and 3,
    so the picker under-reported an 11-reading history and ranked it too low."""
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


# ------------------------------------------------------- the ordered-tests drawer
ORDERED_DOCUMENT = "P20-R04.pdf"


def _ordered_document() -> tuple[str, dict]:
    """P20-R04 and its lists, or a skip when it has no doctor's order to check."""
    found = [
        d for d in api("/review/queue?limit=500")["items"] if d["file_name"] == ORDERED_DOCUMENT
    ]
    if not found:
        pytest.skip(f"{ORDERED_DOCUMENT} is not in this database")
    lists = api(f"/documents/{found[0]['id']}/lists")
    if not lists["doctor_order"]["terms"]:
        pytest.skip(f"{ORDERED_DOCUMENT} has no doctor's order to check")
    return found[0]["id"], lists


def test_a_chip_edits_the_order_without_checking_it(page: Page) -> None:
    """Pressing a chip sent the list to be checked, every press - seconds each against
    a distant database. Now it only edits the text; Check does the checking, and the
    result already shown is marked out of date in the meantime. Nothing is saved."""
    doc_id, lists = _ordered_document()
    saves: list[str] = []
    page.on(
        "request",
        lambda r: saves.append(r.url) if r.method == "PUT" and "/lists/" in r.url else None,
    )
    page.goto(f"{WEB}/review?doc={doc_id}", wait_until="networkidle")
    page.get_by_role("button", name=re.compile("Doctor.s order")).click()
    order = page.locator("section.dsec.order")
    ordered_names = {t.get("panel_name") for t in lists["doctor_order"]["terms"]}
    chip = next(
        c
        for c in order.locator("button.quick-chip").all()
        if c.inner_text() not in ordered_names
    )

    chip.click()
    expect(order.get_by_text("List changed - press Check")).to_be_visible()
    chip.click()  # and back: the list matches what was checked again
    expect(order.get_by_text("List changed - press Check")).to_be_hidden()
    assert saves == [], f"a chip press sent the list: {saves}"


def test_panels_nobody_ordered_are_listed_as_additional(page: Page) -> None:
    """Ordered CBC, the page also has a lipid profile: the lipid profile is extra."""
    doc_id, lists = _ordered_document()
    extra = lists["doctor_order"]["additional"]
    if not extra:
        pytest.skip(f"everything on {ORDERED_DOCUMENT} was ordered")
    page.goto(f"{WEB}/review?doc={doc_id}", wait_until="networkidle")
    page.get_by_role("button", name=re.compile("Doctor.s order")).click()
    expect(page.get_by_text("Also on the page, not asked for")).to_be_visible()
    for panel in extra:
        expect(page.locator("li.tick.extra", has_text=panel["panel_name"])).to_be_visible()
