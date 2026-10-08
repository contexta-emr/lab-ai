"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { api, ApiError, isAbort, formatDate, STATUS_LABEL } from "@/lib/api";
import type { Coverage, DocRows, DocumentDetail, Patient } from "@/lib/api";
import { ResultsTable } from "./ResultsTable";
import { OrderLists } from "@/components/OrderLists";

/**
 * One document, read closely.
 *
 * The page on the left at a size someone can actually read, everything known
 * about it on the right. The queue lives at /queue - a list to choose from and
 * a page you are checking a value against are different jobs, and they were
 * competing for the same screen.
 */
/** A document in one of these has not been read yet. Anything the screen says
 *  about its contents while it sits here is a guess, and the guess it used to
 *  make was "no rows came out of this page" - reporting not-finished as
 *  found-nothing, which reads as failure and is not. */
const STILL_READING = new Set(["received", "parsing"]);

export default function ReviewPage() {
  return (
    <Suspense fallback={<div className="empty">Loading…</div>}>
      <Review />
    </Suspense>
  );
}

function Review() {
  const params = useSearchParams();
  const router = useRouter();
  const selected = params.get("doc");

  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  const [rows, setRows] = useState<DocRows | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Re-reading a document REPLACES it: fn_complete_document deletes the placeholder
  // and inserts a new row with a new id. A screen open on the old id then polls
  // something that no longer exists and would sit on "reading the page" forever.
  const [replaced, setReplaced] = useState(false);
  const [busy, setBusy] = useState(false);
  // Every request this screen issues belongs to one document. When the selection
  // changes, the old document's requests are ABORTED rather than left in flight to
  // land later and overwrite the new one's state. The sequence-counter this replaces
  // guarded setDoc and setCoverage but not setRows, so a slow rows response for the
  // previous document could paint its analytes under the current document's header -
  // which is what "sometimes it shows the analyte, sometimes it does not" was.
  const loadRows = useCallback(async (id: string, signal: AbortSignal) => {
    try {
      const r = await api.rows(id, signal);
      if (!signal.aborted) setRows(r);
    } catch {
      /* aborted, or the rows failed: the document still stands either way */
    }
  }, []);

  const load = useCallback(async (id: string, signal: AbortSignal) => {
    try {
      const d = await api.document(id, signal);
      if (signal.aborted) return;
      setDoc(d);
      setError(null);
    } catch (e) {
      // A superseded request is not a failure and must not raise a banner.
      if (isAbort(e) || signal.aborted) return;
      if (e instanceof ApiError && e.status === 404) {
        setReplaced(true);
        setDoc(null);
        return;
      }
      setError(e instanceof Error ? e.message : "Could not load the document");
    }
    // Coverage failing must not take the document with it: it is a second
    // opinion about completeness, not the record.
    api.coverage(id, signal).then((c) => {
      if (!signal.aborted) setCoverage(c);
    }).catch(() => undefined);
    void loadRows(id, signal);
  }, [loadRows]);

  useEffect(() => {
    if (!selected) { setDoc(null); setCoverage(null); setRows(null); return; }
    setReplaced(false);
    setCoverage(null);
    setRows(null);
    const controller = new AbortController();
    void load(selected, controller.signal);
    return () => controller.abort();
  }, [selected, load]);

  // Poll only while there is something to wait for. A document that has been read
  // never polls, so an idle review screen makes no requests at all.
  // Depend on the id and the status, NOT on the doc object. Each poll replaces doc
  // with a new object, so an object dependency re-runs this effect every time a poll
  // lands - tearing down and rebuilding the timer, and stacking overlapping ones.
  // Measured before the fix: 15 requests in 9 seconds against a 2.5s interval.
  const docId = doc?.id;
  const docStatus = doc?.status;
  useEffect(() => {
    if (!docId || !docStatus || !STILL_READING.has(docStatus)) return;
    const timer = setInterval(() => {
      void load(docId, new AbortController().signal);
    }, 2500);
    return () => clearInterval(timer);
  }, [docId, docStatus, load]);

  async function decide(decision: "verify" | "reject", patientId?: string) {
    if (!doc) return;
    setBusy(true);
    setError(null);
    try {
      await api.review(doc.id, { decision, patient_id: patientId });
      await load(doc.id, new AbortController().signal);
    } catch (e) {
      setError(e instanceof Error ? e.message : "That did not go through");
    } finally {
      setBusy(false);
    }
  }

  if (!selected) {
    return (
      <div className="card empty">
        Pick a document from the <Link href="/queue">queue</Link>.
      </div>
    );
  }
  if (replaced) {
    return (
      <div className="card empty">
        <p>This document was read again, and reading it again replaces it.</p>
        <p className="faint" style={{ marginTop: 6 }}>
          The new copy has a new id, so this address no longer points at anything.
          Open it from the queue.
        </p>
        <p style={{ marginTop: 12 }}>
          <Link href="/queue" className="btn primary">Go to the queue</Link>
        </p>
      </div>
    );
  }

  if (!doc) {
    // A failure here used to be a dead end: the message sat on an otherwise
    // blank page with no way forward and no retry, so one bad response made
    // the document look permanently broken. Offer both ways out.
    return (
      <div className="card empty">
        {error ? (
          <>
            <div style={{ marginBottom: 12 }}>{error}</div>
            <button className="primary small"
                    onClick={() => { setError(null); void load(selected, new AbortController().signal); }}>
              Try again
            </button>
            <span className="faint" style={{ marginLeft: 12 }}>
              or go back to the <Link href="/queue">queue</Link>
            </span>
          </>
        ) : "Loading…"}
      </div>
    );
  }

  const report = doc.reports[0];

  return (
    <>
      <div className="spread" style={{ marginBottom: 10 }}>
        <div>
          <h1 style={{ marginBottom: 2 }}>{doc.file_name ?? `Document ${doc.id}`}</h1>
          <p className="subtitle" style={{ margin: 0 }}>
            {doc.lab_name ?? "lab name not read"}
            {report?.collected_at ? ` · collected ${formatDate(report.collected_at)}` : ""}
          </p>
        </div>
        <Link href="/queue" className="faint">← queue</Link>
      </div>

      {error && <div className="error" style={{ marginBottom: 12 }}>{error}</div>}

      <Band doc={doc} coverage={coverage} />

      <div className="reader">
        <div className="page-view">
          <object data={api.fileUrl(doc.id)} type="application/pdf">
            <div className="empty" style={{ padding: 20 }}>
              This browser will not show the page inline.{" "}
              <a href={api.fileUrl(doc.id)} target="_blank" rel="noreferrer">
                Open it in a new tab
              </a>
              .
            </div>
          </object>
        </div>

        <div className="results-pane">
          {STILL_READING.has(doc.status) ? (
            <Reading status={doc.status} />
          ) : (
            <>
          <Identify doc={doc} busy={busy} onDecide={decide} />
          <OrderLists documentId={doc.id} />
          <ResultsTable documentId={doc.id} rows={rows}
                        onChanged={() => void loadRows(doc.id, new AbortController().signal)} />
            </>
          )}
        </div>
      </div>
    </>
  );
}

/** Everything you need before reading a single row, on one line. */
function Band({ doc, coverage }: { doc: DocumentDetail; coverage: Coverage | null }) {
  const report = doc.reports[0];
  const rows = doc.result_count;
  const missing = coverage?.panels.reduce((n, p) => n + p.core_missing.length, 0) ?? 0;
  const confirm = coverage?.panels.reduce((n, p) => n + (p.needs_confirm?.length ?? 0), 0) ?? 0;

  return (
    <div className="band">
      <Field k="Document" v={doc.file_name ?? `#${doc.id}`}
             sub={`${doc.ocr_engine ?? "unread"} · ${doc.page_count ?? 1} page · ${rows} rows read`} />
      <Field k="Patient"
             v={doc.patient_name ?? report?.patient_name_printed ?? "not printed"}
             sub={doc.patient_uhid ? `matched ${doc.patient_uhid}` : "not matched to a record"} />
      <Field k="UHID on page" v={doc.detected_uhid ?? "—"}
             sub={report?.age_printed || report?.sex_printed
               ? `${report?.age_printed ?? ""} ${report?.sex_printed ?? ""}`.trim()
               : undefined} />
      <Field k="Panels"
             v={coverage?.panels.length
               ? coverage.panels.map((p) => p.panel_name).join(", ")
               : "none detected"} />
      <Field k="Verdict"
             v={missing > 0
               ? <span className="cov missing">{missing} core missing</span>
               : <span className="cov found">nothing core missing</span>}
             sub={confirm > 0 ? `${confirm} awaiting confirmation` : undefined} />
      <div style={{ marginLeft: "auto" }}>
        <span className={`chip ${doc.status}`}>
          {STATUS_LABEL[doc.status] ?? doc.status}
        </span>
      </div>
    </div>
  );
}

function Field({ k, v, sub }: { k: string; v: React.ReactNode; sub?: string }) {
  return (
    <div>
      <div className="k">{k}</div>
      <div className="v">{v}</div>
      {sub && <div className="faint" style={{ fontSize: 11 }}>{sub}</div>}
    </div>
  );
}

/**
 * Which patient this belongs to.
 *
 * A UHID that could not be read used to be the end of the road: the only
 * option was reject, which throws away a perfectly readable report because
 * one number on it was blurred. Searching by name or id and attaching by hand
 * is the whole point of a review queue.
 */
function Identify({
  doc, busy, onDecide,
}: {
  doc: DocumentDetail;
  busy: boolean;
  onDecide: (d: "verify" | "reject", patientId?: string) => void;
}) {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Patient[]>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    const term = q.trim();
    if (term.length < 2) { setHits([]); return; }
    setSearching(true);
    const timer = setTimeout(() => {
      api.patients(term)
        .then((p) => setHits(p.slice(0, 8)))
        .catch(() => setHits([]))
        .finally(() => setSearching(false));
    }, 250);                       // one request per pause, not per keystroke
    return () => clearTimeout(timer);
  }, [q]);

  if (doc.status === "verified" || doc.status === "rejected") {
    return (
      <div className="card">
        <div className="spread">
          <strong>
            {doc.status === "verified" ? "Verified" : "Rejected"}
            {doc.patient_name ? ` · ${doc.patient_name}` : ""}
          </strong>
          <span className={`chip ${doc.status}`}>{STATUS_LABEL[doc.status]}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>Which patient is this?</h2>
      {doc.candidates.length > 0 && (
        <p className="faint" style={{ marginTop: -4, marginBottom: 8 }}>
          {doc.candidates.some((c) => c.match_method.startsWith("uhid"))
            ? "Matched on the identifier printed on the page."
            : "No usable UHID on the page — suggested from the printed name, age and sex. Check before attaching."}
        </p>
      )}

      {doc.patient_id && (
        <div className="row" style={{ marginBottom: 10 }}>
          <span>
            Matched to <strong>{doc.patient_name}</strong>{" "}
            <span className="mono faint">{doc.patient_uhid}</span>
          </span>
          <button className="primary small" disabled={busy}
                  onClick={() => onDecide("verify", doc.patient_id!)}>
            Confirm
          </button>
        </div>
      )}

      {!doc.patient_id && doc.candidates.length > 0 && (
        <table style={{ marginBottom: 10 }}>
          <tbody>
            {doc.candidates.map((c) => (
              <tr key={c.patient_id}>
                <td>
                  <div>{c.full_name}</div>
                  <div className="mono faint">{c.uhid}</div>
                </td>
                <td className="faint">
                  {c.match_method.replace("uhid_", "").replace("_", " + ")}
                  {" · "}{Math.round(c.confidence * 100)}%
                  {/* A demographic match says what it matched on. A reviewer
                      choosing between two people with one surname needs that,
                      and a percentage on its own does not carry it. */}
                  {c.evidence && (
                    <div className="faint" style={{ fontSize: 11, marginTop: 2 }}>
                      name {Math.round((c.evidence.name_similarity ?? 0) * 100)}%
                      {c.evidence.dob && c.evidence.dob !== "no_evidence"
                        ? ` · ${c.evidence.dob.replace(/_/g, " ")}` : ""}
                      {c.evidence.sex === "match" ? " · sex agrees" : ""}
                    </div>
                  )}
                </td>
                <td className="num">
                  <button className="primary small" disabled={busy}
                          onClick={() => onDecide("verify", c.patient_id)}>
                    This one
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <label className="k" htmlFor="psearch">
        {doc.patient_id ? "Or attach to someone else" : "Find the patient by name or UHID"}
      </label>
      <input
        id="psearch"
        value={q}
        placeholder="Mahesh, or SRV/207431"
        onChange={(e) => setQ(e.target.value)}
        style={{ width: "100%", marginTop: 4 }}
      />
      {q.trim().length >= 2 && (
        <table style={{ marginTop: 8 }}>
          <tbody>
            {hits.length === 0 ? (
              <tr><td className="faint">
                {searching ? "Searching…" : "No patient in this practice matches that."}
              </td></tr>
            ) : hits.map((p) => (
              <tr key={p.id}>
                <td>
                  <div>{p.full_name}</div>
                  <div className="mono faint">
                    {p.uhid}{p.dob ? ` · born ${formatDate(p.dob)}` : ""}
                    {p.city ? ` · ${p.city}` : ""}
                  </div>
                </td>
                <td className="num">
                  <button className="primary small" disabled={busy}
                          onClick={() => onDecide("verify", p.id)}>
                    Attach
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <Register doc={doc} busy={busy} onCreated={(id) => onDecide("verify", id)} />

      <div className="row" style={{ marginTop: 12 }}>
        <button className="danger small" disabled={busy}
                onClick={() => onDecide("reject")}>
          Reject this document
        </button>
        <span className="faint">
          Reject only when the page is unreadable or belongs to nobody here.
        </span>
      </div>
    </div>
  );
}

/** Register a patient the practice has not seen, from what the page printed.
 *
 *  Deliberately a disclosure rather than a button sitting open: creating a
 *  patient is the last resort, after looking for them. An automatic create - or
 *  one that is easier than searching - turns a single misread UHID into a
 *  duplicate record, and duplicates split one person's history across two
 *  charts. The reviewer searches first, and registers only when nobody matches.
 */
function Register({
  doc, busy, onCreated,
}: {
  doc: DocumentDetail;
  busy: boolean;
  onCreated: (patientId: string) => void;
}) {
  const printed = doc.reports?.[0];
  const printedName = (printed?.patient_name_printed ?? "").trim();
  const cut = printedName.lastIndexOf(" ");

  const [open, setOpen] = useState(false);
  const [uhid, setUhid] = useState(printed?.uhid_printed ?? "");
  const [first, setFirst] = useState(cut > 0 ? printedName.slice(0, cut) : printedName);
  const [last, setLast] = useState(cut > 0 ? printedName.slice(cut + 1) : "");
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  if (doc.patient_id) return null;

  async function register() {
    setSaving(true);
    setProblem(null);
    try {
      const p = await api.createPatient({
        uhid: uhid.trim(),
        first_name: first.trim(),
        last_name: last.trim(),
        gender: printed?.sex_printed ?? null,
      });
      onCreated(p.id);
    } catch (e) {
      // The server says exactly what is wrong - a UHID already in this practice,
      // a missing identifier. Show that, not a generic failure.
      setProblem(e instanceof Error ? e.message : "Could not register this patient");
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <p className="faint" style={{ marginTop: 14 }}>
        Nobody here matches?{" "}
        <button className="rm" style={{ font: "inherit", color: "var(--brand)", padding: 0 }}
                onClick={() => setOpen(true)}>
          Register this patient from the page
        </button>
      </p>
    );
  }

  return (
    <div style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid var(--rule)" }}>
      <div className="k" style={{ marginBottom: 8 }}>Register from what the page printed</div>
      {problem && <div className="error">{problem}</div>}
      <div className="row" style={{ alignItems: "flex-end" }}>
        <label className="faint" style={{ display: "block" }}>
          UHID
          <input value={uhid} onChange={(e) => setUhid(e.target.value)}
                 placeholder="as printed" style={{ display: "block", marginTop: 3 }} />
        </label>
        <label className="faint" style={{ display: "block" }}>
          Given name
          <input value={first} onChange={(e) => setFirst(e.target.value)}
                 style={{ display: "block", marginTop: 3 }} />
        </label>
        <label className="faint" style={{ display: "block" }}>
          Surname
          <input value={last} onChange={(e) => setLast(e.target.value)}
                 placeholder="optional" style={{ display: "block", marginTop: 3 }} />
        </label>
        <button className="primary" disabled={busy || saving || !uhid.trim() || !first.trim()}
                onClick={() => void register()}>
          {saving ? "Registering…" : "Register and attach"}
        </button>
        <button onClick={() => setOpen(false)} disabled={saving}>Cancel</button>
      </div>
      <p className="faint" style={{ marginTop: 8 }}>
        Creates a patient in this practice and files this document against them.
      </p>
    </div>
  );
}


/** What the screen shows while the worker is still reading the page.
 *
 *  The page itself is already on the left, so there is something to look at. The
 *  point of this panel is only to be honest about which of two different things
 *  is true: nothing was found, or nothing has been looked for yet.
 */
function Reading({ status }: { status: string }) {
  const queued = status === "received";
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div className="row">
        <span className={`chip ${status}`}>
          <span className="dot" />
          {queued ? "Waiting for a worker" : "Reading the page"}
        </span>
      </div>
      <p className="muted" style={{ fontSize: 13 }}>
        {queued
          ? "This document is queued. A worker will pick it up and read it."
          : "The engine is reading this page now. Results appear here as soon as it finishes."}
      </p>
      <p className="faint" style={{ fontSize: 12 }}>
        Usually a few seconds; a dense multi-page report can take a minute. This
        screen updates on its own — there is nothing to refresh.
      </p>
    </div>
  );
}
