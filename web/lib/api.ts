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
};

export type DocumentDetail = DocumentSummary & {
  reports: Report[];
  candidates: PatientCandidate[];
};

export type QueueItem = {
  id: string;
  status: string;
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

  document: (id: string) => request<DocumentDetail>(`/documents/${id}`),

  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentSummary>("/documents", { method: "POST", body: form });
  },

  queue: () =>
    request<{ counts: Record<string, number>; items: QueueItem[] }>("/review/queue"),

  review: (id: string, body: { patient_id?: string; decision: "verify" | "reject"; note?: string }) =>
    request<{ document_id: string; status: string }>(`/review/${id}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  patients: (q?: string) =>
    request<Patient[]>(`/patients${q ? `?q=${encodeURIComponent(q)}` : ""}`),

  patient: (id: string) => request<Patient>(`/patients/${id}`),

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
