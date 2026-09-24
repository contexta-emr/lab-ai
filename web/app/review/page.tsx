"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { api, isAbort, formatDate, STATUS_LABEL } from "@/lib/api";
import type { Coverage, DocRows, DocumentDetail, Patient } from "@/lib/api";
import { ResultsTable } from "./ResultsTable";

/**
 * One document, read closely.
 *
 * The page on the left at a size someone can actually read, everything known
 * about it on the right. The queue lives at /queue - a list to choose from and
 * a page you are checking a value against are different jobs, and they were
 * competing for the same screen.
 */
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
    setCoverage(null);
    setRows(null);
    const controller = new AbortController();
    void load(selected, controller.signal);
    return () => controller.abort();
  }, [selected, load]);

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
        <div className="card page-view" style={{ padding: 6 }}>
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
          <Identify doc={doc} busy={busy} onDecide={decide} />
          <ResultsTable documentId={doc.id} rows={rows}
                        onChanged={() => void loadRows(doc.id, new AbortController().signal)} />
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
                  {c.match_method.replace("uhid_", "")} · {Math.round(c.confidence * 100)}%
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
