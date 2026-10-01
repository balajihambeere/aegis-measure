const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8001";
// A shared key for an internal single-tenant tool — not a per-user secret.
// It's inlined into the client bundle like any NEXT_PUBLIC_ variable, which
// is why this dashboard is meant to sit behind its own access control (VPN,
// SSO proxy, etc.) rather than relying on this key as the real boundary.
const API_KEY = process.env.NEXT_PUBLIC_AEGIS_API_KEY || "change-me-dev-key";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export interface Suite {
  id: string;
  name: string;
  description: string;
  default_schedule_interval_hours: number;
  created_at: string;
  updated_at: string;
}

export interface GoldenCase {
  id: string;
  suite_id: string;
  rubric_id: string | null;
  question: string;
  context: string | null;
  reference_answer: string | null;
  check_mode: "component" | "end_to_end" | "both";
  status: "draft" | "needs_resolution" | "approved" | "retired";
  source: string;
  tags: string[];
  resolved_by: string | null;
  resolved_at: string | null;
  resolution_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewStatus {
  case_id: string;
  submission_count: number;
  reviewer_names: string[];
  submissions:
    | { id: string; reviewer_name: string; proposed_answer: string; submitted_at: string }[]
    | null;
}

export interface EvalRun {
  id: string;
  suite_id: string;
  trigger_source: "schedule" | "on_change" | "manual";
  judge_model_version: string;
  status: "running" | "completed" | "errored";
  started_at: string;
  finished_at: string | null;
  error_message: string;
}

export interface CaseResult {
  id: string;
  run_id: string;
  case_id: string;
  check_mode: "component" | "end_to_end";
  grader_type: string;
  candidate_answer: string;
  retrieved_context: string | null;
  dimension_results: Record<string, { passed: boolean; rationale: string }>;
  passed: boolean;
  diagnosis: "upstream_retrieval_fault" | "reasoning_fault" | "none";
  created_at: string;
}

export interface CalibrationRun {
  id: string;
  rubric_id: string;
  judge_model_version: string;
  sample_size: number;
  agreement_count: number;
  agreement_rate: number;
  threshold: number;
  passed_threshold: boolean;
  disagreements: Record<string, unknown>[];
  created_at: string;
}

export interface Rubric {
  id: string;
  name: string;
  dimensions: { key: string; description: string }[];
  created_at: string;
}

export interface LaunchCoverageCheck {
  id: string;
  feature_name: string;
  launch_date: string;
  linked_suite_id: string | null;
  declared_gaps: string[];
  coverage_status: "covered" | "partial" | "none";
  answered_by: string;
  answered_at: string;
  re_review_due_at: string | null;
  re_review_completed_at: string | null;
}

export interface Alert {
  id: string;
  suite_id: string | null;
  run_id: string | null;
  alert_type: "pass_rate_drop" | "new_failure" | "calibration_stale" | "coverage_gap_due";
  message: string;
  created_at: string;
  acknowledged_at: string | null;
}

export const api = {
  listSuites: () => request<Suite[]>("/suites"),
  getSuite: (id: string) => request<Suite>(`/suites/${id}`),
  createSuite: (data: {
    name: string;
    description?: string;
    default_schedule_interval_hours?: number;
  }) => request<Suite>("/suites", { method: "POST", body: JSON.stringify(data) }),

  listCases: (params: { suite_id?: string; status?: string } = {}) => {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return request<GoldenCase[]>(`/cases${qs ? `?${qs}` : ""}`);
  },
  getCase: (id: string) => request<GoldenCase>(`/cases/${id}`),
  createCase: (data: Partial<GoldenCase> & { suite_id: string; question: string; source: string }) =>
    request<GoldenCase>("/cases", { method: "POST", body: JSON.stringify(data) }),
  getReviewStatus: (caseId: string) => request<ReviewStatus>(`/cases/${caseId}/reviews`),
  submitReview: (caseId: string, reviewer_name: string, proposed_answer: string) =>
    request(`/cases/${caseId}/reviews`, {
      method: "POST",
      body: JSON.stringify({ reviewer_name, proposed_answer }),
    }),
  resolveCase: (
    caseId: string,
    data: {
      decision: "approve" | "needs_resolution";
      resolved_by: string;
      reference_answer?: string;
      notes?: string;
    },
  ) => request<GoldenCase>(`/cases/${caseId}/resolve`, { method: "POST", body: JSON.stringify(data) }),
  retireCase: (caseId: string) => request<GoldenCase>(`/cases/${caseId}/retire`, { method: "POST" }),

  listRuns: (suiteId?: string) =>
    request<EvalRun[]>(`/runs${suiteId ? `?suite_id=${suiteId}` : ""}`),
  getRun: (id: string) => request<EvalRun>(`/runs/${id}`),
  getRunResults: (id: string) => request<CaseResult[]>(`/runs/${id}/results`),
  triggerRun: (suiteId: string) =>
    request<EvalRun>("/runs", {
      method: "POST",
      body: JSON.stringify({ suite_id: suiteId, trigger_source: "manual" }),
    }),

  listRubrics: () => request<Rubric[]>("/rubrics"),
  listCalibrationRuns: (rubricId?: string) =>
    request<CalibrationRun[]>(`/calibration-runs${rubricId ? `?rubric_id=${rubricId}` : ""}`),

  listCoverageChecks: () => request<LaunchCoverageCheck[]>("/coverage-checks"),
  completeReReview: (id: string) =>
    request<LaunchCoverageCheck>(`/coverage-checks/${id}/complete-re-review`, { method: "POST" }),

  listAlerts: (params: { suite_id?: string; unacknowledged_only?: boolean } = {}) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).map(([k, v]) => [k, String(v)])),
    ).toString();
    return request<Alert[]>(`/alerts${qs ? `?${qs}` : ""}`);
  },
  acknowledgeAlert: (id: string) => request<Alert>(`/alerts/${id}/acknowledge`, { method: "POST" }),
};
