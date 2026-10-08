"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, formatDate, STATUS_LABEL } from "@/lib/api";
import type { AvailableAnalyte, Patient, Trend } from "@/lib/api";
import { TrendChart } from "@/components/TrendChart";
import { Find } from "@/components/Filters";

export default function PatientPage() {
  const { id } = useParams<{ id: string }>();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [analytes, setAnalytes] = useState<AvailableAnalyte[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [trend, setTrend] = useState<Trend | null>(null);
  const [documents, setDocuments] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [trendError, setTrendError] = useState<string | null>(null);
  const [find, setFind] = useState("");

  useEffect(() => {
    if (!id) return;
    Promise.all([api.patient(id), api.patientAnalytes(id), api.patientDocuments(id)])
      .then(([p, a, d]) => {
        setPatient(p);
        setAnalytes(a);
        setDocuments(d);
        setError(null);
        // Open on whatever has the most points: the test this record is about.
        if (a.length > 0) setSelected(a[0].code);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load"));
  }, [id]);

  // The trend has its own error rather than the page-level one, because a
  // failed chart should not replace the whole patient record with an error.
  //
  // It previously did .catch(() => setTrend(null)), which rendered a failed
  // request as "No points for this test." - a clinician cannot tell a patient
  // who was never tested from a request that did not arrive. That is the same
  // mistake as guessing an analyte code: an honest blank is fine, a confident
  // wrong statement is not.
  const latestTrend = useRef(0);

  useEffect(() => {
    if (!id || !selected) return;
    const mine = ++latestTrend.current;
    // Clear first, so a slow load never shows the previous analyte's readings
    // under the newly selected analyte's name.
    setTrend(null);
    setTrendError(null);
    api
      .trend(id, selected)
      .then((t) => {
        if (mine !== latestTrend.current) return;
        setTrend(t);
      })
      .catch((e) => {
        if (mine !== latestTrend.current) return;
        setTrendError(e instanceof Error ? e.message : "Could not load this trend");
      });
  }, [id, selected]);

  const shownAnalytes = useMemo(() => {
    const needle = find.trim().toLowerCase();
    if (!needle) return analytes;
    return analytes.filter((a) =>
      a.display_name.toLowerCase().includes(needle)
      || a.code.toLowerCase().includes(needle)
      || (a.panel_code ?? "").toLowerCase().includes(needle));
  }, [analytes, find]);

  if (error) return <div className="error">{error}</div>;
  if (!patient) return <div className="empty">Loading…</div>;

  return (
    <>
      <div className="spread">
        <div>
          <h1>{patient.full_name}</h1>
          <p className="subtitle">
            <span className="mono">{patient.uhid}</span>
            {patient.dob && ` · born ${formatDate(patient.dob)}`}
            {patient.gender && ` · ${patient.gender}`}
            {patient.city && ` · ${patient.city}`}
          </p>
        </div>
        <Link href="/patients" className="faint">← all patients</Link>
      </div>

      <div className="stat-row" style={{ marginBottom: 20 }}>
        <div className="stat">
          <div className="value">{patient.document_count}</div>
          <div className="label">Documents</div>
        </div>
        <div className="stat">
          <div className="value">{patient.result_count}</div>
          <div className="label">Results stored</div>
        </div>
        <div className="stat">
          <div className="value">{analytes.length}</div>
          <div className="label">Chartable tests</div>
        </div>
        <div className="stat">
          <div className="value" style={{ fontSize: 16, paddingTop: 6 }}>
            {formatDate(patient.last_report_at)}
          </div>
          <div className="label">Last report</div>
        </div>
      </div>

      <h2>Trend</h2>
      {analytes.length === 0 ? (
        <div className="card empty">
          No verified numeric results yet. Results appear here once a document has
          been verified in the review queue.
        </div>
      ) : (
        <div className="card">
          {/* These were a dropdown, which showed one test and hid the rest -
              so how much of this record is chartable at all took a click to
              learn. Laid out, the answer is the first thing you see, and the
              point counts say which lines are worth opening. A test with two
              points is not a trend. */}
          <div className="row" style={{ marginBottom: 10 }}>
            <Find
              value={find}
              onChange={setFind}
              placeholder="Find a test…  /"
              hint="Filter the chartable tests for this patient"
            />
            {trend && (
              <span className="faint">
                {trend.point_count} reading{trend.point_count === 1 ? "" : "s"}
                {trend.unit ? ` in ${trend.unit}` : ""}
              </span>
            )}
          </div>
          <div className="pchips" style={{ marginBottom: 16 }}>
            {shownAnalytes.map((a) => (
              <button
                key={a.code}
                className="pchip plain"
                aria-pressed={selected === a.code}
                onClick={() => setSelected(a.code)}
                title={a.panel_code ? `${a.display_name} — ${a.panel_code}` : a.display_name}
              >
                <span className="nm">{a.display_name}</span>
                <span className="frac">{a.point_count}</span>
              </button>
            ))}
            {shownAnalytes.length === 0 && (
              <span className="faint">No test here matches “{find}”.</span>
            )}
          </div>

          {trend && trend.points.length > 0 ? (
            <>
              <TrendChart trend={trend} />
              <table style={{ marginTop: 16 }}>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th className="num">Value</th>
                    <th>Reference</th>
                    <th>Printed as</th>
                    <th>Lab</th>
                  </tr>
                </thead>
                <tbody>
                  {trend.points.map((p, i) => (
                    <tr key={`${p.document_id}-${i}`}>
                      <td>{formatDate(p.collected_at)}</td>
                      <td className="num">
                        {p.value_text}
                        {p.flag && <span className={`flag ${p.flag}`}> {p.flag}</span>}
                      </td>
                      <td className="faint">{p.reference_printed ?? "—"}</td>
                      <td className="faint">{p.printed_label}</td>
                      <td className="faint">{p.lab_name ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="faint" style={{ marginTop: 10 }}>
                The same test printed under different names by different labs is one
                line here. That is what the alias master is for.
              </p>
            </>
          ) : trendError ? (
            // Not "no points": this says the request failed, which is a
            // different fact and the only honest one available.
            <div className="error">
              {trendError}
              <div className="faint" style={{ marginTop: 6 }}>
                These readings could not be loaded. They have not been deleted and
                nothing has changed - try again in a moment.
              </div>
            </div>
          ) : trend === null ? (
            <div className="empty">Loading…</div>
          ) : (
            <div className="empty">No points for this test.</div>
          )}
        </div>
      )}

      <h2>Documents</h2>
      <div className="card" style={{ padding: 0 }}>
        {documents.length === 0 ? (
          <div className="empty">Nothing filed for this patient yet.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Collected</th>
                <th>Lab</th>
                <th>Panels</th>
                <th className="num">Results</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((d, i) => (
                // The whole row opens the document, as the queue and the overview
                // do. One gesture across all three lists; the status chip alone
                // was a small target and an invisible one.
                <tr key={i} style={{ cursor: "pointer" }}
                    onClick={() => { window.location.href = `/review?doc=${d.document_id}`; }}>
                  <td>{formatDate(d.collected_at as string)}</td>
                  <td>{(d.lab_name as string) ?? "—"}</td>
                  <td className="faint">{(d.panels as string) ?? "—"}</td>
                  <td className="num">{d.result_count as number}</td>
                  <td>
                    <span className={`chip ${d.status}`}>
                      {STATUS_LABEL[d.status as string] ?? (d.status as string)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
