"""Restore the micro sign the extractor deleted from stored units (review B1).

Until the fix in ocr/pipeline.py, _unmath() deleted a LaTeX \\mu as if it were
formatting, so "86 $\\mu g/dL$" was stored as 86 g/dL and "/ \\mu L" as "/ L".
That code is fixed; this repairs what it already wrote.

HOW IT DECIDES
    Every document whose recorded engine output contains \\mu is re-extracted
    from bench/results/ with the fixed code - no OCR call, no cost - and run
    through the same payload builder ingest used, so labels and values come out
    exactly as they were stored. A stored row is repaired only when:

      * its printed label AND its value match a re-extracted row exactly, and
      * the ONLY difference in the unit is the restored symbol -
        "µg/dL".replace("µ", "") == "g/dL"

    Nothing else about a row can change, and a row the re-extraction does not
    match exactly is left alone and reported.

IT WRITES NOTHING
    CLAUDE.md section 11: the database is run by a person. This prints a report,
    and with --sql the statements to apply, inside one transaction with an audit
    event per document. Review them, then run them:

        docker compose exec -T api python /work/scripts/repair_micro_units.py
        docker compose exec -T api python /work/scripts/repair_micro_units.py --sql > repair.sql
        docker compose exec -T db psql -U labidp -d labidp < repair.sql
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT / "api", Path("/app")):
    if (candidate / "app").is_dir():
        sys.path.insert(0, str(candidate))
        break

DUMPS = Path(os.environ.get("RESULTS_DIR", "/work/bench/results"))
MICRO = "µ"
BACKSLASH_MU = "\\" + "mu"


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--sql", action="store_true", help="print the repair SQL instead of the report"
    )
    args = ap.parse_args()

    import psycopg
    from psycopg.rows import dict_row

    from app.services.ocr.outputs import read_raw
    from app.services.ocr.pipeline import build_extraction
    from app.services.ocr_ingest import payload_from_extraction

    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set")

    affected = sorted(
        p for p in DUMPS.glob("*.raw.json") if BACKSLASH_MU in p.read_text(encoding="utf-8")
    )
    repairs: list[dict] = []
    unmatched: list[str] = []

    with psycopg.connect(url, row_factory=dict_row) as conn:
        for dump in affected:
            pdf = dump.name.split(".")[0] + ".pdf"
            doc = conn.execute(
                "SELECT d.id, d.practice_id, d.status FROM lab.documents d "
                "JOIN core.visit_attachments va ON va.id = d.visit_attachment_id "
                "WHERE va.original_file_name = %s AND d.is_deleted = FALSE",
                (pdf,),
            ).fetchone()
            if doc is None:
                continue  # not loaded in this database

            payload = payload_from_extraction(build_extraction(read_raw(dump)), checksum="")
            fixed: dict[tuple[str, str], str | None] = {}
            for section in payload["reports"][0]["sections"]:
                for row in section["results"]:
                    fixed[(row["printed_label"], row["value_text"])] = row.get("unit_printed")

            stored = conn.execute(
                "SELECT id, printed_label, value_text, unit_printed FROM lab.results "
                "WHERE document_id = %s AND is_deleted = FALSE",
                (doc["id"],),
            ).fetchall()
            for r in stored:
                new = fixed.get((r["printed_label"], r["value_text"]))
                old = r["unit_printed"] or ""
                if new and MICRO in new and MICRO not in old and new.replace(MICRO, "") == old:
                    repairs.append(
                        {
                            **r,
                            "document_id": doc["id"],
                            "status": doc["status"],
                            "practice_id": doc["practice_id"],
                            "pdf": pdf,
                            "new": new,
                        }
                    )
                elif new is None and (r["printed_label"], r["value_text"]) not in fixed:
                    unmatched.append(f"{pdf}: {r['printed_label']!r} {r['value_text']!r}")

    if args.sql:
        by_doc: dict[int, list[dict]] = defaultdict(list)
        for r in repairs:
            by_doc[r["document_id"]].append(r)
        print("-- Review B1: restore the micro sign deleted from stored units.")
        print(f"-- {len(repairs)} row(s) across {len(by_doc)} document(s). Generated by")
        print("-- scripts/repair_micro_units.py; each change is only the restored symbol.")
        print("BEGIN;")
        for doc_id, rows in sorted(by_doc.items()):
            for r in rows:
                print(
                    f"UPDATE lab.results SET unit_printed = {_quote(r['new'])}, updated_at = now() "  # noqa: S608 - text for review; ids int-cast, strings quoted
                    f"WHERE id = {int(r['id'])} AND unit_printed = {_quote(r['unit_printed'])};"
                )
            detail = json.dumps(
                {
                    "review": "B1",
                    "rows": [
                        {"result_id": r["id"], "was": r["unit_printed"], "now": r["new"]}
                        for r in rows
                    ],
                }
            )
            print(
                "INSERT INTO lab.document_events (document_id, practice_id, event_type, detail) "  # noqa: S608 - text for review; ids int-cast, strings quoted
                f"VALUES ({int(doc_id)}, {int(rows[0]['practice_id'])}, 'units_repaired', "
                f"{_quote(detail)}::jsonb);"
            )
        print("COMMIT;")
        return 0

    print(f"dumps containing {BACKSLASH_MU}: {len(affected)}")
    print(
        f"rows to repair: {len(repairs)} across {len({r['document_id'] for r in repairs})} document(s)\n"
    )
    for r in repairs:
        print(
            f"  {r['pdf']:<13} {r['status']:<13} {r['printed_label'][:24]:<24} "
            f"{r['value_text']:>8}  {r['unit_printed']!r:>10} -> {r['new']!r}"
        )
    if unmatched:
        print(
            f"\nstored rows the re-extraction did not reproduce exactly (left alone): {len(unmatched)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
