"""Read a digital PDF directly. No model, no GPU, no network.

A PDF with a text layer already contains the characters. There is nothing to *recognise*.
Rasterising the page and asking a vision model to read a picture of that text is slower by
five orders of magnitude and strictly less accurate - it replaces the actual characters
with a probabilistic reading of them.

Measured on this project: **1385 seconds** for one page through PaddleOCR-VL on CPU,
against **milliseconds** here, and exactly rather than approximately.

Built on pdfplumber: MIT licensed, geometry-based, and it exposes every character with its
coordinates - which is what its table finder reconstructs rows and columns from. The
licence matters as much as the accuracy: PyMuPDF is AGPL-3.0, whose network clause is
triggered by hosted SaaS.

This engine reports **nothing at all** for a scanned or photographed page. That is correct
- it is not a fallback OCR, it is a fast path for documents that do not need OCR, and the
caller decides what to do when it comes back empty.
"""

from __future__ import annotations

from pathlib import Path

from .base import RawBlock, RawDocument, RawPage
from .tables import grid_to_html

__all__ = ["TextLayerEngine", "has_text_layer"]


def _bounds(words: list[dict[str, float]]) -> tuple[float, float, float, float] | None:
    """The rectangle enclosing a group of words, or ``None`` when there are none."""
    if not words:
        return None
    return (
        min(float(w["x0"]) for w in words),
        min(float(w["top"]) for w in words),
        max(float(w["x1"]) for w in words),
        max(float(w["bottom"]) for w in words),
    )


#: Below this many characters a "text layer" is a scanner watermark, not a document.
MIN_TEXT_CHARS = 40


def has_text_layer(path: Path, *, minimum: int = MIN_TEXT_CHARS) -> bool:
    """Whether a PDF carries enough real text to be read without OCR.

    Args:
        path: The document to check.
        minimum: Characters required across the whole document.

    Returns:
        ``True`` when the file is a PDF with extractable text. ``False`` for images,
        scans, and anything that cannot be opened - never raises, because this is a
        routing question and an unreadable file simply routes to the other engine.
    """
    if path.suffix.lower() != ".pdf":
        return False
    try:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            total = 0
            for page in pdf.pages:
                total += len(page.extract_text() or "")
                if total >= minimum:
                    return True
    except Exception:  # noqa: BLE001 - a broken file is just "not this engine's job"
        return False
    return False


class TextLayerEngine:
    """Reads tables and text straight out of a digital PDF."""

    name = "TEXT_LAYER"
    version = "pdfplumber"

    def __init__(self, *, min_text_chars: int = MIN_TEXT_CHARS) -> None:
        """Configure the engine.

        Args:
            min_text_chars: Characters a page must have before its text is trusted.
        """
        self._min_text_chars = min_text_chars

    def extract(self, path: Path) -> RawDocument:
        """Read one digital PDF.

        Args:
            path: The document to read.

        Returns:
            Blocks in the same shape every other engine produces: tables as HTML, other
            content as text, all with coordinates. Pages with no text layer contribute
            no blocks rather than raising - a mixed document is normal.

        Raises:
            FileNotFoundError: If ``path`` does not exist.
            RuntimeError: If pdfplumber is not installed.
        """
        if not path.exists():
            raise FileNotFoundError(path)
        try:
            import pdfplumber
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                'the text-layer engine needs pdfplumber: uv pip install -e ".[textlayer]"'
            ) from exc

        pages: list[RawPage] = []
        with pdfplumber.open(path) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                pages.append(self._read_page(page, index))
        return RawDocument(
            source_path=path, engine=self.name, engine_version=self.version, pages=pages
        )

    def _read_page(self, page: object, number: int) -> RawPage:
        """Turn one pdfplumber page into a grid plus its position.

        Lab result grids are usually **borderless** - aligned by whitespace, not ruled -
        so pdfplumber's own table finder returns either the whole page as one cell or a
        fragmented mess. Columns are reconstructed from word x-positions instead, which is
        what the alignment actually is.
        """
        width = float(getattr(page, "width", 0) or 1)
        height = float(getattr(page, "height", 0) or 1)

        lines = self._lines(page)
        if not lines:
            return RawPage(page_number=number, width=width, height=height, blocks=[])

        anchors = self._column_anchors(lines)
        rows = [(self._to_cells(words, anchors), words) for _key, words in lines]

        blocks: list[RawBlock] = []
        run: list[tuple[list[str], list[dict[str, float]]]] = []

        def flush() -> None:
            """Emit the accumulated run as a table, or as text if it is too short."""
            if not run:
                return
            if len(run) >= 3:
                blocks.append(
                    RawBlock(
                        label="table",
                        content=grid_to_html([cells for cells, _w in run]),
                        bbox=_bounds([w for _c, words in run for w in words]),
                        order=len(blocks),
                    )
                )
            else:
                for cells, words in run:
                    blocks.append(
                        RawBlock(
                            label="text",
                            content=" ".join(c for c in cells if c).strip(),
                            bbox=_bounds(words),
                            order=len(blocks),
                        )
                    )
            run.clear()

        for cells, words in rows:
            filled = {i for i, c in enumerate(cells) if c.strip()}
            if not filled:
                continue
            if len(filled) < 2:
                # One occupied column is a heading or a line of prose, not a table row.
                #
                # This is the tuning point. Some labs print the assay method on its own
                # line under the test name, and treating those as boundaries fragments
                # the grid. Two attempts to special-case them - matching the label
                # column, then also requiring a complete row above - both scored *worse*
                # across the 13-document corpus (420 -> 353 core, 15 -> 10 values).
                # Whatever distinguishes a continuation from a heading is not captured by
                # column position alone. Measure against tools/score_corpus.py before
                # changing this.
                flush()
                blocks.append(
                    RawBlock(
                        label="text",
                        content=" ".join(c for c in cells if c).strip(),
                        bbox=_bounds(words),
                        order=len(blocks),
                    )
                )
                continue
            # A table is a run of lines sharing a column structure. When the occupied
            # columns stop overlapping, a different block has started - which is what
            # separates the patient header from the results grid below it.
            if run:
                previous = {i for i, c in enumerate(run[-1][0]) if c.strip()}
                if len(filled & previous) < 2:
                    flush()
            run.append((cells, words))
        flush()

        return RawPage(page_number=number, width=width, height=height, blocks=blocks)

    @staticmethod
    def _lines(page: object) -> list[tuple[int, list[dict[str, float]]]]:
        """Words grouped into printed lines, top to bottom.

        Two points of tolerance absorbs the sub-pixel drift between characters that sit on
        the same printed line but differ slightly in reported height.
        """
        try:
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - an unreadable page yields nothing, not a crash
            return []

        rows: dict[int, list[dict[str, float]]] = {}
        for word in words:
            rows.setdefault(round(float(word["top"]) / 2), []).append(word)
        return [(key, sorted(rows[key], key=lambda w: float(w["x0"]))) for key in sorted(rows)]

    @staticmethod
    def _column_anchors(
        lines: list[tuple[int, list[dict[str, float]]]], *, tolerance: float = 6.0
    ) -> list[float]:
        """Left edges shared by enough lines to be real columns.

        A lab grid aligns every row's cells to the same left edges. Clustering the word
        start positions across the whole page recovers those edges without needing a
        single ruled line. Positions used by only one or two lines are prose, not a
        column, and are folded into the column to their left.

        Args:
            lines: Output of :meth:`_lines`.
            tolerance: Points within which two left edges are the same column.

        Returns:
            Column left edges, ascending. Always at least one.
        """
        starts = sorted(float(w["x0"]) for _key, words in lines for w in words)
        if not starts:
            return [0.0]

        clusters: list[list[float]] = [[starts[0]]]
        for value in starts[1:]:
            if value - clusters[-1][-1] <= tolerance:
                clusters[-1].append(value)
            else:
                clusters.append([value])

        # A column that only two lines use is an indent or a stray, not a column.
        minimum = max(2, len(lines) // 12)
        anchors = [
            sum(cluster) / len(cluster) for cluster in clusters if len(cluster) >= minimum
        ]
        return anchors or [starts[0]]

    @staticmethod
    def _to_cells(
        words: list[dict[str, float]], anchors: list[float], *, slack: float = 6.0
    ) -> list[str]:
        """Place one line's words into the column they start in."""
        cells = [""] * len(anchors)
        for word in words:
            x0 = float(word["x0"])
            index = 0
            for position, anchor in enumerate(anchors):
                if x0 >= anchor - slack:
                    index = position
                else:
                    break
            text = str(word["text"])
            cells[index] = f"{cells[index]} {text}".strip() if cells[index] else text
        return cells
