"""Copy uploaded files from storage/ into lab.document_files.

    python scripts/store_files_in_db.py            # say what would be copied
    python scripts/store_files_in_db.py --apply    # copy it

Needs DATABASE_URL (or .env). Karthik runs it against Neon - CLAUDE.md section 7.

Documents uploaded before db/033 have their bytes on disk only, and Vercel has
no disk. Copying them in lets the Sample data workspace show its pages there.
Idempotent: an attachment that already has a row is skipped. One transaction,
so a failure copies nothing.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PENDING = """
SELECT va.id, va.practice_id, va.stored_file_name
FROM   core.visit_attachments va
JOIN   lab.documents d ON d.visit_attachment_id = va.id AND d.is_deleted = FALSE
WHERE  va.is_deleted = FALSE
  AND  NOT EXISTS (SELECT 1 FROM lab.document_files f
                   WHERE f.visit_attachment_id = va.id AND f.is_deleted = FALSE)
ORDER  BY va.id
"""


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
    ap.add_argument("--apply", action="store_true", help="copy; without it, only count")
    ap.add_argument("--storage", default=os.environ.get("STORAGE_DIR", str(ROOT / "storage")))
    args = ap.parse_args()

    load_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set.")

    import psycopg

    storage = Path(args.storage)
    copied = missing = size = 0
    with psycopg.connect(url) as conn:
        for attachment_id, practice_id, stored in conn.execute(PENDING).fetchall():
            path = storage / Path(stored or "").name
            if not stored or not path.is_file():
                missing += 1
                continue
            blob = path.read_bytes()
            size += len(blob)
            copied += 1
            if args.apply:
                conn.execute(
                    "INSERT INTO lab.document_files "
                    "(practice_id, visit_attachment_id, content, byte_count) "
                    "VALUES (%s, %s, %s, %s)",
                    (practice_id, attachment_id, blob, len(blob)),
                )
        if args.apply:
            conn.commit()

    verb = "copied" if args.apply else "would copy"
    print(f"{verb} {copied} file(s), {size / 1048576:.1f} MB; {missing} with no file on disk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
