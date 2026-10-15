"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, formatDate } from "@/lib/api";
import type { Patient, WorkspaceInfo } from "@/lib/api";

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[] | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ws, setWs] = useState<WorkspaceInfo | null>(null);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    api.workspace().then(setWs).catch(() => setWs(null));
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      api
        .patients(query || undefined)
        .then((p) => { setPatients(p); setError(null); })
        .catch((e) => setError(e instanceof Error ? e.message : "Could not load"));
    }, 200);                       // debounce: one request per pause, not per keystroke
    return () => clearTimeout(timer);
  }, [query]);

  const canAdd = ws !== null && !ws.read_only;

  return (
    <>
      <div className="list-head">
        <div>
          <h1>Patients</h1>
          <p className="subtitle" style={{ margin: 0 }}>
            Everyone with lab reports filed here.
          </p>
        </div>
        {canAdd && !adding && (
          <button type="button" className="cta" onClick={() => setAdding(true)}>
            + Add patient
          </button>
        )}
      </div>

      {adding && <AddPatient onCancel={() => setAdding(false)} />}

      {error && <div className="error" style={{ marginBottom: 14 }}>{error}</div>}

      <div style={{ maxWidth: 360, margin: "16px 0 14px" }}>
        <input
          type="search"
          placeholder="Search by name or UHID"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <div className="card" style={{ padding: 0 }}>
        {patients === null ? (
          <div className="empty">Loading…</div>
        ) : patients.length === 0 ? (
          <div className="empty">
            {query
              ? "No patients matched."
              : canAdd
                ? "No patients yet. Add one here, or register one from a report you are checking."
                : "No patients yet."}
          </div>
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

/**
 * Register a patient before any report arrives for them. The same deliberate
 * act as registering one from a report - only the UHID and a given name are
 * required, because Indian reports often print one name and nothing else - and
 * a UHID already registered here is refused with the server's own words.
 */
function AddPatient({ onCancel }: { onCancel: () => void }) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const text = (key: string) => String(f.get(key) ?? "").trim();
    setSaving(true);
    setProblem(null);
    try {
      const p = await api.createPatient({
        uhid: text("uhid"),
        first_name: text("first"),
        last_name: text("last"),
        dob: text("dob") || null,
        gender: text("sex") || null,
        city: text("city") || null,
      });
      router.push(`/patients/${p.id}`);
    } catch (err) {
      setProblem(err instanceof Error ? err.message : "Could not add this patient.");
      setSaving(false);
    }
  }

  return (
    <form className="card add-patient" onSubmit={submit}>
      <h2>Add a patient</h2>
      {problem && <div className="error">{problem}</div>}
      <div className="add-patient-grid">
        <label>
          UHID
          <input name="uhid" required autoFocus placeholder="as the lab prints it" />
        </label>
        <label>
          Given name
          <input name="first" required />
        </label>
        <label>
          Surname
          <input name="last" placeholder="optional" />
        </label>
        <label>
          Date of birth
          <input name="dob" type="date" />
        </label>
        <label>
          Sex
          <select name="sex" defaultValue="">
            <option value="">—</option>
            <option value="F">Female</option>
            <option value="M">Male</option>
            <option value="O">Other</option>
          </select>
        </label>
        <label>
          City
          <input name="city" placeholder="optional" />
        </label>
      </div>
      <div className="add-patient-actions">
        <button className="primary" disabled={saving}>
          {saving ? "Adding…" : "Add patient"}
        </button>
        <button type="button" onClick={onCancel} disabled={saving}>Cancel</button>
        <span className="faint">
          Reports uploaded from now on that print this UHID are matched to them
          automatically. One already waiting is attached from its report.
        </span>
      </div>
    </form>
  );
}
