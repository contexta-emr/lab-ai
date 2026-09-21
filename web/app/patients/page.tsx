"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, formatDate } from "@/lib/api";
import type { Patient } from "@/lib/api";

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      api
        .patients(query || undefined)
        .then(setPatients)
        .catch((e) => setError(e instanceof Error ? e.message : "Could not load"));
    }, 200);                       // debounce: one request per pause, not per keystroke
    return () => clearTimeout(timer);
  }, [query]);

  return (
    <>
      <h1>Patients</h1>
      <p className="subtitle">Everyone with lab documents filed in this practice.</p>

      {error && <div className="error" style={{ marginBottom: 14 }}>{error}</div>}

      <div style={{ maxWidth: 360, marginBottom: 14 }}>
        <input
          type="search"
          placeholder="Search by name or UHID"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <div className="card" style={{ padding: 0 }}>
        {patients.length === 0 ? (
          <div className="empty">No patients matched.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>UHID</th>
                <th>Born</th>
                <th className="num">Documents</th>
                <th className="num">Results</th>
                <th>Last report</th>
              </tr>
            </thead>
            <tbody>
              {patients.map((p) => (
                <tr key={p.id}>
                  <td>
                    <Link href={`/patients/${p.id}`}>{p.full_name}</Link>
                    {p.city && <div className="faint">{p.city}</div>}
                  </td>
                  <td className="mono">{p.uhid}</td>
                  <td>{formatDate(p.dob)}</td>
                  <td className="num">{p.document_count}</td>
                  <td className="num">{p.result_count}</td>
                  <td>{formatDate(p.last_report_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
