import { progressFetch } from "./loadingProgress";
import { API_BASE_URL } from "../config/apiBase";

export const DEFAULT_COACHING_TIMEOUT_MS = 200_000;

export type CoachingFailureState = "schema_violation" | "auth_error" | "timeout" | "rate_limited" | "context_error" | "mcp_error" | "provider_error";
export type CoachingStatus = "ok" | "needs_more_info" | "unsupported" | "unavailable";
export type CoachingAnalyzeRequest = {
  action: "analyze";
  question_id: string;
  answer_revision_id: string;
  job_snapshot_id: string;
};
export type CoachingEvidence = {
  source_type: "job_alignment" | "criterion_assessment";
  source_id: string;
  segment_id: string;
  quote: string;
  reason: string;
};
export type CoachingResponse = {
  status: CoachingStatus;
  job_alignment: Array<{ requirement_id: string; label: string; reason: string }>;
  intent_assessment: { label: string; reason: string };
  criterion_assessments: Array<{ criterion_id: string; assessment: string; reason: string; needed: string | null }>;
  evidence: CoachingEvidence[];
  gaps: Array<{ criterion_id: string; assessment: string; reason: string; needed: string }>;
  clarifying_question: string | null;
  next_actions: Array<{ target_type: string; target_id: string; action: string }>;
  example_answer: string | null;
};

type ApiErrorBody = {
  detail?: {
    state?: CoachingFailureState;
    code?: string;
    message?: string;
    retryable?: boolean;
  };
};

export class CoachingApiError extends Error {
  constructor(
    readonly state: CoachingFailureState,
    message: string,
    readonly retryable: boolean,
    readonly status: number | null,
  ) {
    super(message);
    this.name = "CoachingApiError";
  }
}

export async function requestCoaching({
  request,
  accessToken,
  timeoutMs = DEFAULT_COACHING_TIMEOUT_MS,
  fetchImpl = progressFetch,
}: {
  request: CoachingAnalyzeRequest;
  accessToken: string;
  timeoutMs?: number;
  fetchImpl?: typeof fetch;
}): Promise<CoachingResponse> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(`${API_BASE_URL}/api/agent`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    });
    const payload = await readJson(response);
    if (!response.ok) throw normalizeFailure(response.status, payload);
    if (!isCoachingResponse(payload)) {
      throw new CoachingApiError("schema_violation", "코칭 결과 형식을 확인하지 못했습니다.", true, response.status);
    }
    return payload;
  } catch (error) {
    if (error instanceof CoachingApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new CoachingApiError("timeout", "코칭 응답 시간이 초과되었습니다. 다시 시도해 주세요.", true, null);
    }
    throw new CoachingApiError("provider_error", "코칭 서버에 연결하지 못했습니다.", true, null);
  } finally {
    window.clearTimeout(timeout);
  }
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function normalizeFailure(status: number, payload: unknown): CoachingApiError {
  const body = payload && typeof payload === "object" ? payload as ApiErrorBody : {};
  const detail = body.detail;
  const state = detail?.state || stateFromStatus(status);
  return new CoachingApiError(
    state,
    detail?.message || defaultMessage(state),
    detail?.retryable ?? [429, 502, 504].includes(status),
    status,
  );
}

function stateFromStatus(status: number): CoachingFailureState {
  if (status === 401) return "auth_error";
  if (status === 422 || status === 502) return "schema_violation";
  if (status === 429) return "rate_limited";
  if (status === 504) return "timeout";
  if (status === 404 || status === 409) return "context_error";
  return "provider_error";
}

function defaultMessage(state: CoachingFailureState): string {
  if (state === "auth_error") return "로그인이 필요하거나 세션이 만료되었습니다.";
  if (state === "rate_limited") return "요청이 많아 잠시 뒤 다시 시도해 주세요.";
  if (state === "timeout") return "코칭 응답 시간이 초과되었습니다. 다시 시도해 주세요.";
  if (state === "schema_violation") return "코칭 결과 형식을 확인하지 못했습니다.";
  if (state === "context_error") return "사용할 수 있는 연습 기록을 찾지 못했습니다.";
  return "코칭 서버에 연결하지 못했습니다.";
}

function isCoachingResponse(value: unknown): value is CoachingResponse {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<CoachingResponse>;
  const hasExpectedExample = candidate.status === "ok" || candidate.status === "needs_more_info"
    ? typeof candidate.example_answer === "string" && candidate.example_answer.trim().length > 0
    : candidate.example_answer === null;
  return typeof candidate.status === "string"
    && Array.isArray(candidate.job_alignment)
    && Boolean(candidate.intent_assessment)
    && Array.isArray(candidate.criterion_assessments)
    && Array.isArray(candidate.evidence)
    && Array.isArray(candidate.gaps)
    && Array.isArray(candidate.next_actions)
    && hasExpectedExample;
}
