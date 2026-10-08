"""Re-score the corpus from recorded raw dumps, without calling OpenParser.

WHY THIS EXISTS
    Reading 300 documents costs about forty minutes and Rs 27, which makes
    every pipeline change an expensive question. The raw dumps written beside
    each PDF are the engine's blocks before any interpretation, so the whole
    corpus can be pushed through a changed pipeline in seconds and for nothing.
    Change something, run this, see whether recall moved. Try three ideas and
    throw two away - which is not a thing you do when each measurement is
    billed per page.

    This is the idp workspace's tools/score_corpus.py --raw, in our shape.

WHAT IT CAN AND CANNOT MEASURE
    Recall and value accuracy, which are the pipeline's job and the reason to
    iterate. Not code accuracy: an analyte code comes from fn_resolve_analyte
    against the alias table, so measuring it needs the database and a real
    ingest. Use scripts/score_corpus.py for that, after a run.

    So: this answers "did the change find more rows", the other answers "did
    the right codes land on them". They are different questions and neither
    substitutes for the other.

USAGE
    docker compose exec -T api python /work/scripts/replay.py
    docker compose exec -T api python /work/scripts/replay.py --by-layout
    docker compose exec -T api python /work/scripts/replay.py --write

    --write also regenerates each <stem>.<ENGINE>.extraction.json from its raw
    dump, so the files on disk match the pipeline as it stands now. Off by
    default: a scoring run should not quietly rewrite what you are comparing
    against.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The app package sits at ./api on the host and at /app in the container,
# because docker-compose mounts ./api there. Take whichever exists.
for candidate in (ROOT / "api", Path("/app")):
    if (candidate / "app").is_dir():
        sys.path.insert(0, str(candidate))
        break
sys.path.insert(0, str(Path(__file__).resolve().parent))

from score_corpus import ANSWERS, align, norm_value  # noqa: E402

from app.services.ocr.outputs import read_raw, write_extraction  # noqa: E402
from app.services.ocr.pipeline import build_extraction  # noqa: E402

DUMPS = Path("/work/bench/results")


def load_key() -> tuple[dict[str, list[dict]], dict[str, str]]:
    """The sealed key: expected rows per report, and each report's layout.

    Read here and nowhere near the pipeline. CLAUDE.md section 7 - a parser
    that can see the answers measures nothing.
    """
    key: dict[str, list[dict]] = defaultdict(list)
    with (ANSWERS / "rows.csv").open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            key[row["report_id"]].append(row)

    layout_of: dict[str, str] = {}
    with (ANSWERS / "reports.csv").open(encoding="utf-8", newline="") as fh:
        for rep in csv.DictReader(fh):
            layout_of[rep["report_id"]] = rep["layout_style"]
    return key, layout_of


def rows_of(extraction) -> list[dict]:
    """The extraction flattened to the shape align() pairs on."""
    return [
        {"printed_label": row.raw_label, "value": row.raw_value or ""}
        for section in extraction.sections
        for row in section.rows
    ]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--raw", type=Path, default=DUMPS, help=f"directory of *.raw.json (default {DUMPS})"
    )
    ap.add_argument(
        "--write",
        action="store_true",
        help="also regenerate each .extraction.json from its dump",
    )
    ap.add_argument(
        "--by-layout",
        action="store_true",
        help="break the score down by layout, which is the only "
        "view that says WHICH pages fail",
    )
    ap.add_argument(
        "--missed", action="store_true", help="list the labels never found, commonest first"
    )
    args = ap.parse_args()

    dumps = sorted(args.raw.glob("*.raw.json"))
    if not dumps:
        sys.exit(
            f"no *.raw.json in {args.raw}. Run bench/run.ps1 first - the "
            f"dumps are written as the corpus is read."
        )

    key, layout_of = load_key()
    tally: dict[str, dict] = defaultdict(
        lambda: {"reports": 0, "printed": 0, "produced": 0, "found": 0, "value_ok": 0}
    )
    never_found: defaultdict[str, int] = defaultdict(int)
    unknown = 0

    for path in dumps:
        # "P01-R09.OPENPARSER.raw.json" -> "P01-R09". The dump is named after
        # the document precisely so this needs no lookup table.
        report_id = path.name.split(".")[0]
        expected = key.get(report_id)
        if expected is None:
            unknown += 1
            continue

        raw = read_raw(path)
        extraction = build_extraction(raw)
        if args.write:
            write_extraction(extraction, args.raw, Path(f"{report_id}.pdf"), engine=raw.engine)

        actual = rows_of(extraction)
        pairs, missed, _spurious = align(expected, actual)

        buckets = ["overall"]
        if args.by_layout:
            buckets.append(layout_of.get(report_id, "unknown"))
        for b in buckets:
            t = tally[b]
            t["reports"] += 1
            t["printed"] += len(expected)
            t["produced"] += len(actual)
            t["found"] += len(pairs)
            t["value_ok"] += sum(
                1 for e, a in pairs if norm_value(e["value"]) == norm_value(a["value"])
            )
        for e in missed:
            never_found[e["printed_label"]] += 1

    if unknown:
        print(f"note: {unknown} dump(s) are not corpus documents and were skipped\n")

    width = max((len(k) for k in tally), default=7)
    head = (
        f"{'':<{width}}  {'rpts':>5} {'rows':>6} {'found':>6} "
        f"{'recall':>8} {'precis':>8} {'value':>8}"
    )
    print("=" * len(head))
    print(head)
    print("-" * len(head))
    for name in sorted(tally, key=lambda k: (k != "overall", k)):
        t = tally[name]
        pct = lambda n, d: f"{100 * n / d:.1f}%" if d else "-"  # noqa: E731
        print(
            f"{name:<{width}}  {t['reports']:>5} {t['printed']:>6} {t['found']:>6} "
            f"{pct(t['found'], t['printed']):>8} "
            f"{pct(t['found'], t['produced']):>8} "
            f"{pct(t['value_ok'], t['found']):>8}"
        )
    print("=" * len(head))
    print("recall  rows found / rows printed      precis  rows found / rows produced")
    print("value   right value / rows found       (code accuracy needs the database:")
    print("                                        scripts/score_corpus.py)")

    if args.missed and never_found:
        print("\nnever found, commonest first")
        for label, n in sorted(never_found.items(), key=lambda kv: -kv[1])[:30]:
            print(f"  {n:>4}  {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
