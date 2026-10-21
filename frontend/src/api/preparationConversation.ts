import { API_BASE_URL } from "../config/apiBase";
import type { JobPosting, GithubReadmeAnalysis } from "./practiceSetup";
import type { ResumeProfile } from "./resume";
export type PreparationMaterials = { selected_ncs_ids: string[]; readme_analysis: GithubReadmeAnalysis | null; resume_profile: ResumeProfile | null };

export type PreparationStage = "ncs" | "readme" | "resume" | "first_coaching";
export type PreparationSelection = {
  job_posting_id: string | null;
  requirement_ids: string[];
  question_id: string | null;
  custom_question_text: string | null;
};
export type PreparationSelectionState = PreparationSelection & { selected_ncs_ids: string[] };
export type RestartTarget = "ncs" | "resume" | "readme" | "jobs" | "questions";
export type PracticeRestart = { token: string; target: RestartTarget; new_graduate_only: boolean; materials: PreparationMaterials; selection: PreparationSelection; expires_at: string };
export type PreparationResponse = {
  conversation_id: string;
  message: string;
  follow_up_question: string | null;
  action: "stay" | "request_rerecord" | "selection_updated" | "practice_restarted";
  status: "ok" | "unavailable";
  selection_state?: PreparationSelectionState | null;
  selection_revision?: number | null;
  execution_result?: "verified" | "awaiting_confirmation" | "failed" | null;
  selection_job?: JobPosting | null;
  restart?: PracticeRestart | null;
};

export class PreparationSelectionConflict extends Error {
  constructor(message: string, public readonly selection: PreparationSelectionState,
    public readonly revision: number, public readonly job: JobPosting | null) { super(message); }
}

async function post(path: string, accessToken: string, input: object) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    if (response.status === 409 && detail?.code === "selection_conflict" && detail.selection_state
        && Number.isInteger(detail.selection_revision) && detail.selection_revision >= 0) {
      throw new PreparationSelectionConflict(detail.message, detail.selection_state, detail.selection_revision, detail.selection_job ?? null);
    }
    throw new Error(typeof body?.detail === "string" ? body.detail : "대화 요청을 처리하지 못했어요. 다시 시도해 주세요.");
  }
  return response;
}

export async function sendPreparationMessage(accessToken: string, input: {
  request_id: string; conversation_id: string | null; practice_session_id: string | null;
  current_stage: PreparationStage; message: string;
  review_context: PreparationMaterials;
  selection?: PreparationSelection;
  selection_revision?: number | null;
  ui_context?: string;
  restart_target?: RestartTarget;
  restart_confirmation?: { token: string; confirm: boolean };
}): Promise<PreparationResponse> {
  return (await post("/api/agent/preparation", accessToken, input)).json();
}

export async function bindPreparationConversation(accessToken: string, conversationId: string, sessionId: string) {
  await post("/api/agent/preparation/bind", accessToken, {
    conversation_id: conversationId, practice_session_id: sessionId,
  });
}

export type ConfirmedPreparationExperience = {
  id: string;
  source_type: "user_chat";
  user_confirmed: true;
  facts: { kind: string; value: string; source_excerpt: string; source_message_id: string }[];
};

export async function getConfirmedPreparationExperiences(accessToken: string, conversationId: string): Promise<ConfirmedPreparationExperience[]> {
  const response = await fetch(`${API_BASE_URL}/api/agent/preparation/${encodeURIComponent(conversationId)}/confirmed`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) throw new Error("저장한 경험을 참고자료에 불러오지 못했어요. 채팅을 다시 보내면 재시도합니다.");
  const body = await response.json();
  return body.experiences.filter((item: ConfirmedPreparationExperience) => item.user_confirmed === true && item.source_type === "user_chat");
}
