"""Generate db/021_seed_benchmark_30.sql from db/seed/benchmark_30.py.

    python db/seed/export_benchmark.py

WHY A SECOND SEED AND NOT A BIGGER 004
    004 is generated from catalog.py, which is the CORPUS vocabulary - what the
    300 synthetic reports actually print. This is the BENCHMARK vocabulary -
    everything the 30-panel document says we should recognise, most of which the
    corpus never prints. Keeping them in separate files keeps that distinction
    legible: regenerate 004 and the corpus moved; regenerate 021 and the
    benchmark did.

    The two unions in the database. Nothing here restates or edits a row 004
    already inserted - every statement is ON CONFLICT DO NOTHING on the natural
    key, so running both in either order lands the same database.

WHAT IT WILL NOT DO
    Delete, rename or re-point anything. If the benchmark and catalog.py disagree
    about an analyte that already exists, this file leaves the existing row alone
    and the disagreement is reported at the end rather than silently resolved.
    A seed that quietly rewrites clinical vocabulary is not a seed.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "corpus" / "generator"))

import benchmark_30  # noqa: E402
import catalog  # noqa: E402

OUT = ROOT / "db" / "022_seed_benchmark_30.sql"


def q(value) -> str:
    if value is None or value == "":
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def main() -> None:
    existing_panels = set(catalog.PANELS)
    existing_analytes = set(catalog.ANALYTES)

    # An analyte's PRIMARY panel is the first one that lists it - panel_id on
    # lab.analytes still has to hold something, and the join table carries the
    # rest. Order in MEMBERS is the benchmark's own section order.
    primary: dict[str, str] = {}
    for panel, code, _role in benchmark_30.MEMBERS:
        primary.setdefault(code, panel)

    lines: list[str] = []
    add = lines.append
    add("-- =============================================================================")
    add("-- Contexta - Lab extraction store")
    add(
        f"-- 022  Seed: the 30-panel benchmark - {len(benchmark_30.PANELS)} panels, "
        f"{len(benchmark_30.ANALYTES)} new analytes"
    )
    add("-- =============================================================================")
    add("-- GENERATED FILE - do not edit by hand.")
    add("--   Source:     db/seed/benchmark_30.py")
    add("--               (itself read off Contexta_Lab_30_Panels_Full_Tabular_Benchmark.md)")
    add("--   Regenerate: python db/seed/export_benchmark.py")
    add("--")
    add("-- Requires 020 (lab.panel_analytes, the widened CHECK) and 021 (the column")
    add("-- itself widened to VARCHAR(20), without which every qualitative analyte")
    add("-- here fails to insert).")
    add("--")
    add("-- Every statement is ON CONFLICT DO NOTHING. This file ADDS vocabulary; it")
    add("-- never edits or removes a row that 004 already seeded. Where the benchmark")
    add("-- and catalog.py disagree about an analyte that already exists, the existing")
    add("-- row stands and the disagreement is listed at the bottom of this file.")
    add("-- =============================================================================")
    add("")
    add("BEGIN;")
    add("")

    # ----------------------------------------------------------- panels
    add("-- ---------------------------------------------------------------- panels")
    add("INSERT INTO lab.panels (code, display_name, description, is_core, sort_order)")
    add("VALUES")
    rows = []
    for code, name, number, is_core in benchmark_30.PANELS:
        note = f"Benchmark panel {number}"
        if code in existing_panels:
            note += " - already present from catalog; this row is a no-op"
        rows.append(
            f"    -- {note}\n"
            f"    ({q(code)}, {q(name)}, {q(f'Benchmark 30-panel reference, section {number}')}, "
            f"{'TRUE' if is_core else 'FALSE'}, {number * 10})"
        )
    add(",\n".join(rows))
    add("ON CONFLICT (code) DO NOTHING;")
    add("")

    # --------------------------------------------------- panel aliases
    add("-- ------------------------------------------------- the titles panels use")
    add("INSERT INTO lab.panel_aliases (panel_id, alias)")
    add("SELECT p.id, v.alias")
    add("FROM (VALUES")
    rows = []
    for panel, aliases in benchmark_30.PANEL_ALIASES.items():
        for alias in aliases:
            rows.append(f"    ({q(panel)}, {q(alias)})")
    add(",\n".join(rows))
    add(") AS v(panel_code, alias)")
    add("JOIN lab.panels p ON p.code = v.panel_code")
    add("ON CONFLICT DO NOTHING;")
    add("")

    # --------------------------------------------------------- analytes
    add("-- -------------------------------------------------------------- analytes")
    add("-- panel_id is the PRIMARY panel only. Full membership is in")
    add("-- lab.panel_analytes below, because one analyte belongs to several.")
    add("INSERT INTO lab.analytes (code, panel_id, display_name, value_type,")
    add("                          default_unit, is_derived, specimen, sort_order)")
    add("SELECT v.code, p.id, v.display_name, v.value_type, v.default_unit,")
    add("       v.is_derived, v.specimen, v.sort_order")
    add("FROM (VALUES")
    rows = []
    for i, (code, name, _syn, unit, vtype, calc, specimen) in enumerate(benchmark_30.ANALYTES):
        rows.append(
            f"    ({q(code)}, {q(primary.get(code))}, {q(name)}, {q(vtype)}, "
            f"{q(unit)}, {'TRUE' if calc else 'FALSE'}, {q(specimen)}, {i * 10})"
        )
    add(",\n".join(rows))
    add(") AS v(code, panel_code, display_name, value_type, default_unit,")
    add("       is_derived, specimen, sort_order)")
    add("LEFT JOIN lab.panels p ON p.code = v.panel_code")
    add("ON CONFLICT (code) DO NOTHING;")
    add("")

    # -------------------------------------------------- analyte aliases
    add("-- ---------------------------------------------- every spelling they print")
    add("-- This is what makes the new analytes DETECTABLE. Without the aliases the")
    add("-- codes exist and no printed label ever resolves to them.")
    add("INSERT INTO lab.analyte_aliases (analyte_id, alias, source, confidence)")
    add("SELECT a.id, v.alias, 'seed', 1.0")
    add("FROM (VALUES")
    rows = []
    seen: set[str] = set()
    for code, name, synonyms, *_ in benchmark_30.ANALYTES:
        for alias in [name, code, *synonyms]:
            k = "".join(ch for ch in alias.lower() if ch.isalnum())
            if k and k not in seen:
                seen.add(k)
                rows.append(f"    ({q(code)}, {q(alias)})")
    add(",\n".join(rows))
    add(") AS v(analyte_code, alias)")
    add("JOIN lab.analytes a ON a.code = v.analyte_code")
    add("ON CONFLICT DO NOTHING;")
    add("")

    # ------------------------------------------------------- membership
    add("-- ------------------------------------------------------------ membership")
    add("-- Many-to-many, per benchmark section 11 rule 2. The role is the")
    add("-- benchmark's own: core and common are worth flagging when absent,")
    add("-- optional and derived are not.")
    add("INSERT INTO lab.panel_analytes (panel_id, analyte_id, role, is_core,")
    add("                                sort_order, source)")
    add("SELECT p.id, a.id, v.role, v.is_core, v.sort_order, 'benchmark_v1'")
    add("FROM (VALUES")
    rows = []
    order: dict[str, int] = {}
    for panel, code, role in benchmark_30.MEMBERS:
        n = order[panel] = order.get(panel, 0) + 10
        rows.append(
            f"    ({q(panel)}, {q(code)}, {q(role)}, "
            f"{'TRUE' if benchmark_30.is_core(role) else 'FALSE'}, {n})"
        )
    add(",\n".join(rows))
    add(") AS v(panel_code, analyte_code, role, is_core, sort_order)")
    add("JOIN lab.panels   p ON p.code = v.panel_code")
    add("JOIN lab.analytes a ON a.code = v.analyte_code")
    add("ON CONFLICT DO NOTHING;")
    add("")
    add("COMMIT;")
    add("")

    # ------------------------------------------------- the disagreements
    clashes = [c for c, *_ in benchmark_30.ANALYTES if c in existing_analytes]
    repanelled = [
        (code, catalog.ANALYTES[code].get("panel"), primary[code])
        for code in primary
        if code in existing_analytes
        and catalog.ANALYTES[code].get("panel")
        and catalog.ANALYTES[code].get("panel") != primary[code]
    ]
    add("-- =============================================================================")
    add("-- Where the benchmark and the existing master disagree")
    add("-- =============================================================================")
    if clashes:
        add(f"-- {len(clashes)} analyte code(s) defined in BOTH. The existing row stands:")
        for code in clashes:
            add(f"--   {code}")
    else:
        add("-- No analyte code is defined in both. Nothing was shadowed.")
    add("--")
    if repanelled:
        add(f"-- {len(repanelled)} analyte(s) whose PRIMARY panel differs from catalog.py.")
        add("-- panel_id is left as catalog set it; the benchmark's grouping is expressed")
        add("-- through lab.panel_analytes instead, which is the point of the join table:")
        for code, was, now in repanelled:
            add(f"--   {code:16} catalog says {was:16} benchmark says {now}")
    else:
        add("-- No analyte changes its primary panel.")
    add("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(
        f"  panels         {len(benchmark_30.PANELS)}  ({len([p for p in benchmark_30.PANELS if p[0] not in existing_panels])} new)"
    )
    print(f"  analytes       {len(benchmark_30.ANALYTES)} new")
    print(f"  aliases        {len(seen)}")
    print(f"  membership     {len(benchmark_30.MEMBERS)} rows")
    print(f"  code clashes   {len(clashes)}")
    print(f"  re-panelled    {len(repanelled)}")


if __name__ == "__main__":
    main()
