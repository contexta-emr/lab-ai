"""Column-role inference: which column is the value, the unit, the reference range.

This is the core of the layout-independence claim. Lab report grids vary in column
*order, naming and presence* - but not in the set of roles. So roles are inferred from
**what the cells contain**, never from what the header says. A header reading "Result",
"Value(s)", "Observed Value" or nothing at all makes no difference.

Roles are assigned **jointly**: every column is scored against every role, and the
combination with the highest total score wins (bounded brute force over each role's
top candidates, since no scipy/OR-tools dependency is available). Column position is
not a signal - a "Method" column outscoring "Test" for label, or an "S.No" column
outscoring "Result" for value, is ruled out by content, not by where the column sits.
An internal test code printed left of the test name, or a whole grid printed right to
left, is handled the same way as the common case.

Header text is used only as a small tiebreak, never to make the decision. The decisive
tiebreak for LABEL vs. a look-alike column is how much of it resolves against the
analyte vocabulary in `synonyms.py`.

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
    split_flag_suffix,
    split_value_unit,
    looks_like_bound,
    looks_like_flag,
    looks_like_qualified_range,
    looks_like_range,
    looks_like_unit,
)
from .synonyms import resolve

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
    CODE = "code"
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

#: "HAE-001", "BIO-221", "CBC/03". Short, mostly upper case, carries a digit and a
#: separator. Deliberately narrow: a real test name almost never matches it.
_CODE_RE = re.compile(r"^[A-Z]{2,5}[-/_ ]?\d{1,5}[A-Z]?$")


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
    vocab_fraction: float
    code_like_fraction: float

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

        A column of bare short integers - ``7``, ``8``, ``9`` - scores exactly as high as
        one of real readings by numeric_fraction alone, and a running S.No is exactly
        that. It carries no more information than the row index. A real value column
        almost always carries more: a decimal point, a magnitude past two digits, or (via
        categorical_fraction) a mixed qualitative reading. Damping the bare-integer case
        is what stops a serial-number column outscoring the true value column when no
        header survives to tell them apart.
        """
        numeric = self.numeric_fraction
        if numeric >= 0.99 and self.mean_length < 2.5:
            numeric *= 0.5
        return min(
            1.0,
            numeric + 0.5 * self.bound_fraction + 0.8 * self.categorical_fraction,
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
        shape = 0.6 * variety + 0.4 * length
        # A column that resolves against the analyte vocabulary IS the label
        # column, whatever its shape or position. Shape alone cannot separate
        # "HAE-001" from "Haemoglobin" - both are wordy and both are distinct.
        return max(shape, min(1.0, 0.55 + 0.45 * self.vocab_fraction)) \
            if self.vocab_fraction > 0 else shape

    @property
    def flag_score(self) -> float:
        """Flag columns are mostly empty *and* their non-empty cells are all markers."""
        return self.flag_fraction if self.empty_fraction >= 0.3 else 0.0

    @property
    def code_score(self) -> float:
        """An internal test code is short, unique per row and resolves to nothing.

        Labs print codes like "HAE-001" or "BIO-221" left of the test name. They
        are wordy enough to score as labels and distinct enough to look like test
        names, which is precisely why they need a role of their own.
        """
        if self.vocab_fraction > 0.2:
            return 0.0
        return self.code_like_fraction

    @property
    def vocab_score(self) -> float:
        """How much of this column reads as known test names.

        The decisive signal. `synonyms` already loads 662 spellings from
        lab_analytes_seed.sql at runtime, so this is a lookup against data we
        maintain, not another heuristic.
        """
        return self.vocab_fraction


def _bare_number(cell: str) -> str:
    """The cell with a trailing flag and a trailing unit taken off.

    Both are printed inside the value cell by real labs - "214 H", "12.9 g/dL", and
    occasionally both at once - and neither changes the fact that the column holds
    values. Stripping them before the numeric test is what stops a whole panel being
    typed :attr:`Role.UNKNOWN` and extracting with no readings at all.
    """
    return split_value_unit(split_flag_suffix(cell)[0])[0]


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
                ColumnProfile(
                    col, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0, 0.0, 0.0, 0.0, 0.0
                )
            )
            continue
        resolved = sum(1 for c in filled if resolve(c)) / n
        code_like = sum(1 for c in filled if _CODE_RE.match(c.strip())) / n
        profiles.append(
            ColumnProfile(
                index=col,
                # Through a trailing flag or unit: "214 H" and "12.9 g/dL" are
                # both numbers wearing something extra, and a column of them is
                # a value column. Counting them as non-numeric collapsed the
                # fraction and classified the whole column 'unknown', which
                # silently dropped every reading on the panel.
                numeric_fraction=sum(is_numeric(_bare_number(c)) for c in filled) / n,
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
                vocab_fraction=resolved,
                code_like_fraction=code_like,
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

    Every column is scored against every role and the combination with the highest total
    score wins, searched as bounded brute force over each role's top-scoring candidates
    (no positional assumption, no external solver dependency). That is what stops a
    serial-number column being read as the result and a method column as the test name,
    without relying on where either column sits.

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

    # Every role is contested by every column. The old implementation claimed
    # LABEL as the leftmost text-like column and then allowed the other roles
    # only to its right. That is two positional assumptions, and real reports
    # break both: an internal test code prints left of the test name, and some
    # labs print the whole grid right to left. Position is not a signal.
    scorers: list[tuple[Role, Callable[[ColumnProfile], float]]] = [
        (Role.LABEL, lambda p: p.label_score),
        (Role.REFERENCE, lambda p: p.reference_score),
        (Role.UNIT, lambda p: p.unit_fraction),
        (Role.FLAG, lambda p: p.flag_score),
        (Role.CODE, lambda p: p.code_score),
        (Role.VALUE, lambda p: p.value_score),
    ]

    # Top-K per role, not every column, so the product stays small. K=4 is well
    # past the widest real grid's genuine ambiguity and caps the search at 4**6.
    candidates: dict[Role, list[tuple[int, float]]] = {}
    for role, score_of in scorers:
        scored = [
            (p.index, score_of(p) + _header_bonus(header, p.index, role))
            for p in profiles
        ]
        viable = sorted(
            ((i, s) for i, s in scored if s >= THRESHOLD), key=lambda t: -t[1]
        )[:4]
        candidates[role] = viable

    best_total, best = -1.0, {}
    order = [r for r, _ in scorers]

    def search(depth: int, used: set[int], total: float, acc: dict[int, Role]) -> None:
        nonlocal best_total, best
        if depth == len(order):
            if total > best_total:
                best_total, best = total, dict(acc)
            return
        role = order[depth]
        # Leaving a role unassigned is always allowed. A two-column slip has no
        # unit column, and inventing one would put a number in raw_unit.
        search(depth + 1, used, total, acc)
        for col, score in candidates[role]:
            if col in used:
                continue
            acc[col] = role
            search(depth + 1, used | {col}, total + score, acc)
            del acc[col]

    search(0, set(), 0.0, {})
    roles.update(best)
    return roles


def role_of(roles: dict[int, Role], role: Role) -> int | None:
    """Reverse lookup: which column index holds ``role``, if any."""
    for col, assigned in roles.items():
        if assigned is role:
            return col
    return None
