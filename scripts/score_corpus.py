"""Score what the database stored against the sealed answer key.

    python scripts/score_corpus.py            # the headline numbers
    python scripts/score_corpus.py --wrong    # list every wrong code
    python scripts/score_corpus.py --null     # list every honest blank

Run after load_corpus.py. This is the measurement the whole corpus exists for:
of the 4,177 printed test lines, how many did the pipeline give the right
canonical code, how many did it honestly refuse, and how many did it get wrong.

    right   the stored analyte code equals the key
    blank   the key has a code, the pipeline stored NULL. Costs a trend point,
            corrupts nothing, and the label lands in lab.unmatched_labels
    WRONG   the pipeline stored a different code from the key. The expensive
            failure - a wrong code silently corrupts a trend line for years

The key is read here and nowhere else. CLAUDE.md section 7: a parser that reads
corpus/data/answers/ measures nothing. This is not the parser; it is the scorer,
and it runs after the fact.

Documents are matched to key reports by the SHA-256 of the PDF, which is how
load_corpus.py identified them going in. Rows are matched within a report by
printed order, which lab.results preserves in section and sequence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import psycopg
except ImportError:  # pragma: no cover
    sys.exit("psycopg is not installed.  pip install 'psycopg[binary]'")

ROOT = Path(__file__).resolve().parents[1]
ANSWERS = ROOT / "corpus" / "data" / "answers"
PDFS = ROOT / "corpus" / "data" / "pdfs"


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
    ap.add_argument("--wrong", action="store_true", help="list every wrong code")
    ap.add_argument("--null", action="store_true", help="list every honest blank")
    args = ap.parse_args()

    load_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set. Copy .env.example to .env first.")

    # key: report_id -> rows, in printed order
    key_rows: dict[str, list[dict]] = defaultdict(list)
    with (ANSWERS / "rows.csv").open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            key_rows[row["report_id"]].append(row)

    # checksum -> report_id, the same hash load_corpus.py computed
    by_checksum: dict[str, str] = {}
    with (ANSWERS / "reports.csv").open(encoding="utf-8", newline="") as fh:
        for rep in csv.DictReader(fh):
            pdf = PDFS / f"P{int(rep['patient_number']):02d}" / f"{rep['report_id']}.pdf"
            if pdf.exists():
                by_checksum[hashlib.sha256(pdf.read_bytes()).hexdigest()] = rep["report_id"]

    with psycopg.connect(url) as conn:
        stored = conn.execute("""
            SELECT d.checksum_sha256, r.printed_label, a.code, r.match_method
            FROM   lab.results   r
            JOIN   lab.documents d ON d.id = r.document_id
            LEFT   JOIN lab.analytes a ON a.id = r.analyte_id
            WHERE  d.is_synthetic = TRUE AND r.is_deleted = FALSE
            ORDER  BY d.id, r.section_id NULLS FIRST, r.sequence, r.id
        """).fetchall()

    got: dict[str, list[tuple]] = defaultdict(list)
    for checksum, label, code, method in stored:
        rid = by_checksum.get(checksum)
        if rid:
            got[rid].append((label, code, method))

    right = blank = wrong = uncoded = 0
    wrongs: list[tuple] = []
    blanks: Counter = Counter()
    skipped = 0

    for rid, expected in key_rows.items():
        actual = got.get(rid)
        if actual is None or len(actual) != len(expected):
            skipped += len(expected)
            continue
        for exp, (label, code, method) in zip(expected, actual):
            want = exp["code"] or None
            if want is None:
                uncoded += 1            # deliberately uncoded in the key
            elif code == want:
                right += 1
            elif code is None:
                blank += 1
                blanks[exp["printed_label"]] += 1
            else:
                wrong += 1
                wrongs.append((rid, label, want, code, method))

    scored = right + blank + wrong
    print("=" * 62)
    print(f"key rows scored        {scored}   (+{uncoded} deliberately uncoded"
          + (f", {skipped} unmatched reports" if skipped else "") + ")")
    print(f"  right                {right}   ({right / scored:.2%})" if scored else "")
    print(f"  blank, honest        {blank}")
    print(f"  WRONG CODE           {wrong}")
    print("=" * 62)

    if wrongs and (args.wrong or wrong <= 20):
        print("\nwrong codes:")
        for rid, label, want, code, method in wrongs[:200]:
            print(f"  {rid}  {label!r:38s} key={want:10s} stored={code:10s} via {method}")
    if args.null and blanks:
        print("\nhonest blanks, by printed label:")
        for label, n in blanks.most_common(60):
            print(f"  {n:4d}x  {label!r}")

    return 1 if wrong else 0


if __name__ == "__main__":
    raise SystemExit(main())
