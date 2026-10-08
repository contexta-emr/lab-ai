"""Load the 300-report synthetic corpus into the database.

    python scripts/load_corpus.py              # the 300-report training corpus
    python scripts/load_corpus.py --limit 20   # just the first 20, to try it
    python scripts/load_corpus.py --reset      # delete the synthetic rows first
    python scripts/load_corpus.py --holdout    # the 15-report evaluation set instead
    python scripts/load_corpus.py --benchmark  # the 30-panel vocabulary fixtures

It reads the sealed answer key in corpus/data/answers/ and feeds each report
through lab.fn_ingest_lab_document - the same function the real parser will call.
That matters: the fixture exercises alias resolution, panel detection, UHID
matching and the unmatched-label queue exactly as production will, rather than
inserting pre-digested rows that prove nothing.

Three things are deliberately left imperfect, because a review queue with
nothing in it teaches nobody anything:

  * the three reports marked illegible_scan stay unverified - a human would
    have asked for a clean copy, and the pipeline should show that
  * every 30th document gets a deliberately mangled UHID, the way OCR mangles
    one, so the fuzzy matcher and the quarantine path are both exercised
  * everything else is verified, so the patient timeline has data to draw

Every document is written with is_synthetic = true and can be removed in one
statement. No row describes a real person.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

try:
    import psycopg
except ImportError:  # pragma: no cover
    sys.exit("psycopg is not installed.  pip install 'psycopg[binary]'")

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "corpus" / "data"
# Set by main() once it knows which corpus is being loaded. The holdout set lives in
# its own tree so that loading one can never pull in the other by accident.
ANSWERS = DATA / "answers"
PDFS = DATA / "pdfs"

PRACTICE_NAME = "Contexta Demo Clinic"
SEED_USER = "idp.seed@contexta.local"

# OCR reads O for 0 and 1 for 7. Applied to one document in thirty so the
# fuzzy matcher and the review queue both have something real to do.
OCR_CONFUSIONS = str.maketrans({"0": "O", "5": "S", "1": "7"})


def load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def dsn() -> str:
    load_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set. Copy .env.example to .env first.")
    return url


def read_key() -> tuple[list[dict], dict[str, list[dict]]]:
    with (ANSWERS / "reports.csv").open(encoding="utf-8", newline="") as fh:
        reports = list(csv.DictReader(fh))
    rows_by_report: dict[str, list[dict]] = defaultdict(list)
    with (ANSWERS / "rows.csv").open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            rows_by_report[row["report_id"]].append(row)
    return reports, rows_by_report


def build_payload(rep: dict, rows: list[dict], index: int) -> dict:
    """One answer-key report becomes one extractor payload."""
    traps = set(filter(None, rep["traps"].split("|")))

    uhid = rep["uhid"]
    if index % 30 == 29:  # one in thirty arrives misread
        uhid = uhid.translate(OCR_CONFUSIONS)

    # Sections are runs of consecutive rows under the same printed heading.
    sections: list[dict] = []
    for row in rows:
        heading = row["section_heading"]
        if not sections or sections[-1]["heading_printed"] != heading:
            sections.append({"heading_printed": heading, "results": []})
        sections[-1]["results"].append(
            {
                "printed_label": row["printed_label"],
                "value_text": row["value"],
                "unit_printed": row["unit"] or None,
                "reference_printed": row["reference"] or None,
                "method_printed": row["method"] or None,
                "flag": row["flag"] or None,
                "is_text_result": row["trap"] == "text_result",
                "sequence": len(sections[-1]["results"]) + 1,
            }
        )

    pdf = PDFS / f"P{int(rep['patient_number']):02d}" / f"{rep['report_id']}.pdf"
    checksum = (
        hashlib.sha256(pdf.read_bytes()).hexdigest()
        if pdf.exists()
        else hashlib.sha256(rep["report_id"].encode()).hexdigest()
    )

    # An illegible photograph would not come back with high confidence.
    illegible = "illegible_scan" in traps
    damaged = traps & {
        "aged_paper",
        "fold_creases",
        "stain_damage",
        "cropped_edge",
        "blurred_photo",
        "poor_lighting",
        "torn_corner",
    }
    confidence = 0.34 if illegible else (0.78 if damaged else 0.96)

    return {
        "source": "bulk_import",
        "checksum_sha256": checksum,
        "page_count": 2 if rep["layout_style"] in ("continuation", "discharge_summary") else 1,
        "has_text_layer": not bool(damaged),
        # "fixture", not an engine name. Nothing read these pages: the rows
        # come from the answer key, not from the PDF. Claiming paddle_vl or
        # pdf-text here would put a fictional engine in the same scoring table
        # as engines that really ran, and make the comparison meaningless.
        "ocr_engine": "fixture",
        "engine_version": "corpus-fixture-1.0",
        "extraction_confidence": confidence,
        "is_synthetic": True,
        "reports": [
            {
                "lab_name": rep["lab_name"],
                "accession_no": None,
                "uhid_printed": uhid,
                "uhid_label_printed": rep["uhid_label"],
                "patient_name_printed": rep["patient_name"],
                "age_printed": rep["age_printed"],
                "sex_printed": rep["sex"],
                "collected_text": rep["collected_at"],
                "collected_at": rep["collected_at"],
                "reported_at": rep["reported_at"],
                "referring_doctor": rep["referring_doctor"],
                "department": rep["department"],
                "layout_hint": rep["layout_style"],
                "header_hint": rep["header_style"],
                "sections": sections,
                "notes": [],
            }
        ],
    }, illegible


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, help="load only the first N reports")
    ap.add_argument(
        "--reset",
        action="store_true",
        help="delete ALL synthetic documents first - training corpus and "
        "holdout alike, since a document row records no report id to "
        "tell them apart. Reload both afterwards.",
    )
    ap.add_argument(
        "--no-verify",
        action="store_true",
        help="leave every document unverified, for review-queue testing",
    )
    ap.add_argument(
        "--holdout",
        action="store_true",
        help="load the held-out evaluation set from corpus/data/holdout/ "
        "instead of the training corpus",
    )
    ap.add_argument(
        "--benchmark",
        action="store_true",
        help="load the 30-panel vocabulary fixtures from "
        "corpus/data/benchmark/ instead of the training corpus",
    )
    args = ap.parse_args()

    global ANSWERS, PDFS
    tree = "holdout" if args.holdout else "benchmark" if args.benchmark else ""
    if tree:
        ANSWERS, PDFS = DATA / tree / "answers", DATA / tree / "pdfs"
        if not (ANSWERS / "reports.csv").exists():
            sys.exit(
                f"no {tree} corpus built. Run:\n"
                f"  python corpus/generator/build.py --patient {tree} --fresh"
            )
        print(f"loading the {tree.upper()} set, not the training corpus")

    reports, rows_by_report = read_key()
    if args.limit:
        reports = reports[: args.limit]

    with psycopg.connect(dsn()) as conn:
        practice_id = conn.execute(
            "SELECT id FROM core.practices WHERE name = %s", (PRACTICE_NAME,)
        ).fetchone()
        if practice_id is None:
            sys.exit(
                "Demo practice not found. Run scripts/run_migrations.py first "
                "so 005_seed_practice_and_patients.sql has been applied."
            )
        practice_id = practice_id[0]
        actor = conn.execute(
            "SELECT id FROM core.users WHERE email = %s", (SEED_USER,)
        ).fetchone()
        actor = actor[0] if actor else None

        if args.reset:
            # Through the function. The bare DELETE this used to do fails on
            # the child foreign keys - reports, sections, results and events
            # all reference a document - which is what --reset found the very
            # first time anyone ran it.
            docs, results = conn.execute(
                "SELECT * FROM lab.fn_purge_synthetic(%s)", (practice_id,)
            ).fetchone()
            print(f"removed {docs} existing synthetic document(s), {results} results")
            conn.commit()

        loaded = verified = quarantined = 0
        for i, rep in enumerate(reports):
            payload, illegible = build_payload(rep, rows_by_report[rep["report_id"]], i)

            doc_id = conn.execute(
                "SELECT lab.fn_ingest_lab_document(%s, %s::jsonb, %s)",
                (practice_id, json.dumps(payload), actor),
            ).fetchone()[0]
            loaded += 1

            status = conn.execute(
                "SELECT status, patient_id FROM lab.documents WHERE id = %s", (doc_id,)
            ).fetchone()

            if status[0] == "needs_review" or illegible or args.no_verify:
                quarantined += 1
            else:
                conn.execute(
                    "SELECT lab.fn_review_lab_document(%s, %s, %s, %s, 'verify', %s)",
                    (practice_id, doc_id, status[1], actor, "corpus fixture auto-verify"),
                )
                verified += 1

            if loaded % 50 == 0:
                conn.commit()
                print(f"  {loaded} documents ...")

        conn.commit()

        unmatched = conn.execute(
            "SELECT count(*) FROM lab.results WHERE practice_id = %s AND analyte_id IS NULL",
            (practice_id,),
        ).fetchone()[0]
        total = conn.execute(
            "SELECT count(*) FROM lab.results WHERE practice_id = %s", (practice_id,)
        ).fetchone()[0]
        gaps = conn.execute(
            "SELECT printed_label, occurrence_count FROM lab.unmatched_labels "
            "WHERE resolved_analyte_id IS NULL ORDER BY occurrence_count DESC LIMIT 8"
        ).fetchall()

    print("\n" + "=" * 62)
    print(f"documents loaded      {loaded}")
    print(f"  verified            {verified}")
    print(f"  awaiting review     {quarantined}")
    print(f"results stored        {total}")
    print(
        f"  matched to analyte  {total - unmatched}  ({(total - unmatched) / total * 100:.1f}%)"
        if total
        else ""
    )
    print(f"  no code (honest)    {unmatched}")
    if gaps:
        print("\ntop unmatched printed labels - the queue for growing the master:")
        for label, count in gaps:
            print(f"  {count:>4}x  {label}")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
