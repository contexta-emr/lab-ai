"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { api, formatDate, STATUS_LABEL } from "@/lib/api";
import type { DocumentDetail, QueueItem } from "@/lib/api";

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

  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadQueue = useCallback(async () => {
    try {
      const q = await api.queue();
      setQueue(q.items);
      setCounts(q.counts);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the queue");
    }
  }, []);

  useEffect(() => { void loadQueue(); }, [loadQueue]);

  useEffect(() => {
    if (!selected) { setDoc(null); return; }
    api.document(selected).then(setDoc).catch((e) =>
      setError(e instanceof Error ? e.message : "Could not load the document"));
  }, [selected]);

  async function decide(decision: "verify" | "reject", patientId?: string) {
    if (!doc) return;
    setBusy(true);
    setError(null);
    try {
      await api.review(doc.id, { decision, patient_id: patientId });
      await loadQueue();
      const fresh = await api.document(doc.id);
      setDoc(fresh);
    } catch (e) {
      setError(e instanceof Error ? e.message : "That did not go through");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Review queue</h1>
      <p className="subtitle">
        Every document the machine was not certain about. Nothing here counts as
        clinical fact until it is verified against a patient.
      </p>

      {error && <div className="error" style={{ marginBottom: 14 }}>{error}</div>}

      <div className="stat-row" style={{ marginBottom: 18 }}>
        <div className={`stat${(counts.needs_review ?? 0) > 0 ? " attention" : ""}`}>
          <div className="value">{counts.needs_review ?? 0}</div>
          <div className="label">No patient matched</div>
        </div>
        <div className="stat">
          <div className="value">{counts.awaiting_confirm ?? 0}</div>
          <div className="label">Matched, unconfirmed</div>
        </div>
        <div className="stat">
          <div className="value">{counts.verified ?? 0}</div>
          <div className="label">Verified</div>
        </div>
        <div className="stat">
          <div className="value">{counts.rejected ?? 0}</div>
          <div className="label">Rejected</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card" style={{ padding: 0 }}>
          {queue.length === 0 ? (
            <div className="empty">Nothing waiting. Everything has been reviewed.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Lab and UHID</th>
                  <th>Why it is here</th>
                  <th className="num">Results</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((q) => (
                  <tr
                    key={q.id}
                    onClick={() => router.push(`/review?doc=${q.id}`)}
                    style={{
                      cursor: "pointer",
                      background: q.id === selected ? "var(--brand-soft)" : undefined,
                    }}
                  >
                    <td>
                      <div>{q.lab_name ?? "Unnamed lab"}</div>
                      <div className="mono faint">{q.detected_uhid ?? "no UHID read"}</div>
                    </td>
                    <td className="faint">{q.reason}</td>
                    <td className="num">{q.result_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div>
          {!doc ? (
            <div className="card empty">Pick a document to review it.</div>
          ) : (
            <DocumentPanel doc={doc} busy={busy} onDecide={decide} />
          )}
        </div>
      </div>
    </>
  );
}

function DocumentPanel({
  doc,
  busy,
  onDecide,
}: {
  doc: DocumentDetail;
  busy: boolean;
  onDecide: (d: "verify" | "reject", patientId?: string) => void;
}) {
  const report = doc.reports[0];

  return (
    <div className="card">
      <div className="spread">
        <div>
          <strong>{doc.lab_name ?? "Unnamed lab"}</strong>
          <div className="faint">
            {report?.patient_name_printed} · {report?.age_printed}
            {report?.sex_printed ? ` / ${report.sex_printed}` : ""} ·{" "}
            {formatDate(doc.collected_at)}
          </div>
        </div>
        <span className={`chip ${doc.status}`}>
          {STATUS_LABEL[doc.status] ?? doc.status}
        </span>
      </div>

      <div className="row" style={{ marginTop: 10, gap: 18 }}>
        <span className="faint">
          UHID on page <span className="mono">{doc.detected_uhid ?? "—"}</span>
        </span>
        <span className="faint">
          Extraction{" "}
          {doc.extraction_confidence !== null
            ? `${Math.round(doc.extraction_confidence * 100)}%`
            : "—"}
        </span>
        {doc.unmatched_count > 0 && (
          <span className="unmatched">{doc.unmatched_count} labels with no code</span>
        )}
      </div>

      {doc.status !== "verified" && doc.status !== "rejected" && (
        <>
          <h2 style={{ marginTop: 18 }}>Which patient is this?</h2>
          {doc.patient_id ? (
            <div className="row">
              <span>
                Matched to <strong>{doc.patient_name}</strong>{" "}
                <span className="mono faint">{doc.patient_uhid}</span>
              </span>
              <button
                className="primary small"
                disabled={busy}
                onClick={() => onDecide("verify", doc.patient_id!)}
              >
                Confirm
              </button>
            </div>
          ) : doc.candidates.length > 0 ? (
            <table>
              <tbody>
                {doc.candidates.map((c) => (
                  <tr key={c.patient_id}>
                    <td>
                      <div>{c.full_name}</div>
                      <div className="mono faint">{c.uhid}</div>
                    </td>
                    <td className="faint">
                      {c.match_method.replace("uhid_", "")} ·{" "}
                      {Math.round(c.confidence * 100)}%
                    </td>
                    <td className="num">
                      <button
                        className="primary small"
                        disabled={busy}
                        onClick={() => onDecide("verify", c.patient_id)}
                      >
                        This one
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="muted">
              No patient in this practice resembles{" "}
              <span className="mono">{doc.detected_uhid ?? "the UHID on the page"}</span>.
            </p>
          )}

          <div className="row" style={{ marginTop: 14 }}>
            <button className="danger small" disabled={busy} onClick={() => onDecide("reject")}>
              Reject this document
            </button>
            <span className="faint">
              Use reject when the page is unreadable or belongs to no one here.
            </span>
          </div>
        </>
      )}

      {doc.status === "verified" && doc.patient_id && (
        <p style={{ marginTop: 14 }}>
          Verified against{" "}
          <Link href={`/patients/${doc.patient_id}`}>{doc.patient_name}</Link>.
        </p>
      )}

      <h2>What was read</h2>
      {report?.sections.map((s) => (
        <div key={s.id} style={{ marginBottom: 14 }}>
          <div className="spread">
            <strong style={{ fontSize: 13 }}>{s.heading_printed ?? "Untitled section"}</strong>
            <span className="chip muted">
              {s.panel_code ?? "panel not identified"}
            </span>
          </div>
          <table>
            <thead>
              <tr>
                <th>Printed as</th>
                <th>Resolved to</th>
                <th className="num">Value</th>
                <th>Reference</th>
              </tr>
            </thead>
            <tbody>
              {s.results.map((r) => (
                <tr key={r.id}>
                  <td>{r.printed_label}</td>
                  <td>
                    {r.analyte_code ? (
                      <span className="mono">{r.analyte_code}</span>
                    ) : (
                      <span className="unmatched">no code</span>
                    )}
                    {r.match_method === "fuzzy_alias" && (
                      <span className="faint"> (fuzzy)</span>
                    )}
                  </td>
                  <td className="num">
                    {r.value_text}
                    {r.unit ? <span className="faint"> {r.unit}</span> : null}
                    {r.flag && <span className={`flag ${r.flag}`}> {r.flag}</span>}
                  </td>
                  <td className="faint">{r.reference_printed ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      {report?.notes && report.notes.length > 0 && (
        <>
          <h2>Notes on the report</h2>
          {report.notes.map((n, i) => (
            <p key={i} className="faint" style={{ marginTop: 4 }}>
              {n.marker ? `[${n.marker}] ` : ""}
              {n.note_text}
            </p>
          ))}
        </>
      )}
    </div>
  );
}
