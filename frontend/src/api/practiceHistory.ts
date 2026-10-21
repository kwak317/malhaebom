import { API_BASE_URL } from "../config/apiBase";
import type { InterviewSummary } from "./interviewChat";

export type PracticeInterviewChatHistory = {
  conversation_id: string;
  completed_at: string;
  messages: Array<{
    role: "user" | "assistant";
    message: string;
    follow_up_question: string | null;
    summary: InterviewSummary | null;
  }>;
};

export type PracticeHistoryMetrics = {
  cpm: number | null;
  long_silence_count: number;
  repetition_count: number;
};

export type ComparisonAssessment = "met" | "partial" | "not_observed" | "undetermined";
export type ComparisonChange = "added" | "unchanged" | "no_longer_observed" | "changed";
export type ComparisonDirection = "increased" | "decreased" | "same" | "unavailable";

export type PracticeContentAssessment = {
  assessment: ComparisonAssessment;
  reason: string;
  evidence: string[];
  needed: string | null;
};

export type PracticeContentCriterion = {
  criterion_id: string;
  description: string;
  first: PracticeContentAssessment;
  second: PracticeContentAssessment;
  change: ComparisonChange;
};

export type PracticeMetricChange = {
  first: number | null;
  second: number | null;
  direction: ComparisonDirection;
};

export type PracticeComparison = {
  content_available: boolean;
  content_notice: string | null;
  criteria: PracticeContentCriterion[];
  added_explanations: Array<{
    criterion_id: string;
    description: string;
    evidence: string[];
  }>;
  still_missing: Array<{
    criterion_id: string;
    description: string;
    assessment: ComparisonAssessment;
    needed: string | null;
  }>;
  contradictions: Array<{
    attempt_no: 1 | 2;
    criterion_id: string;
    description: string;
    reason: string;
    evidence: string[];
  }>;
  delivery: {
    cpm: PracticeMetricChange;
    long_silence_count: PracticeMetricChange;
    repetition_count: PracticeMetricChange;
  };
};

export type PracticeHistoryAttempt = {
  attempt_no: 1 | 2;
  job_id: string;
  transcript: string;
  metrics: PracticeHistoryMetrics;
  feedback: string[];
  content_analysis?: {
    criteria: Array<{
      criterion_id: string;
      description: string;
      assessment: ComparisonAssessment;
      reason: string;
      evidence: string[];
      needed: string | null;
    }>;
  };
};

export type PracticeHistoryRecord = {
  practice_session_id: string;
  question_type: "preset" | "custom";
  question_id: string | null;
  custom_question_text: string | null;
  practiced_at: string;
  attempts: PracticeHistoryAttempt[];
  comparison?: PracticeComparison;
  interview_chat?: PracticeInterviewChatHistory;
};

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export class PracticeHistoryApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PracticeHistoryApiError";
  }
}

export async function fetchPracticeRecords(
  accessToken: string,
  apiBase = API_BASE_URL,
  fetcher: Fetcher = fetch,
): Promise<PracticeHistoryRecord[]> {
  const response = await request("/practice-records", accessToken, apiBase, fetcher, "연습 기록을 불러오지 못했습니다. 다시 시도해 주세요.");
  const payload: unknown = await response.json().catch(() => null);
  if (!isRecordsPayload(payload)) throw new PracticeHistoryApiError("연습 기록을 불러오지 못했습니다. 다시 시도해 주세요.");
  return payload.records;
}

export async function fetchPracticeRecord(
  practiceSessionId: string,
  accessToken: string,
  apiBase = API_BASE_URL,
  fetcher: Fetcher = fetch,
): Promise<PracticeHistoryRecord> {
  const response = await request(`/practice-records/${encodeURIComponent(practiceSessionId)}`, accessToken, apiBase, fetcher, "연습 기록을 불러오지 못했습니다. 다시 시도해 주세요.");
  const payload: unknown = await response.json().catch(() => null);
  if (!isRecord(payload)) throw new PracticeHistoryApiError("연습 기록을 불러오지 못했습니다. 다시 시도해 주세요.");
  return payload;
}

export type PreparationHistoryMessage = {
  role: "user" | "assistant";
  message: string;
  follow_up_question: string | null;
};

export async function fetchPreparationChatHistory(
  practiceSessionId: string, accessToken: string, apiBase = API_BASE_URL, fetcher: Fetcher = fetch,
): Promise<PreparationHistoryMessage[]> {
  const response = await request(`/practice-records/${encodeURIComponent(practiceSessionId)}/preparation-chat`,
    accessToken, apiBase, fetcher, "채팅 내역을 불러오지 못했어요. 다시 시도해 주세요.");
  const payload = await response.json().catch(() => null);
  if (!Array.isArray(payload?.messages) || !payload.messages.every((item: PreparationHistoryMessage) =>
    item && ["user", "assistant"].includes(item.role) && typeof item.message === "string"
    && (item.follow_up_question === null || typeof item.follow_up_question === "string"))) {
    throw new PracticeHistoryApiError("채팅 내역을 불러오지 못했어요. 다시 시도해 주세요.");
  }
  return payload.messages;
}

export async function deletePracticeRecord(
  practiceSessionId: string,
  accessToken: string,
  apiBase = API_BASE_URL,
  fetcher: Fetcher = fetch,
): Promise<void> {
  await request(`/practice-records/${encodeURIComponent(practiceSessionId)}`, accessToken, apiBase, fetcher, "연습 기록을 삭제하지 못했습니다. 다시 시도해 주세요.", "DELETE");
}

export async function deleteAllPracticeRecords(
  accessToken: string,
  apiBase = API_BASE_URL,
  fetcher: Fetcher = fetch,
): Promise<void> {
  await request("/practice-records", accessToken, apiBase, fetcher, "연습 기록을 삭제하지 못했습니다. 다시 시도해 주세요.", "DELETE");
}

async function request(
  path: string,
  accessToken: string,
  apiBase: string | undefined,
  fetcher: Fetcher,
  errorMessage: string,
  method = "GET",
): Promise<Response> {
  const base = apiBase?.replace(/\/$/, "") || "";
  if (!accessToken) throw new PracticeHistoryApiError("로그인 후 연습 기록을 확인할 수 있어요.");
  let response: Response;
  try {
    response = await fetcher(`${base}${path}`, { method: method === "GET" ? undefined : method, headers: { Authorization: `Bearer ${accessToken}` } });
  } catch {
    throw new PracticeHistoryApiError(errorMessage);
  }
  if (!response.ok) throw new PracticeHistoryApiError(errorMessage);
  return response;
}

function isRecordsPayload(value: unknown): value is { records: PracticeHistoryRecord[] } {
  return Boolean(value && typeof value === "object" && Array.isArray((value as { records?: unknown }).records));
}

function isRecord(value: unknown): value is PracticeHistoryRecord {
  return Boolean(value && typeof value === "object" && typeof (value as { practice_session_id?: unknown }).practice_session_id === "string" && Array.isArray((value as { attempts?: unknown }).attempts));
}
