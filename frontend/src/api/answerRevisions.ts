import { API_BASE_URL } from "../config/apiBase";

export type AnswerRevision = {
  answer_revision_id: string;
  analysis_job_id: string;
  practice_session_id: string;
  question_id: string;
  answer_segments: Array<{ segment_id: string; text: string }>;
  confirmed_at: string;
  expires_at: string;
  job_snapshot_id: string | null;
};

export async function confirmAnswerRevision({
  analysisJobId,
  confirmedText,
  accessToken,
  fetchImpl = fetch,
}: {
  analysisJobId: string;
  confirmedText: string;
  accessToken: string;
  fetchImpl?: typeof fetch;
}): Promise<AnswerRevision> {
  const response = await fetchImpl(
    `${API_BASE_URL}/analysis-jobs/${encodeURIComponent(analysisJobId)}/answer-revisions`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ confirmed_text: confirmedText }),
    },
  );
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(apiMessage(payload, "전사문을 확정하지 못했습니다."));
  }
  if (!isAnswerRevision(payload)) {
    throw new Error("답변 revision 형식을 확인하지 못했습니다.");
  }
  return payload;
}

function isAnswerRevision(value: unknown): value is AnswerRevision {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<AnswerRevision>;
  return typeof item.answer_revision_id === "string"
    && typeof item.analysis_job_id === "string"
    && typeof item.practice_session_id === "string"
    && typeof item.question_id === "string"
    && Array.isArray(item.answer_segments)
    && (typeof item.job_snapshot_id === "string" || item.job_snapshot_id === null);
}

function apiMessage(value: unknown, fallback: string): string {
  if (!value || typeof value !== "object" || !("detail" in value)) return fallback;
  const detail = (value as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "message" in detail) {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string") return message;
  }
  return fallback;
}
