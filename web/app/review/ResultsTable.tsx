"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { DocRow, DocRows } from "@/lib/api";
import { Cell } from "./Cell";

const VERDICT: Record<string, string> = {
  found: "found",
  confirm: "confirm?",
  missing: "missing",
  no_value: "no value",
  extra: "extra",
  absent: "not present",
};

/**
 * The one table.
 *
 * What the page printed and what we resolved it to, side by side, with the
 * verdict carried by the row itself. There used to be a coverage panel and a
 * results table, and a reviewer had to hold one in their head while reading
 * the other. A missing core analyte now sits in the table with an empty value
 * cell, so you see the hole where the number should be rather than reading a
 * count somewhere else.
 *
 * Six verdicts, and each means something different. The two that get confused:
 * MISSING means the lab did not run it, "no value" means the test is printed
 * on the page and WE failed to read its value - only one of those is our bug.
 * And "extra" is a row the document CONTAINS, never a failure to find one.
 */
export function ResultsTable({
  documentId, rows, onChanged,
}: {
  documentId: string;
  rows: DocRows | null;
  onChanged: () => void;
}) {
  if (!rows) return <div className="card empty">Loading results…</div>;
  if (rows.rows.length === 0) {
    return (
      <div className="card empty">
        No rows came out of this page. It may be a scan the engine could not
        read, or a layout it did not recognise as a table.
      </div>
    );
  }

  // Grouped by the panel or printed heading each row belongs to, in the order
  // they arrive, so the table still reads like the document does.
  const groups: { name: string; rows: DocRow[] }[] = [];
  for (const r of rows.rows) {
    const name = r.section ?? r.panel ?? "Results";
    const last = groups[groups.length - 1];
    if (last && last.name === name) last.rows.push(r);
    else groups.push({ name, rows: [r] });
  }

  return (
    <div className="card">
      <div className="spread" style={{ marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>Results</h2>
        <span className="faint">
          {rows.panels.length
            ? rows.panels.map((p) => `${p.panel_name} ${p.found}/${p.expected}`).join(" · ")
            : `${rows.rows.length} rows`}
        </span>
      </div>
      {rows.note && <div className="empty" style={{ marginBottom: 8 }}>{rows.note}</div>}

      <div className="results-wrap">
        <table className="editable">
          <thead>
            <tr>
              <th>Status</th>
              <th>Analyte (ours)</th>
              <th>Code</th>
              <th>Req</th>
              <th>Printed as</th>
              <th className="num">Value</th>
              <th>Unit</th>
              <th>Flag</th>
              <th>Reference</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {groups.map((g, gi) => (
              <React.Fragment key={`${g.name}-${gi}`}>
                <tr className="grouphead"><td colSpan={10}>{g.name}</td></tr>
                {g.rows.map((r, i) => (
                  <Line
                    key={r.result_id ?? `x${gi}-${i}`}
                    documentId={documentId}
                    row={r}
                    onChanged={onChanged}
                  />
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/**
 * One line.
 *
 * Owns its own saving state, so the row that lights up is the one being
 * saved. A single flag on the table would light all of them, and a reviewer
 * needs to see which edit landed.
 */
function Line({
  documentId, row, onChanged,
}: {
  documentId: string;
  row: DocRow;
  onChanged: () => void;
}) {
  const [current, setCurrent] = useState<DocRow>(row);
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [why, setWhy] = useState<string | null>(null);
  const [gone, setGone] = useState(false);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => setCurrent(row), [row]);

  async function save(patch: Record<string, string>) {
    if (!current.result_id) return;
    setState("saving");
    setWhy(null);
    try {
      const updated = await api.correctResult(documentId, current.result_id, patch);
      setCurrent({
        ...current,
        printed_label: updated.printed_label,
        analyte_code: updated.analyte_code,
        analyte_name: updated.analyte_name ?? current.analyte_name,
        value_text: updated.value_text,
        unit: updated.unit,
        flag: updated.flag,
        reference_printed: updated.reference_printed,
        is_reviewed: true,
      });
      setState("saved");
      setTimeout(() => setState("idle"), 1200);
      // The verdict can change with the mapping, and that is decided by the
      // template on the server - not something to guess at here.
      onChanged();
    } catch (e) {
      setState("error");
      setWhy(e instanceof Error ? e.message : "Could not save that");
    }
  }

  async function remove() {
    if (!current.result_id) return;
    setState("saving");
    try {
      await api.removeResult(documentId, current.result_id);
      setGone(true);
      onChanged();
    } catch (e) {
      setState("error");
      setWhy(e instanceof Error ? e.message : "Could not remove that row");
    }
  }

  if (gone) return null;

  const feedback = state === "saving" ? " saving"
    : state === "saved" ? " saved"
    : state === "error" ? " rowerr" : "";

  return (
    <>
      <tr className={`st-${current.status}${feedback}`}>
        <td className="status">
          <span className="dot" style={{ background: "currentColor" }} />
          {VERDICT[current.status] ?? current.status}
        </td>
        <td>{current.analyte_name ?? <span className="faint">—</span>}</td>

        {current.editable ? (
          <>
            <td>
              <Cell value={current.analyte_code} className="mono"
                    onSave={(v) => save({ analyte_code: v })} />
            </td>
            <td className="faint">{current.required || "—"}</td>
            <td><Cell value={current.printed_label} onSave={(v) => save({ label: v })} /></td>
            <td><Cell value={current.value_text} className="num" onSave={(v) => save({ value: v })} /></td>
            <td><Cell value={current.unit} onSave={(v) => save({ unit: v })} /></td>
            <td><Cell value={current.flag} onSave={(v) => save({ flag: v })} /></td>
            <td><Cell value={current.reference_printed} onSave={(v) => save({ reference: v })} /></td>
            <td style={{ width: 34 }}>
              {/* Two presses to remove. One press is how a row disappears
                  while somebody is reaching for the scrollbar. */}
              <button
                className="rm"
                aria-pressed={confirming}
                title={confirming ? "Press again to remove" : "Remove this row"}
                onClick={() => (confirming ? remove() : setConfirming(true))}
                onBlur={() => setConfirming(false)}
              >
                {confirming ? "sure?" : "×"}
              </button>
            </td>
          </>
        ) : (
          <>
            <td className="mono">{current.analyte_code ?? "—"}</td>
            <td className="faint">{current.required || "—"}</td>
            <td colSpan={5} className="void">not printed on this page</td>
            <td />
          </>
        )}
      </tr>

      {why && (
        <tr className="rowerr">
          <td colSpan={10} className="faint" style={{ padding: "4px 10px" }}>{why}</td>
        </tr>
      )}
      {current.corrected_from && (
        <tr>
          <td colSpan={10} className="faint" style={{ padding: "2px 10px", fontSize: 11 }}>
            read as {current.corrected_from} before it was corrected — kept, because that
            is what the alias master learns from
          </td>
        </tr>
      )}
    </>
  );
}
