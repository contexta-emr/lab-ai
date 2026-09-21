"""Set a login password for a seeded user.

    python scripts/set_password.py idp.seed@contexta.local
    python scripts/set_password.py someone@clinic.in --role admin --create

The password is read from the LABIDP_PASSWORD environment variable, or typed at
a hidden prompt. It is never a command-line argument, because arguments show up
in shell history and in `ps`.

WHY THIS IS A SCRIPT AND NOT A MIGRATION
    db/005 creates the service user with password_hash NULL, so nobody can log
    in - app.auth.verify_password returns False for a NULL hash, correctly. The
    obvious fix is to put a hash in 006. That would bake a known credential into
    the repository and into every database the migration is ever applied to,
    which is the incident contexta-emr already has on record (real passwords in
    docs/GETTING_STARTED.md and apps/api/.env.example, and git rm does not clear
    history). A migration is a file that gets committed. A password is not.

    So the schema ships with no credentials and you run this once per database.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

try:
    import psycopg
except ImportError:  # pragma: no cover
    sys.exit("psycopg is not installed.  pip install 'psycopg[binary]'")


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
    ap.add_argument("email", help="the user to set a password for")
    ap.add_argument("--create", action="store_true",
                    help="create the user if no row matches that address")
    ap.add_argument("--role", default="admin",
                    choices=["admin", "reviewer", "clinician", "service"],
                    help="role to use with --create (default: admin)")
    ap.add_argument("--practice", default="Contexta Demo Clinic",
                    help="practice name to use with --create")
    args = ap.parse_args()

    load_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set. Copy .env.example to .env first.")

    # Imported after sys.path is set up so the API package is importable without
    # installing it. This is the same hasher the login endpoint verifies against.
    from app.auth import hash_password

    password = os.environ.get("LABIDP_PASSWORD")
    if not password:
        password = getpass.getpass(f"New password for {args.email}: ")
        if password != getpass.getpass("Repeat: "):
            sys.exit("Passwords do not match.")
    if len(password) < 12:
        sys.exit("Use at least 12 characters. This account can verify clinical results.")

    encoded = hash_password(password)

    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute("UPDATE core.users SET password_hash = %s, updated_at = now() "
                    "WHERE email = %s AND is_deleted = FALSE RETURNING id, role",
                    (encoded, args.email))
        row = cur.fetchone()

        if row is None and args.create:
            cur.execute("SELECT id FROM core.practices WHERE name = %s AND is_deleted = FALSE",
                        (args.practice,))
            practice = cur.fetchone()
            if practice is None:
                sys.exit(f"No practice named {args.practice!r}. Apply db/005 first.")
            cur.execute(
                "INSERT INTO core.users (practice_id, email, full_name, role, password_hash) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id, role",
                (practice[0], args.email, args.email.split("@")[0], args.role, encoded))
            row = cur.fetchone()
            print(f"created user {args.email}")

        if row is None:
            sys.exit(f"No user {args.email!r}. Pass --create to add one.")

        conn.commit()

    print(f"password set for {args.email} (id {row[0]}, role {row[1]})")
    print("POST /auth/login with that address and password to get a token.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
