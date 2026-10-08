"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, formatDate, STATUS_LABEL } from "@/lib/api";
import type { QueueItem } from "@/lib/api";
import { Find, HiddenNote } from "@/components/Filters";

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
  // Narrowing by hand, over what the server already sent. The status counts
  // above are a server query; this is not - a reviewer looking for one file
  // name should not wait for a round trip, and cannot mistype their way into
  // an empty result they cannot explain.
  const [find, setFind] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  // Confirming everything makes readings clinical fact in one press, so it asks
  // once. The same two-press shape the row-remove button uses.
  const [confirmingAll, setConfirmingAll] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // What the last bulk confirm did. Documents it held back are the gate doing
  // its job, not a failure, so this is a notice and not an error.
  const [notice, setNotice] = useState<string | null>(null);
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

  const shown = useMemo(() => {
    const needle = find.trim().toLowerCase();
    if (!needle) return items;
    return items.filter((q) =>
      (q.file_name ?? "").toLowerCase().includes(needle)
      || (q.lab_name ?? "").toLowerCase().includes(needle)
      || (q.detected_uhid ?? "").toLowerCase().includes(needle));
  }, [items, find]);

  async function confirmOne(id: string) {
    setBusy(id);
    setError(null);
    setNotice(null);
    try {
      // No patient id: this confirms the match already on the document rather
      // than asserting a new one, which is what keeps the audit honest about
      // whether the UHID found them or a person did.
      await api.review(id, { decision: "verify" });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not confirm that document");
    } finally {
      setBusy(null);
    }
  }

  async function confirmEverything() {
    setBusy("all");
    setError(null);
    setNotice(null);
    try {
      const { confirmed, held, held_because } = await api.confirmAll();
      setConfirmingAll(false);
      await load();
      const why = Object.entries(held_because).map(([reason, n]) => `${reason} (${n})`);
      setNotice(
        confirmed + held === 0
          ? "Nothing to confirm - no matched documents are waiting."
          : `Confirmed ${confirmed}.`
            + (held > 0 ? ` ${held} left for you to open: ${why.join("; ")}.` : ""),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not confirm the queue");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <h1>Queue</h1>
      <p className="subtitle">
        Everything waiting on a human. Nothing counts as clinical fact until it
        is verified against a patient.
      </p>

      {error && <div className="error" style={{ marginBottom: 14 }}>{error}</div>}
      {notice && <div className="notice" style={{ marginBottom: 14 }}>{notice}</div>}

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
        <button className={`stat pick${filter === "verified" ? " on" : ""}`}
                onClick={() => setFilter(filter === "verified" ? null : "verified")}>
          <div className="value">{counts.verified ?? 0}</div>
          <div className="label">Verified</div>
        </button>
        <button className={`stat pick${filter === "rejected" ? " on" : ""}`}
                onClick={() => setFilter(filter === "rejected" ? null : "rejected")}>
          <div className="value">{counts.rejected ?? 0}</div>
          <div className="label">Rejected</div>
        </button>
      </div>

      <div className="spread" style={{ marginBottom: 8 }}>
        <div className="small">
          {filter === "needs_review" && "Documents where no patient matched the UHID."}
          {filter === "parsed" && "Matched to a patient, waiting for someone to confirm."}
          {!filter && "Everything waiting, the unmatched first."}
        </div>
        <div className="row">
          {(counts.awaiting_confirm ?? 0) > 0 && (
            confirmingAll ? (
              <>
                <button className="primary" disabled={busy !== null}
                        onClick={() => void confirmEverything()}>
                  {busy === "all" ? "Confirming…" : "Yes, confirm the complete ones"}
                </button>
                <button disabled={busy !== null} onClick={() => setConfirmingAll(false)}>
                  Cancel
                </button>
                <span className="faint">
                  Files each one with nothing outstanding against its matched
                  patient. A missing core test, an unread value or a mapping to
                  confirm keeps a document here for you to open.
                </span>
              </>
            ) : (
              <button disabled={busy !== null} onClick={() => setConfirmingAll(true)}>
                Confirm complete matches…
              </button>
            )
          )}
        </div>
        <div className="row">
          <Find
            value={find}
            onChange={setFind}
            placeholder="Find a file, lab or UHID…  /"
            hint="Filter the queue by file name, lab or UHID"
          />
          <span className="small">
            {items.length < total
              ? `Showing ${items.length} of ${total} — pick a number above to narrow it`
              : `${total} document${total === 1 ? "" : "s"}`}
          </span>
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {items.length === 0 ? (
          <div className="empty">
            Nothing waiting. Upload a report and it will appear here once the
            worker has read it.
          </div>
        ) : shown.length === 0 ? (
          <div className="empty">
            Nothing in this queue matches “{find}”. It may be filed under a
            different lab, or the UHID may not have been read off the page.
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
                <th />
              </tr>
            </thead>
            <tbody>
              {shown.map((q, i) => {
                // The reason is real per-row data, but a queue is usually waiting on
                // one thing, so it prints the same sentence on every line. Showing it
                // only when it changes turns fifty repetitions into one heading per
                // group - the reader still learns why, without reading it fifty times.
                const repeats = i > 0 && shown[i - 1].reason === q.reason;
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
                  {/* Only a document already matched to somebody can be confirmed
                      from here. One that matched nobody has nothing to agree with
                      and has to be opened. */}
                  <td className="num" onClick={(e) => e.stopPropagation()}>
                    {q.status === "parsed" ? (
                      <button className="primary small" disabled={busy !== null}
                              onClick={() => void confirmOne(q.id)}>
                        {busy === q.id ? "…" : "Confirm"}
                      </button>
                    ) : (
                      <span className="faint">open</span>
                    )}
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <HiddenNote hidden={items.length - shown.length} onClear={() => setFind("")} />
    </>
  );
}
