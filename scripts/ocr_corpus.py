"""Read the image-only corpus PDFs with a hosted or local OCR engine.

    uv run --with "psycopg[binary]" --with requests         python scripts/ocr_corpus.py --limit 5      # five, spread over damage types
    uv run ... python scripts/ocr_corpus.py         # all 61
    uv run ... python scripts/ocr_corpus.py --dry-run   # what it would send, sends nothing

Run it through uv. requests and psycopg are needed by this script alone and
do not belong in the api image - the service itself never calls out and never
should acquire the means to. uv gives them to this one process and leaves
nothing behind.

Needs DATABASE_URL pointing at the stack, which for local Docker is:
    postgresql://labidp:labidp_local_only@localhost:5433/labidp

An offline batch tool, run deliberately. POST /documents is unchanged: a file
with no text layer is still stored, marked ocr_engine "none" and queued. That
separation is on purpose - OCR quality has to be measured before anything
starts trusting it automatically.

    python scripts/probe_text_layer.py --json > corpus/data/no_text_layer.json
    python scripts/ocr_corpus.py --limit 5
    python scripts/score_corpus.py                  # openparser beside pdf-text

WHERE THE DATA GOES
    --engine openparser uploads each document to api.openparser.dev in the
    United States. Permitted for this service by Karthik's decision of
    2026-09-21, recorded in CLAUDE.md section 2. About 6 seconds and Rs 0.09
    a page.

    --engine paddle_vl runs the same model on this machine and nothing leaves
    the network, at roughly 20 minutes a page on CPU. It needs the optional
    2 GB paddlepaddle dependency, which is why it is not the default here.

    Whichever ran is written to lab.documents.ocr_engine, so a stored result
    can always be traced back to how it was read.

RUNS ON THE HOST, NOT IN THE CONTAINER
    The api image has no requests and no API key, both deliberately - the
    service itself never calls out. This script does, so it runs where the
    .env is, and writes to the database over the same connection string.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

PDFS = ROOT / "corpus" / "data" / "pdfs"
LISTING = ROOT / "corpus" / "data" / "no_text_layer.json"
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


def pick(ids: list[str], limit: int | None) -> list[str]:
    """A limited run should span damage types, not the first N of one patient.

    The listing is sorted by report id, so patient 1's scans come first and a
    plain head() would measure one patient's lab. Striding across the list
    gives different patients, labs and damage kinds for the same money.
    """
    if not limit or limit >= len(ids):
        return ids
    step = len(ids) / limit
    return [ids[int(i * step)] for i in range(limit)]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--engine", default="openparser", choices=["openparser", "paddle_vl"])
    ap.add_argument("--limit", type=int, help="how many documents (spread, not the first N)")
    ap.add_argument(
        "--dry-run", action="store_true", help="list what would be sent, send nothing"
    )
    ap.add_argument(
        "--text-layer",
        action="store_true",
        help="the INVERSE set: the reports that already have a text "
        "layer and are read for free today. Sending these is how "
        "you find out whether one OCR engine could replace the "
        "text-layer reader entirely, rather than only cover what "
        "it cannot see.",
    )
    args = ap.parse_args()

    load_env()
    if not LISTING.exists():
        sys.exit(
            f"{LISTING} not found. Run:\n"
            f"  docker compose exec -T api python /work/scripts/probe_text_layer.py"
            f" --json > corpus/data/no_text_layer.json"
        )
    no_text = set(json.loads(LISTING.read_text(encoding="utf-8")))
    if args.text_layer:
        every = sorted(p.stem for p in PDFS.rglob("*.pdf"))
        ids = pick([r for r in every if r not in no_text], args.limit)
    else:
        ids = pick(sorted(no_text), args.limit)

    pages = len(ids)  # one page each; the listing is per report
    print(f"{len(ids)} document(s), engine {args.engine}")
    if args.engine == "openparser":
        print(f"  these leave the network: api.openparser.dev, United States")
        print(f"  about {pages * 6}s and roughly Rs {pages * 0.09:.2f}")
    print()

    if args.dry_run:
        for rid in ids:
            print(f"  would send {rid}")
        return 0

    import psycopg
    from app.services.ocr_ingest import payload_from_raw

    if args.engine == "openparser":
        from app.services.ocr.openparser import OpenParserEngine, read_key

        key = read_key(ROOT)
        if not key:
            sys.exit("IDP_OPENPARSER_KEY is not set. Put it in .env, never in the repo.")
        engine = OpenParserEngine(key=key)
    else:
        from app.services.ocr.paddle_vl import PaddleVLEngine

        engine = PaddleVLEngine()

    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit(
            "DATABASE_URL is not set. For the local stack:\n"
            "  DATABASE_URL=postgresql://labidp:labidp_local_only@localhost:5433/labidp"
        )

    started = time.time()
    ok = failed = 0
    with psycopg.connect(url) as conn:
        practice = conn.execute(
            "SELECT id FROM core.practices WHERE name = %s", (PRACTICE_NAME,)
        ).fetchone()
        if practice is None:
            sys.exit("Demo practice not found. Apply db/005 first.")
        practice_id = practice[0]
        actor = conn.execute(
            "SELECT id FROM core.users WHERE email = %s", ("idp.seed@contexta.local",)
        ).fetchone()
        actor = actor[0] if actor else None

        for i, rid in enumerate(ids, 1):
            pdf = PDFS / rid[:3] / f"{rid}.pdf"
            if not pdf.exists():
                print(f"  {rid}: no such file")
                failed += 1
                continue
            checksum = hashlib.sha256(pdf.read_bytes()).hexdigest()
            try:
                raw = engine.extract(pdf)
                payload = payload_from_raw(raw, checksum=checksum, source="bulk_import")
                payload["is_synthetic"] = True
            except Exception as exc:  # noqa: BLE001
                print(f"  {rid}: {type(exc).__name__}: {exc}")
                failed += 1
                continue

            # The text-layer run already stored this document by checksum, with
            # no rows. Replace it, or the unique index rejects the insert and
            # the OCR result is silently dropped.
            conn.execute(
                "SELECT * FROM lab.fn_purge_synthetic(%s, %s)", (practice_id, checksum)
            )
            doc_id = conn.execute(
                "SELECT lab.fn_ingest_lab_document(%s, %s::jsonb, %s)",
                (practice_id, json.dumps(payload), actor),
            ).fetchone()[0]
            conn.commit()

            n = sum(len(s["results"]) for s in payload["reports"][0]["sections"])
            print(
                f"  {i:3d}/{len(ids)}  {rid}  doc {doc_id}  {n:3d} rows  "
                f"uhid {payload['reports'][0]['uhid_printed'] or '-'}"
            )
            ok += 1

    elapsed = time.time() - started
    print(f"\n{'=' * 58}")
    print(f"read     {ok}")
    print(f"failed   {failed}")
    print(f"elapsed  {elapsed:.0f}s  ({elapsed / max(ok, 1):.1f}s a document)")
    print("=" * 58)
    print("\nNow: docker compose exec api python /work/scripts/score_corpus.py")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
