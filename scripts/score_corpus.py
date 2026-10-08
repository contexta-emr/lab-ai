"""Score what the database stored against the sealed answer key.

    python scripts/score_corpus.py                 # the table
    python scripts/score_corpus.py --engine pdf-text   # one engine only
    python scripts/score_corpus.py --wrong         # every wrong code
    python scripts/score_corpus.py --missed        # rows on the page we never found
    python scripts/score_corpus.py --doc P01-R03   # one report, row by row

WHAT THIS MEASURES, AND WHY IT IS FOUR NUMBERS AND NOT ONE

    A lab report goes through two independent steps, and a single accuracy
    figure hides which one failed:

        the page  ->  printed rows        the extractor, or OCR
        a printed row  ->  a canonical code and a value    the alias master

    So:

      recall     of the rows actually printed on the page, how many did we
                 find at all? An extractor that silently drops half the page
                 can still score 100% on everything it did find.
      precision  of the rows we produced, how many are real? Guards against an
                 extractor that invents rows out of headers and footnotes.
      code       given a row we found, did it get the right analyte code? This
                 is the alias master's score and nothing else.
      value      given a row we found, is the value the one on the page? A
                 wrong number is worse than a wrong code: a wrong code lands
                 the reading on the wrong chart, a wrong number puts a false
                 reading on the right one.

    Rows are aligned by printed label, not by position. Position only worked
    while load_corpus.py fed the key back in and row counts matched exactly. A
    real extractor misses rows, merges rows and invents rows, and positional
    alignment would silently skip every report where that happened - reporting
    a beautiful number computed over almost nothing.

    Results are broken down by lab.documents.ocr_engine, so the fixture loader,
    the text-layer reader and an OCR engine are directly comparable in one
    table.

THE KEY IS READ HERE AND NOWHERE ELSE
    CLAUDE.md section 7: a parser that reads corpus/data/answers/ measures
    nothing. This is not the parser. It is the scorer, and it runs after.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import psycopg
except ImportError:  # pragma: no cover
    sys.exit("psycopg is not installed.  pip install 'psycopg[binary]'")

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "corpus" / "data"
ANSWERS = DATA / "answers"          # reassigned by --corpus holdout
PDFS = DATA / "pdfs"


def norm(s: str | None) -> str:
    """Same normalisation the database uses, so alignment matches resolution."""
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def norm_value(s: str | None) -> str:
    """Compare values ignoring spacing and case. 1.40 and 1.4 stay different:
    trailing zeros are a real difference in how a lab reported precision."""
    return re.sub(r"\s+", "", (s or "").strip().lower())


def load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def align(expected: list[dict], actual: list[dict]) -> tuple[list, list, list]:
    """Pair key rows with stored rows by printed label.

    Greedy and order-preserving within a label, so a report printing Glucose
    twice pairs the first with the first. Returns (pairs, missed, spurious).
    """
    pool: dict[str, list[dict]] = defaultdict(list)
    for a in actual:
        pool[norm(a["printed_label"])].append(a)

    pairs, missed = [], []
    for e in expected:
        bucket = pool.get(norm(e["printed_label"]))
        if bucket:
            pairs.append((e, bucket.pop(0)))
        else:
            missed.append(e)
    spurious = [a for bucket in pool.values() for a in bucket]
    return pairs, missed, spurious


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", help="score only documents read by this ocr_engine")
    ap.add_argument("--wrong", action="store_true", help="list every wrong code")
    ap.add_argument("--missed", action="store_true", help="list rows never found")
    ap.add_argument("--doc", help="one report id, row by row")
    ap.add_argument("--by-layout", action="store_true",
                    help="group by the printed layout instead of by engine. "
                         "The corpus has 26 of them and the answer key records "
                         "which, so this turns one undifferentiated recall "
                         "number into a list of the layouts that actually fail.")
    ap.add_argument("--json", action="store_true",
                    help="emit the metrics as JSON instead of a table, so a run "
                         "can be diffed against the last one rather than "
                         "remembered")
    ap.add_argument("--holdout", type=int, metavar="N",
                    help="split the table: patients 1..N as the set the "
                         "extractor was developed against, the rest as never "
                         "inspected. If the two scores differ much, the "
                         "extractor was tuned to what was looked at. This is a "
                         "proxy - for the real answer use --corpus holdout.")
    ap.add_argument("--corpus", choices=("training", "holdout", "benchmark"), default="training",
                    help="which corpus tree to read. 'holdout' is the 15-report "
                         "evaluation set in corpus/data/holdout/ - three patients "
                         "and twelve layouts the extractor has never been shown. "
                         "Not the same thing as --holdout N, which only splits "
                         "the training corpus by patient number.")
    args = ap.parse_args()

    global ANSWERS, PDFS
    if args.corpus != "training":
        ANSWERS = DATA / args.corpus / "answers"
        PDFS = DATA / args.corpus / "pdfs"
        if not (ANSWERS / "reports.csv").exists():
            sys.exit(f"no {args.corpus} corpus built. Run:\n"
                     f"  python corpus/generator/build.py --patient {args.corpus} --fresh")


    load_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set. Copy .env.example to .env first.")

    key: dict[str, list[dict]] = defaultdict(list)
    with (ANSWERS / "rows.csv").open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            key[row["report_id"]].append(row)

    by_checksum: dict[str, str] = {}
    layout_of: dict[str, str] = {}
    with (ANSWERS / "reports.csv").open(encoding="utf-8", newline="") as fh:
        for rep in csv.DictReader(fh):
            layout_of[rep["report_id"]] = rep["layout_style"]
            pdf = PDFS / f"P{int(rep['patient_number']):02d}" / f"{rep['report_id']}.pdf"
            if pdf.exists():
                by_checksum[hashlib.sha256(pdf.read_bytes()).hexdigest()] = rep["report_id"]

    sql = """
        SELECT d.checksum_sha256, d.ocr_engine, d.has_text_layer,
               r.printed_label, a.code, r.value_text
        FROM   lab.documents d
        LEFT   JOIN lab.results  r ON r.document_id = d.id AND r.is_deleted = FALSE
        LEFT   JOIN lab.analytes a ON a.id = r.analyte_id
        WHERE  d.is_deleted = FALSE
        ORDER  BY d.id, r.section_id NULLS FIRST, r.sequence, r.id
    """
    with psycopg.connect(url) as conn:
        rows = conn.execute(sql).fetchall()

    stored: dict[str, list[dict]] = defaultdict(list)
    engine_of: dict[str, str] = {}
    for checksum, engine, _has_text, label, code, value in rows:
        rid = by_checksum.get(checksum or "")
        if not rid:
            continue
        engine_of[rid] = engine or "unknown"
        if label is not None:
            stored[rid].append({"printed_label": label, "code": code, "value": value})

    if args.doc:
        return one_document(args.doc, key, stored, engine_of)

    # engine -> counters
    agg: dict[str, Counter] = defaultdict(Counter)
    wrongs: list[tuple] = []
    missed_labels: Counter = Counter()

    for rid, expected in key.items():
        engine = engine_of.get(rid)
        if engine is None:
            agg["(not ingested)"]["reports"] += 1
            agg["(not ingested)"]["expected"] += len(expected)
            continue
        if args.engine and engine != args.engine:
            continue

        if args.by_layout:
            engine = layout_of.get(rid, "?") if engine != "none" else "(no text layer)"
        if args.holdout:
            n = int(rid[1:3])
            engine = f"{engine} {'dev' if n <= args.holdout else 'heldout'}"
        c = agg[engine]
        c["reports"] += 1
        pairs, missed, spurious = align(expected, stored.get(rid, []))
        c["expected"] += len(expected)
        c["produced"] += len(stored.get(rid, []))
        c["found"] += len(pairs)
        c["missed"] += len(missed)
        c["spurious"] += len(spurious)
        if not stored.get(rid):
            c["empty_reports"] += 1
        for e in missed:
            missed_labels[e["printed_label"]] += 1

        for e, a in pairs:
            if norm_value(e["value"]) == norm_value(a["value"]):
                c["value_right"] += 1
            else:
                c["value_wrong"] += 1
            want = e["code"] or None
            if want is None:
                c["uncoded"] += 1
            elif a["code"] == want:
                c["code_right"] += 1
            elif a["code"] is None:
                c["code_blank"] += 1
            else:
                c["code_wrong"] += 1
                wrongs.append((rid, e["printed_label"], want, a["code"]))

    if args.json:
        import json as _json
        out = {}
        for group, c in agg.items():
            coded = c["code_right"] + c["code_wrong"] + c["code_blank"]
            valued = c["value_right"] + c["value_wrong"]
            out[group] = {
                "reports": c["reports"],
                "rows_printed": c["expected"],
                "rows_produced": c["produced"],
                "rows_found": c["found"],
                "rows_missed": c["missed"],
                "rows_spurious": c["spurious"],
                "empty_reports": c["empty_reports"],
                "recall": round(c["found"] / c["expected"], 4) if c["expected"] else None,
                "precision": round(c["found"] / c["produced"], 4) if c["produced"] else None,
                "code_accuracy": round(c["code_right"] / coded, 4) if coded else None,
                "value_accuracy": round(c["value_right"] / valued, 4) if valued else None,
                "code_right": c["code_right"],
                "code_wrong": c["code_wrong"],
                "code_blank": c["code_blank"],
                "uncoded_in_key": c["uncoded"],
            }
        print(_json.dumps(out, indent=1, sort_keys=True))
        return 0

    pct = lambda n, d: f"{n / d:6.1%}" if d else "     -"
    print("=" * 94)
    print(f"{('layout' if args.by_layout else 'engine'):<24}{'rpts':>5}{'rows':>7}{'found':>7}{'recall':>9}"
          f"{'precis':>9}{'code':>9}{'value':>9}{'wrong':>7}{'empty':>7}")
    print("-" * 94)
    order = (sorted(agg, key=lambda e: (agg[e]["found"] / agg[e]["expected"])
                    if agg[e]["expected"] else 1.0)
             if args.by_layout else sorted(agg))
    for engine in order:
        c = agg[engine]
        coded = c["code_right"] + c["code_wrong"] + c["code_blank"]
        valued = c["value_right"] + c["value_wrong"]
        print(f"{engine:<24}{c['reports']:>5}{c['expected']:>7}{c['found']:>7}"
              f"{pct(c['found'], c['expected']):>9}"
              f"{pct(c['found'], c['produced']):>9}"
              f"{pct(c['code_right'], coded):>9}"
              f"{pct(c['value_right'], valued):>9}"
              f"{c['code_wrong']:>7}{c['empty_reports']:>7}")
    print("=" * 94)
    print("recall  rows found / rows printed      precis  rows found / rows produced")
    print("code    right code / rows with a code  value   right value / rows found")
    print("wrong   rows given the WRONG code      empty   reports that yielded nothing")

    total_wrong = sum(agg[e]["code_wrong"] for e in agg)
    if wrongs and (args.wrong or total_wrong <= 20):
        print("\nwrong codes:")
        for rid, label, want, got in wrongs[:200]:
            print(f"  {rid}  {label!r:36s} key={want:10s} stored={got}")
    if args.missed and missed_labels:
        print("\nrows on the page that were never found:")
        for label, n in missed_labels.most_common(50):
            print(f"  {n:5d}x  {label!r}")

    return 1 if total_wrong else 0


def one_document(rid: str, key, stored, engine_of) -> int:
    expected = key.get(rid)
    if not expected:
        sys.exit(f"{rid} is not in the answer key.")
    actual = stored.get(rid, [])
    pairs, missed, spurious = align(expected, actual)
    print(f"{rid}   engine={engine_of.get(rid, '(not ingested)')}   "
          f"printed={len(expected)} produced={len(actual)} found={len(pairs)}")
    print("-" * 78)
    for e, a in pairs:
        ok_c = "ok " if (e["code"] or None) == a["code"] else "COD"
        ok_v = "ok " if norm_value(e["value"]) == norm_value(a["value"]) else "VAL"
        print(f"  {ok_c} {ok_v}  {e['printed_label'][:30]:32s} "
              f"key={str(e['code'] or '-'):10s} got={str(a['code'] or '-'):10s} "
              f"{e['value']!r} -> {a['value']!r}")
    for e in missed:
        print(f"  MISSED     {e['printed_label'][:30]:32s} key={e['code'] or '-'}")
    for a in spurious:
        print(f"  SPURIOUS   {a['printed_label'][:30]:32s} got={a['code'] or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
