"""Column-role inference: which column is the value, the unit, the reference range.

This is the core of the layout-independence claim. Lab report grids vary in column
*order, naming and presence* - but not in the set of roles. So roles are inferred from
**what the cells contain**, never from what the header says. A header reading "Result",
"Value(s)", "Observed Value" or nothing at all makes no difference.

Two structural facts about lab reports do the heavy lifting, and both are exploited
deliberately:

1. The label column is the **leftmost** column that reads like test names. Nothing is
   printed to the left of the test except a serial number, which is not text.
2. Every other role sits **to the right of the label**. A result never precedes the name
   of the test it belongs to.

Together these kill the two failure modes content-scoring alone gets wrong: a "Method"
column outscoring "Test" for label, and an "S.No" column outscoring "Result" for value.

Header text is used only as a small tiebreak, never to make the decision.

See `attachment-extraction-engine.md` section 5.2.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from .numbers import (
    is_categorical_result,
    is_numeric,
    looks_like_bound,
    looks_like_flag,
    looks_like_qualified_range,
    looks_like_range,
    looks_like_unit,
)

__all__ = [
    "ColumnProfile",
    "Role",
    "detect_header_row",
    "infer_roles",
    "profile_columns",
    "role_of",
]

Grid = Sequence[Sequence[str]]


class Role(StrEnum):
    """What a grid column is for."""

    LABEL = "label"
    VALUE = "value"
    UNIT = "unit"
    REFERENCE = "reference"
    FLAG = "flag"
    UNKNOWN = "unknown"


#: Minimum score for a role to be assigned at all. Below this a column is left UNKNOWN
#: rather than guessed at - the same principle as returning a NULL analyte_code.
THRESHOLD = 0.55

#: How much agreement between the printed header and the content-derived role is worth.
#: Small on purpose: it breaks ties, it does not make decisions.
HEADER_BONUS = 0.15

_HEADER_HINTS: dict[Role, frozenset[str]] = {
    Role.LABEL: frozenset({"test", "testname", "investigation", "parameter", "analyte",
                           "description", "particulars", "examination", "name"}),
    Role.VALUE: frozenset({"result", "value", "values", "observedvalue", "observed",
                           "reading", "patientvalue", "yourvalue", "found"}),
    Role.UNIT: frozenset({"unit", "units", "uom"}),
    Role.REFERENCE: frozenset({"reference", "referencerange", "range", "normalrange",
                               "normalvalue", "biologicalreferenceinterval",
                               "refrange", "normal", "interval"}),
    Role.FLAG: frozenset({"flag", "abnormal", "status", "indicator"}),
}

_ALPHA_RE = re.compile(r"[a-zA-Z]")


def _norm_header(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


@dataclass(frozen=True, slots=True)
class ColumnProfile:
    """Content statistics for one column, computed over data rows only.

    Fractions are over *non-empty* cells, except ``flag_fraction`` and ``empty_fraction``
    which are over every cell - a flag column is mostly blank by nature, and that
    blankness is the signal.
    """

    index: int
    numeric_fraction: float
    range_fraction: float
    qualified_fraction: float
    bound_fraction: float
    categorical_fraction: float
    unit_fraction: float
    flag_fraction: float
    empty_fraction: float
    distinct_count: int
    mean_length: float
    alpha_fraction: float

    @property
    def reference_score(self) -> float:
        """Two-sided and qualified ranges are decisive; one-sided bounds count for half.

        Bounds appear in value columns too - a below-detection-limit result reads
        ``<0.01`` - so they must not on their own claim the reference column. A
        sex-qualified range cannot be *parsed* without the patient, but it is still an
        unmistakable reference column, so it scores nearly as high as a plain range.
        """
        return min(
            1.0,
            self.range_fraction + 0.8 * self.qualified_fraction + 0.5 * self.bound_fraction,
        )

    @property
    def value_score(self) -> float:
        """Bare numbers are the signal; bounds and categorical results count partially.

        A serology result column reads ``Negative`` throughout and contains no numbers at
        all. Without the categorical term such a column would be left unassigned, and the
        whole panel would extract with no values.
        """
        return min(
            1.0,
            self.numeric_fraction + 0.5 * self.bound_fraction + 0.8 * self.categorical_fraction,
        )

    @property
    def label_score(self) -> float:
        """Test names are wordy and nearly all distinct.

        That is what separates a label column from a categorical result column, which is
        short and highly repetitive: twenty rows of ``Negative`` have a distinct count of
        one, while twenty test names have a distinct count of twenty.
        """
        if self.alpha_fraction < 0.5 or self.mean_length < 3:
            return 0.0
        variety = min(1.0, self.distinct_count / 3)
        length = min(1.0, self.mean_length / 8)
        return 0.6 * variety + 0.4 * length

    @property
    def flag_score(self) -> float:
        """Flag columns are mostly empty *and* their non-empty cells are all markers."""
        return self.flag_fraction if self.empty_fraction >= 0.3 else 0.0


def profile_columns(grid: Grid, *, skip_rows: int = 0) -> list[ColumnProfile]:
    """Compute content statistics for every column in the grid.

    Args:
        grid: Rows of cells. Ragged rows are tolerated; missing cells count as empty.
        skip_rows: Leading rows to exclude, normally the detected header row.

    Returns:
        One profile per column, indexed left to right. Empty when there are no data rows.
    """
    rows = list(grid)[skip_rows:]
    if not rows:
        return []
    width = max((len(r) for r in rows), default=0)
    profiles: list[ColumnProfile] = []

    for col in range(width):
        cells = [(r[col] if col < len(r) else "") for r in rows]
        filled = [c for c in cells if c.strip()]
        n = len(filled)
        if n == 0:
            profiles.append(
                ColumnProfile(col, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0, 0.0, 0.0)
            )
            continue
        profiles.append(
            ColumnProfile(
                index=col,
                numeric_fraction=sum(is_numeric(c) for c in filled) / n,
                range_fraction=sum(looks_like_range(c) for c in filled) / n,
                qualified_fraction=sum(looks_like_qualified_range(c) for c in filled) / n,
                bound_fraction=sum(looks_like_bound(c) for c in filled) / n,
                categorical_fraction=sum(is_categorical_result(c) for c in filled) / n,
                unit_fraction=sum(looks_like_unit(c) for c in filled) / n,
                flag_fraction=sum(looks_like_flag(c) for c in cells) / len(cells),
                empty_fraction=1.0 - n / len(cells),
                distinct_count=len({c.strip().lower() for c in filled}),
                mean_length=sum(len(c.strip()) for c in filled) / n,
                alpha_fraction=sum(bool(_ALPHA_RE.search(c)) for c in filled) / n,
            )
        )
    return profiles


def detect_header_row(grid: Grid) -> int | None:
    """Return the index of a leading header row, or ``None`` if there is not one.

    Header *words* are the one place printed text is allowed to matter: deciding whether
    a row is data at all is a different question from deciding what a column means.

    Args:
        grid: Rows of cells.

    Returns:
        ``0`` when the first row reads as a header, otherwise ``None``.
    """
    if not grid:
        return None
    first = [_norm_header(c) for c in grid[0] if c.strip()]
    if not first:
        return None
    known = {word for words in _HEADER_HINTS.values() for word in words}
    hits = sum(any(h in cell or cell in h for h in known) for cell in first if cell)
    # Two hits, or one in a two-column grid. A data row would need two header words in
    # it to be misread, which does not happen.
    return 0 if hits >= min(2, len(first)) else None


def _header_bonus(header: Sequence[str] | None, col: int, role: Role) -> float:
    """Small nudge when the printed header agrees with the content-derived role."""
    if header is None or col >= len(header):
        return 0.0
    cell = _norm_header(header[col])
    if not cell:
        return 0.0
    hints = _HEADER_HINTS.get(role, frozenset())
    return HEADER_BONUS if any(h in cell or cell in h for h in hints) else 0.0


def infer_roles(grid: Grid, *, header_row: int | None = None) -> dict[int, Role]:
    """Assign a role to each column of a result grid.

    The label is claimed first, as the leftmost column that reads like test names. Every
    other role is then contested only among columns to its right, which is what stops a
    serial-number column being read as the result and a method column as the test name.

    Among those, roles are claimed most-distinctive-first: a two-sided reference range is
    the least ambiguous thing on the page, so it goes before the value.

    Args:
        grid: Rows of cells, optionally including a header row.
        header_row: Index of the header row, or ``None`` to detect it.

    Returns:
        Mapping of column index to role. Columns matching nothing convincingly are mapped
        to :attr:`Role.UNKNOWN` rather than guessed at.
    """
    rows = list(grid)
    if not rows:
        return {}
    hdr_idx = detect_header_row(rows) if header_row is None else header_row
    header = list(rows[hdr_idx]) if hdr_idx is not None else None
    profiles = profile_columns(rows, skip_rows=(hdr_idx + 1) if hdr_idx is not None else 0)
    if not profiles:
        return {}

    roles: dict[int, Role] = {p.index: Role.UNKNOWN for p in profiles}
    taken: set[int] = set()

    # 1. Label: leftmost column that reads like test names, not highest-scoring.
    label_col = -1
    for p in profiles:
        if p.label_score + _header_bonus(header, p.index, Role.LABEL) >= THRESHOLD:
            label_col = p.index
            roles[label_col] = Role.LABEL
            taken.add(label_col)
            break

    # 2-5. Everything else, only to the right of the label.
    candidates = [p for p in profiles if p.index > label_col and p.index not in taken]

    def claim(role: Role, score_of: Callable[[ColumnProfile], float]) -> None:
        best_col, best_score = -1, THRESHOLD
        for p in candidates:
            if p.index in taken:
                continue
            score = score_of(p) + _header_bonus(header, p.index, role)
            if score > best_score:
                best_col, best_score = p.index, score
        if best_col >= 0:
            roles[best_col] = role
            taken.add(best_col)

    claim(Role.REFERENCE, lambda p: p.reference_score)
    claim(Role.UNIT, lambda p: p.unit_fraction)
    claim(Role.FLAG, lambda p: p.flag_score)
    claim(Role.VALUE, lambda p: p.value_score)
    return roles


def role_of(roles: dict[int, Role], role: Role) -> int | None:
    """Reverse lookup: which column index holds ``role``, if any."""
    for col, assigned in roles.items():
        if assigned is role:
            return col
    return None
