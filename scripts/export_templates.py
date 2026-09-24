"""Generate panel templates from the analyte master.

WHY THESE ARE GENERATED AND NOT WRITTEN
    A template says what a panel should contain, so coverage can report that a
    lipid report arrived without an LDL. That membership already exists, in
    lab.analytes.panel_id, and the synonyms already exist, in
    lab.panel_aliases - both seeded from corpus/generator/catalog.py, which
    CLAUDE.md section 9 makes the single source of truth for the vocabulary.
    Hand-writing the same lists a second time creates two of them, and two
    lists of the same thing drift. Same reason db/seed/export_master.py
    generates the analyte master rather than anyone typing it.

WHAT THIS FIXES
    Three templates existed against sixteen panels. Measured over the 300
    recorded extractions: 175 of 300 documents matched no template at all, and
    only 7.1% of extracted rows sat inside a recognised panel. Everything else
    showed in the review screen as "extra" - the six-state coverage design was
    inert on 93% of what we extract.

is_core, AND THE KNOWN HOLE IN IT
    is_core marks a member worth flagging when it is absent. Here it is set
    mechanically: is_core = NOT is_derived. Karthik's call of 2026-09-24,
    chosen over per-panel editorial judgement for being reproducible from the
    database with no opinion in the loop.

    The limitation is known and was accepted, not overlooked. LDL and VLDL are
    computed from the other lipids, so is_derived is true and this rule calls
    them optional - but every lipid report prints them, and the hand-written
    lipid-profile.json calls them core. So a generated template will UNDER-flag
    a derived-but-always-printed analyte. If a panel's coverage looks too
    forgiving, that is where to look first, and the fix is to set is_core by
    hand on that member.

    The three hand-written templates are left alone for exactly this reason -
    regenerating them would downgrade LDL and VLDL on the one panel currently
    known to be right.

USAGE
    docker compose exec -T api python /work/scripts/export_templates.py
    docker compose exec -T api python /work/scripts/export_templates.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from score_corpus import load_env  # noqa: E402

TEMPLATES = Path("/app/app/services/ocr/templates")
if not TEMPLATES.is_dir():
    TEMPLATES = ROOT / "api" / "app" / "services" / "ocr" / "templates"


def normalise(text: str) -> str:
    """Loose enough to catch 'Lipid Profile' against 'LIPID PROFILE, SERUM'."""
    return "".join(ch for ch in text.lower() if ch.isalnum())


def existing_synonyms() -> dict[str, set[str]]:
    """What the templates already on disk answer to, by file."""
    out: dict[str, set[str]] = {}
    for path in sorted(TEMPLATES.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        keys = {normalise(s) for s in data.get("panel_synonyms", [])}
        keys.add(normalise(data.get("panel_name", "")))
        keys.add(normalise(data["panel_code"]))
        out[path.name] = {k for k in keys if k}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="say what would be written, write nothing")
    ap.add_argument("--out", type=Path, default=TEMPLATES)
    args = ap.parse_args()

    load_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set. Copy .env.example to .env first.")

    import psycopg

    with psycopg.connect(url) as conn:
        panels = conn.execute("""
            SELECT p.id, p.code, p.display_name, p.description, p.is_core
            FROM   lab.panels p
            WHERE  p.is_deleted = FALSE
            ORDER  BY p.is_core DESC, p.code
        """).fetchall()

        members_of = {}
        aliases_of = {}
        for pid, *_ in panels:
            members_of[pid] = conn.execute("""
                SELECT a.code, a.display_name, a.is_derived, a.default_unit
                FROM   lab.analytes a
                WHERE  a.panel_id = %s AND a.is_deleted = FALSE
                ORDER  BY a.sort_order, a.code
            """, (pid,)).fetchall()
            aliases_of[pid] = [r[0] for r in conn.execute("""
                SELECT pa.alias
                FROM   lab.panel_aliases pa
                WHERE  pa.panel_id = %s AND pa.is_deleted = FALSE
                ORDER  BY pa.alias
            """, (pid,)).fetchall()]

    taken = existing_synonyms()
    written = skipped = 0

    for pid, code, name, description, is_core in panels:
        members = members_of[pid]
        aliases = aliases_of[pid]
        if not members:
            print(f"  {code:<15} no analytes, skipped")
            skipped += 1
            continue

        # Skip a panel an existing template already answers to. Two templates
        # matching one heading is worse than one missing template: the review
        # screen would report the same rows under two panels.
        keys = {normalise(s) for s in (*aliases, name, code)}
        clash = next((f for f, k in taken.items() if k & keys), None)
        if clash:
            print(f"  {code:<15} already covered by {clash}, left alone")
            skipped += 1
            continue

        core = sum(1 for _c, _n, derived, _u in members if not derived)
        doc = {
            "panel_code": code,
            "panel_name": name,
            "panel_synonyms": aliases,
            "members": [
                {
                    "analyte_code": acode,
                    "analyte_name": aname,
                    # Karthik's rule of 2026-09-24. See the module docstring
                    # for what it under-flags and why that was accepted.
                    "is_core": not derived,
                }
                for acode, aname, derived, _unit in members
            ],
            "notes": [
                f"Generated by scripts/export_templates.py from lab.panels and "
                f"lab.analytes, which are seeded from corpus/generator/catalog.py. "
                f"Do not hand-edit - rerun the generator.",
                f"is_core is set mechanically as NOT is_derived, so the {len(members) - core} "
                f"computed member(s) here are not flagged when absent. A derived "
                f"value that every lab does print should have is_core set by hand.",
            ],
            "sources": ["corpus/generator/catalog.py"],
        }

        target = args.out / f"{code.lower().replace('_', '-')}.json"
        print(f"  {code:<15} {len(members):>2} members ({core} core)  -> {target.name}")
        if not args.dry_run:
            target.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
        written += 1

    verb = "would write" if args.dry_run else "wrote"
    print(f"\n{verb} {written} template(s), left {skipped} alone")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
