"""Push corpus PDFs through the real upload endpoint.

    python scripts/upload_corpus.py                  # all 300
    python scripts/upload_corpus.py --no-text-layer  # only the 61 needing OCR
    python scripts/upload_corpus.py --limit 20
    python scripts/upload_corpus.py --reset          # clear synthetic rows first

This is NOT load_corpus.py. The difference is the whole point:

    load_corpus.py    reads the answer key and hands the database a perfect
                      payload. It measures the alias master, panel detection,
                      UHID matching and storage - everything AFTER extraction.

    upload_corpus.py  POSTs the actual PDF bytes to /documents and lets the
                      service read them. It measures extraction itself, and
                      then everything after it. This is the product path: the
                      same endpoint a doctor's browser calls.

It goes over HTTP on purpose rather than calling extract_document() directly,
because the path being tested includes the parts that are easy to forget -
auth, the file-type gate, the size limit, checksum dedupe, writing the blob,
the core.visit_attachments row, and the transaction that wraps ingestion.

Credentials come from LABIDP_EMAIL and LABIDP_PASSWORD, or --email with a
hidden prompt. Never an argv, which shell history and ps both keep.

    python scripts/upload_corpus.py --reset
    python scripts/score_corpus.py

The checksum matters: /documents dedupes on SHA-256 of the bytes, and
load_corpus.py stored exactly that same hash. So without --reset, every upload
returns the existing fixture document and extracts nothing at all. The run
looks like it worked and measures nothing.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "corpus" / "data"
PDFS = DATA / "pdfs"  # the training tree; --corpus holdout reads a sibling instead


def load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def post_json(base: str, path: str, body: dict, token: str | None = None) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def post_file(base: str, path: str, pdf: Path, token: str) -> tuple[int, dict | str]:
    """multipart/form-data by hand: no requests dependency for one endpoint."""
    boundary = "----contexta" + os.urandom(8).hex()
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{pdf.name}"\r\n'.encode(),
            b"Content-Type: application/pdf\r\n\r\n",
            pdf.read_bytes(),
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    req = urllib.request.Request(base + path, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:300]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--api", default=os.environ.get("LABIDP_API", "http://localhost:8000"))
    ap.add_argument(
        "--email", default=os.environ.get("LABIDP_EMAIL", "idp.seed@contexta.local")
    )
    ap.add_argument("--limit", type=int)
    ap.add_argument(
        "--corpus",
        choices=("training", "holdout", "benchmark"),
        default="training",
        help="which corpus tree to upload. 'holdout' is the 15-report "
        "evaluation set in corpus/data/holdout/ - three patients "
        "and twelve layouts the extractor has never been shown. "
        "Upload these only when you mean to score.",
    )

    ap.add_argument(
        "--reset",
        action="store_true",
        help="delete synthetic documents first, so checksums do not dedupe",
    )
    ap.add_argument(
        "--no-text-layer",
        action="store_true",
        help="only the reports with no text layer, listed by probe",
    )
    args = ap.parse_args()

    load_env()

    if args.reset:
        url = os.environ.get("DATABASE_URL")
        if not url:
            sys.exit("--reset needs DATABASE_URL so it can clear the synthetic rows.")
        import psycopg

        with psycopg.connect(url) as conn:
            pid = conn.execute(
                "SELECT id FROM core.practices WHERE name = %s", ("Contexta Demo Clinic",)
            ).fetchone()
            if pid is None:
                sys.exit("Demo practice not found. Apply db/005 first.")
            # Through the function: a bare DELETE fails on the child foreign
            # keys, and only the function is guaranteed to touch synthetic rows.
            docs, results = conn.execute(
                "SELECT * FROM lab.fn_purge_synthetic(%s)", (pid[0],)
            ).fetchone()
            conn.commit()
        print(f"reset: removed {docs} synthetic documents, {results} results\n")

    # The service runs with AUTH_DISABLED in development, so ask first rather
    # than demanding a password nobody set. Only log in if it actually wants one.
    token = ""
    try:
        req = urllib.request.Request(args.api + "/auth/me")
        with urllib.request.urlopen(req, timeout=15):
            print("auth is disabled on the API; no sign-in needed")
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            raise
        password = os.environ.get("LABIDP_PASSWORD") or getpass.getpass(
            f"Password for {args.email}: "
        )
        token = post_json(args.api, "/auth/login", {"email": args.email, "password": password})[
            "access_token"
        ]

    # A local, not a rebinding of the module constant. Assigning PDFS here made
    # it local to the whole function, so the default --corpus training path
    # read it before anything bound it and died with UnboundLocalError - the
    # one-command benchmark crashed at upload.
    pdf_root = PDFS
    if args.corpus != "training":
        pdf_root = DATA / args.corpus / "pdfs"
        if not pdf_root.exists():
            sys.exit(
                f"no {args.corpus} corpus built. Run:\n"
                f"  python corpus/generator/build.py --patient {args.corpus} --fresh"
            )
        print(f"uploading the {args.corpus.upper()} set, not the training corpus")

    pdfs = sorted(pdf_root.rglob("*.pdf"))
    if args.no_text_layer:
        listing = ROOT / "corpus" / "data" / "no_text_layer.json"
        if not listing.exists():
            sys.exit(f"{listing} not found. Run scripts/probe_text_layer.py first.")
        wanted = set(json.loads(listing.read_text()))
        pdfs = [p for p in pdfs if p.stem in wanted]
    if args.limit and args.limit < len(pdfs):
        # Spread across the corpus, not the first N. The list is sorted by
        # report id, so a plain head() would upload fifteen reports belonging
        # to patient 1 - one patient, one lab, a handful of layouts - and
        # measure almost nothing.
        step = len(pdfs) / args.limit
        pdfs = [pdfs[int(i * step)] for i in range(args.limit)]

    print(f"uploading {len(pdfs)} PDFs to {args.api}/documents\n")
    started = time.time()
    ok = dup = failed = 0
    seen_status: dict[str, int] = {}

    uploaded_ids: list[int] = []

    for i, pdf in enumerate(pdfs, 1):
        code, body = post_file(args.api, "/documents", pdf, token)
        if code == 201 and isinstance(body, dict):
            ok += 1
            uploaded_ids.append(int(body["id"]))
            seen_status[body.get("status", "?")] = (
                seen_status.get(body.get("status", "?"), 0) + 1
            )
        elif code == 200:
            dup += 1  # checksum already present: nothing was extracted
        else:
            failed += 1
            if failed <= 5:
                print(f"  {pdf.stem}: HTTP {code} {body}")
        if i % 25 == 0:
            print(f"  {i}/{len(pdfs)} ...")

    # Mark what we just created as fixture data, so --reset can remove it next
    # time. /documents cannot do this itself: is_synthetic describes where a
    # file came from, and the endpoint has no way to know it was handed a
    # corpus PDF rather than a real report. Without this the first --reset
    # purges nothing, the next upload dedupes on checksum and extracts nothing,
    # and the run silently measures the previous run.
    if uploaded_ids:
        url = os.environ.get("DATABASE_URL")
        if url:
            import psycopg

            with psycopg.connect(url) as conn:
                conn.execute(
                    "UPDATE lab.documents SET is_synthetic = TRUE WHERE id = ANY(%s)",
                    (uploaded_ids,),
                )
                conn.commit()
            print(
                f"\nflagged {len(uploaded_ids)} documents is_synthetic "
                f"(so --reset can clear them)"
            )
        else:
            print(
                "\nWARNING: DATABASE_URL not set, so these documents are NOT "
                "flagged is_synthetic and --reset will not remove them."
            )

    elapsed = time.time() - started
    print(f"\n{'=' * 58}")
    print(f"uploaded        {ok}")
    if dup:
        print(f"already present {dup}   <- deduped, NOT extracted. Use --reset.")
    print(f"failed          {failed}")
    for status, n in sorted(seen_status.items()):
        print(f"  status {status:<14} {n}")
    print(f"elapsed         {elapsed:.0f}s  ({elapsed / max(len(pdfs), 1):.2f}s a document)")
    print("=" * 58)
    print("\nNow: python scripts/score_corpus.py")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
