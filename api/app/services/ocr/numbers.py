"""Cell-content primitives: is this text a number, a unit, a range, or a flag?

These are the discriminators column-role inference is built on. They look at *what a
cell contains*, never at what a column header claims, which is what makes the pipeline
work across lab layouts without per-lab configuration.

Nothing here knows what a lab test is. That is deliberate - see docs
`attachment-extraction-engine.md` section 5.
"""

from __future__ import annotations

import re

__all__ = [
    "UNIT_LEXICON",
    "is_numeric",
    "looks_like_bound",
    "looks_like_flag",
    "looks_like_range",
    "looks_like_reference",
    "looks_like_unit",
    "parse_numeric",
    "parse_reference",
    "split_flag_prefix",
    "split_flag_suffix",
    "split_reference_unit",
    "split_value_unit",
]

# 11.2 | 1,200 | 0.5 | -3.2 | 1.2e3 | 4,50,000 (Indian grouping)
_NUMBER = r"[-+]?(?:\d+(?:[, ]\d+)*)(?:\.\d+)?(?:[eE][-+]?\d+)?"
_NUMBER_RE = re.compile(rf"^\s*{_NUMBER}\s*$")

# A unit may be printed inside the reference cell rather than in its own column:
# "35-104 U/L", "<1.2 mg/dL", "6.6-8.7 g/dL". Many labs have no unit column at all,
# so this trailing group is how units get recovered - see split_reference_unit.
_TRAILING_UNIT = r"(?:\s*(?P<unit>[a-zA-Zµμ%][a-zA-Zµμ%0-9./^]{0,14}))?"

# Two-sided ranges: 13.0 - 17.0 | 13.0–17.0 | 0.4 to 4.0 | 35-104 U/L
_RANGE_RE = re.compile(
    rf"^\s*({_NUMBER})\s*(?:-|–|—|~|to)\s*({_NUMBER}){_TRAILING_UNIT}\s*$", re.IGNORECASE
)

# One-sided bounds: < 200 | <=5 | > 40 | ≥ 0.5 | Up to 200 | <1.2 mg/dL
_BOUND_RE = re.compile(
    rf"^\s*(?:<=?|>=?|≤|≥|up\s+to|below|above)\s*({_NUMBER}){_TRAILING_UNIT}\s*$", re.IGNORECASE
)

# Labs print the abnormality marker inside the reference cell rather than in its own
# column: "High 80.00 - 200.00". Anchored range patterns match nothing against that, so
# the flag is peeled off before the range is read - and kept, since it is real data.
#: Longest alternatives first. Alternation is ordered, so a leading H would otherwise
#: match inside "High" and leave "igh" behind as the range.
_LEADING_FLAG_RE = re.compile(
    r"^\s*(Critical\s+High|Critical\s+Low|Critical|Abnormal|Normal|High|Low"
    r"|HH|LL|H|L)\b[\s:.\-]*",
    re.IGNORECASE,
)

# Sex- or age-qualified ranges, which are common on Indian reports and must NOT be
# collapsed into one range here. They are kept raw and resolved against the patient
# at write time.
_QUALIFIED_RE = re.compile(
    r"(male|female|men|women|adult|child|children|neonate|infant|pregnan)\s*[:\-]",
    re.IGNORECASE,
)

# A result column that reads "Negative" is still a result column. These are values,
# not labels, and they must not be mistaken for test names.
_CATEGORICAL_RESULTS = frozenset(
    {
        "positive",
        "negative",
        "reactive",
        "nonreactive",
        "non reactive",
        "detected",
        "not detected",
        "present",
        "absent",
        "nil",
        "normal",
        "abnormal",
        "trace",
        "seen",
        "not seen",
        "clear",
        "turbid",
    }
)

# Flags a lab prints beside an out-of-range value.
_FLAGS = frozenset({"h", "l", "hh", "ll", "n", "a", "*", "**", "↑", "↓", "+", "-", "++"})

#: Units seen on Indian outpatient lab reports. Sourced from the default_unit and
#: alt_units columns of `config.lab_analytes` in lab_analytes_seed.sql, plus casing
#: and spacing variants. Matching is done on a normalised form, so "MG/DL" hits.
UNIT_LEXICON = frozenset(
    {
        # haematology
        "g/dl",
        "g/l",
        "mil/ul",
        "10^12/l",
        "10^6/ul",
        "%",
        "fl",
        "pg",
        "/ul",
        "10^9/l",
        "10^3/ul",
        "cells/ul",
        "mm/hr",
        "mm/1hr",
        "/hpf",
        "/lpf",
        # chemistry
        "mg/dl",
        "mmol/l",
        "umol/l",
        "u/l",
        "iu/l",
        "mg/l",
        "ug/dl",
        "ug/l",
        "ng/dl",
        "ng/ml",
        "pg/ml",
        "uiu/ml",
        "miu/l",
        "iu/ml",
        "uiu/l",
        "nmol/l",
        "pmol/l",
        "mmol/mol",
        "meq/l",
        "mosm/kg",
        "ml/min/1.73m2",
        "ml/min",
        "mg/g",
        "mg/gm",
        "mg/24hr",
        "g/24hr",
        # dimensionless
        "ratio",
        "index",
        "ph",
        "sec",
        "seconds",
        "titre",
        "score",
        "cop",
        "s/co",
        "au/ml",
        "ku/l",
        "copies/ml",
    }
)

# A unit we have never seen still looks like a unit: letters, optional slashes,
# optional exponents, no sentence structure. Deliberately conservative.
_UNIT_SHAPE_RE = re.compile(
    r"^\s*(?:%|µ|μ)?[a-zµμ]{1,10}"
    r"(?:\^?\d+)?"
    r"(?:\s*/\s*(?:\d+\.?\d*)?[a-zµμ0-9.^]{1,12}){0,3}\s*$",
    re.IGNORECASE,
)


def _norm(text: str) -> str:
    """Lowercase, collapse whitespace, strip micro-sign variants to a common form."""
    return re.sub(r"\s+", "", text.strip().lower()).replace("µ", "u").replace("μ", "u")


def is_numeric(text: str) -> bool:
    """True when the cell is a bare number, with no comparator or range.

    Bare numbers are the strongest signal for a value column. Bounds like ``<0.01``
    are excluded here on purpose - they are scored separately, because they appear
    in both value and reference columns.
    """
    return bool(_NUMBER_RE.match(text)) if text.strip() else False


def parse_numeric(text: str) -> float | None:
    """Parse a bare number, tolerating thousands separators.

    Returns:
        The value, or ``None`` when the cell is not a bare number. A comparator-bounded
        cell such as ``<0.01`` returns ``None`` deliberately: the raw text is kept and a
        human decides, because a below-detection-limit result is not the number 0.01.
    """
    if not is_numeric(text):
        return None
    try:
        return float(text.strip().replace(",", "").replace(" ", ""))
    except ValueError:  # pragma: no cover - guarded by is_numeric
        return None


def split_flag_prefix(text: str) -> tuple[str | None, str]:
    """Peel an abnormality marker off the front of a cell.

    ``High 80.00 - 200.00`` is a reference range with a flag glued to it. Returning both
    keeps the flag - which is genuine clinical information - while letting the range
    patterns see what they expect.

    Args:
        text: The cell as printed.

    Returns:
        ``(flag, remainder)``. ``flag`` is ``None`` when the cell does not start with a
        marker, and the remainder is then the original text.
    """
    match = _LEADING_FLAG_RE.match(text)
    if not match:
        return None, text
    remainder = text[match.end() :].strip()
    # A cell that is *only* a flag is a flag, not a range with a flag on it.
    return (match.group(1), remainder) if remainder else (None, text)


def looks_like_range(text: str) -> bool:
    """True for a two-sided reference range such as ``13.0 - 17.0``.

    Tolerates a leading abnormality marker, since some labs print the flag inside the
    reference cell.
    """
    return bool(_RANGE_RE.match(split_flag_prefix(text)[1]))


def looks_like_bound(text: str) -> bool:
    """True for a one-sided bound such as ``< 200`` or ``> 40``.

    A weaker reference signal than :func:`looks_like_range`, because value columns
    legitimately carry bounds for below-detection-limit results.
    """
    return bool(_BOUND_RE.match(split_flag_prefix(text)[1]))


def looks_like_qualified_range(text: str) -> bool:
    """True for a sex- or age-qualified range such as ``Male: 13-17 Female: 12-15``.

    Common on Indian reports and a strong reference-column signal, even though the range
    itself cannot be resolved without knowing the patient.
    """
    return bool(_QUALIFIED_RE.search(text))


def looks_like_reference(text: str) -> bool:
    """True for anything that reads as a reference range, including qualified ones."""
    return looks_like_range(text) or looks_like_bound(text) or looks_like_qualified_range(text)


def parse_reference(text: str) -> tuple[float | None, float | None] | None:
    """Split a reference range into ``(low, high)``.

    Returns:
        ``(low, high)`` for a two-sided range, ``(None, high)`` or ``(low, None)`` for a
        one-sided bound, and ``None`` when the range cannot be resolved without knowing
        the patient - a sex- or age-qualified range is kept raw rather than guessed at.
    """
    if _QUALIFIED_RE.search(text):
        return None
    text = split_flag_prefix(text)[1]
    if m := _RANGE_RE.match(text):
        return parse_numeric(m.group(1)), parse_numeric(m.group(2))
    if m := _BOUND_RE.match(text):
        value = parse_numeric(m.group(1))
        lowered = text.strip().lower()
        if lowered.startswith((">", "≥", "above")):
            return value, None
        return None, value
    return None


def split_reference_unit(text: str) -> tuple[str, str | None]:
    """Separate a reference cell into its range and any unit printed inside it.

    Many Indian lab reports print no unit column at all - the unit rides along in the
    reference cell as ``35-104 U/L``. Recovering it here is the only way those rows get
    a unit, and a value without a unit is not safe to trend.

    Args:
        text: The reference cell as printed.

    Returns:
        ``(range_text, unit)``, where ``unit`` is ``None`` when none was printed. The
        range text is returned with the unit stripped, so downstream parsing is
        unaffected by which layout the lab used.
    """
    text = split_flag_prefix(text)[1]
    for pattern in (_RANGE_RE, _BOUND_RE):
        match = pattern.match(text)
        if match:
            unit = match.groupdict().get("unit")
            if unit and looks_like_unit(unit):
                return text[: match.start("unit")].strip(), unit.strip()
            return text.strip(), None
    return text.strip(), None


# A value with its unit in the same cell: "12.9 g/dL", "268000 /uL", "39.1 %".
# Deliberately NOT _TRAILING_UNIT, which requires the unit to begin with a letter and so
# misses the very common "/uL" and "/hpf" forms.
_VALUE_UNIT_RE = re.compile(
    rf"^\s*(?P<value>{_NUMBER})\s*(?P<unit>[a-zA-Zµμ%/][a-zA-Zµμ%0-9./^]{{0,19}})\s*$"
)


def split_value_unit(text: str) -> tuple[str, str | None]:
    """Separate a bare value from a unit printed in the same cell.

    Many Indian labs print no unit column and write ``12.9 g/dL`` in the value cell. The
    column profiler asks whether a cell is a bare number, so a column of these scored
    zero, was typed :attr:`Role.UNKNOWN`, and every reading on the panel was dropped -
    the same failure the trailing-flag split already guards against for ``214 H``.

    Ranges and bounds are left alone on purpose: ``35-104 U/L`` is a reference cell and
    belongs to :func:`split_reference_unit`, which already handles it.

    Args:
        text: The cell as printed.

    Returns:
        ``(value, unit)``, or ``(text, None)`` when the cell is not a bare number
        followed by something that reads as a unit.
    """
    stripped = text.strip()
    if not stripped or is_numeric(stripped):
        return stripped, None
    if looks_like_range(stripped) or looks_like_bound(stripped):
        return stripped, None
    match = _VALUE_UNIT_RE.match(stripped)
    if not match:
        return stripped, None
    value, unit = match.group("value").strip(), match.group("unit").strip()
    # "214 H" is a high result, not 214 hectares. The unit shape heuristic accepts a bare
    # letter, and H/L/N/M are the commonest abnormality markers printed after a value -
    # 515 such cells in the corpus. split_flag_suffix owns this shape; treating one as a
    # unit would file the marker under unit and lose the flag.
    if looks_like_flag(unit):
        return stripped, None
    # A lone letter is a marker, an initial or noise - never a measurement. The shape
    # heuristic accepts one, so stray column markers ("22.4 M") would become units.
    # Every real unit in the lexicon is multi-character or "%", so this closes the class
    # rather than the particular letters this corpus happens to contain.
    if len(unit) == 1 and unit.lower() not in UNIT_LEXICON:
        return stripped, None
    if is_numeric(value) and looks_like_unit(unit):
        return value, unit
    return stripped, None


def looks_like_unit(text: str) -> bool:
    """True when the cell reads as a measurement unit.

    Checks the lexicon first, then falls back to a shape heuristic so a unit we have
    never seen is still recognised. Bare numbers and known categorical results are
    excluded, since both would otherwise pass the shape test.
    """
    stripped = text.strip()
    if not stripped or len(stripped) > 20:
        return False
    normalised = _norm(stripped)
    if normalised in UNIT_LEXICON:
        return True
    if normalised in _CATEGORICAL_RESULTS or is_numeric(stripped):
        return False
    return bool(_UNIT_SHAPE_RE.match(stripped))


#: A flag printed AFTER the value, which is how most Indian labs mark an
#: abnormal result: "214 H", "34 L", "9.6 H*". The space is optional because a
#: reading model merges the two cells when the flag sits in its own narrow
#: column with no border.
_TRAILING_FLAG_RE = re.compile(
    r"^(?P<value>.*?[0-9.\)])\s*(?P<flag>H{1,2}|L{1,2}|N|A|\*{1,2}|↑|↓)$"
)


def split_flag_suffix(text: str) -> tuple[str, str | None]:
    """Peel an abnormality marker off the END of a cell.

    Returns ``(value, flag)``, and the value unchanged when there is no flag.

    Worth its own function because of what happened without it. A column of
    "214 H", "298 H", "9.6 H" is not numeric to is_numeric, so its numeric
    fraction collapses and the column is classified 'unknown' rather than
    'value'. Every row then extracts with no value at all, and the adapter
    drops it - so a DIABETES PROFILE and a LIPID PROFILE vanished from a
    report entirely while the RENAL panel beside them came through perfectly,
    for the single reason that the renal results were all normal and carried
    no flags.

    An abnormal result is the one a doctor most needs to see. Losing exactly
    those is the worst failure this parser can have.
    """
    match = _TRAILING_FLAG_RE.match(text.strip())
    if match is None:
        return text, None
    return match.group("value").strip(), match.group("flag")


def looks_like_flag(text: str) -> bool:
    """True for an abnormality marker such as ``H``, ``L`` or ``*``.

    Empty cells count as flag-like: a flag column is mostly blank by nature, which is
    exactly what distinguishes it from a label column.
    """
    stripped = text.strip()
    return not stripped or _norm(stripped) in _FLAGS


def is_categorical_result(text: str) -> bool:
    """True for a non-numeric result such as ``Negative`` or ``Not Detected``."""
    return _norm(text).replace(" ", "") in {_norm(v) for v in _CATEGORICAL_RESULTS}
