"""Apply db/*.sql in filename order, once each, and record what was applied.

    python scripts/run_migrations.py                 # apply anything new
    python scripts/run_migrations.py --status        # show what is applied
    python scripts/run_migrations.py --force 003     # re-apply one file

Reads DATABASE_URL from the environment or from .env in the project root.

Why a runner and not an ORM: this service owns its database and the DDL is
written by hand, reviewed as SQL, and applied in order. Nothing generates it and
nothing infers it from models. Each file is applied inside its own transaction,
so a failure halfway leaves the database on the last good migration.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

try:
    import psycopg
except ImportError:  # pragma: no cover
    sys.exit("psycopg is not installed.  pip install 'psycopg[binary]'")

ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "db"

TRACKING_DDL = """
CREATE TABLE IF NOT EXISTS public.schema_migrations (
    filename    VARCHAR(200) PRIMARY KEY,
    checksum    CHAR(64)     NOT NULL,
    applied_at  TIMESTAMP(6) NOT NULL DEFAULT now(),
    applied_by  VARCHAR(100) NOT NULL DEFAULT current_user
);
"""


def load_env() -> None:
    """Minimal .env reader. No dependency, and it never overwrites a real env var."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def dsn() -> str:
    load_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit(
            "DATABASE_URL is not set.\n"
            "  Copy .env.example to .env and put your connection string there.\n"
            "  Never commit .env - the repo already has one credential incident."
        )
    return url


def migrations(with_holdout: bool = False) -> list[Path]:
    """db/NNN_name.sql, in numeric order. Files in db/seed/ are generators, not migrations.

    A migration that seeds FIXTURE PATIENTS is skipped unless asked for. Applying
    the holdout seed by accident puts the evaluation patients in the same database
    as the training corpus, and a query that forgets to filter them then scores the
    extractor on data it was tuned against. The benchmark fixture patient is gated
    the same way for the same reason.

    Note what is NOT gated: 022, the 30-panel vocabulary. That is product master
    data - the analytes a real report may contain - and a database without it
    cannot read a culture report at all. Only the invented PEOPLE are optional.
    """
    files = sorted(p for p in DB_DIR.glob("*.sql") if re.match(r"^\d{3}_", p.name))
    if not with_holdout:
        files = [p for p in files
                 if not any(mark in p.name for mark in
                            ("holdout", "benchmark_patients", "demo_patient"))]
    return files


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--status", action="store_true", help="list applied and pending")
    ap.add_argument("--with-holdout", action="store_true",
                    help="also apply the fixture-patient seeds - the holdout "
                         "evaluation patients (019) and the benchmark vocabulary "
                         "patient (023). Off by default. The 30-panel vocabulary "
                         "in 022 is NOT gated and always applies.")
    ap.add_argument("--force", metavar="PREFIX",
                    help="re-apply the migration whose filename starts with this")
    args = ap.parse_args()

    files = migrations(args.with_holdout)
    if not files:
        sys.exit(f"no migrations found in {DB_DIR}")

    with psycopg.connect(dsn(), autocommit=True) as conn:
        conn.execute(TRACKING_DDL)
        applied = {
            row[0]: row[1]
            for row in conn.execute(
                "SELECT filename, checksum FROM public.schema_migrations").fetchall()
        }

        if args.status:
            print(f"{'migration':<44}{'state':<12}note")
            print("-" * 78)
            for f in files:
                if f.name not in applied:
                    state, note = "pending", ""
                elif applied[f.name] != checksum(f):
                    state, note = "applied", "FILE CHANGED SINCE IT WAS APPLIED"
                else:
                    state, note = "applied", ""
                print(f"{f.name:<44}{state:<12}{note}")
            return 0

        ran = 0
        for f in files:
            if args.force and not f.name.startswith(args.force):
                continue
            if not args.force and f.name in applied:
                if applied[f.name] != checksum(f):
                    print(f"!! {f.name} was applied but the file has changed since.")
                    print("   Write a new migration; do not edit an applied one.")
                continue

            sql = f.read_text(encoding="utf-8")
            print(f"applying {f.name} ...", end=" ", flush=True)
            try:
                # Each file carries its own BEGIN/COMMIT, so run it as written.
                conn.execute(sql)
            except Exception as exc:                      # noqa: BLE001
                print("FAILED")
                print(f"\n{type(exc).__name__}: {exc}")
                return 1
            conn.execute(
                "INSERT INTO public.schema_migrations (filename, checksum) VALUES (%s, %s) "
                "ON CONFLICT (filename) DO UPDATE SET checksum = EXCLUDED.checksum, "
                "applied_at = now()",
                (f.name, checksum(f)),
            )
            ran += 1
            print("ok")

        print(f"\n{ran} migration(s) applied, {len(files) - ran} already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
