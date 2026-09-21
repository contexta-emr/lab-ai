"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { api, STATUS_LABEL } from "@/lib/api";
import type { DocumentSummary } from "@/lib/api";

type Item = {
  name: string;
  state: "uploading" | "done" | "error";
  result?: DocumentSummary;
  error?: string;
};

export default function UploadPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [over, setOver] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  async function send(files: FileList | File[]) {
    const list = Array.from(files);
    setItems((prev) => [
      ...list.map((f) => ({ name: f.name, state: "uploading" as const })),
      ...prev,
    ]);

    // One at a time. The extractor is CPU-bound and a reviewer would rather see
    // the first result than have six half-finished.
    for (const file of list) {
      try {
        const result = await api.upload(file);
        setItems((prev) =>
          prev.map((it) =>
            it.name === file.name && it.state === "uploading"
              ? { ...it, state: "done", result }
              : it
          )
        );
      } catch (e) {
        const message = e instanceof Error ? e.message : "Upload failed";
        setItems((prev) =>
          prev.map((it) =>
            it.name === file.name && it.state === "uploading"
              ? { ...it, state: "error", error: message }
              : it
          )
        );
      }
    }
  }

  return (
    <>
      <h1>Upload</h1>
      <p className="subtitle">
        A PDF or a photograph of a lab report. The service reads it, works out
        which patient it belongs to from the UHID on the page, and files the results.
      </p>

      <div
        className={`dropzone${over ? " over" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          if (e.dataTransfer.files?.length) void send(e.dataTransfer.files);
        }}
      >
        <p style={{ fontSize: 15, color: "var(--text)" }}>
          Drop lab reports here
        </p>
        <p>PDF, PNG, JPEG or TIFF, up to 25 MB each</p>
        <button className="primary" onClick={() => input.current?.click()} style={{ marginTop: 10 }}>
          Choose files
        </button>
        <input
          ref={input}
          type="file"
          multiple
          hidden
          accept=".pdf,.png,.jpg,.jpeg,.webp,.tiff,.tif"
          onChange={(e) => e.target.files && send(e.target.files)}
        />
      </div>

      {items.length > 0 && (
        <>
          <h2>This session</h2>
          <div className="card" style={{ padding: 0 }}>
            <table>
              <thead>
                <tr>
                  <th>File</th>
                  <th>Outcome</th>
                  <th>UHID read</th>
                  <th>Patient</th>
                  <th className="num">Results</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map((it, i) => (
                  <tr key={`${it.name}-${i}`}>
                    <td>{it.name}</td>
                    <td>
                      {it.state === "uploading" && <span className="chip muted">Reading…</span>}
                      {it.state === "error" && <span className="chip failed">Failed</span>}
                      {it.state === "done" && it.result && (
                        <span className={`chip ${it.result.status}`}>
                          {STATUS_LABEL[it.result.status] ?? it.result.status}
                        </span>
                      )}
                      {it.error && <div className="faint">{it.error}</div>}
                    </td>
                    <td className="mono">{it.result?.detected_uhid ?? "—"}</td>
                    <td>
                      {it.result?.patient_id ? (
                        <Link href={`/patients/${it.result.patient_id}`}>
                          {it.result.patient_name}
                        </Link>
                      ) : it.state === "done" ? (
                        <span className="unmatched">needs a human</span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="num">{it.result?.result_count ?? "—"}</td>
                    <td>
                      {it.result && (
                        <Link href={`/review?doc=${it.result.id}`} className="faint">
                          open
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="faint" style={{ marginTop: 12 }}>
            A document with no text layer — a scan or a phone photograph — is stored
            but not read: it needs OCR, and nothing is invented in the meantime.
          </p>
        </>
      )}
    </>
  );
}
