"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, formatDate, getToken, setToken, STATUS_LABEL } from "@/lib/api";
import type { DocumentSummary } from "@/lib/api";

export default function OverviewPage() {
  const [authed, setAuthed] = useState(false);
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
    }
  }, []);

  useEffect(() => {
    if (getToken()) {
      setAuthed(true);
      void load();
    }
  }, [load]);

  if (!authed) {
    return <LoginCard onSignedIn={() => { setAuthed(true); void load(); }} />;
  }

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

      <div className="stat-row">
        <div className="stat">
          <div className="value">{total}</div>
          <div className="label">Documents</div>
        </div>
        <div className="stat">
          <div className="value">{counts.verified ?? 0}</div>
          <div className="label">Verified</div>
        </div>
        <div className={`stat${(counts.needs_review ?? 0) > 0 ? " attention" : ""}`}>
          <div className="value">{counts.needs_review ?? 0}</div>
          <div className="label">Need review</div>
        </div>
        <div className="stat">
          <div className="value">{counts.awaiting_confirm ?? 0}</div>
          <div className="label">Awaiting confirmation</div>
        </div>
        <div className="stat">
          <div className="value">{health?.analytes ?? "—"}</div>
          <div className="label">Analytes in master</div>
        </div>
        <div className="stat">
          <div className="value">{health?.aliases ?? "—"}</div>
          <div className="label">Known spellings</div>
        </div>
      </div>

      {health && health.analytes === 0 && (
        <div className="notice" style={{ marginTop: 16 }}>
          The analyte master is empty, so every printed label will resolve to nothing.
          Apply <span className="mono">db/004_seed_analyte_master.sql</span>.
        </div>
      )}

      <h2>Recent documents</h2>
      <div className="card" style={{ padding: 0 }}>
        {recent.length === 0 ? (
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
                <tr key={d.id}>
                  <td>
                    <span className={`chip ${d.status}`}>
                      {STATUS_LABEL[d.status] ?? d.status}
                    </span>
                  </td>
                  <td>
                    <Link href={`/review?doc=${d.id}`}>{d.lab_name ?? "Unnamed lab"}</Link>
                  </td>
                  <td>
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

function LoginCard({ onSignedIn }: { onSignedIn: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.login(email, password);
      setToken(res.access_token);
      onSignedIn();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ maxWidth: 380, margin: "8vh auto" }}>
      <h1>Sign in</h1>
      <p className="subtitle">Contexta Lab IDP review console.</p>
      <form className="card" onSubmit={submit}>
        {error && <div className="error" style={{ marginBottom: 12 }}>{error}</div>}
        <label className="faint" htmlFor="email">Email</label>
        <input
          id="email" type="email" value={email} required autoComplete="username"
          onChange={(e) => setEmail(e.target.value)} style={{ marginBottom: 12 }}
        />
        <label className="faint" htmlFor="password">Password</label>
        <input
          id="password" type="password" value={password} required autoComplete="current-password"
          onChange={(e) => setPassword(e.target.value)} style={{ marginBottom: 16 }}
        />
        <button className="primary" type="submit" disabled={busy} style={{ width: "100%" }}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
