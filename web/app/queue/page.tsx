"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, formatDate, STATUS_LABEL } from "@/lib/api";
import type { QueueItem } from "@/lib/api";

/**
 * The queue: which document to open next.
 *
 * Its own page, so the review screen can give the whole width to the document
 * and what was read from it. A list and a page you are reading closely are
 * different jobs and were competing for the same screen.
 */
export default function QueuePage() {
  const router = useRouter();
  const [items, setItems] = useState<QueueItem[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [total, setTotal] = useState(0);
  // Which pile the reader asked for. The headline numbers are the filter: the
  // number you click is the list you get.
  const [filter, setFilter] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const latest = useRef(0);

  const load = useCallback(async () => {
    const mine = ++latest.current;
    try {
      const q = await api.queue(filter ?? undefined);
      if (mine !== latest.current) return;
      setItems(q.items);
      setCounts(q.counts);
      setTotal(q.total);
      setError(null);
    } catch (e) {
      if (mine !== latest.current) return;
      setError(e instanceof Error ? e.message : "Could not load the queue");
    }
  }, [filter]);

  useEffect(() => { void load(); }, [load]);

  return (
    <>
      <h1>Queue</h1>
      <p className="subtitle">
        Everything waiting on a human. Nothing counts as clinical fact until it
        is verified against a patient.
      </p>

      {error && <div className="error" style={{ marginBottom: 14 }}>{error}</div>}

      <div className="stat-row" style={{ marginBottom: 18 }}>
        <button className={`stat pick${filter === "needs_review" ? " on" : ""}`}
                onClick={() => setFilter(filter === "needs_review" ? null : "needs_review")}>
          <div className="value">{counts.needs_review ?? 0}</div>
          <div className="label">No patient matched</div>
        </button>
        <button className={`stat pick${filter === "parsed" ? " on" : ""}`}
                onClick={() => setFilter(filter === "parsed" ? null : "parsed")}>
          <div className="value">{counts.awaiting_confirm ?? 0}</div>
          <div className="label">Matched, unconfirmed</div>
        </button>
        <div className="stat">
          <div className="value">{counts.verified ?? 0}</div>
          <div className="label">Verified</div>
        </div>
        <div className="stat">
          <div className="value">{counts.rejected ?? 0}</div>
          <div className="label">Rejected</div>
        </div>
      </div>

      <div className="spread" style={{ marginBottom: 8 }}>
        <div className="small">
          {filter === "needs_review" && "Documents where no patient matched the UHID."}
          {filter === "parsed" && "Matched to a patient, waiting for someone to confirm."}
          {!filter && "Everything waiting, the unmatched first."}
        </div>
        <div className="small">
          {items.length < total
            ? `Showing ${items.length} of ${total} — pick a number above to narrow it`
            : `${total} document${total === 1 ? "" : "s"}`}
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {items.length === 0 ? (
          <div className="empty">
            Nothing waiting. Upload a report and it will appear here once the
            worker has read it.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>File</th>
                <th>Lab</th>
                <th>UHID on page</th>
                <th>Why it is here</th>
                <th className="num">Rows</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map((q, i) => {
                // The reason is real per-row data, but a queue is usually waiting on
                // one thing, so it prints the same sentence on every line. Showing it
                // only when it changes turns fifty repetitions into one heading per
                // group - the reader still learns why, without reading it fifty times.
                const repeats = i > 0 && items[i - 1].reason === q.reason;
                return (
                <tr
                  key={q.id}
                  style={{ cursor: "pointer" }}
                  onClick={() => router.push(`/review?doc=${q.id}`)}
                >
                  <td className="mono">{q.file_name ?? `document ${q.id}`}</td>
                  <td>{q.lab_name ?? <span className="faint">not read</span>}</td>
                  <td className="mono">
                    {q.detected_uhid ?? <span className="faint">not read</span>}
                  </td>
                  <td className="faint">
                    {repeats ? <span aria-hidden="true">·</span> : q.reason}
                    {repeats && <span className="sr-only">{q.reason}</span>}
                  </td>
                  <td className="num">{q.result_count}</td>
                  <td>
                    <span className={`chip ${q.status}`}>
                      {STATUS_LABEL[q.status] ?? q.status}
                    </span>
                    <div className="faint" style={{ fontSize: 11, marginTop: 2 }}>
                      {formatDate(q.received_at)}
                    </div>
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
