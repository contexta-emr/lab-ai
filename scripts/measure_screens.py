"""How long each console screen waits on the API, and why.

    docker compose exec -T api python /work/scripts/measure_screens.py
    docker compose exec -T api python /work/scripts/measure_screens.py --runs 5

Requests exactly what each screen requests, in the order the console makes them -
in parallel where it fires them together, one after another where it waits - and
reports, for each call, the median wall time and the database statements behind it
from the API's Server-Timing header (development only; see app.main). A screen's
time is its critical path: the longest chain of calls it waits on, not their sum.

Read-only. Nothing is uploaded, saved or confirmed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

API = os.environ.get("API_URL", "http://localhost:8000")


def call(path: str) -> tuple[float, int, float, bytes]:
    """One GET: (wall ms, db statements, db ms, body)."""
    started = time.perf_counter()
    with urllib.request.urlopen(API + path, timeout=120) as response:
        body = response.read()
        timing = response.headers.get("Server-Timing", "")
    wall = (time.perf_counter() - started) * 1000
    m = re.search(r'db;dur=(\d+);desc="(\d+) statements"', timing)
    return wall, int(m.group(2)) if m else -1, float(m.group(1)) if m else -1.0, body


def measure(path: str, runs: int) -> dict:
    samples = [call(path) for _ in range(runs)]
    return {
        "path": path,
        "ms": statistics.median(s[0] for s in samples),
        "statements": statistics.median(s[1] for s in samples),
        "db_ms": statistics.median(s[2] for s in samples),
    }


def parallel(paths: list[str], runs: int) -> list[dict]:
    with ThreadPoolExecutor(len(paths)) as pool:
        return list(pool.map(lambda p: measure(p, runs), paths))


def first(path: str, key: str, pick: object = None) -> object:
    data = json.loads(call(path)[3])
    items = data.get("items", data) if isinstance(data, dict) else data
    for item in items:
        if pick is None or pick(item):
            return item[key]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--runs", type=int, default=3, help="samples per call; the median is reported"
    )
    ap.add_argument(
        "--document", default="P20-R04.pdf", help="file name to open on the review screen"
    )
    args = ap.parse_args()

    doc = first(
        "/review/queue?limit=500", "id", lambda i: i.get("file_name") == args.document
    ) or first("/review/queue?limit=1", "id")
    patient = first("/patients", "id")
    analytes = json.loads(call(f"/patients/{patient}/analytes")[3]) if patient else []
    term = urllib.parse.quote((first("/patients", "full_name") or "a")[:3])

    screens: list[tuple[str, list[dict], float]] = []

    calls = parallel(["/review/queue", "/documents?limit=12", "/health"], args.runs)
    screens.append(("Overview", calls, max(c["ms"] for c in calls)))

    calls = [measure("/review/queue", args.runs)]
    screens.append(("Queue", calls, calls[0]["ms"]))

    # Everything the review screen needs is requested at once as it opens: the
    # document, its coverage and rows, and the drawer's lists and panel chips.
    # The patient search fires only as somebody types, so it is shown, not waited on.
    opening = parallel(
        [
            f"/documents/{doc}",
            f"/documents/{doc}/coverage",
            f"/documents/{doc}/rows",
            f"/documents/{doc}/lists",
            "/master/panels?core_only=true",
        ],
        args.runs,
    )
    search = measure(f"/patients?q={term}", args.runs)
    critical = max(c["ms"] for c in opening)
    screens.append(("Review", [*opening, search], critical))

    calls = [measure("/patients", args.runs)]
    screens.append(("Patients", calls, calls[0]["ms"]))

    if patient:
        calls = parallel(
            [
                f"/patients/{patient}",
                f"/patients/{patient}/analytes",
                f"/patients/{patient}/documents",
            ],
            args.runs,
        )
        if analytes:
            calls.append(measure(f"/patients/{patient}/trend/{analytes[0]['code']}", args.runs))
        screens.append(("Patient", calls, max(c["ms"] for c in calls)))

    print(f"API {API}, median of {args.runs}, review screen on document {doc}\n")
    print(f"{'screen / call':<46}{'ms':>8}{'db stmts':>10}{'db ms':>8}")
    for name, calls, critical in screens:
        print(f"{name:<46}{critical:>8.0f}   <- what the screen waits for")
        for c in calls:
            path = re.sub(r"/\d+", "/{id}", c["path"])
            print(f"  {path:<44}{c['ms']:>8.0f}{c['statements']:>10.0f}{c['db_ms']:>8.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
