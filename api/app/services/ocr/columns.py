"""Column-role inference: which column is the value, the unit, the reference range.

This is the core of the layout-independence claim. Lab report grids vary in column
*order, naming and presence* - but not in the set of roles. So roles are inferred from
**what the cells contain**, never from what the header says. A header reading "Result",
"Value(s)", "Observed Value" or nothing at all makes no difference.

Roles are assigned **jointly**, in two priority tiers: every column is scored against
every role in its tier, and the combination with the highest total score wins (bounded
brute force over each role's top candidates, since no scipy/OR-tools dependency is
available). LABEL and VALUE are decided first and outrank REFERENCE, UNIT, FLAG and CODE
by construction - a row with no label is dropped outright, so trading a real LABEL column
away for a false-positive UNIT match elsewhere is never worth it, whatever the raw scores
say. Column position is not a signal for the *decision* - a "Method" column outscoring
"Test" for label, or an "S.No" column outscoring "Result" for value, is ruled out by
content. An internal test code printed left of the test name, or a whole grid printed
right to left, is handled the same way as the common case. Position remains the very
last tiebreak, deliberately: see `_best_assignment` for when and why.

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
    UNIT_LEXICON,
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
    "assignment_strength",
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
    Role.LABEL: frozenset(
        {
            "test",
            "testname",
            "investigation",
            "parameter",
            "analyte",
            "description",
            "particulars",
            "examination",
            "name",
        }
    ),
    Role.VALUE: frozenset(
        {
            "result",
            "value",
            "values",
            "observedvalue",
            "observed",
            "reading",
            "patientvalue",
            "yourvalue",
            "found",
        }
    ),
    Role.UNIT: frozenset({"unit", "units", "uom"}),
    Role.REFERENCE: frozenset(
        {
            "reference",
            "referencerange",
            "range",
            "normalrange",
            "normalvalue",
            "biologicalreferenceinterval",
            "refrange",
            "normal",
            "interval",
        }
    ),
    Role.FLAG: frozenset({"flag", "abnormal", "status", "indicator"}),
}

_ALPHA_RE = re.compile(r"[a-zA-Z]")

#: "HAE-001", "BIO-221", "CBC/03". Short, mostly upper case, carries a digit and a
#: separator. The separator is required, not optional: real analyte shorthand -
#: "CA125", "VITD3", "CEA2", "CO2" - is letters glued straight to digits with nothing
#: between them, and none of those resolve, so an optional separator let code_score
#: beat label_score on a genuine test-name column and drop the whole grid.
_CODE_RE = re.compile(r"^[A-Z]{2,5}[-/_ ]\d{1,5}[A-Z]?$")

#: A cell that is a bare integer, nothing else - what a serial-number column is made of.
_INT_RE = re.compile(r"^-?\d+$")


def _norm_header(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


def _known_unit(cell: str) -> bool:
    """True when the cell is a unit this codebase's lexicon already knows by name.

    Distinct from `looks_like_unit`, which also matches through a permissive shape
    fallback (letters, optionally followed by digits) so as not to miss a unit it has
    never seen - and that fallback matches "CA125" and "VITD3" exactly as readily as it
    matches a real, unlisted unit, because both are short letters-then-digits strings.
    label_score needs to tell a genuine unit column ("mEq/L", "mmol/L", both in the
    lexicon) apart from real analyte shorthand that merely happens to look unit-shaped,
    and the lexicon - not the shape heuristic - is what draws that line.
    """
    normalised = re.sub(r"\s+", "", cell.strip().lower()).replace("µ", "u").replace("μ", "u")
    return normalised in UNIT_LEXICON


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
    serial_run_fraction: float
    known_unit_fraction: float

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

        A column of bare integers scores exactly as high as one of real readings by
        numeric_fraction alone, and a running S.No is exactly that - but a *width* or
        *mean-length* proxy for "looks like a counter" is wrong on both sides: it misses
        a three-digit serial ("101", "102", ...) and it wrongly convicts genuine short
        integer results (a WBC differential's "62, 30, 4, 3, 1", urine microscopy's
        "2, 3, 0, 0, 1"), which are exactly as short as a counter but do not count up by
        one. serial_run_fraction reads the content instead of its width: it is the
        longest run of consecutive-ascending-by-one values, as a share of the column. A
        printed serial number IS that run for its whole length; real results hit "+1"
        between neighbours only by coincidence, for a row or two at most.
        """
        numeric = self.numeric_fraction * (1.0 - self.serial_run_fraction)
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
        if self.vocab_fraction == 0 and self.known_unit_fraction >= 0.8:
            # A column that is overwhelmingly *known* units ("mEq/L", "mmol/L", "g/dL")
            # and resolves against nothing is a units column, not a label with an
            # unusual vocabulary - it is exactly as wordy and distinct as a real label
            # column, which is precisely why shape alone cannot rule it out. This checks
            # known_unit_fraction rather than the more permissive unit_fraction on
            # purpose: unit_fraction's shape fallback matches "CA125" and "VITD3" just
            # as readily as a real unit (both are short letters-then-digits strings),
            # which excluded real analyte shorthand from LABEL right along with genuine
            # units. Making `required=` conditional on some column resolving (Ruling 9)
            # stops LABEL being *forced* onto a units column, but an unforced, cost-free
            # assignment still wins a maximising search - a genuinely label-less grid
            # still fabricated `"mEq/L" = 138` instead of leaving the row dropped. This
            # is what actually keeps the column out of contention.
            return 0.0
        variety = min(1.0, self.distinct_count / 3)
        length = min(1.0, self.mean_length / 8)
        shape = 0.6 * variety + 0.4 * length
        # A column that resolves against the analyte vocabulary IS the label
        # column, whatever its shape or position. Shape alone cannot separate
        # "HAE-001" from "Haemoglobin" - both are wordy and both are distinct.
        #
        # This is deliberately a floor, not a blend: a single-row grid ("TSH", one
        # cell) cannot reach a high shape score no matter what it contains - variety
        # tops out at distinct_count/3 - so a column that resolves perfectly still
        # needs the max() to clear THRESHOLD. A fixed-weight blend was tried instead,
        # to also let a low vocab_fraction pull down a same-shaped OCR-garbled
        # fragment's score - and it does that correctly, but it silently failed
        # every single-row report in the training corpus: shape alone could not
        # carry them there, and a partial blend weight could not either. Reverted.
        return (
            max(shape, min(1.0, 0.55 + 0.45 * self.vocab_fraction))
            if self.vocab_fraction > 0
            else shape
        )

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


def _bare_number(cell: str) -> str:
    """The cell with a trailing flag and a trailing unit taken off.

    Both are printed inside the value cell by real labs - "214 H", "12.9 g/dL", and
    occasionally both at once - and neither changes the fact that the column holds
    values. Stripping them before the numeric test is what stops a whole panel being
    typed :attr:`Role.UNKNOWN` and extracting with no readings at all.
    """
    return split_value_unit(split_flag_suffix(cell)[0])[0]


def _serial_run_fraction(filled: list[str]) -> float:
    """The longest run of consecutive-ascending-by-one integers, as a share of the column.

    A printed serial number is exactly this: 7, 8, 9, 10, ... for the whole column. Real
    lab values climb by exactly one between neighbours only by coincidence, and rarely
    for more than a row or two - a WBC differential's "62, 30, 4, 3, 1" never does it
    once; urine microscopy's "2, 3, 0, 0, 1" does it for two rows out of five. Reading
    the longest run (not the count of +1 steps anywhere) is also what survives an OCR
    glitch in the middle of a genuine fifty-row S.No: one bad cell splits one long run
    into two merely-long ones, instead of collapsing a hard numeric_fraction cutoff to
    zero everywhere at once.

    The run must also reach an absolute length of 2 - one genuine +1 step, not just a
    lone value trivially "running" with itself - before it counts for anything. Without
    this floor, any non-empty numeric column with no ascending pair at all (e.g.
    "4400, 198000, 28.4") still reported a phantom 1/n and got dampened for no reason.

    Calibrated against the training corpus, not derived from principle alone: floors of
    2, 3 and 4 were all measured (replay.py --by-layout), and 2 scores the most correct
    values overall. Floor 3 looked safer in isolation - it exempts short microscopy
    grids that floor 2 gives up - but it is worse *in kind* on this corpus: it exempts
    "23, 24" (a two-row S.No fragment, P01-R12) just enough for that fragment to tie a
    genuinely malformed neighbour column at value_score 1.0 and win VALUE on the
    tiebreak, emitting "ESR = 24" - a serial number under a real test name. A wrong
    value under a right label is worse than no value at all, so floor 2's failure mode
    (losing VALUE on a two-row grid like "Pus Cells" 2, "RBC" 3 - a drop, honest and
    visible) is preferred over floor 3's (a fabrication). This is a known, accepted
    trade-off, not a gap: floors 3 and 4 both damp two-row grids that floor 2 does not,
    which is exactly the case they get wrong.
    """
    values = [int(bare) for c in filled if _INT_RE.match(bare := _bare_number(c).strip())]
    if len(values) < 2:
        return 0.0
    longest = current = 1
    for prev, nxt in zip(values, values[1:]):
        current = current + 1 if nxt == prev + 1 else 1
        longest = max(longest, current)
    if longest < 2:
        return 0.0
    return longest / len(filled)


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
                    col, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
                )
            )
            continue
        resolved = sum(1 for c in filled if resolve(c)) / n
        code_like = sum(1 for c in filled if _CODE_RE.match(c.strip())) / n
        serial_run = _serial_run_fraction(filled)
        known_unit = sum(1 for c in filled if _known_unit(c)) / n
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
                serial_run_fraction=serial_run,
                known_unit_fraction=known_unit,
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


def _is_colspan_cell(header: Sequence[str], col: int) -> bool:
    """True when this cell's text is identical to the cell immediately beside it.

    That is the signature of one printed title spanning several columns - "KIDNEY
    FUNCTION TEST" rendered by the OCR into every column beneath it - rather than one
    column's own distinct label. A genuine column header is never identical to its
    immediate neighbour, even when a reused word ("RESULT") appears again for a second,
    glued-on panel several columns away; that is a different column with its own
    legitimate bonus to earn, not part of this run. Checked per cell, not per row: one
    reference range genuinely spanning several sub-columns (three identical
    "BIOLOGICAL REFERENCE INTERVAL" cells) must not blank out a perfectly good
    "RESULT" header two columns over.
    """
    cell = header[col].strip().lower()
    if not cell:
        return False
    left = header[col - 1].strip().lower() if col > 0 else None
    right = header[col + 1].strip().lower() if col + 1 < len(header) else None
    return cell == left or cell == right


def _header_bonus(header: Sequence[str] | None, col: int, role: Role) -> float:
    """Small nudge when the printed header agrees with the content-derived role.

    None where this cell is part of a colspan run (see `_is_colspan_cell`): a title
    merely repeated across several columns is not describing any one of them, so a hint
    word inside it matching by coincidence - "KIDNEY FUNCTION TEST" contains "test" -
    must not hand a bonus to whichever column happens to sit underneath it. That
    coincidence was worth +0.15 to a garbled, non-resolving STATUS column over the
    genuine INVESTIGATION column beside it (vocab_fraction 0 vs. 0.9) on real corpus
    documents, mislabelling every row in the section.
    """
    if header is None or col >= len(header):
        return 0.0
    if _is_colspan_cell(header, col):
        return 0.0
    cell = _norm_header(header[col])
    if not cell:
        return 0.0
    hints = _HEADER_HINTS.get(role, frozenset())
    return HEADER_BONUS if any(h in cell or cell in h for h in hints) else 0.0


def _best_assignment(
    profiles: list[ColumnProfile],
    header: Sequence[str] | None,
    scorers: list[tuple[Role, Callable[[ColumnProfile], float]]],
    *,
    required: frozenset[Role] = frozenset(),
    available: frozenset[int] | None = None,
) -> dict[int, Role]:
    """The highest-scoring way to hand ``scorers``' roles out among ``available`` columns.

    Bounded brute force over each role's top-4 candidates, not every column, so the
    search space stays small (at most ``4**len(scorers)``) without an optimizer
    dependency this codebase does not have. A role in ``required`` may not be left
    unassigned if at least one column clears its threshold - that is how a caller makes
    a role mandatory, not by giving it a bigger number to win a popularity contest with.

    Ties in total score are broken first by which combination is more *decisive* - the
    sum of each assigned role's squared score, favouring a clear 0.9-vs-0.3 split over a
    wishy-washy 0.6-vs-0.6 one. That is still content, read off the same scores the
    search already computed.

    Only once *that* is also tied does column index decide anything: candidates are
    built with a stable sort and the search keeps the first combination it finds at a
    given score (strict ``>``, not ``>=``), so an exact tie on every score this function
    computes resolves to the lowest surviving index. That is a genuine, deliberate last
    resort, not an accidental one - it is what happens when a grid OCR-merges two or
    three real, un-garbled lab panels into one wide row (see I2/`two_column`), so more
    than one column is a fully genuine LABEL candidate for a *different* panel, with
    nothing left in this function's inputs to prefer one panel's phrasing over
    another's. ``vocab_fraction`` was tried as a further tiebreak there and reverted:
    it fixed a real-vs-garbled case correctly (that fix now lives in `_header_bonus`,
    where the false signal actually originates) but actively worsened a real-vs-real
    one, since whichever panel used less standard test-name phrasing would
    systematically lose - a worse bias than the one being removed. Splitting such a
    grid into per-panel sections before role inference ever runs is the real fix, and
    is out of scope here.
    """
    cols = available if available is not None else frozenset(p.index for p in profiles)
    candidates: dict[Role, list[tuple[int, float]]] = {}
    for role, score_of in scorers:
        scored = [
            (p.index, score_of(p) + _header_bonus(header, p.index, role))
            for p in profiles
            if p.index in cols
        ]
        candidates[role] = sorted(
            ((i, s) for i, s in scored if s >= THRESHOLD), key=lambda t: -t[1]
        )[:4]

    order = [r for r, _ in scorers]
    best_key = (-1.0, -1.0)
    best: dict[int, Role] = {}

    def search(
        depth: int, used: frozenset[int], total: float, peak: float, acc: dict[int, Role]
    ) -> None:
        nonlocal best_key, best
        if depth == len(order):
            key = (total, peak)
            if key > best_key:
                best_key, best = key, dict(acc)
            return
        role = order[depth]
        if role not in required or not candidates[role]:
            search(depth + 1, used, total, peak, acc)
        for col, score in candidates[role]:
            if col in used:
                continue
            acc[col] = role
            search(depth + 1, used | {col}, total + score, peak + score * score, acc)
            del acc[col]

    search(0, frozenset(), 0.0, 0.0, {})
    return best


def infer_roles(grid: Grid, *, header_row: int | None = None) -> dict[int, Role]:
    """Assign a role to each column of a result grid.

    Assignment runs in two priority tiers, not one flat contest. LABEL and VALUE go
    first: `_grid_to_section` drops any row with no label outright, so LABEL is required
    whenever some LABEL candidate actually reads like a test name (``vocab_fraction >
    0``), and VALUE is scored alongside it since the two occasionally contest the same
    column. REFERENCE, UNIT, FLAG and CODE are decided second, only among the columns
    LABEL and VALUE left free. Without that ordering nothing stops an unweighted sum
    trading a genuine LABEL column for a false-positive UNIT match elsewhere in the grid
    - a trade that costs one row's unit but, applied to the label, costs the whole row.

    LABEL being *required* is narrower than "some column clears THRESHOLD": a units
    column ("mEq/L", "mg/dL", "g/dL") clears label_score on shape alone - wordy, all
    distinct - with nothing in the grid resolving against the vocabulary, and forcing a
    label onto it fabricated rows like ``"mEq/L" = 138`` on a genuinely label-less grid.
    Requiring at least one real vocabulary match before LABEL becomes mandatory is what
    tells a real test-name column (pH, Nitrite, Ketone - forced, and rightly so) apart
    from a units column wearing the same shape (never forced). A silent drop is a
    missed row; a fabricated value under a unit's name is a wrong one, and wrong is
    worse.

    Within each tier every remaining column contests every role in it and the combination
    with the highest total score wins (see `_best_assignment`). That is what stops a
    serial-number column being read as the result and a method column as the test name,
    without relying on where either column sits - a report printing its columns right to
    left, or a test code sitting left of the test name, is handled the same way.

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

    # Ruling 9: LABEL is hard-required only when some LABEL candidate actually resolves
    # against the analyte vocabulary - not merely because some column's shape clears
    # THRESHOLD. A pure units column ("mEq/L", "mmol/L", "g/dL") is wordy and distinct
    # enough to clear label_score on shape alone with nothing to resolve; requiring it
    # to carry a LABEL anyway fabricates a row rather than dropping one.
    label_candidates_resolve = any(
        p.vocab_fraction > 0
        for p in profiles
        if p.label_score + _header_bonus(header, p.index, Role.LABEL) >= THRESHOLD
    )
    primary = _best_assignment(
        profiles,
        header,
        [(Role.LABEL, lambda p: p.label_score), (Role.VALUE, lambda p: p.value_score)],
        required=frozenset({Role.LABEL}) if label_candidates_resolve else frozenset(),
    )
    roles.update(primary)

    remaining = frozenset(p.index for p in profiles) - frozenset(primary)
    secondary = _best_assignment(
        profiles,
        header,
        [
            (Role.REFERENCE, lambda p: p.reference_score),
            (Role.UNIT, lambda p: p.unit_fraction),
            (Role.FLAG, lambda p: p.flag_score),
            (Role.CODE, lambda p: p.code_score),
        ],
        available=remaining,
    )
    roles.update(secondary)
    return roles


def assignment_strength(grid: Grid, *, header_row: int | None = None) -> float:
    """How convincingly this grid reads as a result table.

    A correctly oriented grid has a confident label column and a confident value
    column; a grid read the wrong way round has neither. Used to choose between
    an orientation and its transpose, so only the two roles that every result
    table must have are counted - units and ranges are often absent.

    A LABEL that resolves against nothing in the analyte vocabulary does not count,
    even when its shape alone clears THRESHOLD. Transposing a genuine tall, narrow
    table turns its many rows into many columns, and with enough columns to choose
    from, the joint search in `infer_roles` reliably finds *some* wordy, distinct
    column to call LABEL and *some* numeric-looking one to call VALUE, on shape
    alone - the wrong reading always has more candidates to gamble with than the
    right one, which has only as many columns as the table has fields. Measured on
    the training corpus: eleven reports this way lost 44 rows they extracted
    correctly before this task, across two_column, ledger_ruled, typewriter_manual,
    boxed_panels, minimal_lines, clean_table, discharge_summary and mixed_print_hand
    - none of them a card layout. In every one of those false positives the wrongly
    oriented reading's LABEL column resolved zero analyte names; requiring at least
    one is the same evidence `infer_roles` itself already leans on to decide LABEL
    is mandatory at all (see Ruling 9), applied here to the *comparison* between
    orientations rather than only within one.
    """
    roles = infer_roles(grid, header_row=header_row)
    rows = list(grid)
    hdr = detect_header_row(rows) if header_row is None else header_row
    profiles = {
        p.index: p for p in profile_columns(rows, skip_rows=(hdr + 1) if hdr is not None else 0)
    }
    label_col = role_of(roles, Role.LABEL)
    value_col = role_of(roles, Role.VALUE)
    if label_col is None or value_col is None:
        return 0.0
    if profiles[label_col].vocab_fraction == 0.0:
        return 0.0
    return profiles[label_col].label_score + profiles[value_col].value_score


def role_of(roles: dict[int, Role], role: Role) -> int | None:
    """Reverse lookup: which column index holds ``role``, if any."""
    for col, assigned in roles.items():
        if assigned is role:
            return col
    return None
