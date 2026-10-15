/**
 * The only place that talks to the API.
 *
 * Ids are strings on purpose, all the way through the frontend. PostgreSQL
 * BIGINT goes to 2^63; JavaScript loses integer precision above 2^53. Parse one
 * into a number and a patient id can change value silently, which in this
 * application means attaching a lab report to the wrong person. So they arrive
 * as strings, stay strings, and go back as strings.
 */

import { getWorkspace } from "./workspace";
import type { Workspace } from "./workspace";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "contexta.lab.token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

/** True when a request was superseded rather than failing. Callers ignore these. */
export function isAbort(e: unknown): boolean {
  return e instanceof DOMException && e.name === "AbortError";
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  headers.set("X-Workspace", getWorkspace());
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${BASE}${path}`, { ...init, headers, cache: "no-store" });

  if (res.status === 401) {
    setToken(null);
    throw new ApiError(401, "Session expired. Sign in again.");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* the body was not JSON; the status text will do */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/* ----------------------------------------------------------------- types */

export type DocumentSummary = {
  id: string;
  status: "received" | "parsing" | "parsed" | "needs_review" | "verified" | "rejected" | "failed";
  source: string;
  detected_uhid: string | null;
  detected_uhid_label: string | null;
  detected_patient_name: string | null;
  patient_id: string | null;
  patient_name: string | null;
  patient_uhid: string | null;
  patient_match_method: string | null;
  patient_match_confidence: number | null;
  page_count: number | null;
  ocr_engine: string | null;
  extraction_confidence: number | null;
  result_count: number;
  unmatched_count: number;
  lab_name: string | null;
  collected_at: string | null;
  received_at: string | null;
  is_synthetic: boolean;
  /** Which page you are looking at. Obvious on paper, invisible in a queue. */
  file_name: string | null;
};

export type ResultRow = {
  id: string;
  printed_label: string;
  analyte_code: string | null;
  analyte_name: string | null;
  panel_code: string | null;
  match_method: string | null;
  match_confidence: number | null;
  value_text: string;
  value_numeric: number | null;
  unit: string | null;
  reference_printed: string | null;
  flag: string | null;
  is_text_result: boolean;
  is_derived: boolean;
  /** Set once a human has edited this row. */
  is_reviewed?: boolean;
  /** What the machine thought before a human changed the mapping. */
  corrected_from?: string | null;
};

export type Section = {
  id: string;
  heading_printed: string | null;
  panel_code: string | null;
  panel_match_method: string | null;
  results: ResultRow[];
};

export type Report = {
  id: string;
  lab_name: string | null;
  accession_no: string | null;
  uhid_printed: string | null;
  patient_name_printed: string | null;
  age_printed: string | null;
  sex_printed: string | null;
  collected_at: string | null;
  referring_doctor: string | null;
  layout_hint: string | null;
  sections: Section[];
  notes: { note_type: string; marker: string | null; note_text: string }[];
};

export type PatientCandidate = {
  patient_id: string;
  uhid: string;
  full_name: string;
  dob: string | null;
  match_method: string;
  confidence: number;
  /** Why this person was suggested, for a demographic match. Absent for a UHID
      match, where the identifier IS the reason. */
  evidence?: {
    name_similarity?: number;
    dob?: string;
    sex?: string;
    printed_name?: string;
  } | null;
};

export type DocumentDetail = DocumentSummary & {
  reports: Report[];
  candidates: PatientCandidate[];
};

export type QueueItem = {
  id: string;
  status: string;
  file_name: string | null;
  detected_uhid: string | null;
  detected_patient_name: string | null;
  patient_match_confidence: number | null;
  extraction_confidence: number | null;
  lab_name: string | null;
  result_count: number;
  unmatched_count: number;
  received_at: string;
  reason: string;
};

export type Patient = {
  id: string;
  uhid: string;
  full_name: string;
  dob: string | null;
  gender: string | null;
  city: string | null;
  document_count: number;
  result_count: number;
  last_report_at: string | null;
};

export type TrendPoint = {
  /** Null when the report's date could not be read - the API's schema has always
   *  said so, and declaring it non-null here is what let the chart pass null to
   *  new Date() and plot the reading at 1 January 1970 (review B3). */
  collected_at: string | null;
  value_numeric: number | null;
  value_text: string;
  // "<" or ">" split off the front of value_text, so <0.01 charts without
  // pretending to be exactly 0.01.
  value_operator: string | null;
  unit: string | null;
  // The range as the lab printed it. ref_low/ref_high are the parsed bounds and
  // are only set when the printed form was parseable.
  reference_printed: string | null;
  ref_low: number | null;
  ref_high: number | null;
  flag: string | null;
  lab_name: string | null;
  printed_label: string;
  document_id: string;
};

/** What a document should have contained, against what it did.
 *  found / missing / extra are three different things and must never share a
 *  colour: a row the page contains is not a failure to find one. */
export type CoverageMember = {
  analyte_code: string;
  analyte_name: string;
  is_core: boolean;
  state: "found" | "confirm" | "no_value" | "missing" | "absent";
  printed_label: string | null;
};

export type CoveragePanel = {
  panel_code: string;
  panel_name: string;
  titled: boolean;
  found: number;
  expected: number;
  core_missing: string[];
  needs_confirm: string[];
  no_value: string[];
  members: CoverageMember[];
  extra: { printed_label: string; value: string | null; state: "extra" }[];
};

export type Coverage = {
  checked: boolean;
  panels: CoveragePanel[];
  unresolved: string[];
  note: string | null;
};

/** One line of the results table: what the page printed, what we resolved it
 *  to, and the verdict on both. Merged server-side so there is one definition
 *  of a row rather than the browser joining two lists. */
export type DocRow = {
  result_id: string | null;
  /** False for a row the page never printed - there is nothing to correct. */
  editable: boolean;
  status: "found" | "confirm" | "missing" | "no_value" | "extra" | "absent";
  analyte_name: string | null;
  analyte_code: string | null;
  required: string;
  panel: string | null;
  section: string | null;
  printed_label: string | null;
  value_text: string | null;
  unit: string | null;
  flag: string | null;
  reference_printed: string | null;
  is_reviewed: boolean;
  corrected_from: string | null;
};

/** One term from a typed checklist, and what the master made of it.
 *  `panel` expanded to its members; `analyte` resolved to one; `unresolved`
 *  matched nothing and carries spelling hints instead of a guess. */
export type ResolvedTerm = {
  input: string;
  kind: "panel" | "analyte" | "unresolved";
  panel_code?: string;
  match_method?: string;
  confidence?: number;
  analytes: { analyte_code: string; analyte_name: string | null;
              from_panel: string | null }[];
  did_you_mean?: { label: string; analyte_code: string }[];
};

/** One term from a typed list, and what the master made of it. `verdict` is
 *  present only on the doctor's list - the patient's is never scored. */
export type PanelRow = {
  id: string; code: string; display_name: string;
  description?: string | null; is_core: boolean; analyte_count: number;
};

export type ListTerm = {
  input: string;
  kind: "panel" | "analyte" | "unresolved";
  panel_code?: string;
  panel_name?: string;
  match_method?: string;
  confidence?: number;
  analytes: { analyte_code: string; analyte_name: string | null;
              is_core?: boolean; from_panel: string | null }[];
  did_you_mean?: { label: string; analyte_code: string }[];
  /** Panel level: present or not. complete says whether all of it was read. */
  verdict?: "present" | "not_present" | "no_value" | "unrecognised";
  complete?: boolean;
  read?: number;
  /** read + the optional members nobody ran. The same definition the coverage
   *  chips use, so a panel reads one total wherever it appears. */
  accounted?: number;
  expected?: number;
  on_page?: string[];
  not_on_page?: string[];
  not_read?: string[];
  /** Optional members the lab did not run. Settled, never listed as missing. */
  not_run?: string[];
};

/** A panel on the page that no ordered term asked for. */
export type AdditionalPanel = {
  panel_code: string;
  panel_name: string;
  read: number;
  accounted: number;
  expected: number;
  complete: boolean;
};

export type DocLists = {
  doctor_order: {
    raw_text: string;
    terms: ListTerm[];
    summary: { present: number; not_present: number; no_value: number;
               unrecognised: number; total: number; incomplete: number };
    /** Panels on the page the order did not include. Empty when nothing was ordered. */
    additional: AdditionalPanel[];
    updated_at?: string | null;
  };
  patient_tag: { raw_text: string; terms: ListTerm[]; updated_at?: string | null };
};

export type DocRows = {
  /** Four buckets that sum to `expected`. `found` is a certain mapping only;
   *  `read` is found + confirm, which is what "how much did we get off the
   *  page" means to a person. See api/app/services/coverage.py::_panel_counts. */
  panels: {
    panel_code: string;
    panel_name: string;
    found: number;
    confirm: number;
    no_value: number;
    missing: number;
    absent: number;
    read: number;
    expected: number;
  }[];
  rows: DocRow[];
  note: string | null;
};

export type Trend = {
  patient_id: string;
  analyte_code: string;
  analyte_name: string | null;
  unit: string | null;
  point_count: number;
  points: TrendPoint[];
};

export type AvailableAnalyte = {
  code: string;
  display_name: string;
  default_unit: string | null;
  panel_code: string | null;
  point_count: number;
  /** Null only when every reading of it is undated - see TrendPoint. */
  first_at: string | null;
  last_at: string | null;
};

/* ------------------------------------------------------------------- api */

/* ------------------------------------------------------- workspace, reading */

export type WorkspaceInfo = {
  workspace: Workspace;
  practice_name: string;
  read_only: boolean;
  sample_available: boolean;
  max_upload_mb: number;
};

/** One line of POST /documents/read-next: a real step, as it happened. */
export type ReadStep =
  | { step: "idle" }
  | { step: "error" }
  | { step: "reading"; document_id: string; attempt: number }
  | { step: "found"; tests: number }
  | { step: "second_look" }
  | {
      step: "done";
      document_id: string;
      replaced: string;
      status?: DocumentSummary["status"];
      patient_id?: string | null;
      patient_name?: string | null;
      tests?: number;
    }
  | { step: "failed"; document_id: string; state: "received" | "failed" };

let workspaceInfo: Promise<WorkspaceInfo> | null = null;

/** One test we know, for "Add a line". */
export type MasterAnalyte = { code: string; display_name: string; default_unit: string | null };

let analyteList: Promise<MasterAnalyte[]> | null = null;

function authHeaders(): Headers {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  headers.set("X-Workspace", getWorkspace());
  return headers;
}

function detailOf(body: unknown): string | null {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return null;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; email: string; role: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  /** Resolve a typed checklist through the same funnel the extractor uses.
   *  One round trip for the whole list - see api/app/routers/master.py. */
  resolveMany: (labels: string[]) =>
    request<{ terms: ResolvedTerm[]; truncated_at: number | null }>(
      "/master/resolve-many",
      { method: "POST", body: JSON.stringify({ labels }) }),

  panels: (coreOnly = false) =>
    request<PanelRow[]>(`/master/panels${coreOnly ? "?core_only=true" : ""}`),

  /** Both lists for a document, resolved against the master as it stands now. */
  documentLists: (id: string) => request<DocLists>(`/documents/${id}/lists`),

  saveDocumentList: (id: string, kind: "doctor_order" | "patient_tag", raw_text: string) =>
    request<DocLists>(`/documents/${id}/lists/${kind}`, {
      method: "PUT",
      body: JSON.stringify({ raw_text }),
    }),

  health: () => request<{ status: string; analytes: number; aliases: number }>("/health"),

  documents: (params: { status?: string; patient_id?: string; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.status) q.set("status", params.status);
    if (params.patient_id) q.set("patient_id", params.patient_id);
    if (params.limit) q.set("limit", String(params.limit));
    return request<DocumentSummary[]>(`/documents?${q}`);
  },

  coverage: (id: string, signal?: AbortSignal) =>
    request<Coverage>(`/documents/${id}/coverage`, { signal }),

  /** The one table: printed and resolved, merged, with a verdict per row. */
  rows: (id: string, signal?: AbortSignal) =>
    request<DocRows>(`/documents/${id}/rows`, { signal }),

  /** Fix one row. Only the fields sent are changed - omitting a field leaves
   *  it alone, while sending "" clears it. That distinction is why this takes
   *  a partial object rather than the whole row. */
  correctResult: (documentId: string, resultId: string, patch: {
    label?: string; value?: string; unit?: string;
    reference?: string; flag?: string; analyte_code?: string;
  }) => request<ResultRow>(`/documents/${documentId}/results/${resultId}`, {
    method: "PATCH", body: JSON.stringify(patch),
  }),

  /** Remove a row the engine should not have produced. Soft, and recorded. */
  removeResult: (documentId: string, resultId: string) =>
    request<void>(`/documents/${documentId}/results/${resultId}`, { method: "DELETE" }),

  /** Delete a report for good: its results and its stored file go with it. */
  deleteDocument: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),

  /** A person adds a row the reading missed. With analyte_code it is that
   *  test; without one it keeps the printed name and no code. */
  addResult: (documentId: string, body: {
    label?: string; value: string; unit?: string; reference?: string;
    flag?: string; analyte_code?: string; heading?: string;
  }) => request<ResultRow>(`/documents/${documentId}/results`, {
    method: "POST", body: JSON.stringify(body),
  }),

  /** Every test we know - the vocabulary changes only by migration, so once a page load. */
  masterAnalytes: (): Promise<MasterAnalyte[]> =>
    (analyteList ??= request<MasterAnalyte[]>("/master/analytes").catch((e: unknown) => {
      analyteList = null;
      throw e;
    })),

  /** The stored page itself. A URL rather than a fetch, because an <iframe>
   *  or <object> loads it directly - and the endpoint is practice-scoped, so
   *  it is not a static file anyone can guess at. The workspace rides in the
   *  query, because an <object> cannot send a header. */
  fileUrl: (id: string) => `${BASE}/documents/${id}/file?workspace=${getWorkspace()}`,

  document: (id: string, signal?: AbortSignal) =>
    request<DocumentDetail>(`/documents/${id}`, { signal }),

  /** Which workspace this browser is in. Asked once per page load. */
  workspace: (): Promise<WorkspaceInfo> =>
    (workspaceInfo ??= request<WorkspaceInfo>("/workspace").catch((e: unknown) => {
      workspaceInfo = null;
      throw e;
    })),

  /** Upload one file and report how much has gone. XMLHttpRequest, because
   *  fetch cannot report upload progress. */
  uploadWithProgress: (file: File, onProgress: (fraction: number) => void) =>
    new Promise<DocumentSummary>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${BASE}/documents`);
      authHeaders().forEach((value, name) => xhr.setRequestHeader(name, value));
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(e.loaded / e.total);
      };
      xhr.onload = () => {
        let body: unknown = null;
        try {
          body = JSON.parse(xhr.responseText);
        } catch {
          /* not JSON; the status text will do */
        }
        if (xhr.status >= 200 && xhr.status < 300) resolve(body as DocumentSummary);
        else reject(new ApiError(xhr.status, detailOf(body) ?? (xhr.statusText || "Upload failed.")));
      };
      xhr.onerror = () =>
        reject(new ApiError(0, "Couldn't reach the server. Check the connection and try again."));
      const form = new FormData();
      form.append("file", file);
      xhr.send(form);
    }),

  /** Read the next waiting report, calling onStep as each step happens.
   *  Resolves with the last step, or null if the stream said nothing. */
  readNext: async (onStep: (step: ReadStep) => void): Promise<ReadStep | null> => {
    const res = await fetch(`${BASE}/documents/read-next`, {
      method: "POST",
      headers: authHeaders(),
      cache: "no-store",
    });
    if (!res.ok || !res.body) {
      let body: unknown = null;
      try {
        body = await res.json();
      } catch {
        /* not JSON */
      }
      throw new ApiError(res.status, detailOf(body) ?? res.statusText);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let last: ReadStep | null = null;
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let newline = buffer.indexOf("\n");
      while (newline >= 0) {
        const line = buffer.slice(0, newline).trim();
        buffer = buffer.slice(newline + 1);
        if (line) {
          last = JSON.parse(line) as ReadStep;
          onStep(last);
        }
        newline = buffer.indexOf("\n");
      }
    }
    return last;
  },

  queue: (status?: string, signal?: AbortSignal) =>
    request<{
      counts: Record<string, number>;
      items: QueueItem[];
      total: number;
      showing: number;
    }>(`/review/queue${status ? `?status=${status}` : ""}`, { signal }),

  /**
   * Confirm every matched document with nothing outstanding on it. The rest are
   * held for a person; held_because counts documents per reason, and one
   * document can carry several, so it may sum to more than held.
   */
  confirmAll: () =>
    request<{ confirmed: number; held: number; held_because: Record<string, number> }>(
      "/review/confirm-all",
      { method: "POST" },
    ),

  review: (id: string, body: { patient_id?: string; decision: "verify" | "reject"; note?: string }) =>
    request<{ document_id: string; status: string }>(`/review/${id}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  patients: (q?: string) =>
    request<Patient[]>(`/patients${q ? `?q=${encodeURIComponent(q)}` : ""}`),

  patient: (id: string) => request<Patient>(`/patients/${id}`),

  /** Register someone a report arrived for. A deliberate act: nothing on the
      server creates a patient on its own, because one misread UHID would
      otherwise become a duplicate record. */
  createPatient: (body: {
    uhid: string;
    first_name: string;
    last_name?: string;
    dob?: string | null;
    gender?: string | null;
    city?: string | null;
  }) => request<Patient>("/patients", { method: "POST", body: JSON.stringify(body) }),

  patientAnalytes: (id: string) =>
    request<AvailableAnalyte[]>(`/patients/${id}/analytes`),

  patientDocuments: (id: string) =>
    request<Record<string, unknown>[]>(`/patients/${id}/documents`),

  trend: (patientId: string, code: string) =>
    request<Trend>(`/patients/${patientId}/trend/${code}`),

  unmatched: () =>
    request<{ id: string; printed_label: string; occurrence_count: number }[]>(
      "/master/unmatched"
    ),
};

/* --------------------------------------------------------------- helpers */

export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  // Indian convention, which is what every report in the corpus prints.
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export const STATUS_LABEL: Record<string, string> = {
  received: "Reading…",
  parsing: "Reading…",
  parsed: "Ready to confirm",
  needs_review: "Needs a look",
  verified: "Checked",
  rejected: "Set aside",
  failed: "Couldn't read",
};
