"""Put back the Pass B marker on documents read before it was kept (review B28).

Until 2026-10-15 engine_key() stripped "+grounded" on the way into
lab.documents.ocr_engine, so a document the language model helped read was
stored as plain "openparser" - and the review screen, which now shows Pass A
or Pass B beside a report's name, called every one of them Pass A.

HOW IT DECIDES
    The extraction dumps in bench/results/ were written at reading time, after
    Pass B, so their document.engine still says "OPENPARSER+grounded" where the
    model helped. A stored document is repaired when its original file name
    matches such a dump and its ocr_engine is exactly "openparser". Nothing
    else changes.

IT WRITES NOTHING
    CLAUDE.md section 11: the database is run by a person. This prints what it
    found, and with --sql the statements, in one transaction with an audit
    event per document:
        docker compose exec -T api python /work/scripts/repair_pass_b_marker.py
        docker compose exec -T api python /work/scripts/repair_pass_b_marker.py --sql > repair.sql
        docker compose exec -T db psql -U labidp -d labidp < repair.sql
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DUMPS = Path(os.environ.get("RESULTS_DIR") or ROOT / "bench" / "results")
SUFFIX = ".OPENPARSER.extraction.json"


def helped_stems(dumps: Path) -> set[str]:
    """File stems whose recorded extraction says Pass B added rows."""
    stems: set[str] = set()
    for path in dumps.glob(f"*{SUFFIX}"):
        try:
            engine = json.loads(path.read_text(encoding="utf-8"))["document"]["engine"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if "+grounded" in (engine or ""):
            stems.add(path.name[: -len(SUFFIX)])
    return stems


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--sql", action="store_true", help="print the statements to apply")
    args = ap.parse_args()

    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set.")

    import psycopg

    stems = helped_stems(DUMPS)
    with psycopg.connect(url) as conn:
        rows = conn.execute(
            "SELECT d.id, va.original_file_name FROM lab.documents d "
            "JOIN core.visit_attachments va ON va.id = d.visit_attachment_id "
            "WHERE d.is_deleted = FALSE AND d.ocr_engine = 'openparser'"
        ).fetchall()
    ids = sorted(doc_id for doc_id, name in rows if name and Path(name).stem in stems)

    if not args.sql:
        print(f"{len(stems)} dump(s) say Pass B helped; {len(ids)} stored document(s) to mark")
        return 0
    if not ids:
        print("-- nothing to repair")
        return 0
    listed = ", ".join(str(int(i)) for i in ids)
    print("BEGIN;")
    print(
        "INSERT INTO lab.document_events (document_id, practice_id, event_type, detail) "  # noqa: S608 - int-cast ids, text for review
        "SELECT id, practice_id, 'engine_marker_repaired', "
        "jsonb_build_object('was', ocr_engine, 'now', 'openparser+grounded', 'review', 'B28') "
        f"FROM lab.documents WHERE id IN ({listed}) AND ocr_engine = 'openparser';"
    )
    print(
        "UPDATE lab.documents SET ocr_engine = 'openparser+grounded', updated_at = now() "  # noqa: S608 - int-cast ids, text for review
        f"WHERE id IN ({listed}) AND ocr_engine = 'openparser';"
    )
    print("COMMIT;")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
