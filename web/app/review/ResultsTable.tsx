"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { DocRow, DocRows, MasterAnalyte } from "@/lib/api";
import { Cell } from "./Cell";
import { PanelChips, CoverageLegend } from "@/components/PanelChips";
import { Seg, Find, HiddenNote } from "@/components/Filters";
import { OrderLists } from "@/components/OrderLists";

const VERDICT: Record<string, string> = {
  found: "found",
  confirm: "confirm?",
  missing: "missing",
  no_value: "no value",
  extra: "extra",
  absent: "not present",
};

/** The verdicts that ask something of a reviewer. `found` is already right and
 *  `absent` is a test the lab never ran - neither is work. */
const WANTS_ATTENTION = new Set(["confirm", "missing", "no_value", "extra"]);

type Show = "all" | "attention";
type Req = "all" | "core" | "optional";
type List = "all" | "on" | "off";

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
 *
 * FILTERING. A forty-row health check asks the reviewer to find three problem
 * rows by reading forty. The filters narrow that, and every one of them is
 * reversible in one press and says what it cost - see HiddenNote. Nothing is
 * filtered by default: the first thing a reviewer sees is the whole document,
 * because a default that hides rows is a default that hides mistakes.
 */
export function ResultsTable({
  documentId, rows, onChanged,
}: {
  documentId: string;
  rows: DocRows | null;
  onChanged: () => void;
}) {
  const [show, setShow] = useState<Show>("all");
  const [req, setReq] = useState<Req>("all");
  const [panel, setPanel] = useState<string | null>(null);
  const [find, setFind] = useState("");
  const [list, setList] = useState<List>("all");
  const wanted = null as null | { codes: Map<string, unknown> };
  const onList = useCallback(
    (r: DocRow) => !!(wanted && r.analyte_code && wanted.codes.has(r.analyte_code)),
    [wanted]);

  const all = useMemo(() => rows?.rows ?? [], [rows]);

  // Each predicate on its own, so a segment's count can be computed against
  // every filter EXCEPT itself. A "Core 12" that ignores the panel you already
  // filtered to is a lie about what pressing it will do.
  const preds = useMemo(() => {
    const needle = find.trim().toLowerCase();
    const nameOf = new Map((rows?.panels ?? []).map((p) => [p.panel_code, p.panel_name]));
    return {
      panel: (r: DocRow) =>
        !panel || r.panel === panel || r.panel === nameOf.get(panel)
        || r.section === nameOf.get(panel),
      show: (r: DocRow) => show === "all" || WANTS_ATTENTION.has(r.status),
      req: (r: DocRow) => req === "all" || r.required === req,
      list: (r: DocRow) =>
        list === "all" || !wanted || (list === "on" ? onList(r) : !onList(r)),
      find: (r: DocRow) =>
        !needle
        || (r.printed_label ?? "").toLowerCase().includes(needle)
        || (r.analyte_name ?? "").toLowerCase().includes(needle)
        || (r.analyte_code ?? "").toLowerCase().includes(needle),
    };
  }, [panel, show, req, find, list, wanted, onList, rows?.panels]);

  const visible = useMemo(
    () => all.filter((r) => preds.panel(r) && preds.show(r) && preds.req(r)
                         && preds.find(r) && preds.list(r)),
    [all, preds],
  );

  const count = (own: keyof typeof preds, extra: (r: DocRow) => boolean) =>
    all.filter((r) => extra(r)
      && (own === "show"  || preds.show(r))
      && (own === "req"   || preds.req(r))
      && (own === "list"  || preds.list(r))
      && preds.panel(r) && preds.find(r)).length;

  // Every analyte this document mentions at all, whatever verdict it carries -
  // what the checklist reconciles against.
  const presentCodes = useMemo(() => {
    const s = new Set<string>();
    for (const r of all) {
      if (r.analyte_code && r.status !== "missing" && r.status !== "absent") {
        s.add(r.analyte_code);
      }
    }
    return s;
  }, [all]);

  if (!rows) return <div className="card empty">Loading results…</div>;
  if (all.length === 0) {
    return (
      <div className="card empty">
        No rows came out of this page. It may be a scan the engine could not
        read, or a layout it did not recognise as a table.
      </div>
    );
  }

  // Grouped by the panel or printed heading each row belongs to, in the order
  // they arrive, so the table still reads like the document does. A group left
  // with no visible rows is dropped rather than printed as a bare heading.
  const groups: { name: string; rows: DocRow[] }[] = [];
  for (const r of visible) {
    const name = r.section ?? r.panel ?? "Results";
    const last = groups[groups.length - 1];
    if (last && last.name === name) last.rows.push(r);
    else groups.push({ name, rows: [r] });
  }

  const hidden = all.length - visible.length;
  const filtered = show !== "all" || req !== "all" || panel !== null
                || find.trim() !== "" || list !== "all";
  function clearAll() {
    // The typed list itself is NOT cleared here: it is a thing the reviewer
    // built and carries across documents, not a view setting.
    setShow("all"); setReq("all"); setPanel(null); setFind(""); setList("all");
  }

  return (
    <div className="card">
      {/* The doctor's order sits with the results it is checked against -
          it used to float between the patient card and this one. */}
      <div className="results-head">
        <h2>Results</h2>
        <div className="results-head-side">
          {rows.panels.length > 0
            ? <PanelChips panels={rows.panels} active={panel} onPick={setPanel} />
            : <span className="faint">{all.length} rows</span>}
          <OrderLists documentId={documentId} />
        </div>
      </div>

      {/* The real row count, not the expected count. They differ whenever the
          page printed something no template lists, and the legend used to
          claim the latter while the table showed the former. */}
      <CoverageLegend panels={rows.panels} rows={all.length} />


      {rows.note && <div className="empty" style={{ marginBottom: 8 }}>{rows.note}</div>}

      <div className="filters">
        <Seg<Show>
          label="Show"
          value={show}
          onChange={setShow}
          options={[
            { value: "all", label: "All", count: count("show", () => true) },
            {
              value: "attention",
              label: "Needs attention",
              count: count("show", (r) => WANTS_ATTENTION.has(r.status)),
            },
          ]}
        />
        <Seg<Req>
          label="Required"
          value={req}
          onChange={setReq}
          options={[
            { value: "all", label: "All", count: count("req", () => true) },
            { value: "core", label: "Core", count: count("req", (r) => r.required === "core") },
            {
              value: "optional",
              label: "Optional",
              count: count("req", (r) => r.required === "optional"),
            },
          ]}
        />
        {wanted && (
          <Seg<List>
            label="List"
            value={list}
            onChange={setList}
            options={[
              { value: "all", label: "All", count: count("list", () => true) },
              { value: "on", label: "On my list", count: count("list", onList) },
              { value: "off", label: "Not on it",
                count: count("list", (r) => !onList(r)) },
            ]}
          />
        )}
        <Find
          value={find}
          onChange={setFind}
          placeholder="Find a test…  /"
          hint="Filter rows by printed label, analyte name or code"
        />
        {filtered && (
          <button onClick={clearAll} style={{ fontSize: 12, padding: "4px 10px" }}>
            Clear filters
          </button>
        )}
      </div>

      <div className="results-wrap">
        <table className="editable">
          <thead>
            <tr>
              {wanted && <th className="lc" title="On the list you typed">List</th>}
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
                <tr className="grouphead">
                  <td colSpan={wanted ? 11 : 10}>{g.name}</td>
                </tr>
                {g.rows.map((r, i) => (
                  <Line
                    key={r.result_id ?? `x${gi}-${i}`}
                    documentId={documentId}
                    row={r}
                    onChanged={onChanged}
                    listed={wanted ? onList(r) : null}
                  />
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>

        {visible.length === 0 && (
          <div className="no-match">
            No rows match these filters. {all.length} row{all.length === 1 ? "" : "s"} on
            this document.
          </div>
        )}
      </div>

      <AddLine documentId={documentId} onAdded={onChanged} />

      <HiddenNote hidden={hidden} onClear={clearAll} />
    </div>
  );
}

/** What a person typed into the small row forms, as the API takes it. */
function typed(form: HTMLFormElement): Record<string, string> {
  const data = new FormData(form);
  const out: Record<string, string> = {};
  for (const key of ["unit", "flag", "reference"]) {
    const v = String(data.get(key) ?? "").trim();
    if (v) out[key] = v;
  }
  return out;
}

/**
 * A test the panel expected that the reading did not find - though the page
 * may well print it (Albumin on page four). The person reads it off the page
 * and types it here; it is stored as their entry, through lab.fn_add_result.
 */
function FillIn({ documentId, row, onChanged }: {
  documentId: string;
  row: DocRow;
  onChanged: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [why, setWhy] = useState<string | null>(null);

  if (!open) {
    return (
      <td colSpan={5} className="void">
        not printed on this page{" "}
        <button type="button" className="linkish" onClick={() => setOpen(true)}>
          It is - add the value
        </button>
      </td>
    );
  }

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    setBusy(true);
    setWhy(null);
    try {
      await api.addResult(documentId, {
        ...typed(form),
        value: String(new FormData(form).get("value") ?? ""),
        analyte_code: row.analyte_code ?? undefined,
        heading: row.section ?? undefined,
      });
      onChanged(); // the row comes back found, with its value
    } catch (err) {
      setWhy(err instanceof Error ? err.message : "Could not add that.");
      setBusy(false);
    }
  }

  return (
    <td colSpan={5}>
      <form className="row-form" onSubmit={submit}>
        <input name="value" placeholder="Value" aria-label="Value" required autoFocus />
        <input name="unit" placeholder="Unit" aria-label="Unit" />
        <input name="flag" placeholder="Flag" aria-label="Flag" size={5} />
        <input name="reference" placeholder="Reference" aria-label="Reference" />
        <button className="primary small" disabled={busy}>Add</button>
        <button type="button" className="small" onClick={() => setOpen(false)}>Cancel</button>
        {why && <span className="row-form-why">{why}</span>}
      </form>
    </td>
  );
}

const optionText = (t: MasterAnalyte) => `${t.display_name} · ${t.code}`;

/**
 * A line the reading missed entirely. Any of our tests, found by name or
 * code; or, for one we do not know, the name as printed and no code - the
 * same honest blank an unknown label gets when it is read.
 */
function AddLine({ documentId, onAdded }: { documentId: string; onAdded: () => void }) {
  const [open, setOpen] = useState(false);
  const [tests, setTests] = useState<MasterAnalyte[]>([]);
  const [busy, setBusy] = useState(false);
  const [why, setWhy] = useState<string | null>(null);

  useEffect(() => {
    if (open) api.masterAnalytes().then(setTests).catch(() => setTests([]));
  }, [open]);

  if (!open) {
    return (
      <button type="button" className="add-line" onClick={() => setOpen(true)}>
        + Add a line the reading missed
      </button>
    );
  }

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const name = String(new FormData(form).get("test") ?? "").trim();
    const known = tests.find((t) => optionText(t) === name);
    setBusy(true);
    setWhy(null);
    try {
      await api.addResult(documentId, {
        ...typed(form),
        value: String(new FormData(form).get("value") ?? ""),
        ...(known ? { analyte_code: known.code } : { label: name }),
      });
      form.reset();
      setOpen(false);
      onAdded();
    } catch (err) {
      setWhy(err instanceof Error ? err.message : "Could not add that.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="row-form add-line-form" onSubmit={submit}>
      <input
        name="test"
        list={`tests-${documentId}`}
        placeholder="Test - search ours, or type it as printed"
        aria-label="Test"
        required
        autoFocus
        className="test"
      />
      <datalist id={`tests-${documentId}`}>
        {tests.map((t) => <option key={t.code} value={optionText(t)} />)}
      </datalist>
      <input name="value" placeholder="Value" aria-label="Value" required />
      <input name="unit" placeholder="Unit" aria-label="Unit" />
      <input name="flag" placeholder="Flag" aria-label="Flag" size={5} />
      <input name="reference" placeholder="Reference" aria-label="Reference" />
      <button className="primary small" disabled={busy}>Add</button>
      <button type="button" className="small" onClick={() => setOpen(false)}>Cancel</button>
      {why && <span className="row-form-why">{why}</span>}
    </form>
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
  documentId, row, onChanged, listed,
}: {
  documentId: string;
  row: DocRow;
  onChanged: () => void;
  /** null when no checklist is active - then the column is not rendered at all */
  listed: boolean | null;
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
      <tr className={`st-${current.status}${feedback}${listed ? " listed" : ""}`}>
        {listed !== null && (
          <td className="lc">
            {listed
              ? <span className="tick" title="On your list">✓</span>
              : <span className="sr-only">not on your list</span>}
          </td>
        )}
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
            <FillIn documentId={documentId} row={current} onChanged={onChanged} />
            <td />
          </>
        )}
      </tr>

      {why && (
        <tr className="rowerr">
          <td colSpan={listed !== null ? 11 : 10} className="faint"
              style={{ padding: "4px 10px" }}>{why}</td>
        </tr>
      )}
      {current.corrected_from && (
        <tr>
          <td colSpan={listed !== null ? 11 : 10} className="faint"
              style={{ padding: "2px 10px", fontSize: 11 }}>
            read as {current.corrected_from} before it was corrected — kept, because that
            is what the alias master learns from
          </td>
        </tr>
      )}
    </>
  );
}
