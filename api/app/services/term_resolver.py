"""One printed or typed term to what the master makes of it.

WHY THIS IS ITS OWN MODULE
    Three callers need the same answer and must not disagree about it: the batch
    endpoint behind the analyte checklist, the document lists a clinician types,
    and anything else that takes free text from a person. Written twice, the two
    copies drift, and then the same word resolves differently depending on which
    box it was typed into - which is indefensible on a screen where both boxes
    are visible at once.

WHAT IT RESOLVES, AND IN WHAT ORDER
    1. A PANEL.  "CBC" means seventeen tests, not a test called CBC. Panels are
       tried first for exactly that reason.
    2. A CANONICAL CODE.  "UREA" typed as itself. fn_resolve_analyte matches
       printed LABELS through the alias table and a code is not an alias of
       itself, so this needs its own pass or UREA falls through the whole funnel.
    3. AN ANALYTE, through lab.fn_resolve_analyte - the same three passes, the
       same thresholds, the same vocabulary that read the document.

    Nothing matches: the term comes back unresolved with its nearest spellings,
    never folded in with tests the lab genuinely did not report. "We do not know
    this word" and "the lab did not run this test" are different facts and only
    one of them is about the document.
"""

from __future__ import annotations

from app.db import fetch_all

#: A human list is an order set or a protocol; those do not run to hundreds. The
#: cap stops a paste accident becoming hundreds of resolver calls, and it is
#: reported rather than silently trimming terms somebody believes they are using.
MAX_TERMS = 200


def split_terms(text: str) -> list[str]:
    """Free text to terms. Newlines, commas, semicolons, tabs; numbering dropped."""
    import re
    out: list[str] = []
    seen: set[str] = set()
    for chunk in re.split(r"[\n,;\t]+", text or ""):
        term = re.sub(r"^\s*(?:\d+[.)]|[-*•])\s*", "", chunk).strip()
        key = term.lower()
        if term and key not in seen:
            seen.add(key)
            out.append(term)
    return out[:MAX_TERMS]


def resolve_terms(practice_id: int, labels: list[str]) -> list[dict]:
    """Each term, and what it is. See the module docstring for the order."""
    out: list[dict] = []
    for term in labels:
        # 1. a panel
        panel = fetch_all(
            "SELECT * FROM lab.fn_resolve_panel(%s::BIGINT, %s::TEXT, %s::REAL)",
            (practice_id, term, 0.72))
        if panel:
            members = fetch_all(
                "SELECT a.code, a.display_name, pa.is_core "
                "FROM   lab.panel_analytes pa "
                "JOIN   lab.panels   p ON p.id = pa.panel_id "
                "JOIN   lab.analytes a ON a.id = pa.analyte_id "
                "WHERE  p.code = %s AND pa.is_deleted = FALSE "
                "  AND  a.is_deleted = FALSE AND a.is_active = TRUE "
                "ORDER  BY pa.sort_order, a.code",
                (panel[0]["panel_code"],))
            if members:
                name = fetch_all("SELECT display_name FROM lab.panels WHERE code = %s",
                                 (panel[0]["panel_code"],))
                out.append({
                    "input": term,
                    "kind": "panel",
                    "panel_code": panel[0]["panel_code"],
                    "panel_name": name[0]["display_name"] if name else panel[0]["panel_code"],
                    "match_method": panel[0]["match_method"],
                    "confidence": float(panel[0]["confidence"]),
                    "analytes": [{"analyte_code": m["code"],
                                  "analyte_name": m["display_name"],
                                  "is_core": bool(m["is_core"]),
                                  "from_panel": panel[0]["panel_code"]}
                                 for m in members],
                })
                continue

        # 2. a canonical code typed as itself
        code_hit = fetch_all(
            "SELECT code, display_name FROM lab.analytes "
            "WHERE upper(code) = upper(%s) AND is_deleted = FALSE AND is_active = TRUE",
            (term,))
        if code_hit:
            out.append(_one_analyte(term, code_hit[0]["code"],
                                    code_hit[0]["display_name"], "canonical_code", 1.0))
            continue

        # 3. a printed label, through the funnel the extractor itself uses
        rows = fetch_all(
            "SELECT * FROM lab.fn_resolve_analyte(%s::BIGINT, %s::TEXT, "
            "                                     %s::BIGINT, %s::REAL)",
            (practice_id, term, None, 0.45))
        if rows:
            name = fetch_all("SELECT display_name FROM lab.analytes WHERE id = %s",
                             (rows[0]["analyte_id"],))
            out.append(_one_analyte(term, rows[0]["analyte_code"],
                                    name[0]["display_name"] if name else None,
                                    rows[0]["match_method"],
                                    float(rows[0]["confidence"])))
            continue

        # Nothing. Offer the nearest spellings we hold - a hint for a person,
        # never a guess written anywhere.
        near = fetch_all(
            "SELECT al.alias AS label, a.code, "
            "       similarity(al.alias_normalised, "
            "                  regexp_replace(lower(%s), '[^a-z0-9]+', '', 'g')) AS sim "
            "FROM   lab.analyte_aliases al "
            "JOIN   lab.analytes a ON a.id = al.analyte_id "
            "WHERE  al.is_deleted = FALSE AND a.is_deleted = FALSE "
            "  AND  similarity(al.alias_normalised, "
            "                  regexp_replace(lower(%s), '[^a-z0-9]+', '', 'g')) > 0.25 "
            "ORDER  BY sim DESC LIMIT 3",
            (term, term))
        out.append({
            "input": term,
            "kind": "unresolved",
            "analytes": [],
            "did_you_mean": [{"label": n["label"], "analyte_code": n["code"]}
                             for n in near],
        })
    return out


def _one_analyte(term: str, code: str, name: str | None,
                 method: str, confidence: float) -> dict:
    return {
        "input": term,
        "kind": "analyte",
        "match_method": method,
        "confidence": confidence,
        "analytes": [{"analyte_code": code, "analyte_name": name,
                      "is_core": True, "from_panel": None}],
    }
