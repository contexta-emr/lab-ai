"""Turn an HTML table into a rectangular grid of cell strings.

PaddleOCR-VL returns recognised tables as HTML in ``block_content``. This module is the
adapter back to a plain grid, which is the only shape :mod:`idp.columns` knows about -
so any future engine only has to produce a grid, not HTML.

Stdlib ``html.parser`` on purpose: the markup is a machine-generated ``table/tr/td``
skeleton, not arbitrary web HTML, so a full parser dependency would not earn its place.
"""

from __future__ import annotations

from html import escape
from html.parser import HTMLParser

__all__ = [
    "is_annotation",
    "Grid",
    "grid_to_html",
    "parse_html_tables",
    "split_sections",
    "to_rectangular",
    "fold_single_column",
    "transpose",
]

Grid = list[list[str]]

_CELL_TAGS = frozenset({"td", "th"})


class _TableParser(HTMLParser):
    """Collect ``<table>`` elements as grids, expanding colspan and rowspan."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[Grid] = []
        self._grid: Grid | None = None
        self._row: list[str] | None = None
        self._buf: list[str] = []
        self._in_cell = False
        self._colspan = 1
        self._rowspan = 1
        # Cells still owed to a lower row by an open rowspan: {row_offset: {col: text}}
        self._pending: dict[int, dict[int, str]] = {}
        self._row_no = 0

    @staticmethod
    def _span(attrs: list[tuple[str, str | None]], name: str) -> int:
        for key, value in attrs:
            if key == name and value:
                try:
                    return max(1, min(50, int(value)))
                except ValueError:
                    return 1
        return 1

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._grid, self._pending, self._row_no = [], {}, 0
        elif tag == "tr" and self._grid is not None:
            self._row = []
        elif tag in _CELL_TAGS and self._row is not None:
            self._in_cell = True
            self._buf = []
            self._colspan = self._span(attrs, "colspan")
            self._rowspan = self._span(attrs, "rowspan")
        elif tag == "br" and self._in_cell:
            self._buf.append(" ")

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in _CELL_TAGS and self._in_cell and self._row is not None:
            text = " ".join("".join(self._buf).split())
            # A cell owed from an earlier rowspan occupies its column first.
            while len(self._row) in self._pending.get(self._row_no, {}):
                self._row.append(self._pending[self._row_no].pop(len(self._row)))
            start = len(self._row)
            self._row.extend([text] * self._colspan)
            for extra in range(1, self._rowspan):
                slot = self._pending.setdefault(self._row_no + extra, {})
                for offset in range(self._colspan):
                    slot[start + offset] = text
            self._in_cell = False
        elif tag == "tr" and self._row is not None and self._grid is not None:
            # Flush any remaining owed cells at the end of the row.
            for col in sorted(self._pending.get(self._row_no, {})):
                while len(self._row) < col:
                    self._row.append("")
                self._row.append(self._pending[self._row_no][col])
            self._pending.pop(self._row_no, None)
            self._grid.append(self._row)
            self._row, self._row_no = None, self._row_no + 1
        elif tag == "table" and self._grid is not None:
            if self._grid:
                self.tables.append(self._grid)
            self._grid = None


def parse_html_tables(html: str) -> list[Grid]:
    """Extract every ``<table>`` in ``html`` as a rectangular grid.

    Args:
        html: Markup containing zero or more tables. Malformed markup is tolerated;
            whatever cells are found are returned.

    Returns:
        One grid per table, each padded to a uniform width. Empty tables are dropped.
    """
    parser = _TableParser()
    parser.feed(html)
    parser.close()
    return [to_rectangular(g) for g in parser.tables if any(any(c for c in r) for r in g)]


def to_rectangular(grid: Grid) -> Grid:
    """Pad every row to the width of the widest row.

    Column inference indexes by position, so ragged rows would silently shift cells
    into the wrong column.

    Args:
        grid: Possibly ragged rows.

    Returns:
        A new grid where every row has the same length.
    """
    if not grid:
        return []
    width = max(len(r) for r in grid)
    return [list(r) + [""] * (width - len(r)) for r in grid]


#: Spanning rows that are NOT headings. A lab prints the assay method under the
#: test it belongs to, merged across the full width, and so a colspan scan calls
#: it a heading and cuts the table there. On one real report "Method: IFCC, pNPP
#: - AMP buffer" became a section title and the four rows after it lost their
#: values entirely, because column inference had to work on a fragment.
#:
#: These lines belong to the row above, which is what raw_method is for.
_ANNOTATION_PREFIXES = (
    "method",
    "methods",
    "note",
    "notes",
    "comment",
    "comments",
    "remark",
    "remarks",
    "interpretation",
    "reference",
    "tested by",
    "verified by",
    "results released",
    "report released",
    "disclaimer",
    "advice",
)


def is_annotation(text: str) -> bool:
    """True for a spanning line that annotates the row above, not a heading."""
    lowered = text.strip().lower().lstrip("*†‡ ")
    return any(lowered.startswith(prefix) for prefix in _ANNOTATION_PREFIXES)


def split_sections(grid: Grid) -> list[tuple[str | None, Grid]]:
    """Split a grid where a full-width heading row divides it into separate tables.

    A reading model will happily merge a results grid and the interpretation guide printed
    below it into one table. The two have completely different content, and mixing them
    destroys column inference: rows reading ``hypothyroidism`` drag the value column's
    numeric fraction below threshold, and the panel extracts with no values at all.

    A row whose **non-empty** cells are all the same text, covering at least half the
    width, came from a ``colspan`` heading and is a reliable boundary. Trailing empties are
    ignored because the same printed
    heading comes back as ``colspan=4`` on one run and ``colspan=3`` plus an empty cell on
    the next - two honest readings of one merged cell, from the same weights.

    Args:
        grid: A rectangular grid, possibly containing several logical tables.

    Returns:
        ``(heading, rows)`` pairs in order. ``heading`` is ``None`` for content appearing
        before any spanning row. Sections with no rows are dropped.
    """
    sections: list[tuple[str | None, Grid]] = []
    heading: str | None = None
    current: Grid = []

    for row in grid:
        cells = [c.strip() for c in row]
        # Trailing empties are ignored on purpose. The same printed heading comes back
        # from the model as `colspan=4`, or as `colspan=3` plus one empty cell - both
        # honest readings of one merged cell, and observed alternating between runs of
        # the *same* document. Requiring every cell to be filled recognised only the
        # first, so on the other reading the interpretation legend stayed welded to the
        # results grid and the panel extracted with no values at all.
        filled = [c for c in cells if c]
        # Two matching cells is the minimum evidence of a span. A row with only its first
        # cell filled is a label, a method line or a stray - treating those as boundaries
        # fragments every grid, which is the trap that broke the text-layer engine twice.
        # And a heading spans the table. A sub-line merged over the label columns only -
        # "Sample - EDTA Whole Blood" in four of nine cells - is part of the test above it;
        # cutting there left one-row sections that column inference could not read.
        spanning = (
            len(cells) > 1
            and len(filled) >= 2
            and len(set(filled)) == 1
            and len(filled) * 2 >= len(cells)
            and not is_annotation(filled[0])
        )
        if spanning:
            if current:
                sections.append((heading, current))
            heading, current = cells[0], []
            continue
        current.append(list(row))

    if current:
        sections.append((heading, current))
    return sections


def grid_to_html(grid: Grid) -> str:
    """Render a grid back to a minimal HTML table.

    An engine that already has rows and cells - a text-layer reader, say - uses this so
    the pipeline receives the one shape it knows, instead of gaining a second code path
    that would need its own tests and drift from the first.

    Args:
        grid: Rows of cell strings.

    Returns:
        A ``<table>`` string. Cell text is escaped, so a value containing ``<`` or ``&``
        survives the round trip.
    """
    rows = "".join(
        "<tr>" + "".join(f"<td>{escape(cell or '')}</td>" for cell in row) + "</tr>"
        for row in grid
    )
    return f"<table>{rows}</table>"


def looks_like_html_table(text: str) -> bool:
    """Cheap check for whether ``text`` is worth handing to :func:`parse_html_tables`."""
    lowered = text.lstrip()[:200].lower()
    return "<table" in lowered or "<tr" in lowered


def fold_single_column(grid: Grid) -> Grid:
    """Read a vertical key-value table as the two-column table it is.

    A narrow page - a thermal slip, a register book - is printed as one column, the
    label on one line and its value on the next. OpenParser returns that faithfully:
    one ``<td>`` per ``<tr>``. Every reader downstream expects columns, so a grid in
    this shape yields labels with no values, and the header pairer - which needs two
    cells to see a pair at all - yields no patient and no UHID.

    Folding it here means nothing downstream has to know this shape exists.

    Args:
        grid: The table as parsed, one list per printed row.

    Returns:
        A two-column grid when every filled row in the input is single-celled,
        otherwise the input unchanged and by identity, so callers can tell nothing
        happened.
    """
    filled = [[c for c in row if c.strip()] for row in grid]
    present = [row for row in filled if row]
    if not present:
        return grid

    # Entirely single-celled, not a majority. A grid with even one multi-cell row is
    # not printed as a single column, and folding it would delete that row - label and
    # value both - with no trace. Mixed grids fall through to the column logic, which
    # already handles them.
    if any(len(row) > 1 for row in present):
        return grid

    cells = [row[0].strip() for row in present]
    folded: Grid = []
    for index in range(0, len(cells), 2):
        value = cells[index + 1] if index + 1 < len(cells) else ""
        folded.append([cells[index], value])
    return folded


def transpose(grid: Grid) -> list[list[str]]:
    """Swap rows and columns, padding ragged rows with empty cells.

    Card layouts print one analyte per column and one attribute per row, which
    is an ordinary result grid turned on its side.
    """
    rows = [list(r) for r in grid]
    if not rows:
        return []
    width = max(len(r) for r in rows)
    return [[(r[c] if c < len(r) else "") for r in rows] for c in range(width)]
