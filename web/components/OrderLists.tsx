"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { DocLists, ListTerm, PanelRow } from "@/lib/api";

/**
 * What was ordered, and what the patient said they were tested for.
 *
 * THE ANSWER IS THE PANEL. THE ANALYTES ARE THE FOOTNOTE.
 *   The question is "was the CBC done?". The box this replaced answered it by
 *   listing twenty analyte names, so a reviewer had to read all twenty to work
 *   out that yes, it was. Here the row says CBC ✓ and nothing else until asked;
 *   press it and the missing tests are there.
 *
 * TWO LISTS, TWO MEANINGS
 *   The doctor's is intent, so the page is judged against it. The patient's is
 *   context: resolved so rows can be highlighted, never scored. They are styled
 *   differently because identical styling would be a visual claim that they mean
 *   the same thing.
 *
 * WHY A DRAWER
 *   Inline, this pushed the results table down on every document, for a feature
 *   used on some of them. Over the right edge it costs nothing when closed, and
 *   the PDF and the table stay where they were while it is open.
 */

const QUICK_LIMIT = 10;

// The quick chips' panels change only with a migration. Fetched once per page
// load rather than once per document opened - against a distant database every
// request is a third of a second.
let corePanels: Promise<PanelRow[]> | null = null;
function loadCorePanels(): Promise<PanelRow[]> {
  corePanels ??= api.panels(true).catch((e: unknown) => { corePanels = null; throw e; });
  return corePanels;
}

type Kind = "doctor_order" | "patient_tag";

export function OrderLists({ documentId }: { documentId: string }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<DocLists | null>(null);
  const [panels, setPanels] = useState<PanelRow[]>([]);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const latest = useRef(0);
  const panelRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    const mine = ++latest.current;
    try {
      const d = await api.documentLists(documentId);
      if (mine !== latest.current) return;
      setData(d);
      setDraft({ doctor_order: d.doctor_order.raw_text,
                 patient_tag: d.patient_tag.raw_text });
      setError(null);
    } catch (e) {
      if (mine !== latest.current) return;
      setError(e instanceof Error ? e.message : "Could not load the lists");
    }
  }, [documentId]);

  useEffect(() => { void load(); }, [load]);

  // The quick chips are the core panels, so the list maintains itself as the
  // master grows rather than being a hand-written copy that drifts.
  useEffect(() => {
    loadCorePanels().then((p) => setPanels(p.slice(0, QUICK_LIMIT))).catch(() => {});
  }, []);

  // Escape closes it, and focus moves into the drawer when it opens - a panel
  // that traps neither is one a keyboard user cannot leave or reach.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    panelRef.current?.querySelector("textarea")?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  /** Save one list - for the doctor's, that is also the check. The only thing
   *  that talks to the server: chips and typing edit the text and nothing else. */
  async function save(kind: Kind) {
    const sent = draft[kind] ?? "";
    setSaving(kind);
    setError(null);
    try {
      const d = await api.saveDocumentList(documentId, kind, sent);
      setData(d);
      // Take the server's copy of the list just saved, unless it was edited while
      // the request was out - then the edit wins and the result reads as stale.
      // The other list's unsaved text is never touched.
      setDraft((cur) => ({ ...cur, [kind]: cur[kind] === sent ? d[kind].raw_text : cur[kind] }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save that list");
    } finally {
      setSaving(null);
    }
  }

  /** Press a quick chip: add the panel to that list, or take it out again.
   *  Only the text changes. Checking on every press sent a request per chip -
   *  seconds each against a distant database - and greyed the chips out while it
   *  ran; now nothing is sent until Check. */
  function toggleQuick(kind: Kind, name: string) {
    const lines = (draft[kind] ?? "").split("\n").map((l) => l.trim()).filter(Boolean);
    const at = lines.findIndex((l) => l.toLowerCase() === name.toLowerCase());
    const next = at >= 0
      ? [...lines.slice(0, at), ...lines.slice(at + 1)]
      : [...lines, name];
    setDraft({ ...draft, [kind]: next.join("\n") });
  }

  /** Which chips read as pressed, per list. */
  const chosenIn = (kind: Kind) =>
    new Set((draft[kind] ?? "").split("\n")
              .map((l) => l.trim().toLowerCase()).filter(Boolean));

  const sum = data?.doctor_order.summary;
  const extra = data?.doctor_order.additional ?? [];
  const tagged = data?.patient_tag.terms.length ?? 0;
  // The shown result belongs to the list as last checked. Once the text differs,
  // it stays in view - greyed - until Check brings it up to date.
  const orderStale = data != null && (draft.doctor_order ?? "") !== data.doctor_order.raw_text;
  const tagUnsaved = data != null && (draft.patient_tag ?? "") !== data.patient_tag.raw_text;

  return (
    <>
      <button className="lists-open" onClick={() => setOpen(true)}>
        Ordered &amp; tagged
        {sum && sum.total > 0 && <span className="lists-n">Dr {sum.total}</span>}
        {tagged > 0 && <span className="lists-n alt">Patient {tagged}</span>}
        {sum && sum.not_present > 0 && (
          <span className="lists-alarm">{sum.not_present} not done</span>
        )}
        {extra.length > 0 && <span className="lists-n alt">+{extra.length} not ordered</span>}
      </button>

      {open && (
        <>
          <div className="drawer-veil" onClick={() => setOpen(false)} aria-hidden="true" />
          <aside className="drawer" ref={panelRef} role="dialog" aria-modal="true"
                 aria-label="Ordered and tagged tests">
            <header className="drawer-head">
              <h2>Ordered &amp; tagged</h2>
              <button className="drawer-x" onClick={() => setOpen(false)}
                      aria-label="Close">×</button>
            </header>

            <div className="drawer-body">
              {error && <div className="error" style={{ marginBottom: 12 }}>{error}</div>}

              {/* ------------------------------------------- the order */}
              <section className="dsec order">
                <h3>Doctor asked for</h3>
                <p className="dhint">Panels or tests, one per line. Checked against this page.</p>
                <QuickChips panels={panels} chosen={chosenIn("doctor_order")}
                            onToggle={(n) => toggleQuick("doctor_order", n)} />
                <textarea
                  rows={3}
                  value={draft.doctor_order ?? ""}
                  placeholder={"CBC\nLipid Profile\nTSH"}
                  onChange={(e) => setDraft({ ...draft, doctor_order: e.target.value })}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                      e.preventDefault(); void save("doctor_order");
                    }
                  }}
                />
                <div className="row" style={{ marginTop: 6 }}>
                  <button className="primary" disabled={saving !== null}
                          onClick={() => void save("doctor_order")}>
                    {saving === "doctor_order" ? "Checking…" : "Check"}
                  </button>
                  <span className="faint">Ctrl+Enter</span>
                </div>

                {sum && sum.total > 0 && (
                  <>
                    {orderStale && saving !== "doctor_order" && (
                      <p className="stale-note">List changed - press Check to see it against this page.</p>
                    )}
                    <div className={`dres${orderStale ? " stale" : ""}`}>
                      <p className="dsum">
                        <b>{sum.present}</b> of <b>{sum.total}</b> on this page
                        {sum.incomplete > 0 && <>, <b>{sum.incomplete}</b> partly</>}
                        {sum.not_present > 0 && <> · <b>{sum.not_present}</b> not done</>}
                        {extra.length > 0 && <> · <b>{extra.length}</b> more not asked for</>}
                      </p>
                      <ul className="ticks" role="list">
                        {data!.doctor_order.terms.map((t, i) => (
                          <Tick key={`${t.input}-${i}`} term={t} open={expanded.has(i)}
                                onToggle={() => {
                                  const next = new Set(expanded);
                                  next.has(i) ? next.delete(i) : next.add(i);
                                  setExpanded(next);
                                }} />
                        ))}
                      </ul>
                      {extra.length > 0 && (
                        <>
                          {/* Extra, not wrong: a panel the patient had that nobody
                              ordered, which the doctor may want to know about. */}
                          <p className="extra-head">Also on the page, not asked for</p>
                          <ul className="ticks" role="list">
                            {extra.map((x) => (
                              <li key={x.panel_code} className="tick extra">
                                <div className="tick-row">
                                  <span className="tick-mark" aria-hidden="true">+</span>
                                  <span className="tick-name">{x.panel_name}</span>
                                  <span className="tick-frac">
                                    {x.complete ? "all" : `${x.accounted}/${x.expected}`}
                                  </span>
                                  <span />
                                </div>
                              </li>
                            ))}
                          </ul>
                        </>
                      )}
                    </div>
                  </>
                )}
              </section>

              {/* ----------------------------------------- the patient */}
              <section className="dsec tag">
                <h3>Patient tagged</h3>
                <p className="dhint">What they say they were tested for. Shown, never scored.</p>

                <QuickChips panels={panels} chosen={chosenIn("patient_tag")}
                            onToggle={(n) => toggleQuick("patient_tag", n)} />

                <textarea
                  rows={2}
                  value={draft.patient_tag ?? ""}
                  placeholder={"or type anything — sugar test, thyroid"}
                  onChange={(e) => setDraft({ ...draft, patient_tag: e.target.value })}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                      e.preventDefault(); void save("patient_tag");
                    }
                  }}
                />
                <div className="row" style={{ marginTop: 6 }}>
                  <button disabled={saving !== null || !tagUnsaved}
                          onClick={() => void save("patient_tag")}>
                    {saving === "patient_tag" ? "Saving…" : "Save"}
                  </button>
                  {tagUnsaved && saving !== "patient_tag" && <span className="unsaved">not saved yet</span>}
                </div>

                {data && data.patient_tag.terms.length > 0 && (
                  <div className="tag-chips">
                    {data.patient_tag.terms.map((t, i) => (
                      <span key={`${t.input}-${i}`}
                            className={`tag-chip${t.kind === "unresolved" ? " bad" : ""}`}
                            title={t.kind === "panel"
                              ? `${t.input} → ${t.panel_name}, ${t.analytes.length} tests`
                              : t.kind === "analyte"
                              ? `${t.input} → ${t.analytes[0]?.analyte_name}`
                              : `${t.input} matches nothing in the master`}>
                        {t.input}{t.kind === "unresolved" && <b> ?</b>}
                      </span>
                    ))}
                  </div>
                )}
              </section>
            </div>
          </aside>
        </>
      )}
    </>
  );
}

/**
 * The ten core panels, pressable. Shared by both lists deliberately: a doctor
 * ordering a CBC and a patient saying they had one should not need two different
 * gestures, and one component means the two cannot drift apart.
 */
function QuickChips({ panels, chosen, onToggle }: {
  panels: PanelRow[];
  chosen: Set<string>;
  onToggle: (name: string) => void;
}) {
  if (panels.length === 0) return null;
  return (
    <div className="quick">
      {panels.map((p) => (
        <button key={p.code}
                className={`quick-chip${chosen.has(p.display_name.toLowerCase()) ? " on" : ""}`}
                aria-pressed={chosen.has(p.display_name.toLowerCase())}
                onClick={() => onToggle(p.display_name)}>
          {p.display_name}
        </button>
      ))}
    </div>
  );
}

/**
 * One ordered panel: the answer, then the detail if asked for.
 *
 * A row that is complete has nothing to open, so it does not pretend to be a
 * button - an affordance that does nothing is worse than none.
 */
function Tick({ term, open, onToggle }: {
  term: ListTerm; open: boolean; onToggle: () => void;
}) {
  const name = term.panel_name ?? term.analytes[0]?.analyte_name ?? term.input;
  const hasDetail = (term.on_page?.length ?? 0) > 0
    || (term.not_on_page?.length ?? 0) > 0
    || (term.not_read?.length ?? 0) > 0
    || (term.kind === "unresolved" && (term.did_you_mean?.length ?? 0) > 0);

  const mark = term.verdict === "present" ? (term.complete ? "✓" : "◑")
             : term.verdict === "unrecognised" ? "?" : "✕";

  return (
    <li className={`tick v-${term.verdict}${term.complete ? " whole" : ""}`}>
      <button className="tick-row" onClick={onToggle} disabled={!hasDetail}
              aria-expanded={hasDetail ? open : undefined}>
        <span className="tick-mark" aria-hidden="true">{mark}</span>
        <span className="tick-name">{name}</span>
        {term.expected ? (
          <span className="tick-frac">
            {term.complete ? "all" : `${term.accounted ?? term.read}/${term.expected}`}
          </span>
        ) : <span className="tick-frac">—</span>}
        {hasDetail && <span className="tick-caret" aria-hidden="true">{open ? "▾" : "▸"}</span>}
      </button>

      {open && hasDetail && (
        <div className="tick-detail">
          {/* What came back, first. A reviewer confirming an order wants to see
              the tests that are there, not deduce them from what is not. */}
          {term.on_page && term.on_page.length > 0 && (
            <p><span className="dk ok">on this page</span> {term.on_page.join(", ")}</p>
          )}
          {term.not_on_page && term.not_on_page.length > 0 && (
            <p><span className="dk">not on this page</span> {term.not_on_page.join(", ")}</p>
          )}
          {term.not_read && term.not_read.length > 0 && (
            <p><span className="dk ours">printed, value unreadable</span> {term.not_read.join(", ")}</p>
          )}
          {term.kind === "unresolved" && term.did_you_mean && (
            <p><span className="dk">did you mean</span> {term.did_you_mean.map((d) => d.label).join(" or ")}?</p>
          )}
        </div>
      )}
    </li>
  );
}
