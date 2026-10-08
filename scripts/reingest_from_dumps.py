"""Re-read every stored document from its recorded dump. No engine calls, no cost.

    docker compose exec -T api python /work/scripts/reingest_from_dumps.py --dry-run
    docker compose exec -T api python /work/scripts/reingest_from_dumps.py

WHY THIS EXISTS
    A fix to the pipeline changes nothing a clinician can see until the stored
    documents are read again. Until today the only way to do that was
    scripts/requeue_failed.sql, whose own comment says it plainly: "one fresh
    OpenParser call each". Three hundred documents is about forty minutes and
    twenty-seven rupees, which is enough friction that a pipeline fix sits
    unapplied - and an unapplied fix is indistinguishable from no fix.

    The raw dumps in bench/results are the engine's blocks before any
    interpretation. Everything downstream of them is ours. So the whole corpus
    can be re-read through the current pipeline in seconds, for nothing, as
    often as a change needs checking.

    This is replay.py's trick, pointed at the database instead of a score table.
    replay.py answers "did the change find more rows"; this one puts the answer
    where the API and the review screen can see it.

WHAT IT DOES NOT DO
    Call an engine, touch a PDF, or invent a document. A dump with no matching
    row in lab.documents is skipped - re-ingest is for documents that already
    exist, and creating one from a file on disk is what POST /documents is for.

    Verification state is NOT preserved. Re-ingest produces a new reading of the
    page, and a human's "yes, this is that patient" was about the old one. They
    go back to the queue, which is the honest outcome: the thing they confirmed
    has changed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

for candidate in (Path(__file__).resolve().parents[1] / "api", Path("/app")):
    if (candidate / "app").is_dir():
        sys.path.insert(0, str(candidate))
        break

from app.db import fetch_all, transaction            # noqa: E402
from app.services.ocr.outputs import read_raw        # noqa: E402
from app.services.ocr.pipeline import build_extraction  # noqa: E402
from app.services.ocr_ingest import payload_from_extraction  # noqa: E402

DUMPS = Path("/work/bench/results")


def _checksum_for(stem: str, by_name: dict) -> str:
    """The checksum of the document this dump belongs to, if it is known by name."""
    d = by_name.get(stem)
    return (d or {}).get("checksum_sha256") or ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, default=DUMPS)
    ap.add_argument("--limit", type=int, help="stop after this many documents")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would change and write nothing")
    args = ap.parse_args()

    if not args.raw.exists():
        sys.exit(f"{args.raw} not found. Run a benchmark first.")

    # visit_attachment_id is selected and carried through on purpose. The first
    # version of this script did not, so every re-ingested document was written
    # with a NULL link to the file it came from - and a document with no
    # attachment has no file name to show in the queue and no PDF to render
    # beside the results. 323 of 324 documents lost both. Re-ingest must preserve
    # everything about the document that is not a reading of the page.
    by_name: dict[str, dict] = {}
    for d in fetch_all("""
        SELECT d.id, d.practice_id, d.checksum_sha256, d.status, d.detected_uhid,
               d.visit_attachment_id, d.source,
               va.original_file_name AS file_name
        FROM   lab.documents d
        LEFT   JOIN core.visit_attachments va ON va.id = d.visit_attachment_id
        WHERE  d.is_deleted = FALSE
    """):
        # Keyed by file name where there is one, and ALWAYS by checksum as well:
        # the file name comes from the attachment, so keying on it alone cannot
        # find a document whose link is already missing - which is exactly the
        # state this script has to be able to repair.
        stem = Path(d["file_name"] or "").stem
        if stem:
            by_name[stem] = d
        if d["checksum_sha256"]:
            by_name.setdefault(d["checksum_sha256"], d)

    dumps = sorted(args.raw.glob("*.raw.json"))
    if args.limit:
        dumps = dumps[:args.limit]

    matched = skipped = changed = same = failed = 0
    uhid_gained = uhid_lost = 0

    for dump in dumps:
        stem = dump.name.split(".")[0]
        doc = by_name.get(stem)
        if doc is None:
            # Fall back to the checksum of the PDF this dump was taken from.
            doc = by_name.get(_checksum_for(stem, by_name))
        if doc is None:
            skipped += 1
            continue
        matched += 1
        try:
            extraction = build_extraction(read_raw(dump))
            payload = payload_from_extraction(
                extraction,
                checksum=doc["checksum_sha256"],
                visit_attachment_id=doc["visit_attachment_id"],
                source=doc["source"] or "bulk_import")
        except Exception as exc:                      # noqa: BLE001
            failed += 1
            print(f"  {stem}: could not rebuild - {exc}")
            continue

        was = doc["detected_uhid"]
        now = payload["reports"][0].get("uhid_printed") if payload.get("reports") else None
        if was != now:
            changed += 1
            # Printed, always. A changed identifier is the whole reason to run
            # this, and a count alone cannot tell a fix from a regression.
            print(f"  {stem:12} {str(was or 'none'):22} -> {now or 'none'}")
            if now and not was:
                uhid_gained += 1
            elif was and not now:
                uhid_lost += 1
        else:
            same += 1

        if args.dry_run:
            continue

        with transaction() as conn:
            # Soft-delete the old reading, then ingest the new one. Not an
            # UPDATE: a document's results are a tree, and fn_ingest_lab_document
            # is the only thing that knows how to write one correctly.
            conn.execute("UPDATE lab.documents SET is_deleted = TRUE, "
                         "deleted_at = now() WHERE id = %s", (doc["id"],))
            conn.execute("SELECT lab.fn_ingest_lab_document(%s, %s::jsonb, %s)",
                         (doc["practice_id"], json.dumps(payload), None))

    print()
    print(f"  dumps seen              {len(dumps)}")
    print(f"  matched to a document   {matched}")
    print(f"  no such document        {skipped}")
    print(f"  could not rebuild       {failed}")
    print()
    print(f"  same UHID as before     {same}")
    print(f"  UHID changed            {changed}")
    print(f"    newly identified      {uhid_gained}")
    print(f"    lost an identifier    {uhid_lost}")
    if args.dry_run:
        print("\n  --dry-run: nothing was written.")
    else:
        print("\n  Re-ingested. Documents return to the queue unverified: the new")
        print("  reading is not the one anybody confirmed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
