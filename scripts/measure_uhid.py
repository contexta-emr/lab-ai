"""How many documents can we identify a patient on, replayed for nothing.

    docker compose exec -T api python /work/scripts/measure_uhid.py
    docker compose exec -T api python /work/scripts/measure_uhid.py --by-layout

WHY THIS IS NOT replay.py
    replay.py scores ROWS - recall, precision, value accuracy. It is blind to
    whether the document reached a patient at all, because that is a header
    question and the header is not part of any row. A change that recovers
    forty patient identifications moves nothing in replay.py's table.

    Which is how "UHID detection on dense_multipanel (57%) and fax_header
    (50%)" stayed open while row accuracy climbed: the number that would have
    shown it was never being printed.

WHAT IT MEASURES
    The real pipeline over the recorded raw dumps, asking one question per
    document: did build_extraction produce a patient identifier, and is it the
    one the sealed key says is printed on the page. Three outcomes, and the
    third is the one that matters most - a WRONG identifier is worse than none,
    because it can file a result against another patient.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT / "api", Path("/app")):
    if (candidate / "app").is_dir():
        sys.path.insert(0, str(candidate))
        break
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.ocr.outputs import read_raw          # noqa: E402
from app.services.ocr.pipeline import build_extraction  # noqa: E402

DUMPS = Path("/work/bench/results")
KEYS = [ROOT / "corpus" / "data" / "answers",
        ROOT / "corpus" / "data" / "holdout" / "answers"]


def load_key() -> dict[str, dict]:
    """report_id -> the sealed row for it. Read here and nowhere near the
    pipeline: a parser that can see the answers measures nothing."""
    out: dict[str, dict] = {}
    for base in KEYS:
        path = base / "reports.csv"
        if path.exists():
            with path.open(encoding="utf-8", newline="") as fh:
                for rep in csv.DictReader(fh):
                    out[rep["report_id"]] = rep
    return out


def squash(text: str | None) -> str:
    return "".join(ch for ch in (text or "") if ch.isalnum()).upper()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, default=DUMPS)
    ap.add_argument("--by-layout", action="store_true",
                    help="split the table by printed layout, which is how you "
                         "find out WHICH format stopped identifying patients")
    ap.add_argument("--wrong", action="store_true",
                    help="list every document given an identifier that is not "
                         "the one on the page - the failures that can misfile")
    args = ap.parse_args()

    key = load_key()
    if not args.raw.exists():
        sys.exit(f"{args.raw} not found. Run a benchmark first.")

    tally: dict[str, Counter] = defaultdict(Counter)
    wrong_ones: list[tuple[str, str, str]] = []

    for dump in sorted(args.raw.glob("*.raw.json")):
        rid = dump.name.split(".")[0]
        rep = key.get(rid)
        if rep is None:
            continue                       # not a corpus document
        extraction = build_extraction(read_raw(dump))
        got = extraction.header.patient_id
        want = rep["uhid"]
        bucket = ("none" if not got
                  else "right" if squash(want) in squash(got) or squash(got) in squash(want)
                  else "wrong")
        tally[rep["layout_style"]][bucket] += 1
        tally["OVERALL"][bucket] += 1
        if bucket == "wrong":
            wrong_ones.append((rid, want, got or ""))

    def line(name: str, c: Counter) -> str:
        total = sum(c.values()) or 1
        return (f"{name[:22]:22} {total:5} {c['right']:6} {c['none']:6} "
                f"{c['wrong']:6}   {c['right'] / total * 100:5.1f}%")

    print()
    print(f"{'layout':22} {'docs':>5} {'right':>6} {'none':>6} {'wrong':>6}   identified")
    print("-" * 68)
    if args.by_layout:
        for name in sorted(k for k in tally if k != "OVERALL"):
            print(line(name, tally[name]))
        print("-" * 68)
    print(line("OVERALL", tally["OVERALL"]))
    print()
    print("right  the identifier on the page       none   no identifier found")
    print("wrong  an identifier, but not that one  <- the only one that can misfile")

    if args.wrong and wrong_ones:
        print(f"\n{len(wrong_ones)} document(s) given the wrong identifier:")
        for rid, want, got in wrong_ones:
            print(f"  {rid:10} page says {want:18} we read {got}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
