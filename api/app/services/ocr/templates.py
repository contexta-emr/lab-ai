"""Panel templates and the coverage check.

A template says which analytes a named panel should contain. Comparing it against what
came out of a document answers the question the extractor cannot answer about itself:
**did we miss anything?**

Three outcomes matter, and they are different problems:

* **missing** - the template expects it, the report did not yield it. Either the lab did
  not run it, or extraction dropped it.
* **unexpected** - the report yielded an analyte the template does not list. Usually a
  legitimate add-on; occasionally OCR noise.
* **unresolved** - a printed label that matched no canonical code at all. This is the
  synonym dictionary's gap, not the extractor's. The row still carries its value, and
  is reported as a finding rather than as a failure.

Core versus optional is not decoration. Indian labs sell a thyroid panel as T3/T4/TSH or
with the free forms added, so a flat expected-list reports a perfectly good extraction as
a failure. Only missing **core** members count against a document.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .contracts import Extraction
from .synonyms import Match, normalise_label, propose, resolve

__all__ = [
    "TEMPLATE_DIR",
    "Coverage",
    "DocumentCoverage",
    "ExtraRow",
    "MemberResult",
    "PanelMatch",
    "PanelTemplate",
    "awaiting_confirmation_count",
    "check_coverage",
    "check_document",
    "detect_panels",
    "load_template",
    "load_templates",
    "match_panel",
    "pick_template",
]

# Beside this module, not two levels up: in the idp layout templates/ sat
# at the project root, here the whole package lives under app/services/ocr.
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

#: Share of a document's resolved analytes a template must account for before it is
#: accepted as that document's panel. Set on the principle that a panel should explain
#: more of a report than it leaves unexplained, not tuned to make any document pass -
#: check it against the whole corpus, never against one report.
MIN_EXPLAINED = 0.5

#: The bar when the report also *prints* the panel name above the grid. Lower, because a
#: lab naming its own panel is real evidence - but not zero, because a title with no
#: matching analytes means something went wrong rather than that the title is right.
MIN_EXPLAINED_TITLED = 0.25

#: Share of a panel's **core** analytes that must be present for the panel to be reported
#: as one of the things a document contains.
#:
#: Note which way round this is. MIN_EXPLAINED asks how much of the *document* a panel
#: accounts for, which is the right question for "what is this report?" and the wrong one
#: for "what is in it": a five-member panel inside a forty-analyte health checkup accounts
#: for an eighth of the document and is unmistakably present. Presence is about the panel;
#: identity is about the document.
MIN_PANEL_PRESENCE = 0.6

#: A panel needs at least this many core members before mere presence counts as
#: evidence that the document contains it. One core member is not a fraction, it
#: is a coin toss: the analyte is there or it is not, and "1 of 1" looks like
#: certainty while carrying no information. The benchmark's standalone panels -
#: Ferritin, CRP, ESR, Vitamin B12, Vitamin D, Uric Acid, HbA1c, Calcium - are
#: all single-core by nature, which is why this had to be stated rather than
#: left to the presence threshold.
MIN_CORE_FOR_PRESENCE = 2

#: What one extracted row contributes: printed label, value, unit, reference, page.
#: The reference is carried through because a row the template never heard of still has
#: one printed beside it, and dropping it makes an extra look less trustworthy than the
#: analytes around it for no reason other than the shape of this tuple.
_RowFacts = tuple[str, "str | None", "str | None", "str | None", int]


@dataclass(frozen=True, slots=True)
class Member:
    """One analyte a panel should contain."""

    analyte_code: str
    analyte_name: str
    is_core: bool


@dataclass(frozen=True, slots=True)
class PanelTemplate:
    """What a named panel is expected to contain, and where that was sourced from."""

    panel_code: str
    panel_name: str
    panel_synonyms: tuple[str, ...]
    members: tuple[Member, ...]
    notes: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()

    @property
    def core(self) -> tuple[Member, ...]:
        """Members whose absence is a real gap."""
        return tuple(m for m in self.members if m.is_core)

    @property
    def codes(self) -> frozenset[str]:
        """Every analyte code the panel may contain, core or optional."""
        return frozenset(m.analyte_code for m in self.members)


@dataclass(frozen=True, slots=True)
class PanelMatch:
    """Which panel a document was judged to be, and on what evidence.

    ``panel`` of ``None`` used to be the whole answer, and it meant three unrelated
    things at once: no panel of that kind is defined, a panel matched but the evidence
    was thin, or the document has no analytes at all. Those need three different actions
    from whoever is looking at the queue - add a panel, review the document, or nothing -
    so ``reason`` separates them.

    Attributes:
        panel: The panel decided on, or ``None`` when nothing was.
        explained: Share of the document's resolved analytes this panel accounts for.
            **A ratio, not a probability.** 0.5 does not mean "half likely to be right",
            and it must not be presented as a confidence until it has been calibrated
            against labelled data - the same mistake the fuzzy-match score invites.
        titled: Whether the report also printed this panel's name above a grid.
        reason: ``TITLE_AND_MEMBERS``, ``MEMBERS``, ``BELOW_THRESHOLD``,
            ``NO_PANEL_DEFINED`` or ``NO_ANALYTES``.
    """

    panel: PanelTemplate | None
    explained: float
    titled: bool
    reason: str

    @property
    def decided(self) -> bool:
        return self.panel is not None


@dataclass(slots=True)
class MemberResult:
    """Whether one expected analyte turned up, and what the report called it.

    ``found`` means an **exact** dictionary hit - the only tier applied without a human.
    ``proposal`` is a fuzzy candidate awaiting confirmation: the value was read, but the
    mapping is a guess and does not count toward coverage until someone agrees with it.
    """

    analyte_code: str
    analyte_name: str
    is_core: bool
    found: bool
    printed_label: str | None = None
    raw_value: str | None = None
    raw_unit: str | None = None
    page: int | None = None
    proposal: Match | None = None

    @property
    def needs_confirmation(self) -> bool:
        """A value was read for this analyte, but only by a fuzzy match."""
        return not self.found and self.proposal is not None

    @property
    def seen_without_value(self) -> bool:
        """The analyte is printed on the report, but no value came out of its row.

        A different problem from an analyte that is simply absent, and it must not be
        reported as one: absent means the lab did not run it, this means we failed to
        read it. Collapsing the two hides every extraction failure inside a column of
        legitimate blanks.
        """
        return not self.found and self.proposal is None and self.printed_label is not None


@dataclass(slots=True)
class ExtraRow:
    """An extracted row the template did not ask for.

    Both kinds live in this one shape, and the difference is ``analyte_code``:

    * **resolved** (a code) - a legitimate add-on the panel simply does not list, like a
      TG/HDL ratio printed under a lipid profile.
    * **unresolved** (``None``) - the synonym dictionary has no entry for the printed
      label. A gap in the vocabulary, *not* a failure to read the document.

    Either way the row **was read**, and it carries its value. An earlier version kept
    unresolved rows as bare label strings, which threw away a perfectly good `3.13` and
    made a successful extraction look like a miss on screen.
    """

    printed_label: str
    analyte_code: str | None
    raw_value: str | None
    page: int | None
    raw_unit: str | None = None
    raw_reference: str | None = None

    @property
    def is_result(self) -> bool:
        """Whether this row carries a value at all.

        Interpretation legends print rows like ``Borderline High  130 - 159`` - a label
        and a range, no result. They are content, so they are never dropped, but they
        are not findings and must not be shown as though they were.
        """
        return bool(self.raw_value and self.raw_value.strip())


@dataclass(slots=True)
class Coverage:
    """The result of checking one document against one template."""

    panel_code: str
    panel_name: str
    source_name: str
    #: Share of the document's resolved analytes this panel accounts for, and whether the
    #: report also printed its name. Set by :func:`check_document`; zero when a panel was
    #: checked directly rather than detected.
    explained: float = 0.0
    titled: bool = False
    members: list[MemberResult] = field(default_factory=list)
    unexpected: list[ExtraRow] = field(default_factory=list)
    unresolved: list[ExtraRow] = field(default_factory=list)
    ambiguous: dict[str, tuple[str, ...]] = field(default_factory=dict)
    #: analyte code -> the reference range the lab printed. Reported as-is, never
    #: compared against an expected range: ranges vary legitimately by lab, method, age
    #: and sex, so a template asserting one would manufacture false failures.
    references: dict[str, str] = field(default_factory=dict)

    @property
    def core_expected(self) -> list[MemberResult]:
        return [m for m in self.members if m.is_core]

    @property
    def core_missing(self) -> list[MemberResult]:
        """Core members the document did not yield. The number that matters."""
        return [m for m in self.core_expected if not m.found]

    @property
    def awaiting_confirmation(self) -> list[MemberResult]:
        """Analytes whose value was read but whose mapping is only a fuzzy guess."""
        return [m for m in self.members if m.needs_confirmation]

    @property
    def optional_missing(self) -> list[MemberResult]:
        """Absent optional members. Informational - never a failure."""
        return [m for m in self.members if not m.is_core and not m.found]

    @property
    def found(self) -> list[MemberResult]:
        return [m for m in self.members if m.found]

    @property
    def is_complete(self) -> bool:
        """True when every core member was found **exactly**.

        A proposal does not count. The mapping is a guess until a human agrees with it,
        and reporting a guessed panel as complete is how a wrong number reaches a chart.
        """
        return not self.core_missing

    @property
    def core_score(self) -> float:
        """Fraction of core members found, 0.0 to 1.0."""
        expected = self.core_expected
        if not expected:
            return 1.0
        return sum(m.found for m in expected) / len(expected)


def _template_from_dict(data: dict[str, Any]) -> PanelTemplate:
    """Build a template from parsed JSON, defaulting a member to core when unstated."""
    members = tuple(
        Member(
            analyte_code=str(m["analyte_code"]).upper(),
            analyte_name=str(m.get("analyte_name", "")),
            is_core=bool(m.get("is_core", True)),
        )
        for m in data.get("members", [])
    )
    return PanelTemplate(
        panel_code=str(data["panel_code"]).upper(),
        panel_name=str(data.get("panel_name", data["panel_code"])),
        panel_synonyms=tuple(str(s) for s in data.get("panel_synonyms", [])),
        members=members,
        notes=tuple(str(n) for n in data.get("notes", [])),
        sources=tuple(str(s) for s in data.get("sources", [])),
    )


def _load_json(path: Path) -> dict[str, Any]:
    parsed: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return parsed


def load_template(path: Path) -> PanelTemplate:
    """Read one template JSON file.

    Args:
        path: The file to read.

    Returns:
        The parsed template.

    Raises:
        KeyError: If ``panel_code`` is absent.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    return _template_from_dict(_load_json(path))


def load_templates(directory: Path | None = None) -> list[PanelTemplate]:
    """Read every template in a directory, sorted by panel code.

    Args:
        directory: Where to look. Defaults to :data:`TEMPLATE_DIR`.

    Returns:
        The templates found. Empty list when the directory does not exist.
    """
    target = directory or TEMPLATE_DIR
    if not target.exists():
        return []
    return sorted((load_template(p) for p in target.glob("*.json")), key=lambda t: t.panel_code)


def match_panel(extraction: Extraction, templates: list[PanelTemplate]) -> PanelMatch:
    """Judge which panel a document is, and say how sure that is and why.

    Three kinds of evidence, in order of how much they are trusted:

    1. **Membership** - how much of the *document* a panel explains. This is the gate.
       Not how much of the panel is present: that reading let a 23-row kidney report
       satisfy the two-member creatinine template completely and report 100%.
    2. **The printed title** - a lab that writes "LIPID PROFILE" above the grid has told
       us what it is, so a corroborated title lowers the bar. It does not remove it.
    3. **Nothing** - and saying so, with a reason, is a real answer.

    A title alone can no longer decide. It used to return the moment any section title
    intersected any synonym, before membership was consulted at all - so a stray heading,
    or a patient whose name normalised onto a panel synonym, would win outright against
    every analyte on the page. Section titles in this corpus include ``YASH M PATEL`` and
    ``SAMPLE COLLECTED AT``, so that is not a hypothetical.

    Args:
        extraction: The document to classify.
        templates: Candidate panels.

    Returns:
        The verdict. ``panel`` is ``None`` whenever nothing was decided, and ``reason``
        says which of the several different reasons applies - they need different actions
        from whoever is looking at the queue.
    """
    if not templates:
        return PanelMatch(None, 0.0, False, "NO_PANEL_DEFINED")

    found = _resolved_codes(extraction)
    if not found:
        # A narrative report, or one nothing could be read from. Not a panel question.
        return PanelMatch(None, 0.0, False, "NO_ANALYTES")

    titles = {normalise_label(s.printed_title or "") for s in extraction.sections}
    titles.discard("")

    ranked: list[tuple[float, bool, PanelTemplate]] = []
    for template in templates:
        overlap = len(template.codes & found)
        if overlap == 0:
            # The hard rule. A title match with no member overlap is either a failed
            # extraction or a heading that is not a panel name, and both deserve to be
            # said out loud rather than papered over with a confident answer.
            continue
        keys = {normalise_label(s) for s in (*template.panel_synonyms, template.panel_name)}
        ranked.append((overlap / len(found), bool(titles & keys), template))

    if not ranked:
        # Nothing we hold a definition for shares a single analyte with this document.
        # That is a gap in the panel catalogue, not a weak match, and the fix is to add
        # the panel rather than to review the document.
        return PanelMatch(None, 0.0, False, "NO_PANEL_DEFINED")

    # Best by how much of the document it explains; a corroborated title breaks ties,
    # which is the only place the title decides anything on its own.
    explained, titled, best = max(ranked, key=lambda r: (r[0], r[1]))
    floor = MIN_EXPLAINED_TITLED if titled else MIN_EXPLAINED
    if explained < floor:
        return PanelMatch(None, explained, titled, "BELOW_THRESHOLD")
    return PanelMatch(best, explained, titled, "TITLE_AND_MEMBERS" if titled else "MEMBERS")


def pick_template(
    extraction: Extraction, templates: list[PanelTemplate]
) -> PanelTemplate | None:
    """The panel this document belongs to, or ``None``.

    A thin wrapper over :func:`match_panel` for callers that only need the answer and not
    the reasoning behind it.
    """
    return match_panel(extraction, templates).panel


def _resolved_codes(extraction: Extraction) -> frozenset[str]:
    """Every analyte code the document's rows point at, exactly or by proposal.

    Proposals count here even though they never count toward coverage. Choosing which
    panel to *compare against* is a low-stakes guess that the user can override; a
    creatinine report whose single label carries a method phrase resolves to nothing
    exactly, and refusing to identify it would leave the screen blank for no good reason.
    """
    codes: set[str] = set()
    for section in extraction.sections:
        for row in section.rows:
            matches = resolve(row.raw_label)
            if len(matches) == 1:
                codes.add(matches[0])
            elif not matches:
                candidates = propose(row.raw_label, limit=1)
                if candidates:
                    codes.add(candidates[0].analyte_code)
    return frozenset(codes)


def check_coverage(extraction: Extraction, template: PanelTemplate) -> Coverage:
    """Compare what a document yielded against what the panel should contain.

    Args:
        extraction: The extraction JSON for one document.
        template: The panel it is being held to.

    Returns:
        Per-member results plus the rows the template did not expect, the labels that
        resolved to nothing, and the ones that resolved to more than one code.
    """
    coverage = Coverage(
        panel_code=template.panel_code,
        panel_name=template.panel_name,
        source_name=extraction.document.source_name,
    )

    # code -> the first row that produced it, so the report can show what was printed.
    by_code: dict[str, _RowFacts] = {}
    # Rows that matched nothing exactly, kept for the fuzzy pass below.
    unmatched: list[tuple[str, _RowFacts]] = []

    for section in extraction.sections:
        for row in section.rows:
            facts: _RowFacts = (
                row.raw_label,
                row.raw_value,
                row.raw_unit,
                row.raw_reference,
                row.page,
            )
            matches = resolve(row.raw_label)
            if not matches:
                unmatched.append((row.raw_label, facts))
                continue
            if len(matches) > 1:
                coverage.ambiguous[row.raw_label] = matches
                continue
            by_code.setdefault(matches[0], facts)
            if row.raw_reference:
                coverage.references.setdefault(matches[0], row.raw_reference)

    # Second tier. A printed label carries assay methods, sample types and traceability
    # notes no dictionary will enumerate, so an unmatched row gets one more chance -
    # against the analytes this panel is still missing, and only as a proposal.
    wanted = {m.analyte_code for m in template.members} - set(by_code)
    proposals: dict[str, tuple[Match, _RowFacts]] = {}
    for label, facts in unmatched:
        best: Match | None = None
        # A proposal is only worth a human's attention if there is a value behind it.
        # Interpretation tables print test names with no results, and proposing mappings
        # for those buries the one row that actually needs confirming.
        if facts[1]:
            for candidate in propose(label):
                if candidate.analyte_code in wanted:
                    best = candidate
                    break
        if best is None:
            coverage.unresolved.append(
                ExtraRow(
                    printed_label=label,
                    analyte_code=None,
                    raw_value=facts[1],
                    raw_unit=facts[2],
                    raw_reference=facts[3],
                    page=facts[4],
                )
            )
            continue
        current = proposals.get(best.analyte_code)
        if current is None or best.confidence > current[0].confidence:
            proposals[best.analyte_code] = (best, facts)

    for member in template.members:
        hit = by_code.get(member.analyte_code)
        suggested = proposals.get(member.analyte_code) if hit is None else None
        # Show the row either way: an exact hit, or the one a proposal points at. Hiding
        # a value that was successfully read - because only its *mapping* is uncertain -
        # is what made the creatinine report look like a total extraction failure.
        shown = hit or (suggested[1] if suggested else None)
        coverage.members.append(
            MemberResult(
                analyte_code=member.analyte_code,
                analyte_name=member.analyte_name,
                is_core=member.is_core,
                # A resolved *label* is not a result. Counting one as found is how a
                # thyroid report with eleven rows and not a single value came out as
                # "100%, every core analyte found by exact match" - the exact failure
                # this whole design exists to prevent. Any value counts, including
                # "Positive" or "Absent"; the test is that the row carried one.
                found=hit is not None and bool((hit[1] or "").strip()),
                printed_label=shown[0] if shown else None,
                raw_value=shown[1] if shown else None,
                raw_unit=shown[2] if shown else None,
                page=shown[4] if shown else None,
                proposal=suggested[0] if suggested else None,
            )
        )

    for code, (label, value, unit, reference, page) in by_code.items():
        if code not in template.codes:
            coverage.unexpected.append(
                ExtraRow(
                    printed_label=label,
                    analyte_code=code,
                    raw_value=value,
                    raw_unit=unit,
                    raw_reference=reference,
                    page=page,
                )
            )

    return coverage


def awaiting_confirmation_count(coverage: Coverage) -> int:
    """How many analytes were read but mapped only by a fuzzy guess."""
    return len(coverage.awaiting_confirmation)


@dataclass(slots=True)
class DocumentCoverage:
    """Every panel found in one document, plus what belongs to none of them.

    A document is not one panel. ``drlogy-kft`` prints urea, creatinine, sodium,
    potassium, chloride, calcium and ALP in a **single grid** - a kidney panel, an
    electrolyte panel and part of a liver panel at once - and a health checkup package
    routinely bundles five or six. Returning one :class:`Coverage` could only ever
    describe one of them, so the other two were reported as "unexpected extras" or, worse,
    the whole document was matched to the narrowest panel that happened to fit.

    ``unresolved``, ``ambiguous`` and ``references`` live here rather than on each panel
    because they are properties of the *document*: a label that matched no canonical code
    did not fail against the lipid panel, it failed against the dictionary, and repeating
    it under every panel would report one gap three times.
    """

    source_name: str
    panels: list[Coverage] = field(default_factory=list)
    #: Resolved, but belonging to **no** detected panel. A stronger statement than the
    #: per-panel version: this is genuinely unexplained rather than merely off-panel.
    unexpected: list[ExtraRow] = field(default_factory=list)
    unresolved: list[ExtraRow] = field(default_factory=list)
    ambiguous: dict[str, tuple[str, ...]] = field(default_factory=dict)
    references: dict[str, str] = field(default_factory=dict)
    #: Why no panel was decided, when none was. See :class:`PanelMatch`.
    reason: str = "MEMBERS"

    @property
    def core_expected(self) -> list[MemberResult]:
        """Core members across every detected panel."""
        return [m for panel in self.panels for m in panel.core_expected]

    @property
    def core_missing(self) -> list[MemberResult]:
        return [m for panel in self.panels for m in panel.core_missing]

    @property
    def awaiting_confirmation(self) -> list[MemberResult]:
        return [m for panel in self.panels for m in panel.awaiting_confirmation]

    @property
    def is_complete(self) -> bool:
        """Every core analyte of every detected panel was found exactly."""
        return bool(self.panels) and all(p.is_complete for p in self.panels)

    @property
    def core_score(self) -> float:
        expected = self.core_expected
        if not expected:
            return 1.0
        return sum(m.found for m in expected) / len(expected)


def detect_panels(
    extraction: Extraction,
    templates: list[PanelTemplate],
    *,
    floor: float = MIN_PANEL_PRESENCE,
) -> list[PanelMatch]:
    """Every panel this document contains, best first.

        Multi-label on purpose. :func:`match_panel` answers "which one panel is this?", which
        is the wrong question for a document holding several - it forces a winner and files
        the rest as extras.

    The test is **how much of the panel is present**, not how much of the document it
        accounts for. Those are different questions and only one of them is about presence: a
        five-member panel inside a forty-analyte health checkup explains an eighth of the
        document and is unmistakably there.

        Args:
            extraction: The document.
            templates: Candidate panels.
            floor: Share of a panel's core analytes that must be present.

        Returns:
            One match per panel present, ordered by how much each explains. Empty when
            nothing cleared the bar.
    """
    found = _resolved_codes(extraction)
    if not found or not templates:
        return []

    titles = {normalise_label(s.printed_title or "") for s in extraction.sections}
    titles.discard("")

    matches: list[PanelMatch] = []
    for template in templates:
        overlap = len(template.codes & found)
        if overlap == 0:
            continue
        share = overlap / len(found)
        core = {m.analyte_code for m in template.core} or template.codes
        present = len(core & found) / len(core)
        keys = {normalise_label(s) for s in (*template.panel_synonyms, template.panel_name)}
        titled = bool(titles & keys)
        # A panel whose core is one analyte is claimed by presence ALONE every
        # time that analyte appears anywhere - a ferritin inside a forty-row
        # health check "proves" the Ferritin panel, and the report then shows a
        # panel nobody ordered. Measured over the stored corpus: 400 of 556
        # untitled claims came from single-core panels, against 156 from panels
        # with enough members for presence to mean something.
        #
        # So presence is evidence only where there is something to be present
        # OUT OF. Below that, the page has to name the panel.
        if len(core) < MIN_CORE_FOR_PRESENCE and not titled:
            continue
        if present < floor and not titled:
            continue
        reason = "TITLE_AND_MEMBERS" if titled else "MEMBERS"
        matches.append(PanelMatch(template, share, titled, reason))
    return sorted(matches, key=lambda m: (-m.explained, m.panel.panel_code if m.panel else ""))


def check_document(extraction: Extraction, templates: list[PanelTemplate]) -> DocumentCoverage:
    """Check a document against every panel it appears to contain.

    Args:
        extraction: The extraction JSON for one document.
        templates: The panel catalogue.

    Returns:
        One :class:`Coverage` per detected panel, plus the rows that belong to none of
        them. Detecting no panel is a normal outcome, not an error - the rows are still
        reported, because a panel is metadata about a document and must never gate its
        data.
    """
    document = DocumentCoverage(source_name=extraction.document.source_name)
    matches = detect_panels(extraction, templates)

    if not matches:
        document.reason = match_panel(extraction, templates).reason
    for match in matches:
        if match.panel is None:
            continue
        panel = check_coverage(extraction, match.panel)
        panel.explained = match.explained
        panel.titled = match.titled
        document.panels.append(panel)

    # Document-level facts, gathered once. Taken from any panel's pass - they are
    # identical across panels by construction, since they describe the document.
    if document.panels:
        first = document.panels[0]
        document.unresolved = list(first.unresolved)
        document.ambiguous = dict(first.ambiguous)
        document.references = dict(first.references)
        covered: set[str] = set()
        for match in matches:
            if match.panel is not None:
                covered |= match.panel.codes
        # Resolved but in no detected panel at all. The per-panel `unexpected` lists say
        # "not in *this* panel", which over-reports once several panels are in play.
        seen: set[str] = set()
        for panel in document.panels:
            for extra in panel.unexpected:
                code = extra.analyte_code
                if code and code not in covered and code not in seen:
                    seen.add(code)
                    document.unexpected.append(extra)
    else:
        bare = check_coverage(extraction, _EMPTY_PANEL)
        document.unresolved = bare.unresolved
        document.ambiguous = bare.ambiguous
        document.references = bare.references
        document.unexpected = bare.unexpected
    return document


#: Used to read a document's rows when no panel was detected, so the extras and the
#: unresolved labels are still gathered. A panel that expects nothing expects nothing.
_EMPTY_PANEL = PanelTemplate(panel_code="", panel_name="", panel_synonyms=(), members=())
