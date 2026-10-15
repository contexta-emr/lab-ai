"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/**
 * Delete a report for good, in two presses. The second says what is lost:
 * for a checked report, its values leave the patient's trends. Nothing to
 * delete in Sample data, which is read-only, so it is not offered there.
 */
export function DeleteReport({
  id,
  verified,
  compact = false,
  onDeleted,
}: {
  id: string;
  verified: boolean;
  compact?: boolean;
  onDeleted: () => void;
}) {
  const [writable, setWritable] = useState(false);
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [why, setWhy] = useState<string | null>(null);

  useEffect(() => {
    api.workspace().then((w) => setWritable(!w.read_only)).catch(() => setWritable(false));
  }, []);

  if (!writable) return null;

  // The card and the row it sits in are links; a press here must not open them.
  const hold = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  async function erase() {
    setBusy(true);
    setWhy(null);
    try {
      await api.deleteDocument(id);
      onDeleted();
    } catch (e) {
      setWhy(e instanceof Error ? e.message : "Could not delete it.");
      setBusy(false);
    }
  }

  if (!asking) {
    return (
      <button
        type="button"
        className={`del-btn${compact ? " small" : ""}`}
        title="Delete this report for good"
        onClick={(e) => {
          hold(e);
          setAsking(true);
        }}
      >
        Delete
      </button>
    );
  }

  return (
    <span className={`del-ask${compact ? " compact" : ""}`} role="group" aria-label="Delete this report">
      <span className="del-q">
        {verified
          ? "Checked report: its values leave the patient's trends. Delete for good?"
          : "Delete for good? This can't be undone."}
      </span>
      <button
        type="button"
        className="danger-solid small"
        disabled={busy}
        onClick={(e) => {
          hold(e);
          void erase();
        }}
      >
        {busy ? "Deleting…" : "Delete"}
      </button>
      <button
        type="button"
        className="small"
        disabled={busy}
        onClick={(e) => {
          hold(e);
          setAsking(false);
        }}
      >
        Cancel
      </button>
      {why && <span className="del-why">{why}</span>}
    </span>
  );
}
