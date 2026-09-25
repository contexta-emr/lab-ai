# api/app/services/ocr/labels.py
"""Separate a printed test label into the parts a lab glued together.

LOINC describes an observation on six axes. Three of them arrive in one cell on
real reports: the COMPONENT ("Creatinine"), the SYSTEM ("Sr.", the specimen) and
the METHOD ("Modified Jaffe, kinetic"). Units are not an axis but are printed in
the label just as often.

Two things are ever taken off ``name``: a trailing unit in brackets, and an
assay method with no brackets of its own (glued straight onto the name, or on
its own "Method: X" line). A bracket that is *not* a unit is never removed -
"Creatinine (Sr.)" and "Creatinine (Pl.)" are different observations, and
merging them would plot one trend line through two analytes. When that kept
bracket is itself a known assay method ("TSH (CLIA)", "HBSAG (ELISA)"), the
method is still recorded, just without touching ``name``: a bracketed method
does not block resolution the way a unit does (``synonyms.resolve`` already
calls ``split_method_suffix`` itself, so ``resolve("TSH (CLIA)")`` needs no
help from this module), so there is no reason to trade the printed label for
the method metadata when both are available for free.

Order is load-bearing. ``synonyms.split_method_suffix`` only cuts when what
remains resolves exactly, and a name still carrying "(mg/dL)" resolves against
nothing. Unit first, then method.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .numbers import UNIT_LEXICON
from .synonyms import METHOD_TERMS, load_synonyms, normalise_label, split_method_suffix

__all__ = ["LabelParts", "split_label"]

#: Lexicon membership ONLY - deliberately not ``looks_like_unit``. That function
#: falls back to a shape heuristic for units it has never seen, which is right in
#: a unit column (where the context guarantees the cell is a unit) and wrong here
#: (where it guarantees nothing). Measured: the fallback calls "Total", "Serum",
#: "CLIA", "Free" and "Direct" units, so it would cut "Cholesterol (Total)" down
#: to "Cholesterol" and "Creatinine (Serum)" to "Creatinine" - throwing away the
#: LOINC COMPONENT and SYSTEM axes and merging serum with plasma.
#:
#: Failing closed costs nothing: an unseen unit stays in the label, which is
#: exactly today's behaviour.
#:
#: Lexicon membership alone is not quite enough, though: "pH" is a genuine unit
#: (a blood-gas pH column reads "pH") but it is also the analyte dictionary's own
#: synonym for urine UR_PH, printed on real reports as "Reaction (pH)" - the
#: parenthesis is the qualifier, not a unit, exactly like "Creatinine (Sr.)".
#: Measured: treating it as a unit corpus-wide turned 17 correctly-labelled
#: "Reaction (pH)" rows into "Reaction", which no longer matches the printed
#: label. A word that is itself a resolvable analyte synonym is a name, not a
#: unit, so it is excluded here rather than removed from ``UNIT_LEXICON``, which
#: other columns still need it for.
#:
#: This exclusion is coupled to the seed, not just to "pH": if a synonym is
#: ever added for "Ratio", "Index", "Score" or "Titre" - all in
#: UNIT_LEXICON's dimensionless section already - unit-stripping silently
#: stops working for that word the same way it just did for "pH". Checked
#: all 54 UNIT_LEXICON entries against the 662-row seed; "ph" is currently
#: the only collision.
def _is_unit(text: str) -> bool:
    key = re.sub(r"\s+", "", text.strip().lower())
    if key not in UNIT_LEXICON:
        return False
    return not load_synonyms().get(normalise_label(text))

#: A trailing parenthesised group, which is where labs put the unit when there is
#: no unit column. Anchored to the end: "Vitamin B-12 (Cyanocobalamin) (pg/mL)"
#: must give up only the last group.
_TRAILING_GROUP_RE = re.compile(r"^(?P<name>.*\S)\s*[(\[](?P<inner>[^()\[\]]{1,20})[)\]]\s*$")

#: The method sub-line, after a real or literal newline. Labs print "Method: X",
#: "Method - X" or just the method under the name; only the labelled forms are
#: safe to cut without a vocabulary check.
_METHOD_LINE_RE = re.compile(
    r"(?:\\n|\n|\r)\s*(?:method|technique)\s*[:\-]\s*(?P<method>.+)$",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class LabelParts:
    """A printed label split into the name, and whatever was glued onto it."""

    name: str
    unit: str | None = None
    method: str | None = None


def split_label(text: str) -> LabelParts:
    """Split a printed label into name, unit and method.

    Args:
        text: The label exactly as printed, possibly carrying a unit and a method.

    Returns:
        The parts. Anything not confidently identified stays in ``name``.
    """
    name = (text or "").strip()
    if not name:
        return LabelParts(name=name)

    method: str | None = None
    found = _METHOD_LINE_RE.search(name)
    if found:
        method = found.group("method").strip().rstrip(".")
        name = name[: found.start()].strip()

    unit: str | None = None
    kept_qualifier = False
    group = _TRAILING_GROUP_RE.match(name)
    if group:
        # _TRAILING_GROUP_RE's name group is `.*\S` - it cannot match on an
        # empty stem, so there is always something left to call the test
        # once the regex has matched at all.
        inner = group.group("inner").strip()
        stem = group.group("name").strip()
        if _is_unit(inner):
            unit, name = inner, stem
        else:
            # A bracket we deliberately did not strip - "(Sr.)", "(pH)",
            # "(ELISA)" - is the analyte's own printed identity, not an
            # appended note, so it stays on `name` exactly as printed and is
            # never handed to split_method_suffix below (the corpus prints
            # the same HBSAG test as "HBSAG (ELISA)" on one report and
            # "HBsAg" on another, and "ELISA" is a real METHOD_TERMS entry -
            # re-examining the kept bracket would strip it for the same
            # wrong reason stripping "(Sr.)" off "Creatinine (Sr.)" would be).
            #
            # It can still BE a known assay method, though, and unlike a
            # unit it does not need to leave `name` to be useful: record it
            # as the method too, so "TSH (CLIA)" keeps both the printed
            # label and the fact that it was CLIA, not immunoassay.
            kept_qualifier = True
            if method is None and normalise_label(inner) in METHOD_TERMS:
                method = inner

    if method is None and not kept_qualifier:
        name, method = split_method_suffix(name)

    return LabelParts(name=name, unit=unit, method=method)
