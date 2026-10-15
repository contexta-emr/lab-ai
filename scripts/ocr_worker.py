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

WHY IT STILL EXISTS
    The console now reads each upload itself, through POST
    /documents/read-next - on Vercel nothing runs between requests, so it
    has to. Locally this keeps reading whatever is left waiting, as it always
    has. The body of a read is app/services/reader.py, shared by both.

    Several copies can run at once, beside the console's reads.
    fn_claim_document uses FOR UPDATE SKIP LOCKED, so no two ever take the
    same document and neither waits.

WHERE THE DATA GOES
    Every document read here is uploaded to api.openparser.dev in the United
    States. Permitted for this service by Karthik's decision of 2026-09-21,
    recorded in CLAUDE.md section 2. About 6 seconds and Rs 0.09 a page when
    idle; the full corpus run averaged 38.9 seconds a document under sustained
    load, so throughput is roughly 90 documents an hour per worker, not 600.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
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
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--forever",
        action="store_true",
        help="keep polling instead of stopping when the queue empties",
    )
    ap.add_argument("--once", action="store_true", help="one document, then stop")
    ap.add_argument(
        "--idle-seconds",
        type=float,
        default=5.0,
        help="how long to wait when the queue is empty (--forever)",
    )
    ap.add_argument("--practice", default=PRACTICE_NAME)
    ap.add_argument(
        "--grounded",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="send documents Pass A read no value from to a language "
        "model (Pass B). On by default, by Karthik's call of "
        "2026-10-08; --no-grounded turns it off. Without "
        "ANTHROPIC_API_KEY it is off and the worker says so.",
    )
    ap.add_argument(
        "--results",
        default=os.environ.get("RESULTS_DIR", str(ROOT / "bench" / "results")),
        help="where to write one JSON per document, named after "
        "the PDF. Empty string turns it off.",
    )
    ap.add_argument(
        "--storage",
        default=os.environ.get("STORAGE_DIR", str(ROOT / "storage")),
        help="where uploaded files live FOR THIS PROCESS. The path in "
        "the database is the one the api container saw, which is "
        "not a path on this machine, so the file is found by name "
        "under this root instead.",
    )
    args = ap.parse_args()
    # The OCR engines report progress through logging. Bare messages, so the
    # console reads exactly as it did when they printed.
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)

    load_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit(
            "DATABASE_URL is not set. For the local stack:\n"
            "  postgresql://labidp:labidp_local_only@localhost:5433/labidp"
        )

    import psycopg

    from app.services import reader
    from app.services.ocr.grounded import GroundedPass
    from app.services.ocr.openparser import OpenParserEngine, read_key

    key = read_key(ROOT)
    if not key:
        sys.exit("IDP_OPENPARSER_KEY is not set. Put it in .env, never in the repo.")
    results_dir = Path(args.results) if args.results else None

    # Pass B: the policy - when to fire, what may leave the machine - lives in
    # app/services/reader.py, shared with the console's own reads.
    pass_b = GroundedPass(status=lambda m: print(f"  grounded: {m}"))
    if args.grounded and not pass_b.configured:
        # Not an exit. docker-compose restarts the worker when it stops, so
        # exiting here would stop every document being read for want of the
        # optional pass. Off, said once and loudly, is the recoverable state: a
        # document Pass A cannot read still lands in the queue with nothing on
        # it, exactly as it did before Pass B existed.
        print("Pass B is OFF: --grounded was given but ANTHROPIC_API_KEY is not set.")
    tools = reader.Tools(
        engine=OpenParserEngine(key=key),
        pass_b=pass_b if args.grounded and pass_b.configured else None,
        storage_dir=Path(args.storage),
        results_dir=results_dir,
    )

    if results_dir is not None:
        results_dir.mkdir(parents=True, exist_ok=True)
        print(f"extractions: {results_dir}")

    done = failed = 0
    started = time.time()
    # Autocommit: each statement - a claim, a completion - is atomic on its
    # own, exactly as the api's pool runs them.
    with psycopg.connect(url, autocommit=True) as conn:
        practice = conn.execute(
            "SELECT id FROM core.practices WHERE name = %s", (args.practice,)
        ).fetchone()
        if practice is None:
            sys.exit(f"No practice named {args.practice!r}. Apply db/005 first.")
        practice_id = practice[0]

        print(f"worker up: practice {practice_id}, engine openparser")
        print("documents read here are uploaded to api.openparser.dev, United States")
        if tools.pass_b is not None:
            print(
                "Pass B on: a document with no value read sends its table and text "
                "blocks, header lines withheld, to api.anthropic.com, United States"
            )
        print()

        @contextmanager
        def connect() -> Iterator[psycopg.Connection]:
            yield conn

        while True:
            outcome = reader.read_next(practice_id, tools, connect)
            if outcome is None:
                if args.forever and not args.once:
                    time.sleep(args.idle_seconds)
                    continue
                break
            # Ids only on the console, never the file name or the UHID: real
            # file names are often the patient's name - review B9.
            if outcome["step"] == "done":
                done += 1
                print(
                    f"  doc {outcome['document_id']:<8} {outcome.get('tests', '?'):>3} rows  "
                    f"{outcome.get('status', '?')}"
                )
            else:
                failed += 1
                print(f"  doc {outcome['document_id']:<8} failed ({outcome['state']})")
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
