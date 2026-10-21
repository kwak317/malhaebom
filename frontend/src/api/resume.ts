import { progressFetch } from "./loadingProgress";
import { API_BASE_URL } from "../config/apiBase";

export const RESUME_CATEGORIES = {
  role: "지원 직무", career: "경력·인턴", technology: "사용 기술",
  project: "프로젝트 경험", education: "교육·졸업 상태", qualification: "자격증·어학",
} as const;
export type ResumeCategory = keyof typeof RESUME_CATEGORIES;
export type ConfirmedResumeFact = { category: ResumeCategory; value: string; keyword: string | null };
export type ResumeFact = ConfirmedResumeFact & { page: number; source_excerpt: string };
export type ResumeAnalysis = { facts: ResumeFact[]; model: string };
export type ResumeProfile = { facts: ConfirmedResumeFact[] };

export async function analyzeResumePdf(file: File, accessToken: string, signal?: AbortSignal): Promise<ResumeAnalysis> {
  const body = new FormData();
  body.append("file", file);
  const response = await progressFetch(`${API_BASE_URL}/api/resume/analyze`, {
    method: "POST", headers: { Authorization: `Bearer ${accessToken}` }, body, signal,
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload && typeof payload === "object" && "detail" in payload ? payload.detail : null;
    throw new Error(typeof detail === "string" ? detail : "이력서를 검토하지 못했습니다. 다시 제출해 주세요.");
  }
  if (!payload || typeof payload !== "object" || !("model" in payload) || typeof payload.model !== "string"
      || !("facts" in payload) || !Array.isArray(payload.facts) || payload.facts.length > 30
      || !payload.facts.every((fact) => fact && typeof fact === "object"
        && Object.prototype.hasOwnProperty.call(RESUME_CATEGORIES, fact.category)
        && typeof fact.value === "string" && fact.value.length > 0
        && (fact.keyword === null || typeof fact.keyword === "string")
        && Number.isInteger(fact.page) && fact.page >= 1 && fact.page <= 10
        && typeof fact.source_excerpt === "string")) {
    throw new Error("이력서 분석 응답 형식을 확인하지 못했습니다.");
  }
  return payload as ResumeAnalysis;
}
