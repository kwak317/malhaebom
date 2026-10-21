import { API_BASE_URL } from "../config/apiBase";

export type InterviewSummary = { clarified_points: string[]; next_practice: string[] };
export type InterviewChatResponse = {
  conversation_id: string;
  status: "active" | "finished";
  message: string;
  follow_up_question: string | null;
  summary: InterviewSummary | null;
};
export type InterviewChatRequest = {
  action: "start" | "message" | "finish";
  request_id: string;
  practice_session_id: string;
  conversation_id?: string;
  message?: string;
};

export class InterviewChatApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

export async function requestInterviewChat(
  request: InterviewChatRequest,
  accessToken: string,
  apiBase = API_BASE_URL,
  fetcher: typeof fetch = fetch,
): Promise<InterviewChatResponse> {
  if (!accessToken) throw new Error("로그인 후 면접 대화를 이어갈 수 있어요.");
  let response: Response;
  try {
    response = await fetcher(`${apiBase?.replace(/\/$/, "") || ""}/api/agent/chat`, {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
  } catch {
    throw new Error("면접 대화 서버에 연결하지 못했습니다. 다시 시도해 주세요.");
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload && typeof payload === "object" ? (payload as { detail?: unknown }).detail : null;
    throw new InterviewChatApiError(typeof detail === "string" ? detail : "면접 대화를 진행하지 못했습니다. 다시 시도해 주세요.", response.status);
  }
  if (!isChatResponse(payload)) throw new Error("면접 대화 응답 형식을 확인하지 못했습니다.");
  return payload;
}

function isChatResponse(value: unknown): value is InterviewChatResponse {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<InterviewChatResponse>;
  const summary = item.summary;
  const validSummary = Boolean(summary && Array.isArray(summary.clarified_points)
    && summary.clarified_points.length <= 3 && summary.clarified_points.every(isText)
    && Array.isArray(summary.next_practice) && summary.next_practice.length >= 1
    && summary.next_practice.length <= 2 && summary.next_practice.every(isText));
  return isText(item.conversation_id) && isText(item.message)
    && (item.follow_up_question === null || isText(item.follow_up_question))
    && ((item.status === "active" && summary === null)
      || (item.status === "finished" && item.follow_up_question === null && validSummary));
}
function isText(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}
