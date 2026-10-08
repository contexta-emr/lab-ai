"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ResolvedTerm } from "@/lib/api";

/**
 * Check a document against a list of tests you expected.
 *
 * A reviewer holding a requisition wants one question answered: is everything I
 * ordered on this page? The panel template answers a different question - is
 * everything this KIND of panel usually contains on this page - and the two are
 * not the same. A diabetic follow-up might want HbA1c, creatinine and an eGFR;
 * no template covers that set, and no template ever will.
 *
 * WHY THE TYPED LIST GOES TO THE SERVER
 *     Because people type what the requisition said - "S. Creatinine", "SGPT",
 *     "Hb%" - and those match no analyte_code at all. Compared as strings the
 *     checklist would report a test as absent while its value sits on the page,
 *     which is the exact failure the alias master exists to prevent. So the
 *     terms go through /master/resolve-many, which is lab.fn_resolve_analyte -
 *     the same funnel, the same thresholds, the same vocabulary that read the
 *     document. One resolver, or the two disagree with each other.
 *
 * STICKY ON PURPOSE
 *     Held in sessionStorage and mirrored into the URL. A reviewer working
 *     twenty reports against one order set types it once, and the URL makes a
 *     particular check reproducible for somebody else.
 */

const KEY = "labidp.checklist";

export type Wanted = {
  /** analyte_code -> how it got here, for explaining a row's presence */
  codes: Map<string, { name: string | null; fromPanel: string | null; typed: string }>;
  terms: ResolvedTerm[];
  unresolved: ResolvedTerm[];
};

/** Split on newlines, commas, semicolons and tabs; drop list numbering. */
export function parseTerms(text: string): string[] {
  return text
    .split(/[\n,;\t]+/)
    .map((t) => t.replace(/^\s*(?:\d+[.)]|[-*•])\s*/, "").trim())
    .filter(Boolean);
}

function readInitial(): string {
  if (typeof window === "undefined") return "";
  const fromUrl = new URLSearchParams(window.location.search).get("list");
  if (fromUrl) return fromUrl.split("|").join("\n");
  try {
    return window.sessionStorage.getItem(KEY) ?? "";
  } catch {
    return "";               // private window, blocked storage - not an error
  }
}

export function useChecklist() {
  const [text, setText] = useState("");
  const [applied, setApplied] = useState("");
  const [wanted, setWanted] = useState<Wanted | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const latest = useRef(0);

  // Read once on mount rather than in useState, so the server and the first
  // client render agree and React does not complain about hydration.
  useEffect(() => {
    const initial = readInitial();
    if (initial) {
      setText(initial);
      setApplied(initial);
    }
  }, []);

  const apply = useCallback(async (raw: string) => {
    const terms = parseTerms(raw);
    setApplied(raw);
    try {
      window.sessionStorage.setItem(KEY, raw);
    } catch { /* storage unavailable; the list just will not follow them */ }
    // replaceState, not the router: this is a view preference, and pushing a
    // history entry per keystroke-batch makes the back button useless.
    const url = new URL(window.location.href);
    if (terms.length) url.searchParams.set("list", terms.join("|"));
    else url.searchParams.delete("list");
    window.history.replaceState(null, "", url);

    if (terms.length === 0) {
      setWanted(null);
      setError(null);
      return;
    }
    const mine = ++latest.current;
    setBusy(true);
    setError(null);
    try {
      const res = await api.resolveMany(terms);
      if (mine !== latest.current) return;
      const codes = new Map<string, { name: string | null; fromPanel: string | null; typed: string }>();
      for (const t of res.terms) {
        for (const a of t.analytes) {
          if (!codes.has(a.analyte_code)) {
            codes.set(a.analyte_code, {
              name: a.analyte_name, fromPanel: a.from_panel, typed: t.input,
            });
          }
        }
      }
      setWanted({
        codes,
        terms: res.terms,
        unresolved: res.terms.filter((t) => t.kind === "unresolved"),
      });
    } catch (e) {
      if (mine !== latest.current) return;
      setError(e instanceof Error ? e.message : "Could not check that list");
    } finally {
      if (mine === latest.current) setBusy(false);
    }
  }, []);

  // Resolve whatever was restored from the URL or the session.
  useEffect(() => {
    if (applied && !wanted && !busy) void apply(applied);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [applied]);

  const clear = useCallback(() => {
    setText("");
    void apply("");
  }, [apply]);

  return { text, setText, applied, wanted, busy, error, apply, clear };
}

/**
 * The input, and what we made of it.
 *
 * Collapsed until asked for: most documents are reviewed without a list, and a
 * permanent textarea would take room from the table for a feature used
 * sometimes. Open, it echoes every term back as a chip showing what it resolved
 * to - so the reviewer sees what was understood BEFORE any verdict is claimed
 * about the document. A checklist that silently mis-reads a term and then
 * reports a test missing is worse than no checklist.
 */
export function ChecklistBox({
  text, setText, applied, wanted, busy, error, apply, clear,
}: ReturnType<typeof useChecklist>) {
  const [open, setOpen] = useState(false);
  const count = wanted?.codes.size ?? 0;

  // Open it automatically when a list arrived by URL, or the page would show
  // highlighted rows with no visible explanation of why.
  useEffect(() => { if (applied.trim()) setOpen(true); }, [applied]);

  const dirty = text !== applied;

  return (
    <div className="chk">
      <button className="chk-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span>{open ? "▾" : "▸"}</span>
        Check against a list
        {count > 0 && <span className="chk-n">{count}</span>}
      </button>

      {open && (
        <div className="chk-body">
          <label className="lbl" htmlFor="chk-text">
            Paste what was ordered. Codes, printed names or a panel — one per
            line, or comma separated.
          </label>
          <textarea
            id="chk-text"
            className="chk-text"
            rows={4}
            value={text}
            placeholder={"HbA1c\nS. Creatinine\neGFR\nCBC"}
            onChange={(e) => setText(e.target.value)}
            onBlur={() => { if (dirty) void apply(text); }}
            onKeyDown={(e) => {
              // Enter inserts a line, because the list is multi-line. Ctrl or
              // Cmd with Enter is the standard "I am done" in a textarea.
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                void apply(text);
              }
              if (e.key === "Escape") (e.target as HTMLTextAreaElement).blur();
            }}
          />
          <div className="row" style={{ marginTop: 8 }}>
            <button className="primary" disabled={busy || !dirty}
                    onClick={() => void apply(text)}>
              {busy ? "Checking…" : dirty ? "Check" : "Checked"}
            </button>
            {(text || applied) && (
              <button onClick={clear} disabled={busy}>Clear</button>
            )}
            <span className="faint">Ctrl+Enter to check</span>
          </div>

          {error && <div className="error" style={{ marginTop: 10 }}>{error}</div>}

          {wanted && wanted.terms.length > 0 && (
            <div className="chk-echo">
              {wanted.terms.map((t, i) => (
                <span key={`${t.input}-${i}`}
                      className={`chk-chip ${t.kind === "unresolved" ? "bad" : ""}`}
                      title={
                        t.kind === "panel"
                          ? `${t.input} is a panel — expanded to ${t.analytes.length} analytes`
                          : t.kind === "analyte"
                          ? `${t.input} → ${t.analytes[0]?.analyte_code} (${t.match_method})`
                          : `${t.input} matches nothing in the master`
                      }>
                  {t.input}
                  {t.kind === "panel" && <b> → {t.analytes.length} tests</b>}
                  {t.kind === "analyte" && t.analytes[0]?.analyte_code !== t.input
                    && <b> → {t.analytes[0]?.analyte_code}</b>}
                  {t.kind === "unresolved" && <b> ?</b>}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * What the list says about this document, in words.
 *
 * Four facts, and conflating any two of them is the bug worth avoiding: a term
 * we could not understand is NOT a test the lab failed to run, and a row we did
 * not ask for is not a failure at all.
 */
export function ChecklistSummary({
  wanted, presentCodes,
}: {
  wanted: Wanted;
  /** analyte codes that appear on this document, in any state */
  presentCodes: Set<string>;
}) {
  const { onPage, absent } = useMemo(() => {
    const on: string[] = [];
    const off: { code: string; name: string | null }[] = [];
    for (const [code, meta] of wanted.codes) {
      if (presentCodes.has(code)) on.push(code);
      else off.push({ code, name: meta.name });
    }
    return { onPage: on, absent: off };
  }, [wanted, presentCodes]);

  const asked = wanted.codes.size;
  if (asked === 0 && wanted.unresolved.length === 0) return null;

  return (
    <div className="chk-summary" role="status">
      <div className="chk-line">
        <b>{asked}</b> test{asked === 1 ? "" : "s"} on your list ·{" "}
        <span className="cv-ok"><b>{onPage.length}</b> on this page</span>
        {absent.length > 0 && (
          <> · <span className="cv-doubt"><b>{absent.length}</b> not on this page</span></>
        )}
        {wanted.unresolved.length > 0 && (
          <> · <span className="cv-faint"><b>{wanted.unresolved.length}</b> not recognised</span></>
        )}
      </div>

      {absent.length > 0 && (
        <div className="chk-detail">
          <span className="cv-doubt">Ordered but not on this page:</span>{" "}
          {absent.map((a) => a.name ?? a.code).join(", ")}
        </div>
      )}

      {wanted.unresolved.length > 0 && (
        <div className="chk-detail">
          {/* Deliberately separate from the line above. "We do not know this
              word" and "the lab did not run this test" are different facts and
              only one of them is about the document. */}
          <span className="cv-faint">Not recognised — check the spelling:</span>{" "}
          {wanted.unresolved.map((t, i) => (
            <span key={t.input}>
              {i > 0 && ", "}
              <b>{t.input}</b>
              {t.did_you_mean && t.did_you_mean.length > 0 && (
                <span className="faint"> (did you mean {t.did_you_mean
                  .map((d) => d.label).join(" or ")}?)</span>
              )}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
