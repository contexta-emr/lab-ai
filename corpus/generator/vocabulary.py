"""One place to ask what an analyte is called, whatever list it came from.

THE PROBLEM THIS SOLVES
    There are two vocabularies and both are legitimate.

    catalog.py is what the 300-report corpus PRINTS. It is frozen by
    construction: build.py renders a declared panel by iterating
    PANELS[code]["analytes"], so adding one analyte there prints a new row on
    every existing report and invalidates the sealed answer key.

    benchmark_30.py is what the 30-panel benchmark says we should RECOGNISE -
    seventy analytes the corpus never prints, seeded into the database so a real
    report containing them can be read.

    A dummy corpus that exercises the new vocabulary needs to print from the
    second list using the machinery built for the first. So this module answers
    the generator's questions - what is this called, what unit, what range, what
    analytes are in this panel - against catalog first and benchmark second.

WHY CATALOG WINS ON A TIE
    Not arbitrary: catalog's entry is the one the 300 PDFs were rendered from,
    and the sealed answer key records those labels. If the benchmark shadowed an
    existing definition, the key would describe a page that no longer renders
    that way. New vocabulary is additive or it is not safe.

WHAT IT DELIBERATELY DOES NOT DO
    Reference ranges. catalog.ref() knows sex and age bands for the analytes the
    corpus prints; the benchmark document states no intervals at all, and section
    5 is explicit that a universal normal range should not be hard-coded. So a
    benchmark analyte renders with whatever reference the report spec gives it,
    and an empty one when it gives none - which is what a real report does for a
    qualitative result anyway.
"""

from __future__ import annotations

import sys
from pathlib import Path

import catalog as C

# db/seed sits outside the generator package; it is the SEED's home, and the
# benchmark data belongs with the seed rather than with the corpus.
_SEED = Path(__file__).resolve().parents[2] / "db" / "seed"
if str(_SEED) not in sys.path:
    sys.path.insert(0, str(_SEED))

import benchmark_30 as B  # noqa: E402


#: code -> the benchmark's tuple, for the seventy analytes catalog does not have.
_BENCH = {code: (name, syn, unit, vtype, calc, specimen)
          for code, name, syn, unit, vtype, calc, specimen in B.ANALYTES}

#: panel code -> analyte codes, in the benchmark's own order.
_BENCH_PANELS: dict[str, list[str]] = {}
for _panel, _code, _role in B.MEMBERS:
    _BENCH_PANELS.setdefault(_panel, []).append(_code)


def known(code: str) -> bool:
    """Is this code in either vocabulary?"""
    return code in C.ANALYTES or code in _BENCH


def labels(code: str) -> list[str]:
    """Every spelling, catalog's first.

    The generator picks one by index - spec["alias"] - so the ORDER is part of
    the corpus's behaviour and must not change for an existing code.
    """
    if code in C.ANALYTES:
        return C.ANALYTES[code]["labels"]
    if code in _BENCH:
        name, syn, *_ = _BENCH[code]
        return [name, *syn]
    return [code]


def unit(code: str) -> str:
    if code in C.ANALYTES:
        return C.ANALYTES[code]["unit"]
    return _BENCH[code][2] if code in _BENCH else ""


def value_type(code: str) -> str:
    """numeric, ordinal, coded, reactive, organism, susceptibility, narrative...

    catalog predates the distinction and is numeric throughout except where a
    report spec passes a string value. The benchmark states it per analyte, and
    it is what tells the renderer not to right-align 'Non-reactive' as if it
    were a measurement.
    """
    if code in C.ANALYTES:
        return "numeric"
    return _BENCH[code][3] if code in _BENCH else "numeric"


def fmt(code: str, value) -> str:
    """Format a value the way this analyte is printed.

    Strings pass through untouched - a blood group, an organism name and a
    susceptibility are text and formatting them as numbers is nonsense.
    """
    if isinstance(value, str) or value is None:
        return "" if value is None else value
    if code in C.ANALYTES:
        return C.fmt(code, value)
    return f"{value:g}"


def reference(code: str, sex: str = "M", age: int = 40) -> str:
    """The printed interval, or empty.

    Only catalog knows intervals, and only for its own analytes. The benchmark
    states none - its section 5 says not to hard-code a universal normal range,
    and inventing one here to fill a column would be exactly that.
    """
    if code in C.ANALYTES:
        return C.ref(code, sex, age)
    return ""


def flag(code: str, value, sex: str = "M", age: int = 40) -> str:
    """H, L or nothing. Only meaningful where an interval exists."""
    if code in C.ANALYTES and not isinstance(value, str):
        return C.flag(code, value, sex, age)
    return ""


def panel_titles(panel: str) -> list[str]:
    if panel in C.PANELS:
        return C.PANELS[panel]["titles"]
    display = next((d for c, d, _n, _k in B.PANELS if c == panel), panel)
    return [display, *B.PANEL_ALIASES.get(panel, [])]


def panel_analytes(panel: str) -> list[str]:
    """The analytes of a panel, catalog's definition winning where both have one.

    Catalog wins because its member list is what the 300 reports were rendered
    from. A benchmark panel that catalog has never heard of - URINE_CULT,
    HIV_PANEL - comes back from the benchmark, which is the whole point.
    """
    if panel in C.PANELS:
        return C.PANELS[panel]["analytes"]
    return _BENCH_PANELS.get(panel, [])


def panel_known(panel: str) -> bool:
    return panel in C.PANELS or panel in _BENCH_PANELS


def demo() -> None:
    """Runnable check: catalog is unchanged, and the benchmark is reachable."""
    # An existing analyte must answer exactly as catalog does, or the 300
    # reports would render differently through this layer than without it.
    for code in ("HGB", "UR_PROT", "EGFR", "BLOOD_GROUP"):
        assert labels(code) == C.ANALYTES[code]["labels"], code
        assert unit(code) == C.ANALYTES[code]["unit"], code
        assert reference(code, "F", 30) == C.ref(code, "F", 30), code
    assert panel_analytes("CBC") == C.PANELS["CBC"]["analytes"]
    assert panel_titles("CBC") == C.PANELS["CBC"]["titles"]

    # And the new vocabulary has to be visible.
    assert known("CULT_SIR") and not (("CULT_SIR") in C.ANALYTES)
    assert value_type("CULT_SIR") == "susceptibility"
    assert value_type("HIV_SCREEN") == "reactive"
    assert value_type("HGB") == "numeric"
    assert "Occult Blood" in labels("UR_BLOOD")
    assert reference("CULT_SIR") == "", "the benchmark states no intervals"
    assert fmt("CULT_ORGANISM", "Escherichia coli") == "Escherichia coli"
    assert panel_analytes("URINE_CULT")[0] == "CULT_STATUS"
    assert panel_known("HIV_PANEL") and not panel_known("NOT_A_PANEL")
    print(f"vocabulary ok: {len(C.ANALYTES)} from catalog + {len(_BENCH)} from benchmark "
          f"= {len(C.ANALYTES) + len(_BENCH)} analytes, "
          f"{len(C.PANELS)} + {len(_BENCH_PANELS) - len(set(C.PANELS) & set(_BENCH_PANELS))} panels")


if __name__ == "__main__":
    demo()
