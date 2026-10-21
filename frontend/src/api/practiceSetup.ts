import { progressFetch } from "./loadingProgress";
import { API_BASE_URL } from "../config/apiBase";
import type { ResumeProfile } from "./resume";

export type JobRequirement = {
  id: string;
  code: string;
  text: string;
  source_excerpt: string | null;
  display_order: number;
};

export type JobPosting = {
  id: string;
  company: string;
  title: string;
  source_url: string;
  captured_at: string;
  data_origin: "reviewed" | "demo" | "alio" | "public_job" | "mofe_job" | "private_job";
  requirements: JobRequirement[];
};

export type CreatePracticeSessionInput = {
  applicant_context?: {
    selected_ncs_ids: string[];
    readme_analysis: GithubReadmeAnalysis | null;
    resume_profile: ResumeProfile | null;
  };
  job_posting_id: string;
  requirement_ids: string[];
  question_type: "preset" | "custom";
  question_id: string | null;
  custom_question_text: string | null;
};

export type PracticeSession = {
  practice_session_id: string;
  expires_at: string;
};

export type AlioRecruitment = {
  announcement_id: number;
  company: string;
  title: string;
  source_url: string | null;
  announced_at: string | null;
  deadline: string | null;
  location: string | null;
  employment_type: string | null;
  recruitment_type: string | null;
};

export type AnalyzeAlioRecruitmentInput = {
  announcement_id: number;
  company: string;
  title: string;
  source_url: string;
};

export type PublicEmploymentRecruitment = {
  announcement_id: number;
  company: string;
  title: string;
  announced_at: string | null;
  deadline: string | null;
  location: string | null;
  employment_type: string | null;
  recruitment_type: string | null;
};

export type AnalyzePublicEmploymentRecruitmentInput = {
  announcement_id: number;
  company: string;
  title: string;
};

export type MofeRecruitment = {
  announcement_id: number;
  company: string;
  title: string;
  source_url: string | null;
  announced_at: string | null;
  deadline: string | null;
  location: string | null;
  employment_type: string | null;
  recruitment_type: string | null;
};

export type AnalyzeMofeRecruitmentInput = {
  announcement_id: number;
  company: string;
  title: string;
};

export type JobSearchIntent = {
  should_search: boolean;
  query: string | null;
};

export type NcsCompetencyOption = {
  id: string;
  category: "knowledge" | "skill" | "attitude";
  label: string;
  ncs_unit_code: string;
  ncs_unit_name: string;
};

export type NcsBackendCompetencies = {
  data_source?: "live" | "cached";
  fetched_at?: string | null;
  job_name: string;
  source_url: string;
  options: NcsCompetencyOption[];
};

export type GithubReadmeAnalysis = {
  source_url: string;
  readme_sha: string;
  model: string;
  technology_stack: { name: string; description: string; source_excerpt: string }[];
  project_flow: { description: string; source_excerpt: string }[];
};

export type SaraminRecommendation = {
  company: string;
  title: string;
  source_url: string;
  deadline: string | null;
  experience: string;
  matched_technologies: string[];
  matched_project_flows: string[];
  matched_ncs_labels: string[];
  source_excerpt: string;
  matched_resume_technologies?: string[];
  matched_resume_project_flows?: string[];
  matched_chat_experience?: string[];
};

export async function recommendSaraminJobs({
  accessToken,
  selectedNcsIds,
  readmeAnalysis,
  resumeProfile = null,
  preparationConversationId = null,
  fetchImpl = progressFetch,
}: {
  accessToken: string;
  selectedNcsIds: string[];
  readmeAnalysis: GithubReadmeAnalysis | null;
  resumeProfile?: ResumeProfile | null;
  preparationConversationId?: string | null;
  fetchImpl?: typeof fetch;
}): Promise<SaraminRecommendation[]> {
  const response = await fetchImpl(`${API_BASE_URL}/api/job-search/recommendations`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ selected_ncs_ids: selectedNcsIds, readme_analysis: readmeAnalysis, ...(resumeProfile ? { resume_profile: resumeProfile } : {}), ...(preparationConversationId ? { preparation_conversation_id: preparationConversationId } : {}) }),
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(readError(payload, "공고를 검색하지 못했습니다."));
  const candidate = payload as { recommendations?: unknown } | null;
  if (!candidate || !Array.isArray(candidate.recommendations)
      || !candidate.recommendations.every((item: unknown) => {
        if (!item || typeof item !== "object") return false;
        const job = item as Partial<SaraminRecommendation>;
        return typeof job.company === "string" && typeof job.title === "string"
          && typeof job.source_url === "string" && isNullableString(job.deadline)
          && typeof job.experience === "string" && typeof job.source_excerpt === "string"
          && Array.isArray(job.matched_technologies)
          && job.matched_technologies.every((value) => typeof value === "string")
          && Array.isArray(job.matched_project_flows)
          && job.matched_project_flows.every((value) => typeof value === "string")
          && Array.isArray(job.matched_ncs_labels)
          && job.matched_ncs_labels.every((value) => typeof value === "string");
      })) throw new Error("공고 검색 응답 형식을 확인하지 못했습니다.");
  return candidate.recommendations;
}

export async function analyzeRecommendedJob({
  accessToken,
  sourceUrl,
  fetchImpl = fetch,
}: {
  accessToken: string;
  sourceUrl: string;
  fetchImpl?: typeof fetch;
}): Promise<JobPosting> {
  const response = await fetchImpl(`${API_BASE_URL}/api/job-search/recommendations/analyze`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ source_url: sourceUrl }),
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(readError(payload, "공고 원문을 검토하지 못했습니다."));
  if (!isJobPosting(payload)) throw new Error("검토 공고 응답 형식을 확인하지 못했습니다.");
  return payload;
}

export async function analyzeGithubReadme({
  accessToken,
  sourceUrl,
  fetchImpl = progressFetch,
}: {
  accessToken: string;
  sourceUrl: string;
  fetchImpl?: typeof fetch;
}): Promise<GithubReadmeAnalysis> {
  const response = await fetchImpl(`${API_BASE_URL}/api/github/readme/analyze`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ source_url: sourceUrl }),
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(readError(payload, "README를 분석하지 못했습니다."));
  if (!isGithubReadmeAnalysis(payload)) throw new Error("README 분석 응답 형식을 확인하지 못했습니다.");
  return payload;
}

export async function getNcsBackendCompetencies({
  accessToken,
  source = "api",
  fetchImpl = fetch,
}: {
  accessToken: string;
  fetchImpl?: typeof fetch;
  source?: "api" | "database";
}): Promise<NcsBackendCompetencies> {
  const response = await fetchImpl(`${API_BASE_URL}/api/ncs/backend-competencies${source === "database" ? "?source=database" : ""}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(readError(payload, "NCS 역량을 불러오지 못했습니다."));
  if (!isNcsBackendCompetencies(payload)) throw new Error("NCS 역량 응답 형식을 확인하지 못했습니다.");
  return payload;
}

export async function listJobPostings({
  accessToken,
  fetchImpl = fetch,
}: {
  accessToken: string;
  fetchImpl?: typeof fetch;
}): Promise<JobPosting[]> {
  const response = await fetchImpl(`${API_BASE_URL}/api/job-postings`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(readError(payload, "공고를 불러오지 못했습니다."));
  if (!isJobPostingList(payload)) throw new Error("공고 응답 형식을 확인하지 못했습니다.");
  return payload.job_postings;
}

export async function createPracticeSession({
  accessToken,
  input,
  fetchImpl = fetch,
}: {
  accessToken: string;
  input: CreatePracticeSessionInput;
  fetchImpl?: typeof fetch;
}): Promise<PracticeSession> {
  const response = await fetchImpl(`${API_BASE_URL}/api/practice-sessions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(readError(payload, "연습 조건을 저장하지 못했습니다."));
  if (!isPracticeSession(payload)) throw new Error("연습 세션 응답 형식을 확인하지 못했습니다.");
  return payload;
}

export async function searchAlioRecruitments({
  accessToken,
  query,
  page = 1,
  fetchImpl = fetch,
}: {
  accessToken: string;
  query: string;
  page?: number;
  fetchImpl?: typeof fetch;
}): Promise<{ recruitments: AlioRecruitment[]; totalCount: number }> {
  const search = new URLSearchParams({ query, page: String(page) });
  const response = await fetchImpl(`${API_BASE_URL}/api/alio/recruitments?${search}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(readError(payload, "ALIO 공고를 검색하지 못했습니다."));
  if (!isAlioRecruitmentSearchResponse(payload)) {
    throw new Error("ALIO 공고 응답 형식을 확인하지 못했습니다.");
  }
  return { recruitments: payload.recruitments, totalCount: payload.total_count };
}

export async function analyzeAlioRecruitment({
  accessToken,
  input,
  fetchImpl = fetch,
}: {
  accessToken: string;
  input: AnalyzeAlioRecruitmentInput;
  fetchImpl?: typeof fetch;
}): Promise<JobPosting> {
  const response = await fetchImpl(`${API_BASE_URL}/api/alio/recruitments/analyze`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(readError(payload, "AI 공고 분석을 저장하지 못했습니다."));
  if (!isJobPosting(payload)) throw new Error("AI 공고 분석 응답 형식을 확인하지 못했습니다.");
  return payload;
}

export async function searchPublicEmploymentRecruitments({
  accessToken,
  query,
  page = 1,
  fetchImpl = fetch,
}: {
  accessToken: string;
  query: string;
  page?: number;
  fetchImpl?: typeof fetch;
}): Promise<{ recruitments: PublicEmploymentRecruitment[]; totalCount: number }> {
  const search = new URLSearchParams({ query, page: String(page) });
  const response = await fetchImpl(
    `${API_BASE_URL}/api/public-employment/recruitments?${search}`,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  const payload = await readJson(response);
  if (!response.ok) throw new Error(readError(payload, "공공취업정보 공고를 검색하지 못했습니다."));
  if (!isPublicEmploymentRecruitmentSearchResponse(payload)) {
    throw new Error("공공취업정보 공고 응답 형식을 확인하지 못했습니다.");
  }
  return { recruitments: payload.recruitments, totalCount: payload.total_count };
}

export async function analyzePublicEmploymentRecruitment({
  accessToken,
  input,
  fetchImpl = fetch,
}: {
  accessToken: string;
  input: AnalyzePublicEmploymentRecruitmentInput;
  fetchImpl?: typeof fetch;
}): Promise<JobPosting> {
  const response = await fetchImpl(
    `${API_BASE_URL}/api/public-employment/recruitments/analyze`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );
  const payload = await readJson(response);
  if (!response.ok) throw new Error(readError(payload, "AI 공고 분석을 저장하지 못했습니다."));
  if (!isJobPosting(payload)) throw new Error("AI 공고 분석 응답 형식을 확인하지 못했습니다.");
  return payload;
}

export async function searchMofeRecruitments({
  accessToken,
  query,
  page = 1,
  fetchImpl = fetch,
}: {
  accessToken: string;
  query: string;
  page?: number;
  fetchImpl?: typeof fetch;
}): Promise<{ recruitments: MofeRecruitment[]; totalCount: number }> {
  const search = new URLSearchParams({ query, page: String(page) });
  const response = await fetchImpl(`${API_BASE_URL}/api/mofe/recruitments?${search}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(readError(payload, "공공기관 채용정보 공고를 검색하지 못했습니다."));
  if (!isMofeRecruitmentSearchResponse(payload)) {
    throw new Error("공공기관 채용정보 공고 응답 형식을 확인하지 못했습니다.");
  }
  return { recruitments: payload.recruitments, totalCount: payload.total_count };
}

export async function analyzeMofeRecruitment({
  accessToken,
  input,
  fetchImpl = fetch,
}: {
  accessToken: string;
  input: AnalyzeMofeRecruitmentInput;
  fetchImpl?: typeof fetch;
}): Promise<JobPosting> {
  const response = await fetchImpl(`${API_BASE_URL}/api/mofe/recruitments/analyze`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(readError(payload, "AI 공고 분석을 저장하지 못했습니다."));
  if (!isJobPosting(payload)) throw new Error("AI 공고 분석 응답 형식을 확인하지 못했습니다.");
  return payload;
}

export async function interpretJobSearchMessage({
  accessToken,
  message,
  fetchImpl = fetch,
}: {
  accessToken: string;
  message: string;
  fetchImpl?: typeof fetch;
}): Promise<JobSearchIntent> {
  const response = await fetchImpl(`${API_BASE_URL}/api/job-search-intent`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(readError(payload, "채팅 메시지를 이해하지 못했습니다."));
  if (!isJobSearchIntent(payload)) throw new Error("채팅 의도 응답 형식을 확인하지 못했습니다.");
  return payload;
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function readError(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object" || !("detail" in payload)) return fallback;
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "message" in detail) {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string") return message;
  }
  return fallback;
}

function isJobPostingList(value: unknown): value is { job_postings: JobPosting[] } {
  if (!value || typeof value !== "object" || !("job_postings" in value)) return false;
  const postings = (value as { job_postings?: unknown }).job_postings;
  return Array.isArray(postings) && postings.every(isJobPosting);
}

function isNcsBackendCompetencies(value: unknown): value is NcsBackendCompetencies {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<NcsBackendCompetencies>;
  return typeof candidate.job_name === "string"
    && typeof candidate.source_url === "string"
    && (candidate.data_source === undefined || candidate.data_source === "live" || candidate.data_source === "cached")
    && (candidate.fetched_at === undefined || candidate.fetched_at === null || (typeof candidate.fetched_at === "string" && !Number.isNaN(Date.parse(candidate.fetched_at))))
    && Array.isArray(candidate.options)
    && candidate.options.every((option) => option
      && typeof option.id === "string"
      && (option.category === "knowledge" || option.category === "skill" || option.category === "attitude")
      && typeof option.label === "string"
      && typeof option.ncs_unit_code === "string"
      && typeof option.ncs_unit_name === "string");
}

function isGithubReadmeAnalysis(value: unknown): value is GithubReadmeAnalysis {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<GithubReadmeAnalysis>;
  return typeof candidate.source_url === "string"
    && typeof candidate.readme_sha === "string"
    && typeof candidate.model === "string"
    && Array.isArray(candidate.technology_stack)
    && candidate.technology_stack.every((item) => item
      && typeof item.name === "string"
      && typeof item.description === "string"
      && typeof item.source_excerpt === "string")
    && Array.isArray(candidate.project_flow)
    && candidate.project_flow.every((item) => item
      && typeof item.description === "string"
      && typeof item.source_excerpt === "string");
}

function isJobPosting(value: unknown): value is JobPosting {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<JobPosting>;
  return typeof candidate.id === "string"
    && typeof candidate.company === "string"
    && typeof candidate.title === "string"
    && typeof candidate.source_url === "string"
    && (candidate.data_origin === "reviewed"
      || candidate.data_origin === "demo"
      || candidate.data_origin === "alio"
      || candidate.data_origin === "public_job"
      || candidate.data_origin === "mofe_job"
      || candidate.data_origin === "private_job")
    && Array.isArray(candidate.requirements)
    && candidate.requirements.length > 0
    && candidate.requirements.every((requirement) => (
      typeof requirement.id === "string"
      && typeof requirement.code === "string"
      && typeof requirement.text === "string"
      && isNullableString(requirement.source_excerpt)
      && typeof requirement.display_order === "number"
    ));
}

function isPublicEmploymentRecruitmentSearchResponse(value: unknown): value is {
  total_count: number;
  recruitments: PublicEmploymentRecruitment[];
} {
  if (!value || typeof value !== "object") return false;
  const candidate = value as { total_count?: unknown; recruitments?: unknown };
  return typeof candidate.total_count === "number"
    && Array.isArray(candidate.recruitments)
    && candidate.recruitments.every((recruitment) => {
      if (!recruitment || typeof recruitment !== "object") return false;
      const item = recruitment as Partial<PublicEmploymentRecruitment>;
      return typeof item.announcement_id === "number"
        && typeof item.company === "string"
        && typeof item.title === "string"
        && isNullableString(item.announced_at)
        && isNullableString(item.deadline)
        && isNullableString(item.location)
        && isNullableString(item.employment_type)
        && isNullableString(item.recruitment_type);
    });
}

function isMofeRecruitmentSearchResponse(value: unknown): value is {
  total_count: number;
  recruitments: MofeRecruitment[];
} {
  if (!value || typeof value !== "object") return false;
  const candidate = value as { total_count?: unknown; recruitments?: unknown };
  return typeof candidate.total_count === "number"
    && Array.isArray(candidate.recruitments)
    && candidate.recruitments.every((recruitment) => {
      if (!recruitment || typeof recruitment !== "object") return false;
      const item = recruitment as Partial<MofeRecruitment>;
      return typeof item.announcement_id === "number"
        && typeof item.company === "string"
        && typeof item.title === "string"
        && isNullableString(item.source_url)
        && isNullableString(item.announced_at)
        && isNullableString(item.deadline)
        && isNullableString(item.location)
        && isNullableString(item.employment_type)
        && isNullableString(item.recruitment_type);
    });
}

function isJobSearchIntent(value: unknown): value is JobSearchIntent {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<JobSearchIntent>;
  return typeof candidate.should_search === "boolean"
    && isNullableString(candidate.query)
    && (!candidate.should_search || typeof candidate.query === "string");
}

function isPracticeSession(value: unknown): value is PracticeSession {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<PracticeSession>;
  return typeof candidate.practice_session_id === "string"
    && typeof candidate.expires_at === "string";
}

function isAlioRecruitmentSearchResponse(value: unknown): value is {
  total_count: number;
  recruitments: AlioRecruitment[];
} {
  if (!value || typeof value !== "object") return false;
  const candidate = value as { total_count?: unknown; recruitments?: unknown };
  return typeof candidate.total_count === "number"
    && Array.isArray(candidate.recruitments)
    && candidate.recruitments.every((recruitment) => {
      if (!recruitment || typeof recruitment !== "object") return false;
      const item = recruitment as Partial<AlioRecruitment>;
      return typeof item.announcement_id === "number"
        && typeof item.company === "string"
        && typeof item.title === "string"
        && isNullableString(item.source_url)
        && isNullableString(item.announced_at)
        && isNullableString(item.deadline)
        && isNullableString(item.location)
        && isNullableString(item.employment_type)
        && isNullableString(item.recruitment_type);
    });
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}
