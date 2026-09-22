"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { api, formatDate, STATUS_LABEL } from "@/lib/api";
import type { Coverage, DocumentDetail, QueueItem } from "@/lib/api";

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
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Two rules, both learned from a banner that said "Failed to fetch" over a
  // queue that had loaded perfectly well:
  //
  //   success clears the error, or one failed request - the API restarting
  //   under uvicorn --reload, a dropped connection - leaves the banner up for
  //   the rest of the session
  //
  //   only the newest request may write state. Strict mode fires effects twice
  //   in development and decide() reloads while a poll may be in flight, so two
  //   loads overlap routinely. Without this the slower one wins and a stale
  //   failure can overwrite a fresh success.
  const latest = useRef(0);

  const loadQueue = useCallback(async () => {
    const mine = ++latest.current;
    try {
      const q = await api.queue();
      if (mine !== latest.current) return;
      setQueue(q.items);
      setCounts(q.counts);
      setError(null);
    } catch (e) {
      if (mine !== latest.current) return;
      setError(e instanceof Error ? e.message : "Could not load the queue");
    }
  }, []);

  useEffect(() => { void loadQueue(); }, [loadQueue]);

  useEffect(() => {
    if (!selected) { setDoc(null); setCoverage(null); return; }
    setCoverage(null);
    api.document(selected)
      .then((d) => { setDoc(d); setError(null); })
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Could not load the document"));
    // Coverage failing must not take the document with it. It is a second
    // opinion about completeness, not the record itself.
    api.coverage(selected).then(setCoverage).catch(() => setCoverage(null));
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

      {doc && <StatusBand doc={doc} coverage={coverage} />}

      <div className="workbench">
        {/* The queue you are working through. Narrow on purpose - it is a
            list to get through, not the subject of the screen. */}
        <div className="card queue-rail" style={{ padding: 0 }}>
          {queue.length === 0 ? (
            <div className="empty">Nothing waiting. Everything has been reviewed.</div>
          ) : (
            queue.map((q) => (
              <div
                key={q.id}
                className={`row-item${q.id === selected ? " on" : ""}`}
                onClick={() => router.push(`/review?doc=${q.id}`)}
              >
                <div className="lab">{q.lab_name ?? "Unnamed lab"}</div>
                <div className="mono faint">{q.detected_uhid ?? "no UHID read"}</div>
                <div className="faint" style={{ fontSize: 11, marginTop: 3 }}>
                  {q.reason} · {q.result_count} rows
                </div>
              </div>
            ))
          )}
        </div>

        {/* The page. The whole reason this screen exists is checking a value
            against the document without leaving it, so the page gets the room
            and is shown at a size someone can actually read. */}
        <div className="card page-view" style={{ padding: 6 }}>
          {!doc ? (
            <div className="empty">Pick a document to see the page.</div>
          ) : (
            <object data={api.fileUrl(doc.id)} type="application/pdf">
              <div className="empty" style={{ padding: 20 }}>
                This browser will not display the page inline.{" "}
                <a href={api.fileUrl(doc.id)} target="_blank" rel="noreferrer">
                  Open it in a new tab
                </a>
                .
              </div>
            </object>
          )}
        </div>

        <div className="results-pane">
          {!doc ? (
            <div className="card empty">Pick a document to review it.</div>
          ) : (
            <>
              <DocumentPanel doc={doc} busy={busy} onDecide={decide} />
              <CoveragePanel coverage={coverage} />
            </>
          )}
        </div>
      </div>
    </>
  );
}

/** Patient, panel and verdict across the top, so the three things you need
 *  before looking at a single row are never somewhere you have to scroll. */
function StatusBand({ doc, coverage }: { doc: DocumentDetail; coverage: Coverage | null }) {
  const report = doc.reports[0];
  const missing = coverage?.panels.reduce((n, p) => n + p.core_missing.length, 0) ?? 0;
  return (
    <div className="band">
      <div>
        <div className="k">Patient</div>
        <div className="v">
          {doc.patient_name ?? report?.patient_name_printed ?? "not matched"}
        </div>
      </div>
      <div>
        <div className="k">UHID on page</div>
        <div className="v mono">{doc.detected_uhid ?? "—"}</div>
      </div>
      <div>
        <div className="k">Lab</div>
        <div className="v">{doc.lab_name ?? "—"}</div>
      </div>
      <div>
        <div className="k">Panels</div>
        <div className="v">
          {coverage?.panels.length
            ? coverage.panels.map((p) => p.panel_name).join(", ")
            : "none detected"}
        </div>
      </div>
      <div>
        <div className="k">Verdict</div>
        <div className="v">
          {missing > 0 ? (
            <span className="cov missing">{missing} core missing</span>
          ) : (
            <span className="cov found">nothing core missing</span>
          )}
        </div>
      </div>
      <div style={{ marginLeft: "auto" }}>
        <span className={`chip ${doc.status}`}>
          {STATUS_LABEL[doc.status] ?? doc.status}
        </span>
      </div>
    </div>
  );
}

/** What the report should have contained, against what it did.
 *
 *  found / missing / extra never share a colour. An extracted row the
 *  template does not list is CONTENT, not a failure - showing it as one is
 *  how a good extraction gets read as a broken one. */
function CoveragePanel({ coverage }: { coverage: Coverage | null }) {
  if (!coverage) return null;
  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>Did we miss anything?</h2>
      <p className="faint" style={{ marginTop: -6 }}>
        Checked against what each panel should contain. This is the only way to
        notice a dropped row on a real report, where there is no answer key.
      </p>

      {coverage.note && <div className="empty">{coverage.note}</div>}

      {coverage.panels.map((p) => (
        <div key={p.panel_code} style={{ marginTop: 12 }}>
          <div className="spread">
            <strong>{p.panel_name}</strong>
            <span className="faint">
              {p.found} of {p.expected}
            </span>
          </div>
          <table style={{ marginTop: 6 }}>
            <tbody>
              {p.members.map((m) => (
                <tr key={m.analyte_code}>
                  <td>
                    <span className={`cov ${m.state}`}>{m.analyte_name}</span>
                    {m.is_core && m.state === "missing" && (
                      <span className="faint" style={{ fontSize: 11 }}> · core</span>
                    )}
                  </td>
                  <td className="faint">{m.printed_label ?? ""}</td>
                </tr>
              ))}
              {p.extra.map((e, i) => (
                <tr key={`x${i}`}>
                  <td><span className="cov extra">{e.printed_label}</span></td>
                  <td className="faint">also on the page</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      {coverage.unresolved.length > 0 && (
        <p className="faint" style={{ marginTop: 12 }}>
          {coverage.unresolved.length} label
          {coverage.unresolved.length === 1 ? "" : "s"} matched no known test:{" "}
          {coverage.unresolved.join(", ")}. The row is stored either way - that is
          the vocabulary&apos;s gap, not the page&apos;s.
        </p>
      )}
    </div>
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
