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

from app.services.ocr.contracts import DocumentMeta, Extraction, Row, Section
from app.services.ocr.templates import check_document, load_templates


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
        section.rows.append(Row(
            row_index=i,
            raw_label=r.get("printed_label") or "",
            raw_value=r.get("value_text"),
            raw_unit=r.get("unit"),
            raw_reference=r.get("reference_printed"),
            raw_flag=r.get("flag"),
        ))
    return Extraction(
        document=DocumentMeta(engine="stored", engine_version="",
                              source_name="", page_count=1),
        sections=sections,
    )


def _state(m) -> str:
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


def coverage_for(rows: list[dict]) -> dict:
    """Panel coverage for one document's stored rows, as plain JSON."""
    if not rows:
        return {"panels": [], "unresolved": [], "checked": False,
                "note": "Nothing was extracted from this document, so there is "
                        "nothing to check against a panel."}

    report = check_document(_extraction_from_rows(rows), load_templates())

    panels = []
    for cov in report.panels:
        members = [{
            "analyte_code": m.analyte_code,
            "analyte_name": m.analyte_name,
            "is_core": m.is_core,
            "state": _state(m),
            "printed_label": m.printed_label,
        } for m in cov.members]
        panels.append({
            "panel_code": cov.panel_code,
            "panel_name": cov.panel_name,
            "titled": cov.titled,
            "found": sum(1 for m in cov.members if m.found),
            "expected": len(cov.members),
            "core_missing": [m.analyte_name for m in cov.members
                             if _state(m) == "missing"],
            "needs_confirm": [m.analyte_name for m in cov.members
                              if _state(m) == "confirm"],
            "no_value": [m.analyte_name for m in cov.members
                         if _state(m) == "no_value"],
            "members": members,
            "extra": [{"printed_label": e.printed_label,
                       "value": getattr(e, "raw_value", None),
                       "state": "extra"} for e in cov.unexpected],
        })

    return {
        "checked": True,
        "panels": panels,
        # Rows whose label matched no canonical code at all. The vocabulary's
        # gap, not the extractor's - the row is stored and shown regardless.
        "unresolved": [getattr(u, "printed_label", str(u))
                       for u in getattr(report, "unresolved", [])],
        "note": None if panels else
                "No panel template matched this document. That is normal - a "
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
        return {"panels": [], "rows": [], "note":
                "Nothing was extracted from this document."}

    report = check_document(_extraction_from_rows(rows), load_templates())

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
        out.append({
            "result_id": str(r["id"]) if r.get("id") is not None else None,
            "editable": r.get("id") is not None,
            # Extra is the honest default: the row IS on the page, it simply
            # belongs to no template we hold. Never a failure.
            # A row with no value read is that, whatever the template thinks:
            # the page shows the test and we failed to read its number, which
            # is a different problem from a test nobody ran.
            "status": ("no_value" if not (r.get("value_text") or "").strip()
                       else v.get("status", "extra")),
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
        })

    # Then what the panel expected and the page never showed. These go at the
    # end of their panel rather than interleaved, because their position in a
    # printed table is not a thing that exists.
    for cov in report.panels:
        for m in cov.members:
            if m.printed_label:
                continue
            state = _state(m)
            if state == "absent":
                continue          # optional and not run: routine, not a hole
            out.append({
                "result_id": None,
                "editable": False,
                "status": state,
                "analyte_name": m.analyte_name,
                "analyte_code": m.analyte_code,
                "required": "core" if m.is_core else "optional",
                "panel": cov.panel_name,
                "section": cov.panel_name,
                "printed_label": None,
                "value_text": None,
                "unit": None,
                "flag": None,
                "reference_printed": None,
                "is_reviewed": False,
                "corrected_from": None,
            })

    return {
        "panels": [{"panel_code": c.panel_code, "panel_name": c.panel_name,
                    "found": sum(1 for m in c.members if m.found),
                    "expected": len(c.members)} for c in report.panels],
        "rows": out,
        "note": None if report.panels else
                "No panel template matched this report, so nothing is coverage-"
                "checked. Every row was still read and carries its value.",
    }
