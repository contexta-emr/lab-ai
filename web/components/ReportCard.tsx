"use client";

import Link from "next/link";
import { formatDate, STATUS_LABEL } from "@/lib/api";
import { DeleteReport } from "./DeleteReport";
import type { DocumentSummary, ReadStep } from "@/lib/api";

/** A report uploaded in this visit, while it is being read. */
export type Live = {
  key: string;
  name: string;
  phase: "uploading" | "waiting" | "reading" | "done" | "failed" | "rejected";
  progress: number;
  docId?: string;
  tests?: number;
  secondLook?: boolean;
  retrying?: boolean;
  message?: string;
  result?: Extract<ReadStep, { step: "done" }>;
};

function FileIcon({ name }: { name: string | null }) {
  const ext = (name ?? "").split(".").pop()?.toLowerCase() ?? "";
  const image = ["png", "jpg", "jpeg", "webp", "tif", "tiff"].includes(ext);
  return (
    <span className={`file-icon${image ? " img" : ""}`} aria-hidden>
      {image ? "IMG" : "PDF"}
    </span>
  );
}

/** A report already read: what it is, whose it is, where it stands. */
export function ReportCard({ doc, onDeleted }: { doc: DocumentSummary; onDeleted?: () => void }) {
  const read = !["received", "parsing", "failed"].includes(doc.status);
  return (
    <div className="rc-wrap">
    <Link href={`/review?doc=${doc.id}`} className="report-card">
      <div className="rc-top">
        <FileIcon name={doc.file_name} />
        <div className="rc-name" title={doc.file_name ?? undefined}>
          {doc.file_name ?? "Untitled report"}
        </div>
      </div>
      <div className="rc-patient">
        {doc.patient_name ??
          (read ? <span className="ask">Which patient is this?</span> : " ")}
      </div>
      <div className="rc-meta">
        {[doc.lab_name, doc.collected_at ? formatDate(doc.collected_at) : null]
          .filter(Boolean)
          .join(" · ") || " "}
      </div>
      <div className="rc-foot">
        <span className={`chip ${doc.status}`}>{STATUS_LABEL[doc.status] ?? doc.status}</span>
        <span className="rc-tests">
          {doc.result_count} test{doc.result_count === 1 ? "" : "s"}
        </span>
      </div>
    </Link>
    {onDeleted && (
      <div className="rc-del">
        <DeleteReport id={doc.id} verified={doc.status === "verified"} compact onDeleted={onDeleted} />
      </div>
    )}
    </div>
  );
}

type StepView = { label: string; state: "pending" | "active" | "done" | "ask" };

/** The steps a card shows - each one driven by an event the server sent. */
function stepsFor(card: Live): StepView[] {
  const uploaded = card.phase !== "uploading";
  const reading = card.phase === "reading";
  const finished = card.phase === "done";
  const tests = card.tests ?? card.result?.tests;
  const found = card.tests !== undefined || finished;

  const steps: StepView[] = [
    { label: uploaded ? "Uploaded" : "Uploading", state: uploaded ? "done" : "active" },
    {
      label:
        card.phase === "waiting"
          ? card.retrying
            ? "Trying again"
            : "Waiting its turn"
          : "Reading the page",
      state: found ? "done" : reading ? "active" : "pending",
    },
    {
      label:
        tests !== undefined ? `Found ${tests} test${tests === 1 ? "" : "s"}` : "Finding the tests",
      state: found ? "done" : "pending",
    },
  ];
  if (card.secondLook) {
    steps.push({ label: "Taking a second look", state: finished ? "done" : "active" });
  }
  const patient = card.result?.patient_name;
  if (finished) {
    steps.push(
      patient
        ? { label: `Matched to ${patient}`, state: "done" }
        : { label: "Which patient is this?", state: "ask" },
    );
  } else {
    steps.push({
      label: "Matching the patient",
      state: found && reading && !card.secondLook ? "active" : "pending",
    });
  }
  if (card.phase === "failed") {
    steps.push({ label: "Couldn't read this one. A clearer photo usually helps.", state: "ask" });
  }
  return steps;
}

/** A report uploaded in this visit, its steps ticking as the server reports them. */
export function LiveCard({ card }: { card: Live }) {
  const problem = card.phase === "rejected" || (card.phase === "failed" && !card.docId);
  const status = card.result?.status;
  const body = (
    <>
      <div className="rc-top">
        <FileIcon name={card.name} />
        <div className="rc-name" title={card.name}>
          {card.name}
        </div>
      </div>
      {problem ? (
        <p className="rc-problem">{card.message}</p>
      ) : (
        <ol className="steps">
          {stepsFor(card).map((s) => (
            <li key={s.label} className={s.state}>
              <span className="step-dot" aria-hidden />
              {s.label}
            </li>
          ))}
        </ol>
      )}
      {card.phase === "uploading" && (
        <div
          className="bar"
          role="progressbar"
          aria-label="Uploading"
          aria-valuenow={Math.round(card.progress * 100)}
        >
          <span style={{ width: `${Math.round(card.progress * 100)}%` }} />
        </div>
      )}
      {card.phase === "done" && card.message && <p className="rc-note">{card.message}</p>}
      {card.phase === "done" && status && (
        <div className="rc-foot">
          <span className={`chip ${status}`}>{STATUS_LABEL[status] ?? status}</span>
          <span className="rc-tests">Open →</span>
        </div>
      )}
    </>
  );
  return card.result ? (
    <Link
      href={`/review?doc=${card.result.document_id}`}
      className={`report-card live ${card.phase}`}
    >
      {body}
    </Link>
  ) : (
    <div className={`report-card live ${card.phase}`}>{body}</div>
  );
}
