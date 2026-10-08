"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, formatDate, STATUS_LABEL } from "@/lib/api";
import type { DocumentSummary } from "@/lib/api";

export default function OverviewPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [recent, setRecent] = useState<DocumentSummary[]>([]);
  const [health, setHealth] = useState<{ analytes: number; aliases: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [queue, docs, hp] = await Promise.all([
        api.queue(),
        api.documents({ limit: 12 }),
        api.health(),
      ]);
      setCounts(queue.counts);
      setRecent(docs);
      setHealth(hp);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load");
    } finally {
      setLoading(false);
    }
  }, []);

  // No sign-in. The API runs with AUTH_DISABLED, so there is no token to
  // hold and no screen to get past - the console opens on the overview.
  useEffect(() => { void load(); }, [load]);

  const total =
    (counts.verified ?? 0) + (counts.needs_review ?? 0) +
    (counts.awaiting_confirm ?? 0) + (counts.rejected ?? 0);

  return (
    <>
      <h1>Overview</h1>
      <p className="subtitle">
        What has been read, what is waiting for a person, and what the vocabulary knows.
      </p>

      {error && <div className="error" style={{ marginBottom: 16 }}>{error}</div>}

{/* Two groups, because they answer different questions. The first is work -
          every tile is a filter on the queue, so the number you press is the list
          you get, which is the gesture the queue page already teaches. The second
          is what the system knows, which nobody acts on from here. */}
      <div className="stat-row">
        {loading ? (
          <>{[0, 1, 2, 3].map((i) => <div key={i} className="stat skeleton" aria-hidden="true" />)}</>
        ) : (
          <>
            <button className="stat pick" onClick={() => router.push("/queue")}>
              <div className="value">{total}</div>
              <div className="label">Documents</div>
            </button>
            <button className="stat pick" onClick={() => router.push("/queue")}>
              <div className="value">{counts.verified ?? 0}</div>
              <div className="label">Verified</div>
            </button>
            <button className={`stat pick${(counts.needs_review ?? 0) > 0 ? " attention" : ""}`}
                    onClick={() => router.push("/queue")}>
              <div className="value">{counts.needs_review ?? 0}</div>
              <div className="label">No patient matched</div>
            </button>
            <button className={`stat pick${(counts.awaiting_confirm ?? 0) > 0 ? " attention" : ""}`}
                    onClick={() => router.push("/queue")}>
              <div className="value">{counts.awaiting_confirm ?? 0}</div>
              <div className="label">Awaiting confirmation</div>
            </button>
          </>
        )}
      </div>

      <p className="vocab">
        The vocabulary knows <b>{health?.analytes ?? "—"}</b> analytes under{" "}
        <b>{health?.aliases ?? "—"}</b> printed spellings.{" "}
        <Link href="/queue">Work the queue</Link> or{" "}
        <Link href="/upload">upload a report</Link>.
      </p>

      {health && health.analytes === 0 && (
        <div className="notice" style={{ marginTop: 16 }}>
          The analyte master is empty, so every printed label will resolve to nothing.
          Apply <span className="mono">db/004_seed_analyte_master.sql</span>.
        </div>
      )}

      <h2>Recent documents</h2>
      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <div className="empty">Reading the queue…</div>
        ) : recent.length === 0 ? (
          <div className="empty">
            Nothing yet. <Link href="/upload">Upload a lab report</Link> to begin.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Lab</th>
                <th>Patient</th>
                <th>UHID on page</th>
                <th className="num">Results</th>
                <th>Collected</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((d) => (
                // The whole row, as the queue does. A link on the lab name alone
                // is a small target and an invisible affordance.
                <tr key={d.id} style={{ cursor: "pointer" }}
                    onClick={() => router.push(`/review?doc=${d.id}`)}>
                  <td>
                    <span className={`chip ${d.status}`}>
                      {STATUS_LABEL[d.status] ?? d.status}
                    </span>
                  </td>
                  <td>{d.lab_name ?? <span className="faint">not read</span>}</td>
                  <td onClick={(e) => e.stopPropagation()}>
                    {d.patient_id ? (
                      <Link href={`/patients/${d.patient_id}`}>{d.patient_name}</Link>
                    ) : (
                      <span className="unmatched">not matched</span>
                    )}
                  </td>
                  <td className="mono">{d.detected_uhid ?? "—"}</td>
                  <td className="num">
                    {d.result_count}
                    {d.unmatched_count > 0 && (
                      <span className="unmatched" title="printed labels with no canonical code">
                        {" "}({d.unmatched_count} unnamed)
                      </span>
                    )}
                  </td>
                  <td>{formatDate(d.collected_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

