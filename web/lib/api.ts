/**
 * The only place that talks to the API.
 *
 * Ids are strings on purpose, all the way through the frontend. PostgreSQL
 * BIGINT goes to 2^63; JavaScript loses integer precision above 2^53. Parse one
 * into a number and a patient id can change value silently, which in this
 * application means attaching a lab report to the wrong person. So they arrive
 * as strings, stay strings, and go back as strings.
 */

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
  collected_at: string;
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

export type DocRows = {
  panels: { panel_code: string; panel_name: string; found: number; expected: number }[];
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
  first_at: string;
  last_at: string;
};

/* ------------------------------------------------------------------- api */

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; email: string; role: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
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

  /** The stored page itself. A URL rather than a fetch, because an <iframe>
   *  or <object> loads it directly - and the endpoint is practice-scoped, so
   *  it is not a static file anyone can guess at. */
  fileUrl: (id: string) => `${BASE}/documents/${id}/file`,

  document: (id: string, signal?: AbortSignal) =>
    request<DocumentDetail>(`/documents/${id}`, { signal }),

  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentSummary>("/documents", { method: "POST", body: form });
  },

  queue: (status?: string, signal?: AbortSignal) =>
    request<{
      counts: Record<string, number>;
      items: QueueItem[];
      total: number;
      showing: number;
    }>(`/review/queue${status ? `?status=${status}` : ""}`, { signal }),

  /** Confirm every already-matched document waiting in the queue. */
  confirmAll: () =>
    request<{ confirmed: number }>("/review/confirm-all", { method: "POST" }),

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
  received: "Received",
  parsing: "Parsing",
  parsed: "Awaiting confirmation",
  needs_review: "Needs review",
  verified: "Verified",
  rejected: "Rejected",
  failed: "Failed",
};
