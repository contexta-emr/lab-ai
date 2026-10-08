"""What a stored document should have contained, and what it did.

    coverage_for(document_rows) -> dict

WHY THIS EXISTS
    The corpus has a sealed answer key, so we can say exactly which rows an
    extraction missed. A real patient's report has no answer key, and never
    will. Something still has to answer "did we drop a row" on the only kind
    of document that matters.

    A panel template answers it. A lipid profile contains cholesterol,
    triglycerides, HDL, LDL; if a document says LIPID PROFILE at the top and
    HDL is not among the rows, either the lab did not run it or extraction
    lost it - and either way a human should be told rather than shown a
    confident table with a hole in it.

THREE STATES, AND THEY MUST NEVER SHARE A COLOUR
    found      expected, and read.
    missing    expected, and NOT read. A problem.
    extra      read, but the template does not list it. NOT a problem - it is
               content, and showing it as a failure is how a perfectly good
               extraction gets read as a broken one.

    That distinction is the entire reason idp's review.py was written, after
    an extracted "TG / HDL 3.13" was displayed under a grey "unresolved"
    heading and read as a failure to find something the page plainly showed.

WHY IT REBUILDS AN EXTRACTION
    check_document takes the extraction contract, not database rows. Rather
    than a second implementation of coverage that reads SQL, the stored rows
    are assembled back into an Extraction and handed to the tested one. What
    is stored IS what was extracted, so the reconstruction is lossless for
    everything coverage looks at: the printed label, the value, the unit and
    the section title.
"""

from __future__ import annotations

from typing import Any

from app.db import fetch_all
from app.services.ocr.contracts import DocumentMeta, Extraction, Row, Section
from app.services.ocr.templates import (
    Coverage,
    Member,
    MemberResult,
    PanelTemplate,
    check_document,
    load_templates,
)


def panel_templates() -> list[PanelTemplate]:
    """What each panel should contain, read from the database.

    WHY NOT THE JSON ANY MORE
        api/app/services/ocr/templates/*.json is a snapshot, not a source, and
        two things made it wrong:

        1. It predates lab.panel_analytes, so it carries one panel per analyte.
           The Iron Profile template listed five members; the database holds six,
           because Transferrin arrived with the 30-panel benchmark. The chip read
           2/5 while the master said 2/6.

        2. It carries one is_core per analyte. The benchmark states the role per
           analyte PER PANEL - TSAT is Common in the Iron Profile, not Optional
           because it happens to be calculated.

        A snapshot is only safe while nothing it was taken from can change. The
        master changes every time vocabulary is added, and nothing re-exported
        the files. So coverage reads the tables directly and the question of
        whether the snapshot is stale stops existing.

        Fourteen of those files had been generated from this database by a
        script that set is_core as NOT is_derived - exactly the rule point 2
        rejects. They and the script are deleted; the three that remain are the
        hand-curated ones carried over from the idp workspace, which cite their
        clinical sources and predate all of this.

        Safe to do here: load_templates() had exactly one caller - this module -
        which runs inside the API with a connection already open. The OCR
        pipeline never touched templates.

    Falls back to those three when the tables are empty, so a database seeded
    only as far as 004 still reports some coverage rather than none.
    """
    rows = fetch_all("""
        SELECT p.code  AS panel_code,
               p.display_name AS panel_name,
               a.code  AS analyte_code,
               a.display_name AS analyte_name,
               pa.is_core
        FROM   lab.panel_analytes pa
        JOIN   lab.panels   p ON p.id = pa.panel_id
        JOIN   lab.analytes a ON a.id = pa.analyte_id
        WHERE  pa.is_deleted = FALSE
          AND  p.is_deleted  = FALSE AND p.is_active = TRUE
          AND  a.is_deleted  = FALSE AND a.is_active = TRUE
        ORDER  BY p.sort_order, p.code, pa.sort_order, a.code
    """)
    if not rows:
        return load_templates()

    aliases: dict[str, list[str]] = {}
    for r in fetch_all("""
        SELECT p.code AS panel_code, pa.alias
        FROM   lab.panel_aliases pa
        JOIN   lab.panels p ON p.id = pa.panel_id
        WHERE  pa.is_deleted = FALSE AND p.is_deleted = FALSE
    """):
        aliases.setdefault(r["panel_code"], []).append(r["alias"])

    grouped: dict[str, dict] = {}
    for r in rows:
        panel = grouped.setdefault(r["panel_code"], {"name": r["panel_name"], "members": []})
        panel["members"].append(
            Member(
                analyte_code=r["analyte_code"],
                analyte_name=r["analyte_name"],
                is_core=bool(r["is_core"]),
            )
        )
    return [
        PanelTemplate(
            panel_code=code,
            panel_name=panel["name"],
            panel_synonyms=tuple(aliases.get(code, ())),
            members=tuple(panel["members"]),
            sources=("lab.panel_analytes",),
        )
        for code, panel in grouped.items()
    ]


def _extraction_from_rows(rows: list[dict]) -> Extraction:
    """Stored result rows back into the contract check_document expects."""
    sections: list[Section] = []
    by_section: dict[object, Section] = {}
    for i, r in enumerate(rows):
        key = r.get("section_id")
        section = by_section.get(key)
        if section is None:
            section = Section(printed_title=r.get("heading_printed"), rows=[])
            by_section[key] = section
            sections.append(section)
        section.rows.append(
            Row(
                row_index=i,
                raw_label=r.get("printed_label") or "",
                raw_value=r.get("value_text"),
                raw_unit=r.get("unit"),
                raw_reference=r.get("reference_printed"),
                raw_flag=r.get("flag"),
            )
        )
    return Extraction(
        document=DocumentMeta(engine="stored", engine_version="", source_name="", page_count=1),
        sections=sections,
    )


def _state(m: MemberResult) -> str:
    """One expected analyte's verdict. Six, and each means a different thing.

    Taken from idp's review.py, because the distinctions were learned there:

      found     expected, and read with a value.
      confirm   the value WAS read; only the mapping onto a canonical code is
                a guess. Calling this missing would be a lie about data
                sitting right there on the row.
      no_value  the test is printed on the page but no value came out of its
                row. Distinct from missing on purpose - absent means the lab
                did not run it, this means WE failed to read it, and only one
                of those is our bug.
      missing   expected, core, and not there at all. A problem.
      absent    expected, optional, and not there. Routine, not a problem.
      extra     read, and the template never mentioned it. Content, not a
                defect.
    """
    if m.found:
        return "found"
    if getattr(m, "needs_confirmation", False):
        return "confirm"
    if getattr(m, "seen_without_value", False):
        return "no_value"
    return "missing" if m.is_core else "absent"


def _panel_counts(cov: Coverage) -> dict[str, Any]:
    """One panel's coverage, split the way _state splits it.

    The four counts sum to expected, always. That is the property that makes
    the number on screen checkable by the person reading it, and it is the one
    the previous shape did not have.
    """
    counts = {"found": 0, "confirm": 0, "no_value": 0, "missing": 0, "absent": 0}
    for m in cov.members:
        counts[_state(m)] = counts.get(_state(m), 0) + 1

    # THE DENOMINATOR IS EVERY MEMBER. "NOT RUN" COUNTS AS SETTLED.
    #
    # One panel used to carry three different totals on one screen: the chip
    # said 4/7, the table said All 8, and the legend said "15 expected, 15 rows
    # below" over buckets that summed to 21. Each was defensible on its own.
    # Together they were unreadable, because "expected" meant two things - this
    # function excluded the optional tests the lab did not run, merged_rows
    # counted them.
    #
    # The denominator is now what a panel IS: every member, core and optional.
    # That is a property of the template, so the same panel shows the same
    # denominator on every document - where the old one moved about depending
    # on what one lab happened to run.
    #
    # The earlier shape excluded `absent` for a real reason: a complete CBC read
    # "13/23" and looked like a third of it had gone astray. That reason is
    # answered in the NUMERATOR instead. An optional test nobody ran is
    # accounted for, not a gap, so it counts towards `accounted` and a panel
    # with nothing outstanding still reads 8/8. Nothing is hidden - `absent` is
    # still reported separately and still listed in the table as not present.
    #
    # All five buckets sum to expected, so the arithmetic on screen stays
    # checkable by the person reading it. That property is the point.
    expected = len(cov.members)
    accounted = counts["found"] + counts["confirm"] + counts["absent"]
    return {
        "panel_code": cov.panel_code,
        "panel_name": cov.panel_name,
        # kept as it was - certain mappings only - so nothing that reads this
        # field starts meaning something else underneath it
        "found": counts["found"],
        "confirm": counts["confirm"],
        "no_value": counts["no_value"],
        "missing": counts["missing"],
        "absent": counts["absent"],
        # what a human means by "we got this much of the panel"
        "read": counts["found"] + counts["confirm"],
        # read, plus the optional ones nobody ran. What the chip divides by
        # expected: the share of the panel with nothing outstanding on it.
        "accounted": accounted,
        "expected": expected,
        # Optional members nobody ran. Reported, not counted against the panel.
        "optional_not_run": counts["absent"],
        "members": len(cov.members),
    }


def coverage_for(rows: list[dict]) -> dict:
    """Panel coverage for one document's stored rows, as plain JSON."""
    if not rows:
        return {
            "panels": [],
            "unresolved": [],
            "checked": False,
            "note": "Nothing was extracted from this document, so there is "
            "nothing to check against a panel.",
        }

    report = check_document(_extraction_from_rows(rows), panel_templates())

    panels = []
    for cov in report.panels:
        members = [
            {
                "analyte_code": m.analyte_code,
                "analyte_name": m.analyte_name,
                "is_core": m.is_core,
                "state": _state(m),
                "printed_label": m.printed_label,
            }
            for m in cov.members
        ]
        panels.append(
            {
                "panel_code": cov.panel_code,
                "panel_name": cov.panel_name,
                "titled": cov.titled,
                "found": sum(1 for m in cov.members if m.found),
                "expected": len(cov.members),
                "core_missing": [m.analyte_name for m in cov.members if _state(m) == "missing"],
                "needs_confirm": [
                    m.analyte_name for m in cov.members if _state(m) == "confirm"
                ],
                "no_value": [m.analyte_name for m in cov.members if _state(m) == "no_value"],
                "members": members,
                "extra": [
                    {
                        "printed_label": e.printed_label,
                        "value": getattr(e, "raw_value", None),
                        "state": "extra",
                    }
                    for e in cov.unexpected
                ],
            }
        )

    return {
        "checked": True,
        "panels": panels,
        # Rows whose label matched no canonical code at all. The vocabulary's
        # gap, not the extractor's - the row is stored and shown regardless.
        "unresolved": [
            getattr(u, "printed_label", str(u)) for u in getattr(report, "unresolved", [])
        ],
        "note": None
        if panels
        else "No panel template matched this document. That is normal - a "
        "template exists for only a few panels - and the rows are "
        "stored and shown either way.",
    }


def _norm(text: str | None) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def merged_rows(rows: list[dict]) -> dict:
    """Everything about one document's results as a single list of rows.

    ONE TABLE, NOT TWO
        What the page printed and what the panel expected were two panels on
        screen, and a reviewer had to hold one in their head while reading the
        other. Merged, a missing analyte sits in the table with its value cell
        empty - you see the hole where the number should be instead of being
        told a count somewhere else.

    EACH ROW CARRIES BOTH READINGS
        analyte_name and analyte_code are OURS, the canonical test this was
        resolved to. printed_label is what the lab actually printed. Side by
        side on every row, a wrong mapping is obvious at a glance - which is
        the whole job of this screen and was previously impossible without
        cross-referencing two lists.

    Rows the page printed can be corrected and removed, so they carry a
    result_id. Rows that are only expectations cannot: there is nothing there
    to edit. editable says which is which rather than leaving the browser to
    infer it from a null.
    """
    if not rows:
        return {"panels": [], "rows": [], "note": "Nothing was extracted from this document."}

    report = check_document(_extraction_from_rows(rows), panel_templates())

    # printed label -> what the template made of it
    verdict: dict[str, dict] = {}
    for cov in report.panels:
        for m in cov.members:
            if m.printed_label:
                verdict[_norm(m.printed_label)] = {
                    "status": _state(m),
                    "analyte_name": m.analyte_name,
                    "template_code": m.analyte_code,
                    "required": "core" if m.is_core else "optional",
                    "panel": cov.panel_name,
                }

    out: list[dict] = []
    for r in rows:
        v = verdict.get(_norm(r.get("printed_label")), {})
        out.append(
            {
                "result_id": str(r["id"]) if r.get("id") is not None else None,
                "editable": r.get("id") is not None,
                # Extra is the honest default: the row IS on the page, it simply
                # belongs to no template we hold. Never a failure.
                # A row with no value read is that, whatever the template thinks:
                # the page shows the test and we failed to read its number, which
                # is a different problem from a test nobody ran.
                "status": (
                    "no_value"
                    if not (r.get("value_text") or "").strip()
                    else v.get("status", "extra")
                ),
                "analyte_name": v.get("analyte_name") or r.get("analyte_name"),
                "analyte_code": r.get("analyte_code"),
                "required": v.get("required", ""),
                "panel": v.get("panel") or r.get("heading_printed"),
                "section": r.get("heading_printed"),
                "printed_label": r.get("printed_label"),
                "value_text": r.get("value_text"),
                "unit": r.get("unit"),
                "flag": r.get("flag"),
                "reference_printed": r.get("reference_printed"),
                "is_reviewed": r.get("is_reviewed", False),
                "corrected_from": r.get("corrected_from"),
            }
        )

    # A panel is usually printed under a heading of the lab's own choosing -
    # "URINE ROUTINE" for what we call Urine Routine & Microscopy. Rows the page
    # never printed have no heading of their own, and labelling them with the
    # canonical name put the same panel on screen twice under two names. So they
    # borrow the heading the printed rows of that panel actually used.
    heading_of: dict[str, str] = {}
    for row in out:
        if row["panel"] and row["section"] and row["panel"] not in heading_of:
            heading_of[row["panel"]] = row["section"]

    # Then what the panel expected and the page never showed. These go at the
    # end of their panel rather than interleaved, because their position in a
    # printed table is not a thing that exists.
    for cov in report.panels:
        for m in cov.members:
            if m.printed_label:
                continue
            state = _state(m)
            # An optional test the lab did not run used to be dropped here, on
            # the reasoning that it is routine rather than a hole. True, but it
            # left the table unable to account for itself: a panel chip reading
            # 9/11 sat above ten rows, and the eleventh was missing for a reason
            # the screen never gave. A reviewer cannot check arithmetic against
            # a row that was silently withheld.
            #
            # So it is printed, quietly - st-absent is grey and says "not
            # present" - and the rows on screen now equal the denominator on the
            # chip for every panel. Being unremarkable is a reason to style
            # something down, not to hide it.
            out.append(
                {
                    "result_id": None,
                    "editable": False,
                    "status": state,
                    "analyte_name": m.analyte_name,
                    "analyte_code": m.analyte_code,
                    "required": "core" if m.is_core else "optional",
                    "panel": cov.panel_name,
                    "section": heading_of.get(cov.panel_name, cov.panel_name),
                    "printed_label": None,
                    "value_text": None,
                    "unit": None,
                    "flag": None,
                    "reference_printed": None,
                    "is_reviewed": False,
                    "corrected_from": None,
                }
            )

    # EVERY BUCKET, NOT JUST THE CLEAN ONE.
    #
    # This used to return found and expected alone, and `found` counts only
    # members whose mapping is certain. So a panel with five certain rows, three
    # awaiting confirmation and two genuinely absent reported "5/11" while the
    # table below it showed eight rows sitting right there with values on them.
    # Both numbers were correct and the pair was unreadable: the reviewer is
    # left to work out which of four buckets the missing six fell into, and the
    # obvious reading - that something is broken - is wrong.
    #
    # So the counts are all here and they sum to expected. `read` is the number
    # a human means by "how much of this panel did we get off the page": found
    # plus confirm, because a confirm row IS read - only its code is a guess.
    return {
        "panels": [_panel_counts(c) for c in report.panels],
        "rows": out,
        "note": None
        if report.panels
        else "No panel template matched this report, so nothing is coverage-"
        "checked. Every row was still read and carries its value.",
    }
