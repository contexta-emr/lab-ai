"""Read the documents waiting in the queue.

    uv run --with "psycopg[binary]" --with requests \\
        python scripts/ocr_worker.py                 # run until the queue is empty
    uv run ... python scripts/ocr_worker.py --forever   # keep polling
    uv run ... python scripts/ocr_worker.py --once      # exactly one document

Needs DATABASE_URL and IDP_OPENPARSER_KEY. For the local stack:
    postgresql://labidp:labidp_local_only@localhost:5433/labidp

WHAT IT DOES
    Claims a document in 'received' through lab.fn_claim_document, sends the
    stored file to OpenParser, and replaces the placeholder with the real
    extraction through lab.fn_complete_document. A failure is recorded by
    lab.fn_fail_document, which returns the document to the queue while
    attempts remain and gives up afterwards.

WHY IT IS A SEPARATE PROCESS
    The api container has neither requests nor an API key, deliberately: the
    service itself never calls out, so a compromise of the request path cannot
    reach a third party or spend money. This is the only thing that talks to
    OpenParser, and it can be stopped without stopping uploads - they queue.

    Several copies can run at once. fn_claim_document uses FOR UPDATE SKIP
    LOCKED, so two workers never take the same document and neither waits.

WHERE THE DATA GOES
    Every document read here is uploaded to api.openparser.dev in the United
    States. Permitted for this service by Karthik's decision of 2026-09-21,
    recorded in CLAUDE.md section 2. About 6 seconds and Rs 0.09 a page when
    idle; the full corpus run averaged 38.9 seconds a document under sustained
    load, so throughput is roughly 90 documents an hour per worker, not 600.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Where the app package is depends on where this runs. From a checkout it is
# api/; in the worker container the package is pip-installed at /app and this
# script is mounted separately at /work/scripts. Python puts the SCRIPT's
# directory on sys.path, never the working directory, so neither can be
# assumed - add whichever exists.
for _candidate in (ROOT / "api", Path("/app")):
    if (_candidate / "app").is_dir():
        sys.path.insert(0, str(_candidate))

PRACTICE_NAME = "Contexta Demo Clinic"


def load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--forever", action="store_true",
                    help="keep polling instead of stopping when the queue empties")
    ap.add_argument("--once", action="store_true", help="one document, then stop")
    ap.add_argument("--idle-seconds", type=float, default=5.0,
                    help="how long to wait when the queue is empty (--forever)")
    ap.add_argument("--practice", default=PRACTICE_NAME)
    ap.add_argument("--storage", default=os.environ.get("STORAGE_DIR", str(ROOT / "storage")),
                    help="where uploaded files live FOR THIS PROCESS. The path in "
                         "the database is the one the api container saw, which is "
                         "not a path on this machine, so the file is found by name "
                         "under this root instead.")
    args = ap.parse_args()

    load_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set. For the local stack:\n"
                 "  postgresql://labidp:labidp_local_only@localhost:5433/labidp")

    import psycopg

    from app.services.ocr.openparser import OpenParserEngine, read_key
    from app.services.ocr_ingest import extract_with

    key = read_key(ROOT)
    if not key:
        sys.exit("IDP_OPENPARSER_KEY is not set. Put it in .env, never in the repo.")
    engine = OpenParserEngine(key=key)

    done = failed = 0
    started = time.time()
    with psycopg.connect(url) as conn:
        practice = conn.execute("SELECT id FROM core.practices WHERE name = %s",
                                (args.practice,)).fetchone()
        if practice is None:
            sys.exit(f"No practice named {args.practice!r}. Apply db/005 first.")
        practice_id = practice[0]

        print(f"worker up: practice {practice_id}, engine openparser")
        print("documents read here are uploaded to api.openparser.dev, United States\n")

        while True:
            claimed = conn.execute(
                "SELECT * FROM lab.fn_claim_document(%s)", (practice_id,)).fetchone()
            conn.commit()

            if claimed is None:
                if args.forever and not args.once:
                    time.sleep(args.idle_seconds)
                    continue
                break

            doc_id, _attachment, checksum, stored_path, attempts = claimed
            name = Path(stored_path or "").name or f"document {doc_id}"

            try:
                local = Path(args.storage) / Path(stored_path or "").name
                if not local.is_file():
                    raise FileNotFoundError(f"stored file missing: {local}")
                payload = extract_with(engine, local, checksum=checksum)
                new_id = conn.execute(
                    "SELECT lab.fn_complete_document(%s, %s, %s::jsonb, %s)",
                    (practice_id, doc_id, json.dumps(payload), None)).fetchone()[0]
                conn.commit()
                rows = sum(len(s["results"]) for s in payload["reports"][0]["sections"])
                uhid = payload["reports"][0]["uhid_printed"]
                status = conn.execute("SELECT status FROM lab.documents WHERE id = %s",
                                      (new_id,)).fetchone()[0]
                print(f"  {name:34s} -> doc {new_id}  {rows:3d} rows  "
                      f"uhid {uhid or '-':<14} {status}")
                done += 1
            except Exception as exc:                      # noqa: BLE001
                conn.rollback()
                reason = f"{type(exc).__name__}: {exc}"
                state = conn.execute(
                    "SELECT lab.fn_fail_document(%s, %s, %s)",
                    (practice_id, doc_id, reason)).fetchone()[0]
                conn.commit()
                print(f"  {name:34s} -> attempt {attempts} failed ({state}): {reason[:90]}")
                failed += 1

            if args.once:
                break

    elapsed = time.time() - started
    print(f"\n{'=' * 58}")
    print(f"read     {done}")
    print(f"failed   {failed}")
    print(f"elapsed  {elapsed:.0f}s")
    print("=" * 58)
    return 1 if failed and not done else 0


if __name__ == "__main__":
    raise SystemExit(main())
