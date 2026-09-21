"""Which corpus PDFs carry a text layer, and which need OCR.

    python scripts/probe_text_layer.py          # the counts
    python scripts/probe_text_layer.py --write  # also write the listing
    docker compose exec -T api python /work/scripts/probe_text_layer.py --json         > corpus/data/no_text_layer.json

The --json form exists because corpus/ is mounted read-only into the api
container - the service must never be able to write to the corpus - so inside
the container the listing has to come out on stdout and be written by the host.

Writes corpus/data/no_text_layer.json, the list upload_corpus.py --no-text-layer
and the OCR runs read.

WHY THIS IS MEASURED AND NOT ASSUMED
    CLAUDE.md said 52 damaged reports (17%). Counting damage traps in the
    answer key gives 73. Opening all 300 PDFs and asking PyMuPDF gives 61.

    The three disagree because they count different things. A report can carry
    a damage trap that tints or folds the paper without triggering a CSS filter,
    and only a filter forces the browser to rasterise the page at print time.
    Trap counts are a proxy. This is the fact: it opens the file and looks.

    That matters because the OCR bill and the OCR runtime are both per page,
    and because "how many of the 300 can the current reader not touch at all"
    is the number the whole extraction phase is judged against.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDFS = ROOT / "corpus" / "data" / "pdfs"
LISTING = ROOT / "corpus" / "data" / "no_text_layer.json"

# The same threshold api/app/services/extract.py uses to decide a PDF is an
# image. Kept identical on purpose: this script must classify a document the
# way the service will, not more generously.
MIN_CHARS = 40


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="write the JSON listing")
    ap.add_argument("--json", action="store_true",
                    help="print the listing to stdout and nothing else; for "
                         "redirecting from the host when corpus/ is read-only")
    args = ap.parse_args()

    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf  # older wheels
        except ImportError:
            sys.exit("PyMuPDF is not installed.  pip install pymupdf")

    if not PDFS.is_dir():
        sys.exit(f"{PDFS} not found.")

    with_text: list[str] = []
    without: list[str] = []
    pages_without = 0
    multipage = 0

    for pdf in sorted(PDFS.rglob("*.pdf")):
        with pymupdf.open(pdf) as doc:
            text = "".join(page.get_text() for page in doc)
            n_pages = len(doc)
        if n_pages > 1:
            multipage += 1
        if len(text.strip()) > MIN_CHARS:
            with_text.append(pdf.stem)
        else:
            without.append(pdf.stem)
            pages_without += n_pages

    if args.json:
        print(json.dumps(sorted(without), indent=1))
        return 0

    total = len(with_text) + len(without)
    print(f"PDFs probed             {total}")
    print(f"  with a text layer     {len(with_text)}   ({len(with_text) / total:.1%})")
    print(f"  no text layer, OCR    {len(without)}   ({len(without) / total:.1%})")
    print(f"  pages needing OCR     {pages_without}")
    print(f"  multi-page reports    {multipage}")
    print()
    print("OCR cost and time for the no-text-layer set:")
    print(f"  openparser  ~{pages_without * 6 / 60:.0f} min   ~Rs {pages_without * 0.09:.2f}"
          f"   (leaves India)")
    print(f"  paddle_vl   ~{pages_without * 20 / 60:.1f} hours  free"
          f"          (stays in boundary)")

    if args.write:
        try:
            LISTING.write_text(json.dumps(sorted(without), indent=1), encoding="utf-8")
            print(f"\nwrote {LISTING.relative_to(ROOT)}  ({len(without)} report ids)")
        except OSError as exc:
            print(f"\ncould not write {LISTING}: {exc}")
            print("corpus/ is mounted read-only in the api container. From the host:")
            print("  docker compose exec -T api python /work/scripts/probe_text_layer.py"
                  " --json > corpus/data/no_text_layer.json")
            return 1
    else:
        print("\n(pass --write to save the listing, or --json to redirect it)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
