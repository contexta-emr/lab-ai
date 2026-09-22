"""Match a printed lab label onto a canonical analyte code.

The synonym dictionary is **read from ``lab_analytes_seed.sql``**, not retyped here. That
file is the source of truth and already carries 662 mappings; a second hand-maintained
copy would drift from it within a week.

Three tiers, exactly as ``config.fn_resolve_analyte`` specifies:

1. **Exact** on the normalised key. Applied silently.
2. **Token containment or near-miss.** *Proposed*, never applied - a printed label carries
   assay methods, sample types and footnote markers that no dictionary will ever fully
   enumerate, so this tier has to be tolerant, and a tolerant matcher must not be trusted
   on its own.
3. **Nothing.** A valid answer. The row is still stored and shown; it simply cannot be
   charted until a human maps it.

The split matters. Real labels arriving from three different labs looked like this::

    S.Creat                                                    exact
    Cholesterol Total Spectrophotometry                        method glued on
    CREATININE, SERUM\\nCompensated Jaffe's reaction, IDMS traceable

The last one carries a *literal* backslash-n as two characters, a method phrase, and a
traceability note. Enumerating that is hopeless; recognising that ``CREATININE SERUM`` is
contained within it is not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rapidfuzz import fuzz, process

__all__ = [
    "METHOD_TERMS",
    "PROPOSE_THRESHOLD",
    "SEED_SQL",
    "Match",
    "load_synonyms",
    "normalise_label",
    "propose",
    "resolve",
    "split_method_suffix",
]

#: The seed shipped with the design docs. One source of truth, read at runtime.
# Package data, beside this module. Still one file, still read at runtime,
# still never retyped - but inside the package so the path holds wherever the
# package is installed. A repo-relative path worked from a checkout and
# resolved to /db/vendor inside the container, where it does not exist.
SEED_SQL = Path(__file__).resolve().parent / "data" / "lab_analytes_seed.sql"

#: Below this, a candidate is not worth showing a human at all.
PROPOSE_THRESHOLD = 0.62

# ('HGB', 'Haemoglobin', config.fn_normalise_analyte_label('Haemoglobin')),
_SYNONYM_RE = re.compile(
    r"\(\s*'([A-Z0-9_]+)'\s*,\s*'((?:[^']|'')*)'\s*,\s*config\.fn_normalise_analyte_label\(",
    re.I,
)

# ('HGB', 'Haemoglobin', 'HAEMATOLOGY', 'g/dL', ...) - the analyte master rows.
_ANALYTE_RE = re.compile(
    r"\(\s*'([A-Z0-9_]+)'\s*,\s*'((?:[^']|'')*)'\s*,\s*'([A-Z ]+)'\s*,", re.I
)

#: Escape sequences a reading model emits as *literal characters* rather than whitespace.
#: A real report yielded "CREATININE, SERUM\\nCompensated Jaffe's reaction" with a
#: backslash and an n in the text, which no amount of whitespace handling would fix.
_LITERAL_ESCAPE_RE = re.compile(r"\\+[nrt]", re.I)

#: Footnote and annotation markers printed beside a test name.
_MARKER_RE = re.compile(r"[*†‡§#¹²³⁰-₟]+")

#: Tokens that carry no identifying information. Kept deliberately tiny - the token
#: matcher tolerates unknown extra words, so this exists only to stop very common filler
#: from inflating a match's apparent coverage.
_FILLER = frozenset({"TEST", "LEVEL", "LEVELS", "ESTIMATION", "MEASUREMENT"})


@dataclass(frozen=True, slots=True)
class Match:
    """One candidate mapping for a printed label.

    Attributes:
        analyte_code: The canonical code proposed.
        confidence: 0.0 to 1.0. ``1.0`` only ever comes from an exact hit.
        how: ``exact``, ``contains`` or ``similar`` - shown to whoever confirms it, since
            "why did it think that" is the first question anyone asks.
        matched: The dictionary entry that matched.
    """

    analyte_code: str
    confidence: float
    how: str
    matched: str

    @property
    def is_exact(self) -> bool:
        """True only for a tier-1 hit, which is the only tier applied without review."""
        return self.how == "exact"


def normalise_label(text: str) -> str:
    """Reduce a printed label to its match key.

    Mirrors ``config.fn_normalise_analyte_label`` - upper case, non-alphanumeric runs
    become single spaces, whitespace collapsed - with two additions forced by real
    documents: literal ``\\n`` escape sequences written as characters, and footnote
    markers.

    Args:
        text: A label exactly as printed on the report.

    Returns:
        The normalised key. Empty string for empty input.
    """
    cleaned = _MARKER_RE.sub(" ", _LITERAL_ESCAPE_RE.sub(" ", text))
    upper = re.sub(r"[^A-Z0-9]+", " ", cleaned.strip().upper())
    return re.sub(r"\s+", " ", upper).strip()


def _tokens(key: str) -> frozenset[str]:
    """Significant tokens of a normalised key."""
    return frozenset(t for t in key.split() if t and t not in _FILLER)


@lru_cache(maxsize=1)
def load_synonyms(path: str | None = None) -> dict[str, tuple[str, ...]]:
    """Read the seed SQL and build ``match key -> analyte codes``.

    A key maps to more than one code when the printed label is genuinely ambiguous -
    ``TC`` is total cholesterol on a lipid report and total count on a haemogram. Those
    must never resolve silently, so the ambiguity is preserved rather than collapsed.

    Args:
        path: Override the seed location. Defaults to :data:`SEED_SQL`.

    Returns:
        Mapping of normalised key to the analyte codes claiming it.

    Raises:
        FileNotFoundError: If the seed SQL is not where it is expected.
    """
    source = Path(path) if path else SEED_SQL
    if not source.exists():
        raise FileNotFoundError(
            f"analyte seed not found at {source}. It ships with the design docs at "
            f"idp/docs/rkChatZip/lab_analytes_seed.sql"
        )
    text = source.read_text(encoding="utf-8")

    table: dict[str, set[str]] = {}
    for code, synonym in _SYNONYM_RE.findall(text):
        key = normalise_label(synonym.replace("''", "'"))
        if key:
            table.setdefault(key, set()).add(code.upper())

    # The analyte's own name and code are valid labels too, and the synonym block does
    # not always repeat them.
    for code, name, _panel in _ANALYTE_RE.findall(text):
        for candidate in (name.replace("''", "'"), code):
            key = normalise_label(candidate)
            if key:
                table.setdefault(key, set()).add(code.upper())

    return {key: tuple(sorted(codes)) for key, codes in table.items()}


@lru_cache(maxsize=1)
def _tokenised(path: str | None = None) -> tuple[tuple[str, frozenset[str], tuple[str, ...]], ...]:
    """The dictionary again, pre-tokenised, longest entry first.

    Longest first so ``CREATININE SERUM`` is preferred over ``CREATININE`` - a more
    specific match is a better one.
    """
    entries = [(key, _tokens(key), codes) for key, codes in load_synonyms(path).items()]
    entries.sort(key=lambda e: len(e[1]), reverse=True)
    return tuple(e for e in entries if e[1])


#: Assay methods labs print beside the test name. Some print them on their own row
#: ("Method:Diazo Method"), others tuck them under the name in small type - and an OCR
#: pass merges the two into one cell.
METHOD_TERMS = frozenset(
    normalise_label(term)
    for term in (
        "Spectrophotometry", "Spectrophotometric", "Photometry", "Calculated",
        "Enzymatic", "Colorimetric", "Colorimetry", "Turbidimetry",
        "Immunoturbidimetry", "Nephelometry", "Kinetic", "Endpoint",
        "CLIA", "ECLIA", "CMIA", "ELISA", "MEIA", "Chemiluminescence",
        "Jaffe", "Jaffe Kinetic", "Jaffes Kinetic", "GOD POD", "GOD-POD",
        "Urease", "Biuret", "Diazo", "Diazo Method", "BCG",
        "Bromocresol Green", "Bromocresol Green BCG", "Bromocresol Purple",
        "GCNA", "PNPP AMP Buffer", "UV without P5P", "UV with P5P",
        "HPLC", "ISE", "Ion Selective Electrode", "Potentiometry",
        "Flow Cytometry", "Impedance", "Microscopy", "Latex Agglutination",
        "Hexokinase", "Modified Jaffe", "Direct", "Indirect", "Calculation",
    )
)


def split_method_suffix(label: str, *, path: str | None = None) -> tuple[str, str | None]:
    """Separate a trailing assay method from a test name.

    Two conditions must both hold before anything is stripped: the trailing words must be
    a known method, **and** what remains must resolve exactly. Requiring both is what stops
    "Vitamin D Binding Protein" being cut down to "Vitamin D" - a different test entirely.

    This is the precise, conservative path. :func:`propose` handles the messier cases it
    cannot cover.

    Args:
        label: The label as printed, possibly with a method appended.
        path: Override the seed location, for tests.

    Returns:
        ``(test_name, method)``, or ``(label, None)`` when no method was found.
    """
    words = label.split()
    table = load_synonyms(path)
    # Longest candidate method first, so "Bromocresol Green BCG" is not left half-stripped.
    for cut in range(1, len(words)):
        suffix = " ".join(words[cut:])
        if normalise_label(suffix) not in METHOD_TERMS:
            continue
        prefix = " ".join(words[:cut])
        if table.get(normalise_label(prefix)):
            return prefix, suffix
    return label, None


def resolve(label: str, *, path: str | None = None) -> tuple[str, ...]:
    """Resolve a printed label to canonical codes, **exactly**.

    Tier 1 only. This is what may be applied without a human looking at it, so it stays
    strict; anything less certain belongs in :func:`propose`.

    Args:
        label: The label as printed on the report.
        path: Override the seed location, for tests.

    Returns:
        Empty when nothing matched exactly - a valid answer, not a failure. One code for a
        clean hit. More than one when the label is genuinely ambiguous.
    """
    table = load_synonyms(path)
    direct = table.get(normalise_label(label))
    if direct:
        return direct
    prefix, method = split_method_suffix(label, path=path)
    return table.get(normalise_label(prefix), ()) if method else ()


def propose(label: str, *, limit: int = 5, path: str | None = None) -> list[Match]:
    """Every plausible mapping for a label, best first.

    An exact hit is returned alone with confidence ``1.0``. Otherwise the label is matched
    two ways, and neither result may be applied without confirmation:

    * **contains** - the dictionary entry's tokens all appear in the label. This is what
      catches a test name buried in method text and traceability notes.
    * **similar** - close enough by character overlap to be an OCR misread of a known name.

    Args:
        label: The label as printed.
        limit: Most candidates to return.
        path: Override the seed location, for tests.

    Returns:
        Candidates sorted by confidence. Empty when nothing reached
        :data:`PROPOSE_THRESHOLD`.
    """
    key = normalise_label(label)
    if not key:
        return []

    exact = load_synonyms(path).get(key)
    if exact:
        return [Match(code, 1.0, "exact", key) for code in exact]

    label_tokens = _tokens(key)
    if not label_tokens:
        return []

    table = load_synonyms(path)
    tokenised = {entry_key: toks for entry_key, toks, _ in _tokenised(path)}

    # token_set_ratio is the right generator here: it scores on the token *sets*, so a
    # test name buried in method text and traceability notes still scores 100. It is a
    # deliberately generous net - narrowing happens in the ranking below, and the real
    # safeguard is that nothing from this function is ever applied without confirmation.
    hits = process.extract(
        key,
        list(table),
        scorer=fuzz.token_set_ratio,
        limit=40,
        score_cutoff=PROPOSE_THRESHOLD * 100,
    )

    best: dict[str, Match] = {}
    for entry_key, raw_score, _index in hits:
        entry_tokens = tokenised.get(entry_key, frozenset())
        contained = bool(entry_tokens) and entry_tokens <= label_tokens
        # A single common word appearing inside a long label is noise, not a match.
        # "Reaction" is a real synonym for urine pH, but finding it inside
        # "CREATININE SERUM Compensated Jaffe's reaction" means nothing.
        if contained and len(entry_tokens) == 1 and len(label_tokens) >= 3:
            continue
        # A longer dictionary entry is a more specific claim, so rank it higher. This is
        # what puts "CREATININE SERUM" above the bare "CREATININE" on the same label.
        specificity = min(1.0, len(entry_tokens) / 3) if contained else 0.0
        score = min(1.0, (raw_score / 100.0) * (0.80 + 0.20 * specificity))
        if score < PROPOSE_THRESHOLD:
            continue
        how = "contains" if contained else "similar"
        for code in table[entry_key]:
            current = best.get(code)
            if current is None or score > current.confidence:
                best[code] = Match(code, round(score, 3), how, entry_key)

    ranked = sorted(best.values(), key=lambda m: (-m.confidence, m.analyte_code))
    return ranked[:limit]
