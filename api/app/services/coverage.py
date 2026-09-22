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
            # The three states, named here rather than inferred in the browser
            # so one definition serves every client.
            "state": "found" if m.found else "missing",
            "printed_label": m.printed_label,
        } for m in cov.members]
        panels.append({
            "panel_code": cov.panel_code,
            "panel_name": cov.panel_name,
            "titled": cov.titled,
            "found": sum(1 for m in cov.members if m.found),
            "expected": len(cov.members),
            "core_missing": [m.analyte_name for m in cov.members
                             if m.is_core and not m.found],
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
