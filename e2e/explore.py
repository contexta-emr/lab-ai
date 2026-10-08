"""Walk every screen the way a reviewer would, and record what actually happens.

Not a test - nothing here passes or fails. It visits each page, and for each
records the console errors, the network calls that failed, the headings a
reviewer sees, how long the page took to settle, and a full-page screenshot.
The tests in test_console.py were written from what this found, not from what
the code says the pages ought to do.

    docker compose --profile e2e run --rm e2e python explore.py

Output lands in e2e/artifacts/ (gitignored): explore.json and one PNG a page.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

WEB = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path(__file__).parent / "artifacts"


def api(path: str) -> object:
    with urllib.request.urlopen(API + path, timeout=30) as response:
        return json.loads(response.read())


def visit(page: Page, name: str, path: str) -> dict:
    console: list[str] = []
    failed: list[str] = []
    page.on(
        "console",
        lambda m: (
            console.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None
        ),
    )
    page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
    page.on("requestfailed", lambda r: failed.append(f"{r.method} {r.url} - {r.failure}"))
    page.on(
        "response",
        lambda r: (
            failed.append(f"{r.request.method} {r.url} -> {r.status}")
            if r.status >= 400
            else None
        ),
    )

    started = time.monotonic()
    response = page.goto(WEB + path, wait_until="networkidle", timeout=60_000)
    settled = time.monotonic() - started
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)

    return {
        "page": name,
        "path": path,
        "http": response.status if response else None,
        "seconds_to_settle": round(settled, 2),
        "title": page.title(),
        "headings": [h.strip() for h in page.locator("h1, h2").all_inner_texts()][:12],
        "console": console,
        "failed_requests": failed,
    }


def main() -> int:
    OUT.mkdir(exist_ok=True)
    forwarder = subprocess.Popen([sys.executable, str(Path(__file__).parent / "forward.py")])
    time.sleep(1.0)
    try:
        documents = api("/documents?limit=200")
        by_status: dict[str, str] = {}
        for d in documents:  # one document of each status a reviewer can open
            by_status.setdefault(d["status"], d["id"])
        patients = api("/patients?limit=5")

        targets = [
            ("overview", "/"),
            ("upload", "/upload"),
            ("queue", "/queue"),
            ("patients", "/patients"),
        ]
        targets += [
            (f"review-{status}", f"/review?doc={doc}")
            for status, doc in sorted(by_status.items())
        ]
        if patients:
            targets.append(("patient-detail", f"/patients/{patients[0]['id']}"))

        records = []
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for name, path in targets:
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                page = context.new_page()
                try:
                    records.append(visit(page, name, path))
                except Exception as exc:  # noqa: BLE001 - an exploration records failures, it does not stop on them
                    records.append(
                        {"page": name, "path": path, "error": f"{type(exc).__name__}: {exc}"}
                    )
                context.close()
            browser.close()

        (OUT / "explore.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
        for r in records:
            if "error" in r:
                print(f"  {r['page']:<24} ERROR  {r['error'][:110]}")
                continue
            flag = "  " if not (r["console"] or r["failed_requests"]) else "!!"
            print(
                f"{flag}{r['page']:<24} HTTP {r['http']}  {r['seconds_to_settle']:>5}s  "
                f"console {len(r['console']):>2}  failed {len(r['failed_requests']):>2}  "
                f"{(r['headings'] or [''])[0][:40]}"
            )
        return 0
    finally:
        forwarder.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
