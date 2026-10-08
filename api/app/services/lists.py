"""The two lists a human types against a document, and the verdict on one of them.

doctor_order  A claim about INTENT. Each ordered panel is judged against what the
              page contains: complete, partial, or not on the page. That
              judgement is the entire purpose - a panel ordered and absent is a
              call to the lab, and nothing else on the screen says it.

patient_tag   Context. Resolved so matching rows can be highlighted, and never
              judged. A patient naming a test is not a clinical instruction, and
              reporting it "missing" would invent an order nobody placed.

WHY THE TWO ARE SCORED BY DIFFERENT RULES
    Keeping them in one code path with a flag would make it one edit away from
    scoring the patient's list too. They are separate functions because the
    distinction is the feature.

HOW A PANEL IS JUDGED
    Against the coverage already computed for the document - the same numbers the
    chips show - not a second opinion. A panel is:

      complete     every CORE analyte of it was read off the page
      partial      some were, some were not
      not_present  none were, or the panel is nowhere in the document

    Core only. Optional members are excluded from the denominator, or a lab that
    simply did not run the optional half of a panel would read as half-missing.

WHAT IS DELIBERATELY NOT DONE
    The order never influences panel detection. What the doctor asked for is
    intent; what the page contains is evidence. Letting the first colour the
    second would make coverage unfalsifiable - a panel could appear because
    somebody typed it.
"""

from __future__ import annotations

from app.db import fetch_all
from app.services.term_resolver import resolve_terms, split_terms

KINDS = ("doctor_order", "patient_tag")


def _present_codes(document_id: int) -> set[str]:
    """Analyte codes this document actually reported a value for.

    A row printed with no readable value does not count as present: the test is
    on the page and we failed to read it, which is our problem, not evidence the
    lab reported it.
    """
    return {
        r["code"]
        for r in fetch_all(
            """
        SELECT a.code
        FROM   lab.results r
        JOIN   lab.analytes a ON a.id = r.analyte_id
        WHERE  r.document_id = %s
          AND  r.is_deleted = FALSE
          AND  COALESCE(btrim(r.value_text), '') <> ''
    """,
            (document_id,),
        )
    }


def _no_value_codes(document_id: int) -> set[str]:
    """Printed, recognised, and no value came out of the row. Our failure."""
    return {
        r["code"]
        for r in fetch_all(
            """
        SELECT a.code
        FROM   lab.results r
        JOIN   lab.analytes a ON a.id = r.analyte_id
        WHERE  r.document_id = %s
          AND  r.is_deleted = FALSE
          AND  COALESCE(btrim(r.value_text), '') = ''
    """,
            (document_id,),
        )
    }


def _detected_panels(practice_id: int, document_id: int) -> dict[str, dict]:
    """Panels this document was judged to contain - the coverage chips' own answer.

    Read from the same place rather than recomputed, so the drawer and the chips
    can never disagree about whether a panel is on the page.
    """
    from app.services.coverage import merged_rows

    rows = fetch_all(
        """
        SELECT r.id, r.printed_label, r.value_text, r.unit_printed,
               r.reference_printed, r.section_id, s.heading_printed,
               a.display_name AS analyte_name, a.code AS analyte_code,
               r.is_reviewed, NULL::text AS corrected_from
        FROM   lab.results r
        LEFT   JOIN lab.report_sections s ON s.id = r.section_id
        LEFT   JOIN lab.analytes a ON a.id = r.analyte_id
        WHERE  r.document_id = %s AND r.practice_id = %s AND r.is_deleted = FALSE
        ORDER  BY r.section_id NULLS FIRST, r.sequence, r.id
    """,
        (document_id, practice_id),
    )
    if not rows:
        return {}
    return {p["panel_code"]: p for p in merged_rows(rows).get("panels", [])}


def judge(term: dict, detected: dict[str, dict], present: set[str], no_value: set[str]) -> dict:
    """One resolved term, judged against the page. doctor_order only.

    THE HEADLINE IS THE PANEL, NOT ITS PARTS
        "Was the CBC done?" is the question. Answering it with a list of twenty
        analyte names is answering a different one, and the reviewer has to read
        all twenty to work out that yes, the CBC is there.

        So the verdict is binary at panel level - present or not - taken from the
        panels already DETECTED on this document, which is the same judgement the
        coverage chips make. How much of it was read is real and secondary: it
        rides along as read/expected and the names of what is missing, for
        whoever wants to open the row.
    """
    out = dict(term)

    if term["kind"] == "unresolved":
        out["verdict"] = "unrecognised"
        return out

    if term["kind"] == "panel":
        code = term.get("panel_code")
        hit = detected.get(code) if code else None
        # Every member, core and optional - the same denominator the coverage
        # chips use, so one panel does not carry two different totals on one
        # screen. This counted core only, which is why the drawer and the chip
        # disagreed about the same panel.
        members = term["analytes"]
        found = [a for a in members if a["analyte_code"] in present]
        unread = [a for a in members if a["analyte_code"] in no_value]
        outstanding = [
            a
            for a in members
            if a["analyte_code"] not in present and a["analyte_code"] not in no_value
        ]
        # An optional test the lab did not run is settled, not a gap - so it
        # counts towards the numerator and is never named as missing. Only a
        # core test that is genuinely not there is a hole worth reporting.
        absent = [a for a in outstanding if a.get("is_core")]
        not_run = [a for a in outstanding if not a.get("is_core")]

        # Detected by the document, or - for a panel the detector did not claim -
        # present anyway if some of its core tests are on the page. The second
        # case is a panel printed without a heading the detector could use; the
        # tests are there and saying "not on this page" about them would be false.
        on_page = hit is not None or bool(found)

        out["verdict"] = "present" if on_page else "not_present"
        out["read"] = len(found)
        # What the drawer divides by expected, matching the coverage chip.
        out["accounted"] = len(found) + len(not_run)
        out["expected"] = len(members)
        out["not_run"] = [a["analyte_name"] or a["analyte_code"] for a in not_run]
        out["complete"] = on_page and not absent and not unread
        # What IS there, named. A reviewer confirming an order wants to see the
        # tests that came back, not only infer them from what did not - and on a
        # complete panel the absent list is empty, so without this the row has
        # nothing to show at all.
        out["on_page"] = [a["analyte_name"] or a["analyte_code"] for a in found]
        out["not_read"] = [a["analyte_name"] or a["analyte_code"] for a in unread]
        out["not_on_page"] = [a["analyte_name"] or a["analyte_code"] for a in absent]
        return out

    # A single test. The doctor asked for one thing; it is there or it is not.
    code = term["analytes"][0]["analyte_code"]
    name = term["analytes"][0]["analyte_name"] or code
    out["read"] = int(code in present)
    # One test has no optional half, so accounted and read are the same number.
    # Carried anyway so the browser reads one field for both kinds of term.
    out["accounted"] = int(code in present)
    out["expected"] = 1
    out["complete"] = code in present
    out["on_page"] = [name] if code in present else []
    out["not_read"] = [name] if code in no_value else []
    out["not_on_page"] = [] if (code in present or code in no_value) else [name]
    out["verdict"] = (
        "present" if code in present else "no_value" if code in no_value else "not_present"
    )
    return out


def summarise(terms: list[dict]) -> dict:
    """Counts for the headline. Each term lands in exactly one bucket."""
    buckets = {"present": 0, "not_present": 0, "no_value": 0, "unrecognised": 0}
    for t in terms:
        buckets[t.get("verdict", "unrecognised")] = (
            buckets.get(t.get("verdict", "unrecognised"), 0) + 1
        )
    buckets["total"] = len(terms)
    # Secondary: of the panels that ARE on the page, how many are whole. Separate
    # from the headline on purpose - an incomplete panel is still a panel that was
    # done, and conflating the two is what made the old box unreadable.
    buckets["incomplete"] = sum(
        1 for t in terms if t.get("verdict") == "present" and not t.get("complete", True)
    )
    return buckets


def read_lists(practice_id: int, document_id: int) -> dict:
    """Both lists for one document, resolved now rather than when they were typed.

    Re-resolving on read is why only the raw text is stored: a term that matched
    nothing last month resolves today if somebody added the alias, with no
    migration and no backfill.
    """
    stored = {
        r["kind"]: r
        for r in fetch_all(
            """
        SELECT kind, raw_text, updated_at, created_at
        FROM   lab.document_lists
        WHERE  document_id = %s AND practice_id = %s AND is_deleted = FALSE
    """,
            (document_id, practice_id),
        )
    }

    present = _present_codes(document_id)
    no_value = _no_value_codes(document_id)
    detected = _detected_panels(practice_id, document_id)

    out: dict = {}
    for kind in KINDS:
        row = stored.get(kind)
        raw = (row or {}).get("raw_text", "") or ""
        terms = resolve_terms(practice_id, split_terms(raw)) if raw.strip() else []
        if kind == "doctor_order":
            terms = [judge(t, detected, present, no_value) for t in terms]
            out[kind] = {"raw_text": raw, "terms": terms, "summary": summarise(terms)}
        else:
            # No verdict, by design. See the module docstring.
            out[kind] = {"raw_text": raw, "terms": terms}
        out[kind]["updated_at"] = (row or {}).get("updated_at") or (row or {}).get("created_at")
    return out
