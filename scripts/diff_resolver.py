"""Does a changed resolver give the same answers as the one already installed?

    # BEFORE changing anything - copy what is live:
    docker compose exec -T api python /work/scripts/diff_resolver.py --snapshot

    # after applying the change:
    docker compose exec -T api python /work/scripts/diff_resolver.py
    docker compose exec -T api python /work/scripts/diff_resolver.py --all-panels

WHY THE SNAPSHOT STEP EXISTS, AND WHY IT IS NOT OPTIONAL
    The first version of this script compared a new fn_resolve_analyte against a
    "legacy" copy transcribed by hand from db/003_functions.sql. That was not
    what was installed: 007 had replaced the function years of migrations ago,
    adding panel-scoped aliases and the rule that several equally good matches
    must resolve to NOTHING rather than to a guess.

    So the comparison ran 34,003 cases, reported zero disagreements, and proved
    nothing - both sides were missing the same logic. The regression it was
    written to catch sailed through with a clean bill of health. A real number
    against a fabricated baseline is worse than no number, because it buys
    confidence that was never earned.

    --snapshot takes the baseline from pg_get_functiondef, which is the database
    telling you what it is actually running. It cannot be out of date and it
    cannot be mis-transcribed. Nothing else is a baseline.

WHAT A DISAGREEMENT MEANS
    Not automatically a regression - but always worth reading. The case that
    matters most is where both resolve and they disagree: that is a printed
    label that would land on a different analyte, which on a clinical value is
    the expensive failure. Those are listed first.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

for candidate in (Path(__file__).resolve().parents[1] / "api", Path("/app")):
    if (candidate / "app").is_dir():
        sys.path.insert(0, str(candidate))
        break

from app.db import fetch_all, fetch_one, transaction  # noqa: E402

LIVE = "fn_resolve_analyte"
BASELINE = "fn_resolve_analyte_baseline"


def snapshot() -> int:
    """Copy the installed function, verbatim, under the baseline name."""
    row = fetch_one(
        """
        SELECT pg_get_functiondef(p.oid) AS src
        FROM   pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE  n.nspname = 'lab' AND p.proname = %s
    """,
        (LIVE,),
    )
    if not row:
        sys.exit(f"lab.{LIVE} is not installed - nothing to snapshot.")

    src = row["src"]
    # Rename only the definition's own name. The body may legitimately mention
    # other functions, and a blanket replace would rewrite those too.
    renamed, n = re.subn(
        rf"(CREATE OR REPLACE FUNCTION\s+lab\.){LIVE}\b", rf"\1{BASELINE}", src, count=1
    )
    if n != 1:
        sys.exit("could not rename the function definition - refusing to guess.")

    with transaction() as conn:
        conn.execute(f"DROP FUNCTION IF EXISTS lab.{BASELINE}(BIGINT, TEXT, BIGINT, REAL)")
        conn.execute(renamed)
        conn.execute(
            f"COMMENT ON FUNCTION lab.{BASELINE} IS "
            "'A snapshot of lab.fn_resolve_analyte as it was before a "
            "change, taken by scripts/diff_resolver.py --snapshot from "
            "pg_get_functiondef. Compared against, never called.'"
        )
    print(f"  snapshot taken: lab.{BASELINE}")
    print(f"  {len(src)} characters, read from the live database")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--snapshot",
        action="store_true",
        help="copy the INSTALLED function to the baseline name. Run "
        "this before changing it, never after.",
    )
    ap.add_argument(
        "--all-panels",
        action="store_true",
        help="re-resolve every label against EVERY panel, not just "
        "the one its section resolved to. Slower, and the only "
        "way to exercise the panel preference itself.",
    )
    ap.add_argument("--drop", action="store_true", help="remove the baseline copy")
    args = ap.parse_args()

    if args.snapshot:
        return snapshot()
    if args.drop:
        with transaction() as conn:
            conn.execute(f"DROP FUNCTION IF EXISTS lab.{BASELINE}(BIGINT, TEXT, BIGINT, REAL)")
        print(f"  lab.{BASELINE} dropped")
        return 0

    if not fetch_one(
        """SELECT 1 FROM pg_proc p JOIN pg_namespace n
                        ON n.oid = p.pronamespace
                        WHERE n.nspname='lab' AND p.proname=%s""",
        (BASELINE,),
    ):
        sys.exit(
            "No baseline. Take one BEFORE the change:\n"
            "  python /work/scripts/diff_resolver.py --snapshot\n"
            "Taking it now would snapshot the changed function and compare "
            "it with itself, which is the mistake this script exists to "
            "stop making."
        )

    pairs = fetch_all("""
        SELECT DISTINCT r.practice_id, r.printed_label, s.panel_id
        FROM   lab.results r
        LEFT   JOIN lab.report_sections s ON s.id = r.section_id
        WHERE  r.is_deleted = FALSE AND COALESCE(r.printed_label, '') <> ''
    """)
    if args.all_panels:
        panels = [
            p["id"] for p in fetch_all("SELECT id FROM lab.panels WHERE is_deleted = FALSE")
        ]
        labels = sorted({(p["practice_id"], p["printed_label"]) for p in pairs})
        pairs = [
            {"practice_id": pr, "printed_label": lb, "panel_id": pid}
            for pr, lb in labels
            for pid in panels
        ]

    same = both_none = moved = retyped = 0
    differences: list[tuple] = []
    for row in pairs:
        a = fetch_all(
            # BASELINE and LIVE are module constants naming SQL functions, never input.
            f"SELECT analyte_code, match_method FROM lab.{BASELINE}"  # noqa: S608
            "(%s::BIGINT, %s::TEXT, %s::BIGINT)",
            (row["practice_id"], row["printed_label"], row["panel_id"]),
        )
        b = fetch_all(
            f"SELECT analyte_code, match_method FROM lab.{LIVE}"  # noqa: S608
            "(%s::BIGINT, %s::TEXT, %s::BIGINT)",
            (row["practice_id"], row["printed_label"], row["panel_id"]),
        )
        o = a[0]["analyte_code"] if a else None
        n = b[0]["analyte_code"] if b else None
        if o == n:
            both_none += o is None
            same += o is not None
            continue
        if o is not None and n is not None:
            moved += 1
        else:
            retyped += 1
        differences.append(
            (
                row["printed_label"],
                row["panel_id"],
                o,
                n,
                a[0]["match_method"] if a else "-",
                b[0]["match_method"] if b else "-",
            )
        )

    print()
    print(f"  pairs compared                 {len(pairs)}")
    print(f"  identical, resolved            {same}")
    print(f"  identical, both unresolved     {both_none}")
    print(f"  both resolve, DIFFERENT code   {moved}   <- a value would change analyte")
    print(f"  one resolves, the other not    {retyped}")
    print()
    if differences:
        print(f"{len(differences)} disagreement(s):\n")
        print(f"  {'printed label':36} {'panel':>6} {'baseline':>14} {'now':>14}")
        print("  " + "-" * 76)
        for label, panel, o, n, om, nm in differences[:60]:
            print(
                f"  {str(label)[:36]:36} {panel or '-'!s:>6} "
                f"{o or 'none'!s:>14} {n or 'none'!s:>14}   {om} -> {nm}"
            )
        if len(differences) > 60:
            print(f"  ... and {len(differences) - 60} more")
        return 1
    print("  No disagreement against the function that was actually installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
