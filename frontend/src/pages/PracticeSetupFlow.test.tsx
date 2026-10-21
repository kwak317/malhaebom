import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NavigationProvider } from "../navigation";
import PracticePage, { type PracticeQuestion } from "./PracticePage";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

const listJobPostings = vi.fn();
const getNcsBackendCompetencies = vi.fn();
const analyzeGithubReadme = vi.fn();
const recommendSaraminJobs = vi.fn();
const analyzeRecommendedJob = vi.fn();
const createPracticeSession = vi.fn();
const searchAlioRecruitments = vi.fn();
const analyzeAlioRecruitment = vi.fn();
const searchPublicEmploymentRecruitments = vi.fn();
const analyzePublicEmploymentRecruitment = vi.fn();
const searchMofeRecruitments = vi.fn();
const searchIncheonRecruitments = vi.fn();
const analyzeMofeRecruitment = vi.fn();
const interpretJobSearchMessage = vi.fn();
const getSession = vi.fn();
const analyzeResumePdf = vi.fn();
const sendPreparationMessage = vi.fn();
vi.mock("../api/preparationConversation", () => ({ sendPreparationMessage: (...args: unknown[]) => sendPreparationMessage(...args), bindPreparationConversation: vi.fn() }));
const resumeProfile = { facts: [{ category: "technology", value: "Spring Boot 사용", keyword: "Spring Boot" }] };
vi.mock("../api/resume", async (importOriginal) => ({ ...(await importOriginal<object>()), analyzeResumePdf: (...args: unknown[]) => analyzeResumePdf(...args) }));

vi.mock("../api/practiceSetup", () => ({
  listJobPostings: (...args: unknown[]) => listJobPostings(...args),
  getNcsBackendCompetencies: (...args: unknown[]) => getNcsBackendCompetencies(...args),
  analyzeGithubReadme: (...args: unknown[]) => analyzeGithubReadme(...args),
  recommendSaraminJobs: (...args: unknown[]) => recommendSaraminJobs(...args),
  analyzeRecommendedJob: (...args: unknown[]) => analyzeRecommendedJob(...args),
  createPracticeSession: (...args: unknown[]) => createPracticeSession(...args),
  searchAlioRecruitments: (...args: unknown[]) => searchAlioRecruitments(...args),
  analyzeAlioRecruitment: (...args: unknown[]) => analyzeAlioRecruitment(...args),
  searchPublicEmploymentRecruitments: (...args: unknown[]) => searchPublicEmploymentRecruitments(...args),
  analyzePublicEmploymentRecruitment: (...args: unknown[]) => analyzePublicEmploymentRecruitment(...args),
  searchMofeRecruitments: (...args: unknown[]) => searchMofeRecruitments(...args),
  searchIncheonRecruitments: (...args: unknown[]) => searchIncheonRecruitments(...args),
  analyzeMofeRecruitment: (...args: unknown[]) => analyzeMofeRecruitment(...args),
  interpretJobSearchMessage: (...args: unknown[]) => interpretJobSearchMessage(...args),
}));

vi.mock("../api/supabaseAuth", () => ({
  supabase: () => ({ auth: { getSession } }),
}));

describe("PracticePage 공고·질문 선택", () => {
  let root: Root;
  let container: HTMLDivElement;

  beforeEach(() => {
    sendPreparationMessage.mockResolvedValue({ conversation_id: "conversation-1", message: "확인한 자료를 바탕으로 답변해요.", follow_up_question: null, action: "stay", status: "ok" });
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    analyzeResumePdf.mockResolvedValue({ model: "google/gemini-3.1-flash-lite", facts: [{ ...resumeProfile.facts[0], page: 1, source_excerpt: "Spring Boot 사용" }] });
    getSession.mockResolvedValue({ data: { session: { access_token: "user-token" } } });
    getNcsBackendCompetencies.mockResolvedValue({
      job_name: "응용SW엔지니어링",
      source_url: "https://www.data.go.kr/data/15128213/openapi.do",
      options: [
        { id: "knowledge-data", category: "knowledge", label: "데이터 관계와 제약조건을 이해해요", ncs_unit_code: "2001020205_23v6", ncs_unit_name: "데이터 입출력 구현" },
        { id: "skill-server", category: "skill", label: "서버 프로그램을 구현할 수 있어요", ncs_unit_code: "2001020211_23v6", ncs_unit_name: "서버프로그램 구현" },
        { id: "attitude-improvement", category: "attitude", label: "문제가 있으면 코드를 개선하려고 해요", ncs_unit_code: "2001020217_23v6", ncs_unit_name: "애플리케이션 리팩토링" },
      ],
    });
    analyzeGithubReadme.mockResolvedValue({
      source_url: "https://github.com/5Headers/team_project_backend",
      readme_sha: "8c4b0a570bb8bd1572ccd09b3a336668a160d24b",
      model: "google/gemini-3.8-flash",
      technology_stack: [
        { name: "쇼핑 API", description: "최저가 조회 연동", source_excerpt: "쇼핑 API 연동" },
        { name: "Spring Boot", description: "백엔드 API", source_excerpt: "Spring Boot" },
        { name: "MySQL", description: "관계형 데이터 저장", source_excerpt: "MySQL" },
        { name: "OAuth2", description: "소셜 로그인 인증", source_excerpt: "OAuth2" },
      ],
      project_flow: [{ description: "사용자 인증 후 견적을 생성한다.", source_excerpt: "사용자 인증" }],
    });
    recommendSaraminJobs.mockResolvedValue([{
      company: "예시기업",
      title: "신입 백엔드 개발자",
      source_url: "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=123",
      deadline: "2026-10-01",
      experience: "신입",
      matched_technologies: ["Spring Boot"],
      matched_project_flows: ["사용자 인증"],
      matched_ncs_labels: ["서버 프로그램을 구현할 수 있어요"],
      source_excerpt: "Spring Boot API 서버 개발",
    }, {
      company: "다른기업",
      title: "백엔드 개발자",
      source_url: "https://m.jobkorea.co.kr/Recruit/GI_Read/123",
      deadline: null,
      experience: "경력 무관",
      matched_technologies: [],
      matched_project_flows: [],
      matched_ncs_labels: ["서버 프로그램을 구현할 수 있어요"],
      source_excerpt: "서버 개발",
    }]);
    analyzeRecommendedJob.mockResolvedValue({
      id: "private-job-1",
      company: "예시기업",
      title: "신입 백엔드 개발자",
      source_url: "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=123",
      captured_at: "2026-09-23T00:00:00Z",
      data_origin: "private_job",
      requirements: [{
        id: "private-req-1", code: "PRIVATE-SARAMIN-123-R1",
        text: "REST API 서버 개발", source_excerpt: "REST API 서버 개발", display_order: 1,
      }],
    });
    interpretJobSearchMessage.mockResolvedValue({ should_search: true, query: "개발" });
    listJobPostings.mockResolvedValue([{
      id: "job-1",
      company: "가상 회사",
      title: "연습용 백엔드 공고",
      source_url: "https://example.invalid/job",
      captured_at: "2026-09-17T00:00:00Z",
      data_origin: "demo",
      requirements: [
        { id: "req-1", code: "R1", text: "API 오류 분석", source_excerpt: null, display_order: 1 },
        { id: "req-2", code: "R2", text: "회귀 테스트", source_excerpt: null, display_order: 2 },
      ],
    }]);
    createPracticeSession.mockResolvedValue({
      practice_session_id: "session-1",
      expires_at: "2026-09-18T00:00:00Z",
    });
    searchAlioRecruitments.mockResolvedValue({
      totalCount: 1,
      recruitments: [{
        announcement_id: 123,
        company: "한국 예시 공사",
        title: "신입 백엔드 개발자 공고",
        source_url: "https://example.invalid/alio-job",
        announced_at: "2026-09-17",
        deadline: "2026-09-30",
        location: "서울",
        employment_type: "정규직",
        recruitment_type: "신입",
      }],
    });
    analyzeAlioRecruitment.mockResolvedValue({
      id: "alio-job-1",
      company: "한국 예시 공사",
      title: "신입 백엔드 개발자 공고",
      source_url: "https://example.invalid/alio-job",
      captured_at: "2026-09-21T00:00:00Z",
      data_origin: "alio",
      requirements: [{
        id: "alio-req-1",
        code: "ALIO-123-R1",
        text: "API 오류 분석 경험",
        source_excerpt: "지원자격: API 오류를 분석하고 개선한 경험",
        display_order: 1,
      }],
    });
    searchPublicEmploymentRecruitments.mockResolvedValue({
      totalCount: 1,
      recruitments: [{
        announcement_id: 456,
        company: "인사혁신처 예시 기관",
        title: "계약직 개발자 공고",
        announced_at: "2026-09-22",
        deadline: "2026-10-06",
        location: "서울",
        employment_type: "계약직",
        recruitment_type: "경력경쟁채용",
      }],
    });
    analyzePublicEmploymentRecruitment.mockResolvedValue({
      id: "public-job-1",
      company: "인사혁신처 예시 기관",
      title: "계약직 개발자 공고",
      source_url: "https://example.invalid/public-job",
      captured_at: "2026-09-22T00:00:00Z",
      data_origin: "public_job",
      requirements: [{
        id: "public-req-1",
        code: "MPO-456-R1",
        text: "API 오류 분석 경험",
        source_excerpt: "업무내용: API 오류 원인을 분석하고 개선한 경험",
        display_order: 1,
      }],
    });
    searchMofeRecruitments.mockResolvedValue({
      totalCount: 1,
      recruitments: [{
        announcement_id: 305259,
        company: "한국전력공사",
        title: "전문인력 백엔드 개발 채용공고",
        source_url: null,
        announced_at: "2026-09-22",
        deadline: "2026-10-06",
        location: "세종",
        employment_type: "정규직",
        recruitment_type: "경력",
      }],
    });
    analyzeMofeRecruitment.mockResolvedValue({
      id: "mofe-job-1",
      company: "한국전력공사",
      title: "전문인력 백엔드 개발 채용공고",
      source_url: "https://www.data.go.kr/data/15125273/openapi.do",
      captured_at: "2026-09-22T00:00:00Z",
      data_origin: "mofe_job",
      requirements: [{
        id: "mofe-req-1",
        code: "MOFE-305259-R1",
        text: "백엔드 API 개발 경험",
        source_excerpt: "지원자격: 백엔드 API 개발 경력 2년 이상인 자",
        display_order: 1,
      }],
    });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn(async () => ({
          getTracks: () => [{ stop: vi.fn() }],
        })),
      },
    });
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("README·확인 이력서·NCS를 같은 연습 세션에 전달한다", async () => {
    await act(async () => {
      root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><PracticePage isLoggedIn onLogin={vi.fn()} /></NavigationProvider>);
      await Promise.resolve();
      await Promise.resolve();
    });
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료");
    await setInputValue(container.querySelector<HTMLInputElement>("#coach-readme-url"), "https://github.com/5Headers/team_project_backend");
    await clickButton("링크 제출");
    await clickButton("공고 선택");
    await clickButton("REST API 서버 개발");
    await clickButton("이 공고로 질문 유형 고르기");
    await act(async () => container.querySelector<HTMLButtonElement>(".coach-question-type-list button")?.click());
    await clickButton("프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?");
    await clickButton("녹음 시작하기");
    expect(createPracticeSession).toHaveBeenCalledWith(expect.objectContaining({
      input: expect.objectContaining({
        applicant_context: expect.objectContaining({
          selected_ncs_ids: ["skill-server"],
          readme_analysis: expect.objectContaining({ source_url: "https://github.com/5Headers/team_project_backend" }),
          resume_profile: expect.objectContaining({ facts: expect.any(Array) }),
        }),
      }),
    }));
  });

  it("최초 API 조회 실패 후 DB 재시도로 저장 목록을 표시한다", async () => {
    getNcsBackendCompetencies.mockRejectedValueOnce(new Error("DB unavailable")).mockResolvedValueOnce({
      job_name: "응용SW엔지니어링", source_url: "https://www.data.go.kr/data/15128213/openapi.do",
      data_source: "cached", fetched_at: "2026-10-06T02:44:58Z",
      options: [{ id: "skill-server", category: "skill", label: "서버 프로그램을 구현할 수 있어요", ncs_unit_code: "2001020211_23v6", ncs_unit_name: "서버프로그램 구현" }],
    });
    await act(async () => {
      root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><PracticePage isLoggedIn onLogin={vi.fn()} /></NavigationProvider>);
      await Promise.resolve(); await Promise.resolve();
    });
    expect(getNcsBackendCompetencies).toHaveBeenNthCalledWith(1, { accessToken: "user-token", source: "api" });
    expect(getNcsBackendCompetencies).toHaveBeenCalledTimes(1);
    expect(container.textContent).toContain("NCS 실시간 조회에 실패했어요");
    await clickButton("다시 시도");
    expect(getNcsBackendCompetencies).toHaveBeenNthCalledWith(2, { accessToken: "user-token", source: "database" });
    expect(container.textContent).toContain("DB에 저장된 마지막 정상 조회 NCS 목록");
    expect(container.textContent).toContain("마지막 조회:");
    expect(container.querySelector(".coach-ncs-card [role=status]")).not.toBeNull();
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료");
    expect(container.querySelector(".coach-ncs-selection")).not.toBeNull();
  });

  it("중앙 선택 카드 없이 채팅 입력 메시지를 보낸다", async () => {
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn={false} navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn={false} onLogin={vi.fn()} onAnalysisReady={vi.fn()} />
        </NavigationProvider>,
      );
    });

    const chatInput = container.querySelector<HTMLInputElement>("#coach-chat-input");
    await setInputValue(chatInput, "백엔드 면접을 연습하고 싶어요.");
    await clickButton("보내기");

    expect(container.textContent).toContain("백엔드 면접을 연습하고 싶어요.");
    expect(container.querySelector(".coach-message-workspace")).not.toBeNull();
  });

  it("채팅 시작 시 NCS 근거 항목을 고르고 자기점검 메시지로 보낸다", async () => {
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} />
        </NavigationProvider>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(getNcsBackendCompetencies).toHaveBeenCalledWith({ accessToken: "user-token", source: "api" });
    expect(container.querySelectorAll(".coach-ncs-message")).toHaveLength(1);
    expect(container.querySelector(".coach-readme-message")).toBeNull();
    expect(container.textContent).toContain("지식·기술·태도 선택 문구는 말해봄이 작성했어요.");
    await clickButton("데이터 관계와 제약조건을 이해해요");
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("문제가 있으면 코드를 개선하려고 해요");
    await clickButton("선택 완료");

    const summary = container.querySelector(".coach-ncs-selection");
    expect(summary?.textContent).toContain("지식: 데이터 관계와 제약조건을 이해해요");
    expect(summary?.textContent).toContain("기술: 서버 프로그램을 구현할 수 있어요");
    expect(summary?.textContent).toContain("태도: 문제가 있으면 코드를 개선하려고 해요");
    expect(container.querySelectorAll(".coach-readme-message")).toHaveLength(1);

    await setInputValue(container.querySelector<HTMLInputElement>("#coach-readme-url"), "https://github.com/5Headers/team_project_backend");
    await clickButton("링크 제출");
    const readmeLink = container.querySelector<HTMLAnchorElement>(".coach-readme-selection a");
    expect(readmeLink?.href).toBe("https://github.com/5Headers/team_project_backend");
    expect(container.querySelectorAll(".coach-readme-selection")).toHaveLength(1);
    expect(analyzeGithubReadme).toHaveBeenCalledWith({
      accessToken: "user-token",
      sourceUrl: "https://github.com/5Headers/team_project_backend",
    });
    expect(container.querySelector(".coach-readme-analysis-result")?.textContent).toContain("Spring Boot");
    expect(container.querySelector(".coach-readme-analysis-result")?.textContent).toContain("사용자 인증 후 견적을 생성한다.");
    expect(container.querySelector(".coach-readme-analysis-result")?.textContent).toContain("개인의 구현 범위나 숙련도");
    const readmeSummary = container.querySelectorAll(".workspace-reference-excerpts")[1]?.textContent;
    expect(readmeSummary).toBe("Spring Boot — 백엔드 APIMySQL — 관계형 데이터 저장OAuth2 — 소셜 로그인 인증");
    expect(readmeSummary).not.toContain("최저가");
    expect(recommendSaraminJobs).toHaveBeenCalledWith({
      accessToken: "user-token",
      selectedNcsIds: ["knowledge-data", "skill-server", "attitude-improvement"],
      resumeProfile,
      readmeAnalysis: expect.objectContaining({ source_url: "https://github.com/5Headers/team_project_backend" }),
    });
    expect(container.querySelector(".coach-job-search-message")?.textContent).toContain("신입 백엔드 개발자");
    expect(container.querySelector(".coach-job-search-message")?.textContent).toContain("공고 검색");
    expect(container.querySelector(".coach-job-result .coach-job-reason")?.textContent).toContain("README: Spring Boot");
    expect(container.querySelector(".coach-job-result .coach-job-reason")?.textContent).toContain("NCS: 서버 프로그램을 구현할 수 있어요");
    expect(container.querySelectorAll(".coach-job-result .coach-job-reason")[1]?.textContent).toContain("README 일치 근거 없음");
    expect(container.querySelector(".coach-job-result small")?.textContent).toContain("마감일 2026-10-01");
    expect(container.querySelectorAll(".coach-job-result small")[1]?.textContent).toContain("경력 무관 · 채용 시 마감");
    expect(container.querySelector(".coach-job-result")?.textContent).not.toContain("검색 근거:");
    expect(container.querySelector(".coach-job-result")?.textContent).not.toContain("Spring Boot API 서버 개발");
    expect(container.querySelector(".coach-job-search-message")?.textContent).toContain("사람인");
    expect(interpretJobSearchMessage).not.toHaveBeenCalled();
  });

  it("README 분석 실패 뒤 같은 주소로 다시 시도하고 성공 결과를 표시한다", async () => {
    analyzeGithubReadme.mockRejectedValueOnce(new Error("README 원문에 근거한 분석 결과를 만들지 못했습니다."));
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} />
        </NavigationProvider>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료");
    await setInputValue(container.querySelector<HTMLInputElement>("#coach-readme-url"), "https://github.com/5Headers/team_project_backend");
    await clickButton("링크 제출");
    expect(container.querySelector(".coach-readme-analysis-error")?.textContent).toContain("README 원문에 근거한 분석 결과");
    expect(container.querySelector(".coach-readme-analysis-result")).toBeNull();

    await clickButton("다시 분석");
    expect(analyzeGithubReadme).toHaveBeenCalledTimes(2);
    expect(container.querySelector(".coach-readme-analysis-result")?.textContent).toContain("Spring Boot");
  });

  it("README 분석 중에는 채팅 입력 표시가 보이고 응답 뒤 사라진다", async () => {
    let resolveAnalysis: (value: unknown) => void = () => {};
    analyzeGithubReadme.mockImplementationOnce(() => new Promise((resolve) => {
      resolveAnalysis = resolve;
    }));
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} />
        </NavigationProvider>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료");
    await setInputValue(container.querySelector<HTMLInputElement>("#coach-readme-url"), "https://github.com/5Headers/team_project_backend");
    await clickButton("링크 제출");
    expect(container.querySelector(".coach-readme-analysis-loading")?.getAttribute("aria-label")).toBe("README 분석 중");
    expect(container.querySelectorAll(".coach-readme-analysis-loading .coach-typing-dots i")).toHaveLength(3);
    expect(container.querySelector(".coach-readme-analysis-result")).toBeNull();

    await act(async () => {
      resolveAnalysis({
        source_url: "https://github.com/5Headers/team_project_backend",
        readme_sha: "8c4b0a5",
        model: "google/gemini-3.8-flash",
        technology_stack: [{ name: "Spring Boot", description: "백엔드 API", source_excerpt: "Spring Boot" }],
        project_flow: [{ description: "견적을 생성한다", source_excerpt: "견적 생성" }],
      });
      await Promise.resolve();
    });
    expect(container.querySelector(".coach-readme-analysis-loading")).toBeNull();
    expect(container.querySelector(".coach-readme-analysis-result")).not.toBeNull();
  });

  it("README 링크를 제출하지 않고 건너뛰면 분석 없이 채팅을 계속한다", async () => {
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} />
        </NavigationProvider>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료");
    await setInputValue(container.querySelector<HTMLInputElement>("#coach-readme-url"), "https://example.com/not-github");
    await clickButton("링크 제출");
    expect(container.querySelector("#coach-readme-error")).not.toBeNull();

    await clickButton("건너뛰기");
    expect(container.querySelector("#coach-readme-url")).toBeNull();
    expect(container.querySelector("#coach-readme-error")).toBeNull();
    expect(container.querySelector(".coach-readme-skip-selection")?.textContent).toContain("README 제출을 건너뛸게요");
    expect(container.querySelector(".coach-readme-selection")).toBeNull();
    expect(container.querySelector(".coach-readme-analysis-loading")).toBeNull();
    expect(analyzeGithubReadme).not.toHaveBeenCalled();
    expect(recommendSaraminJobs).toHaveBeenCalledWith({
      accessToken: "user-token",
      selectedNcsIds: ["skill-server"],
      readmeAnalysis: null,
      resumeProfile,
    });

    await setInputValue(container.querySelector<HTMLInputElement>("#coach-chat-input"), "백엔드 공고 보여줘");
    await clickButton("보내기");
    expect(interpretJobSearchMessage).toHaveBeenCalledWith({
      accessToken: "user-token",
      message: "백엔드 공고 보여줘",
    });
  });

  it.each([false, true])("공고를 출처별 최대 5개로 분리하고 빈 출처를 안내한다 (사람인만: %s)", async (saraminOnly) => {
    const makeJob = (source: string, index: number) => ({
      company: `${source}기업${index}`, title: `백엔드 개발자 ${index}`,
      source_url: source === "saramin" ? `https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=${index}` : `https://m.jobkorea.co.kr/Recruit/GI_Read/${index}`,
      deadline: null, experience: "신입", matched_technologies: [], matched_project_flows: [],
      matched_ncs_labels: ["서버 프로그램을 구현할 수 있어요"], source_excerpt: "서버 개발",
    });
    recommendSaraminJobs.mockResolvedValue([
      ...["https://www.rallit.com/positions/12/backend", "https://www.wanted.co.kr/wd/13", "https://jumpit.saramin.co.kr/position/14"].map((url) => ({ ...makeJob("extra", 1), source_url: url })),
      ...Array.from({ length: 7 }, (_, i) => makeJob("saramin", i + 1)),
      ...(saraminOnly ? [] : Array.from({ length: 6 }, (_, i) => makeJob("jobkorea", i + 1))),
    ]);
    await act(async () => {
      root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
        <PracticePage isLoggedIn onLogin={vi.fn()} />
      </NavigationProvider>);
      await Promise.resolve();
      await Promise.resolve();
    });
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료");
    await clickButton("건너뛰기");
    const saramin = container.querySelector('[aria-label="사람인 공고"]');
    const jobkorea = container.querySelector('[aria-label="잡코리아 공고"]');
    expect(container.querySelectorAll('[role="tabpanel"]:not([hidden])')).toHaveLength(1);
    expect(saramin?.hasAttribute("hidden")).toBe(false);
    expect(jobkorea?.hasAttribute("hidden")).toBe(true);
    const tabs = Array.from(container.querySelectorAll<HTMLButtonElement>('[role="tab"]'));
    expect(tabs.map((tab) => tab.textContent)).toEqual(["사람인5", `잡코리아${saraminOnly ? 0 : 5}`, "랠릿1", "원티드1", "점핏1"]);
    expect(saramin?.querySelectorAll(".coach-job-result")).toHaveLength(5);
    expect(jobkorea?.querySelectorAll(".coach-job-result")).toHaveLength(saraminOnly ? 0 : 5);
    for (const name of ["랠릿", "원티드", "점핏"]) {
      expect(container.querySelector(`[aria-label="${name} 공고"]`)?.querySelectorAll(".coach-job-result")).toHaveLength(1);
    }
    expect(saramin?.textContent).not.toContain("jumpit.saramin.co.kr");
    await act(async () => tabs[4].click());
    expect(tabs[4].getAttribute("aria-selected")).toBe("true");
    expect(container.querySelector('[aria-label="점핏 공고"]')?.hasAttribute("hidden")).toBe(false);
    expect(saramin?.hasAttribute("hidden")).toBe(true);
    await act(async () => tabs[4].dispatchEvent(new KeyboardEvent("keydown", { key: "Home", bubbles: true })));
    expect(document.activeElement).toBe(tabs[0]);
    expect(tabs[0].getAttribute("aria-selected")).toBe("true");
    await act(async () => tabs[1].click());
    expect(jobkorea?.hasAttribute("hidden")).toBe(false);
    if (saraminOnly) expect(jobkorea?.textContent).toContain("확인된 잡코리아 공고가 없어요");
    else {
      const button = jobkorea?.querySelector<HTMLButtonElement>("button");
      await act(async () => button?.click());
      expect(analyzeRecommendedJob).toHaveBeenCalledWith(expect.objectContaining({ sourceUrl: "https://m.jobkorea.co.kr/Recruit/GI_Read/1" }));
    }
  });

  it("사람인 결과가 없으면 공고가 있는 첫 사이트 탭을 연다", async () => {
    recommendSaraminJobs.mockResolvedValue([{
      company: "원티드 기업", title: "백엔드 개발자", source_url: "https://www.wanted.co.kr/wd/13",
      deadline: null, experience: "신입", matched_technologies: [], matched_project_flows: [],
      matched_ncs_labels: ["서버 개발"], source_excerpt: "서버 개발",
    }]);
    await act(async () => {
      root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
        <PracticePage isLoggedIn onLogin={vi.fn()} />
      </NavigationProvider>);
      await Promise.resolve();
      await Promise.resolve();
    });
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료");
    await clickButton("건너뛰기");
    expect(container.querySelector('[role="tab"][aria-selected="true"]')?.textContent).toBe("원티드1");
    expect(container.querySelectorAll('[role="tabpanel"]:not([hidden])')).toHaveLength(1);
  });

  it("추천 공고를 선택해 원문 검토 후 요구사항·질문·연습 세션으로 이어진다", async () => {
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} />
        </NavigationProvider>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료");
    await clickButton("건너뛰기");
    expect(container.querySelectorAll(".coach-job-result")).toHaveLength(2);
    expect(container.querySelector(".coach-search-retry button")?.textContent).toContain("다시 검색");
    const thread = container.querySelector<HTMLDivElement>(".coach-thread")!;
    const scrollTo = vi.fn();
    let height = 1200;
    Object.defineProperties(thread, {scrollTo:{configurable:true,value:scrollTo},scrollHeight:{configurable:true,get:()=>height}});
    thread.dataset.historyBrowsing = "true";
    thread.dispatchEvent(new Event("workspace-browse"));
    await clickButton("공고 선택");
    expect(thread.dataset.historyBrowsing).toBeUndefined();
    expect(scrollTo).toHaveBeenCalledWith({top:1200,behavior:"smooth"});
    height = 1800;
    await act(async () => { await new Promise((resolve) => window.setTimeout(resolve, 5)); });
    expect(scrollTo).toHaveBeenLastCalledWith({top:1800,behavior:"instant"});
    expect(analyzeRecommendedJob).toHaveBeenCalledWith({
      accessToken: "user-token",
      sourceUrl: "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=123",
    });
    expect(container.querySelector(".coach-requirement-picker")?.textContent)
      .toContain("REST API 서버 개발");
    const jobSummary = [...container.querySelectorAll(".workspace-evidence-card--reference")].find((card) => card.textContent?.includes("예시기업"))?.querySelector(".workspace-reference-excerpts")?.textContent;
    expect(jobSummary).toContain("경력 조건: 신입");
    expect(jobSummary).toContain("마감일: 2026-10-01");
    expect(jobSummary).toContain("REST API 서버 개발");
    await clickButton("REST API 서버 개발");
    await clickButton("이 공고로 질문 유형 고르기");
    expect(container.querySelector(".coach-question-picker")).not.toBeNull();
    const questionTypeButton = container.querySelector<HTMLButtonElement>(".coach-question-type-list button");
    await act(async () => questionTypeButton?.click());
    await clickButton("프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?");
    await clickButton("녹음 시작하기");
    expect(createPracticeSession).toHaveBeenCalledWith(expect.objectContaining({
      input: expect.objectContaining({
        job_posting_id: "private-job-1",
        requirement_ids: ["private-req-1"],
      }),
    }));
  });

  it("공고 변경은 NCS·이력서·README를 남기고 대기 중 WAV와 이후 선택을 초기화한다", async () => {
    await act(async () => {
      root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><PracticePage isLoggedIn onLogin={vi.fn()} /></NavigationProvider>);
      await Promise.resolve();
      await Promise.resolve();
    });
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료");
    await setInputValue(container.querySelector<HTMLInputElement>("#coach-readme-url"), "https://github.com/5Headers/team_project_backend");
    await clickButton("링크 제출");
    await clickButton("공고 선택");
    await clickButton("REST API 서버 개발");
    await clickButton("이 공고로 질문 유형 고르기");
    const questionTypeButton = container.querySelector<HTMLButtonElement>(".coach-question-type-list button");
    await act(async () => questionTypeButton?.click());
    await clickButton("프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?");
    let resolveSession!: (value: {practice_session_id: string}) => void;
    createPracticeSession.mockReturnValueOnce(new Promise((resolve) => { resolveSession = resolve; }));
    const upload = container.querySelector<HTMLInputElement>(".coach-upload-input")!;
    Object.defineProperty(upload, "files", { configurable: true, value: [new File(["wav"], "answer.wav", {type:"audio/wav"})] });
    await act(async () => { upload.dispatchEvent(new Event("change", {bubbles:true})); await Promise.resolve(); });
    const thread = container.querySelector<HTMLDivElement>(".coach-thread")!;
    thread.scrollTop = 800;
    thread.scrollTo = vi.fn();
    thread.getBoundingClientRect = () => ({top:100} as DOMRect);
    const search = container.querySelector<HTMLElement>(".coach-job-search-message")!;
    search.getBoundingClientRect = () => ({top:250} as DOMRect);
    let pending: object;
    sendPreparationMessage.mockImplementation(async (_token, input) => {
      if (input.restart_confirmation?.confirm === false) return { conversation_id: "conversation-1", action: "stay", status: "ok", message: "변경 취소", follow_up_question: null };
      if (input.restart_confirmation?.confirm) return { ...pending, conversation_id: "new-conversation", action: "practice_restarted", execution_result: "verified" };
      pending = { conversation_id: "conversation-1", action: "stay", status: "ok", message: "현재 채팅과 코칭 내역을 삭제합니다.", follow_up_question: "확인할까요?", execution_result: "awaiting_confirmation", restart: { token: "token-1", target: "jobs", new_graduate_only: false, materials: input.review_context, selection: { job_posting_id: null, requirement_ids: [], question_id: null, custom_question_text: null } } };
      return pending;
    });
    const previousTimeline = container.querySelector(".workspace-timeline")?.textContent;
    await clickButton("공고 변경하기");
    expect(container.querySelector(".coach-question-picker")).not.toBeNull();
    expect(container.querySelector(".coach-requirement-picker")).not.toBeNull();
    expect(container.querySelector(".workspace-timeline")?.textContent).toBe(previousTimeline);
    await clickButton("취소");
    expect(container.querySelector(".coach-question-picker")).not.toBeNull();
    await clickButton("공고 변경하기");
    await clickButton("확인하고 변경");
    expect(container.querySelector(".coach-question-picker")).toBeNull();
    expect(container.querySelector(".coach-requirement-picker")).toBeNull();
    expect([...container.querySelectorAll(".workspace-timeline strong")].map((item) => item.textContent)).toEqual(["역량 자기점검 완료", "이력서 정보 확인 완료", "README 분석 완료"]);
    expect(container.querySelectorAll(".workspace-evidence-card--reference")).toHaveLength(2);
    expect([...container.querySelectorAll(".workspace-evidence-card--reference")].some((item) => item.textContent?.includes("GitHub README"))).toBe(true);
    expect(container.querySelector(".coach-job-search-message")).not.toBeNull();
    expect(container.querySelector(".coach-readme-selection")).toBeNull();
    expect(container.querySelector(".coach-readme-analysis-result")).toBeNull();
    await act(async () => { resolveSession({practice_session_id:"old-session"}); await Promise.resolve(); });
    expect(container.querySelector(".coach-audio-attachment")).toBeNull();
    expect(container.textContent).not.toContain("분석 시작");
    await clickButton("공고 선택");
    expect(container.querySelector(".coach-requirement-picker")?.textContent).toContain("REST API 서버 개발");
    expect(thread.dataset.historyBrowsing).toBeUndefined();
    expect(container.textContent).not.toContain("WAV 파일을 보냈어요.");
  });

  it("GitHub README 외부 주소와 다른 파일은 거부하고 README.md 주소를 받는다", async () => {
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} />
        </NavigationProvider>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료");

    const input = container.querySelector<HTMLInputElement>("#coach-readme-url");
    await setInputValue(input, "https://github.com.evil.example/owner/repo");
    await clickButton("링크 제출");
    expect(container.querySelector(".coach-readme-selection")).toBeNull();
    expect(container.querySelector("#coach-readme-error")?.textContent).toContain("GitHub 저장소 또는 README.md 주소");

    await setInputValue(input, "https://github.com/owner/repo/blob/main/secrets.txt");
    await clickButton("링크 제출");
    expect(container.querySelector(".coach-readme-selection")).toBeNull();

    await setInputValue(input, "https://github.com/owner/repo/blob/main/docs/README.md");
    await clickButton("링크 제출");
    expect(container.querySelector<HTMLAnchorElement>(".coach-readme-selection a")?.href)
      .toBe("https://github.com/owner/repo/blob/main/docs/README.md");
    expect(interpretJobSearchMessage).not.toHaveBeenCalled();
  });

  it("NCS 조회 실패 시 가짜 선택지를 표시하지 않고 재시도한다", async () => {
    getNcsBackendCompetencies.mockRejectedValueOnce(new Error("provider unavailable"));
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} />
        </NavigationProvider>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(container.querySelectorAll(".coach-ncs-option")).toHaveLength(0);
    expect(container.textContent).toContain("NCS 실시간 조회에 실패했어요");
    await clickButton("다시 시도");
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    expect(container.querySelectorAll(".coach-ncs-option")).toHaveLength(3);
  });

  it("1차 코칭 전에는 2차 녹음과 답변 비교 분석 메뉴를 비활성화한다", async () => {
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn={false} navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn={false} onLogin={vi.fn()} />
        </NavigationProvider>,
      );
    });

    const secondRecording = Array.from(container.querySelectorAll<HTMLButtonElement>(".coach-followup-menu button"))
      .find((button) => button.textContent?.includes("2차 녹음"));
    const comparison = Array.from(container.querySelectorAll<HTMLButtonElement>(".coach-followup-menu button"))
      .find((button) => button.textContent?.includes("답변 비교 분석"));

    expect(secondRecording?.disabled).toBe(true);
    expect(comparison?.disabled).toBe(true);
    expect(comparison?.title).toBe("2차 전사문을 확인하면 이용할 수 있어요.");
  });

  it("채팅으로 개발 공고를 찾아 선택하면 AI 분석 요구사항을 고를 수 있다", async () => {
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} onAnalysisReady={vi.fn()} />
        </NavigationProvider>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    const chatInput = container.querySelector<HTMLInputElement>("#coach-chat-input");
    await setInputValue(chatInput, "개발 관련 공고 보여줘");
    await clickButton("보내기");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(searchAlioRecruitments).toHaveBeenCalledWith({
      accessToken: "user-token",
      query: "개발",
    });
    expect(searchPublicEmploymentRecruitments).toHaveBeenCalledWith({
      accessToken: "user-token",
      query: "개발",
    });
    expect(searchMofeRecruitments).toHaveBeenCalledWith({
      accessToken: "user-token",
      query: "개발",
    });
    expect(searchIncheonRecruitments).not.toHaveBeenCalled();
    expect(interpretJobSearchMessage).toHaveBeenCalledWith({
      accessToken: "user-token",
      message: "개발 관련 공고 보여줘",
    });
    expect(container.textContent).toContain("ALIO 공공기관 채용");
    expect(container.textContent).toContain("인사혁신처 공공취업정보");
    expect(container.textContent).toContain("재정경제부 공공기관 채용정보");
    expect(container.textContent).not.toContain("인천 채용정보");
    expect(container.textContent).toContain("분석 가능한 공고를 골라주세요.");
    await clickButton("이 공고 분석하기");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(analyzeAlioRecruitment).toHaveBeenCalledWith({
      accessToken: "user-token",
      input: {
        announcement_id: 123,
        company: "한국 예시 공사",
        title: "신입 백엔드 개발자 공고",
        source_url: "https://example.invalid/alio-job",
      },
    });
    expect(container.textContent).toContain("이번 답변에 연결할 요구사항");
    const searchMessage = container.querySelector(".coach-search-message");
    const analysisReply = container.querySelector(".coach-message-reply");
    if (!searchMessage || !analysisReply) throw new Error("공고 목록과 분석 결과가 필요합니다.");
    expect(searchMessage.compareDocumentPosition(analysisReply) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    await clickButton("API 오류 분석 경험");
    expect(container.textContent).toContain("요구사항 1개를 연결했어요.");
    expect(container.querySelector(".coach-selection-markdown")?.textContent)
      .toContain("## 공고한국 예시 공사신입 백엔드 개발자 공고");
    await clickButton("질문 선택으로 이동");
    expect(container.querySelector(".coach-context-panel")?.textContent)
      .toContain("API 오류 분석 경험");
    expect(container.querySelector(".workspace-timeline")?.textContent)
      .toContain("공고 요구사항 선택 완료");
    const searchCalls = interpretJobSearchMessage.mock.calls.length;
    sendPreparationMessage.mockResolvedValueOnce({ conversation_id: "conversation-1",
      message: "공고 원문은 https://example.invalid/alio-job 에서 확인할 수 있어요.",
      follow_up_question: "어떤 요구사항을 더 설명해 드릴까요?", action: "stay", status: "ok" });
    await setInputValue(container.querySelector("#coach-chat-input"), "선택한 공고 원본 사이트 보여줘");
    await clickButton("보내기");
    expect(interpretJobSearchMessage.mock.calls.length).toBe(searchCalls);
    expect(sendPreparationMessage).toHaveBeenLastCalledWith("user-token", expect.objectContaining({
      selection: expect.objectContaining({ job_posting_id: expect.any(String), requirement_ids: expect.any(Array) }),
    }));
    expect(container.textContent).toContain("어떤 요구사항을 더 설명해 드릴까요?");
    expect(container.querySelector('.preparation-chat-turn a')?.getAttribute('href')).toBe('https://example.invalid/alio-job');
    await setInputValue(container.querySelector("#coach-chat-input"), "이 공고만 보여줘");
    await clickButton("보내기");
    expect(interpretJobSearchMessage.mock.calls.length).toBe(searchCalls);
  });

  it("ALIO 응답을 기다리는 동안 코치 입력 중 효과를 표시한다", async () => {
    let resolveSearch: ((value: { recruitments: Array<{
      announcement_id: number;
      company: string;
      title: string;
      source_url: string;
      announced_at: string | null;
      deadline: string | null;
      location: string | null;
      employment_type: string | null;
      recruitment_type: string | null;
    }>; totalCount: number }) => void) | undefined;
    searchAlioRecruitments.mockImplementationOnce(() => new Promise<{
      recruitments: Array<{
        announcement_id: number;
        company: string;
        title: string;
        source_url: string;
        announced_at: string | null;
        deadline: string | null;
        location: string | null;
        employment_type: string | null;
        recruitment_type: string | null;
      }>;
      totalCount: number;
    }>((resolve) => {
      resolveSearch = resolve;
    }));

    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} onAnalysisReady={vi.fn()} />
        </NavigationProvider>,
      );
      await Promise.resolve();
    });

    await setInputValue(container.querySelector<HTMLInputElement>("#coach-chat-input"), "JD 보여줘");
    await clickButton("보내기");
    await act(async () => { await Promise.resolve(); });

    expect(searchAlioRecruitments).toHaveBeenCalledWith({ accessToken: "user-token", query: "개발" });
    expect(container.querySelector(".coach-typing-message")).not.toBeNull();

    resolveSearch?.({ recruitments: [], totalCount: 0 });
    await act(async () => { await Promise.resolve(); });
    expect(container.querySelector(".coach-typing-message")).toBeNull();
  });

  it("공공취업정보 공고도 같은 채팅 흐름에서 분석하고 요구사항을 고른다", async () => {
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} onAnalysisReady={vi.fn()} />
        </NavigationProvider>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    await setInputValue(container.querySelector<HTMLInputElement>("#coach-chat-input"), "개발관련공고");
    await clickButton("보내기");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    const publicCard = Array.from(container.querySelectorAll<HTMLElement>(".coach-provider-result-section"))
      .find((section) => section.textContent?.includes("인사혁신처 공공취업정보"));
    const analyzeButton = Array.from(publicCard?.querySelectorAll<HTMLButtonElement>("button") ?? [])
      .find((button) => button.textContent === "이 공고 분석하기");
    await act(async () => analyzeButton?.click());
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(analyzePublicEmploymentRecruitment).toHaveBeenCalledWith({
      accessToken: "user-token",
      input: {
        announcement_id: 456,
        company: "인사혁신처 예시 기관",
        title: "계약직 개발자 공고",
      },
    });
    expect(container.textContent).toContain("이번 답변에 연결할 요구사항");
    expect(container.querySelector(".coach-selection-markdown")?.textContent)
      .toContain("## 출처인사혁신처 공공취업정보");
  });

  it("LLM이 백엔드 관련 공고 요청을 해석한 검색어로 세 출처를 찾는다", async () => {
    interpretJobSearchMessage.mockResolvedValueOnce({ should_search: true, query: "백엔드" });
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} onAnalysisReady={vi.fn()} />
        </NavigationProvider>,
      );
      await Promise.resolve();
    });

    await setInputValue(container.querySelector<HTMLInputElement>("#coach-chat-input"), "백엔드 관련 공고");
    await clickButton("보내기");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(interpretJobSearchMessage).toHaveBeenCalledWith({
      accessToken: "user-token",
      message: "백엔드 관련 공고",
    });
    expect(searchAlioRecruitments).toHaveBeenCalledWith({ accessToken: "user-token", query: "백엔드" });
    expect(searchPublicEmploymentRecruitments).toHaveBeenCalledWith({ accessToken: "user-token", query: "백엔드" });
    expect(searchMofeRecruitments).toHaveBeenCalledWith({ accessToken: "user-token", query: "백엔드" });
    expect(searchIncheonRecruitments).not.toHaveBeenCalled();
  });

  it("재정경제부 공공기관 채용정보 공고도 같은 채팅 흐름에서 분석하고 요구사항을 고른다", async () => {
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} onAnalysisReady={vi.fn()} />
        </NavigationProvider>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    await setInputValue(container.querySelector<HTMLInputElement>("#coach-chat-input"), "백엔드 관련 공고");
    await clickButton("보내기");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    const mofeCard = Array.from(container.querySelectorAll<HTMLElement>(".coach-provider-result-section"))
      .find((section) => section.textContent?.includes("재정경제부 공공기관 채용정보"));
    const analyzeButton = Array.from(mofeCard?.querySelectorAll<HTMLButtonElement>("button") ?? [])
      .find((button) => button.textContent === "이 공고 분석하기");
    await act(async () => analyzeButton?.click());
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(analyzeMofeRecruitment).toHaveBeenCalledWith({
      accessToken: "user-token",
      input: {
        announcement_id: 305259,
        company: "한국전력공사",
        title: "전문인력 백엔드 개발 채용공고",
      },
    });
    expect(container.querySelector(".coach-selection-markdown")?.textContent)
      .toContain("## 출처재정경제부 공공기관 채용정보");
  });

  it("공고와 요구사항을 고른 뒤 채팅 녹음 시작에서 서버 세션을 만든다", async () => {
    const onAnalysisReady = vi.fn<(question: PracticeQuestion, audio: Blob, attemptNo?: 1 | 2) => void>();
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} onAnalysisReady={onAnalysisReady} />
        </NavigationProvider>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    await clickButton("연습용 백엔드 공고");
    const requirement = container.querySelector<HTMLInputElement>('input[type="checkbox"]');
    expect(requirement).not.toBeNull();
    await act(async () => requirement?.click());
    await clickButton("질문 선택으로 이동");

    const selectedQuestion = Array.from(container.querySelectorAll<HTMLButtonElement>(".preset-question"))
      .find((button) => button.getAttribute("aria-pressed") === "true");
    expect(selectedQuestion).toBeUndefined();

    const questionTypeButton = container.querySelector<HTMLButtonElement>(".coach-question-type-list button");
    await act(async () => questionTypeButton?.click());
    await clickButton("프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?");
    await clickButton("녹음 시작하기");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(createPracticeSession).toHaveBeenCalledWith(expect.objectContaining({
      accessToken: "user-token",
      input: expect.objectContaining({
        job_posting_id: "job-1",
        requirement_ids: ["req-1"],
        question_id: "preset-04",
      }),
    }));
    expect(onAnalysisReady).not.toHaveBeenCalled();
  });

  it("질문 유형을 펼친 뒤 하단으로 이동하고 질문은 직접 선택해야 한다", async () => {
    await act(async () => {
      root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><PracticePage isLoggedIn onLogin={vi.fn()} /></NavigationProvider>);
      await Promise.resolve();
      await Promise.resolve();
    });
    await clickButton("연습용 백엔드 공고");
    const requirement = container.querySelector<HTMLInputElement>('input[type="checkbox"]');
    await act(async () => requirement?.click());
    await clickButton("질문 선택으로 이동");
    const thread = container.querySelector<HTMLDivElement>(".coach-thread")!;
    const scrollTo = vi.fn();
    Object.defineProperties(thread, {
      scrollTo: { configurable: true, value: scrollTo },
      scrollHeight: { configurable: true, get: () => container.querySelector(".coach-preset-picker") ? 1800 : 1200 },
    });
    thread.dataset.historyBrowsing = "true";
    thread.dispatchEvent(new Event("workspace-browse"));
    await clickButton("기본 질문");
    expect(container.querySelector('.coach-question-list [aria-pressed="true"]')).toBeNull();
    expect(container.textContent).not.toContain("녹음 시작하기");
    expect(thread.dataset.historyBrowsing).toBeUndefined();
    expect(scrollTo).toHaveBeenCalledWith({ top: 1800, behavior: "smooth" });
    scrollTo.mockClear();
    await clickButton("내 질문");
    expect(container.querySelector(".coach-custom-question textarea")).not.toBeNull();
    expect(scrollTo).toHaveBeenCalledWith({ top: 1200, behavior: "smooth" });
    expect(container.textContent).not.toContain("녹음 시작하기");
    await clickButton("기본 질문");
    expect(container.querySelector('.coach-question-list [aria-pressed="true"]')).toBeNull();
    await clickButton("프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?");
    expect(container.querySelector('.coach-question-list [aria-pressed="true"]')).not.toBeNull();
    expect(container.textContent).toContain("녹음 시작하기");
  });

  it("질문 유형을 고르면 코치가 녹음 버튼을 보내고 WAV를 채팅 오디오로 준비한다", async () => {
    const onAnalysisReady = vi.fn();
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} onAnalysisReady={onAnalysisReady} />
        </NavigationProvider>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    await clickButton("연습용 백엔드 공고");
    const requirement = container.querySelector<HTMLInputElement>('input[type="checkbox"]');
    await act(async () => requirement?.click());
    await clickButton("질문 선택으로 이동");
    const questionTypeButton = container.querySelector<HTMLButtonElement>(".coach-question-type-list button");
    expect(questionTypeButton?.textContent).toContain("기본 질문");
    await act(async () => questionTypeButton?.click());
    await clickButton("프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?");
    expect(container.textContent).toContain("녹음 시작하기");

    const wavInput = container.querySelector<HTMLInputElement>(".coach-upload-input");
    const wavFile = new File(["wav"], "answer.wav", { type: "audio/wav" });
    Object.defineProperty(wavInput, "files", { configurable: true, value: [wavFile] });
    await act(async () => {
      wavInput?.dispatchEvent(new Event("change", { bubbles: true }));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(container.textContent).toContain("WAV 파일");
    await clickButton("분석 시작");
    expect(onAnalysisReady).toHaveBeenCalledWith(
      expect.objectContaining({ practiceSessionId: "session-1", questionId: "preset-04" }),
      wavFile,
      1,
    );
  });

  it("채팅 안에서 녹음한 답변을 오디오 말풍선으로 분석에 보낸다", async () => {
    const onAnalysisReady = vi.fn();
    class FakeMediaRecorder {
      static isTypeSupported() { return true; }
      state: RecordingState = "inactive";
      mimeType = "audio/webm";
      ondataavailable: ((event: BlobEvent) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      onstop: (() => void) | null = null;

      constructor(_stream: MediaStream, _options?: MediaRecorderOptions) {}

      start() { this.state = "recording"; }

      stop() {
        this.state = "inactive";
        this.ondataavailable?.({ data: new Blob(["answer"], { type: this.mimeType }) } as BlobEvent);
        this.onstop?.();
      }
    }
    vi.stubGlobal("MediaRecorder", FakeMediaRecorder);
    vi.useFakeTimers();

    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} onAnalysisReady={onAnalysisReady} />
        </NavigationProvider>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    await clickButton("연습용 백엔드 공고");
    const requirement = container.querySelector<HTMLInputElement>('input[type="checkbox"]');
    await act(async () => requirement?.click());
    await clickButton("질문 선택으로 이동");
    const questionTypeButton = container.querySelector<HTMLButtonElement>(".coach-question-type-list button");
    await act(async () => questionTypeButton?.click());
    await clickButton("프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?");
    await clickButton("녹음 시작하기");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(5_100);
    });

    expect(container.textContent).toContain("녹음 중");
    expect(container.querySelector(".coach-audio-recording")).not.toBeNull();
    await clickButton("녹음 마치기");
    expect(container.textContent).toContain("분석 시작");
    await clickButton("분석 시작");

    expect(onAnalysisReady).toHaveBeenCalledWith(
      expect.objectContaining({ practiceSessionId: "session-1", questionId: "preset-04" }),
      expect.any(Blob),
      1,
    );
  });

  it("재녹음도 채팅에서 오디오 말풍선으로 보내고 2차 답변으로 표시한다", async () => {
    const onAnalysisReady = vi.fn();
    class FakeMediaRecorder {
      static isTypeSupported() { return true; }
      state: RecordingState = "inactive";
      mimeType = "audio/webm";
      ondataavailable: ((event: BlobEvent) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      onstop: (() => void) | null = null;

      constructor(_stream: MediaStream, _options?: MediaRecorderOptions) {}

      start() { this.state = "recording"; }

      stop() {
        this.state = "inactive";
        this.ondataavailable?.({ data: new Blob(["retry"], { type: this.mimeType }) } as BlobEvent);
        this.onstop?.();
      }
    }
    vi.stubGlobal("MediaRecorder", FakeMediaRecorder);
    vi.useFakeTimers();

    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage
            isLoggedIn
            onLogin={vi.fn()}
            onAnalysisReady={onAnalysisReady}
            resumeQuestion={{
              questionType: "preset",
              question: "프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?",
              questionId: "preset-04",
              practiceSessionId: "session-1",
              jobPostingId: "job-1",
              requirementIds: ["req-1"],
            }}
            resumeAttemptNo={2}
          />
        </NavigationProvider>,
      );
      await Promise.resolve();
    });

    expect(container.textContent).toContain("앞선 피드백을 적용해 다시 답해볼까요?");
    await clickButton("녹음 시작하기");
    await act(async () => {
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(5_100);
    });
    expect(container.querySelector(".coach-audio-recording")).not.toBeNull();
    await clickButton("녹음 마치기");
    await clickButton("분석 시작");

    expect(onAnalysisReady).toHaveBeenCalledWith(
      expect.objectContaining({ practiceSessionId: "session-1", questionId: "preset-04" }),
      expect.any(Blob),
      2,
    );
  });

  it("재녹음도 + 버튼으로 WAV 파일을 올려 2차 답변으로 분석한다", async () => {
    const onAnalysisReady = vi.fn();
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage
            isLoggedIn
            onLogin={vi.fn()}
            onAnalysisReady={onAnalysisReady}
            resumeQuestion={{
              questionType: "preset",
              question: "프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?",
              questionId: "preset-04",
              practiceSessionId: "session-1",
              jobPostingId: "job-1",
              requirementIds: ["req-1"],
            }}
            resumeAttemptNo={2}
          />
        </NavigationProvider>,
      );
      await Promise.resolve();
    });

    const wavInput = container.querySelector<HTMLInputElement>(".coach-upload-input");
    const wavFile = new File(["retry wav"], "retry-answer.wav", { type: "audio/wav" });
    Object.defineProperty(wavInput, "files", { configurable: true, value: [wavFile] });
    await act(async () => {
      wavInput?.dispatchEvent(new Event("change", { bubbles: true }));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(container.textContent).toContain("retry-answer.wav");
    await clickButton("분석 시작");
    expect(onAnalysisReady).toHaveBeenCalledWith(
      expect.objectContaining({ practiceSessionId: "session-1", questionId: "preset-04" }),
      wavFile,
      2,
    );
  });

  it("공고 선택 화면에서 ALIO 공고를 검색하고 원문 링크를 표시한다", async () => {
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} onAnalysisReady={vi.fn()} />
        </NavigationProvider>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    const input = container.querySelector<HTMLInputElement>("#alio-query");
    expect(input).not.toBeNull();
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
      setter?.call(input, "백엔드");
      input?.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await clickButton("검색");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(searchAlioRecruitments).toHaveBeenCalledWith({
      accessToken: "user-token",
      query: "백엔드",
    });
    expect(container.textContent).toContain("신입 백엔드 개발자 공고");
    expect(container.querySelector<HTMLAnchorElement>('a[href="https://example.invalid/alio-job"]')?.textContent)
      .toContain("원문 보기");
  });

  it("AI가 원문을 분석한 ALIO 공고의 요구사항을 선택해 질문 단계로 이동한다", async () => {
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} onAnalysisReady={vi.fn()} />
        </NavigationProvider>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    const searchInput = container.querySelector<HTMLInputElement>("#alio-query");
    await setInputValue(searchInput, "백엔드");
    await clickButton("검색");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    await clickButton("AI 분석하고 요구사항 선택");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(analyzeAlioRecruitment).toHaveBeenCalledWith({
      accessToken: "user-token",
      input: {
        announcement_id: 123,
          company: "한국 예시 공사",
          title: "신입 백엔드 개발자 공고",
          source_url: "https://example.invalid/alio-job",
      },
    });
    expect(container.textContent).toContain("AI 분석 완료 ALIO 공고");
    expect(container.textContent).toContain("원문 근거: 지원자격: API 오류를 분석하고 개선한 경험");

    const requirement = container.querySelector<HTMLInputElement>('input[type="checkbox"]');
    await act(async () => requirement?.click());
    await clickButton("질문 선택으로 이동");
    expect(container.textContent).toContain("연결할 요구사항: API 오류 분석 경험");
  });

  it("NCS 뒤 PDF 확인을 마칠 때까지 README와 추천을 열지 않는다", async () => {
    await act(async () => root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><PracticePage isLoggedIn onLogin={vi.fn()} /></NavigationProvider>));
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료", false);
    expect(container.querySelector(".coach-resume-message")).not.toBeNull();
    expect(container.textContent).toContain("개인정보는 검토·추천 평가에 사용하지 않습니다");
    expect(container.querySelector(".coach-readme-message")).toBeNull();
    expect(recommendSaraminJobs).not.toHaveBeenCalled();
    const input = container.querySelector<HTMLInputElement>(".coach-resume-message input[type=file]")!;
    Object.defineProperty(input, "files", { configurable: true, value: [new File(["%PDF-fake"], "resume.pdf")] });
    await act(async () => input.dispatchEvent(new Event("change", { bubbles: true })));
    await clickButton("이력서 검토하기");
    expect(container.querySelector(".coach-readme-message")).toBeNull();
    await setInputValue(container.querySelector(".resume-fact input"), "MySQL");
    await setInputValue(container.querySelector(".resume-fact textarea"), "MySQL 직접 사용");
    await clickButton("확인하고 계속하기");
    await clickButton("건너뛰기");
    expect(recommendSaraminJobs).toHaveBeenCalledWith(expect.objectContaining({ readmeAnalysis: null, resumeProfile: { facts: [{ category: "technology", value: "MySQL 직접 사용", keyword: "MySQL" }] } }));
  });

  it("PDF 검토 실패와 편집된 연락처는 확인 전 수정할 수 있다", async () => {
    await act(async () => root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><PracticePage isLoggedIn onLogin={vi.fn()} /></NavigationProvider>));
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료", false);
    const input = container.querySelector<HTMLInputElement>(".coach-resume-message input[type=file]")!;
    Object.defineProperty(input, "files", { configurable: true, value: [new File(["%PDF-fake"], "resume.pdf")] });
    await act(async () => input.dispatchEvent(new Event("change", { bubbles: true })));
    analyzeResumePdf.mockRejectedValueOnce(new Error("텍스트 PDF로 제출해 주세요"));
    await clickButton("이력서 검토하기");
    expect(container.textContent).toContain("텍스트 PDF로 제출해 주세요");
    expect(container.querySelector(".coach-readme-message")).toBeNull();
    await clickButton("이력서 검토하기");
    await setInputValue(container.querySelector(".resume-fact textarea"), "person@example.com");
    await clickButton("확인하고 계속하기");
    expect(container.textContent).toContain("연락처·식별번호를 제거");
    expect(container.querySelector(".coach-readme-message")).toBeNull();
    await setInputValue(container.querySelector(".resume-fact textarea"), "Spring Boot 사용");
    await clickButton("확인하고 계속하기");
    expect(container.querySelector(".coach-readme-message")).not.toBeNull();
  });

  it("완료 뒤 질문 시간을 두고 명령·버튼으로만 다음 자료와 공고 검색을 연다", async () => {
    await act(async () => root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><PracticePage isLoggedIn onLogin={vi.fn()} /></NavigationProvider>));
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료", false, false);
    expect(container.querySelector(".coach-resume-message")).toBeNull();
    expect(container.textContent).toContain("NCS 선택을 완료했어요");
    await setInputValue(container.querySelector("#coach-chat-input"), "다음 단계에서 이 역량은 어떻게 활용하나요?");
    await clickButton("보내기");
    expect(sendPreparationMessage).toHaveBeenLastCalledWith("user-token", expect.objectContaining({ current_stage: "ncs", review_context: expect.objectContaining({ selected_ncs_ids: ["skill-server"] }) }));
    expect(container.querySelector(".coach-resume-message")).toBeNull();
    await setInputValue(container.querySelector("#coach-chat-input"), "다음단계로");
    await clickButton("보내기");
    expect(container.querySelector(".coach-resume-message")).not.toBeNull();
    expect(sendPreparationMessage).toHaveBeenCalledTimes(1);
    const ncsTurn = container.querySelector(".preparation-chat-turn")!;
    const resumeCard = container.querySelector(".coach-resume-message")!;
    expect(ncsTurn.compareDocumentPosition(resumeCard) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const input = container.querySelector<HTMLInputElement>(".coach-resume-message input[type=file]")!;
    Object.defineProperty(input, "files", { configurable: true, value: [new File(["%PDF-fake"], "resume.pdf")] });
    await act(async () => input.dispatchEvent(new Event("change", { bubbles: true })));
    await clickButton("이력서 검토하기");
    await clickButton("확인하고 계속하기", false, false);
    expect(container.querySelector(".coach-readme-message")).toBeNull();
    expect(container.textContent).toContain("추가할 경력 사항이나 경험");
    await setInputValue(container.querySelector("#coach-chat-input"), "이력서에 빠진 인증 API 개발 경험을 추가할게요.");
    await clickButton("보내기");
    expect(sendPreparationMessage).toHaveBeenLastCalledWith("user-token", expect.objectContaining({ current_stage: "resume", review_context: expect.objectContaining({ resume_profile: expect.objectContaining({ facts: expect.any(Array) }) }) }));
    expect(container.querySelector(".coach-readme-message")).toBeNull();
    await clickButton("다음 단계");
    const resumeTurn = container.querySelectorAll(".preparation-chat-turn")[1]!;
    const readmeCard = container.querySelector(".coach-readme-message")!;
    expect(ncsTurn.compareDocumentPosition(resumeCard) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(resumeTurn.compareDocumentPosition(readmeCard) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await setInputValue(container.querySelector("#coach-readme-url"), "https://github.com/5Headers/team_project_backend");
    await clickButton("링크 제출", false, false);
    expect(container.textContent).toContain("README 검토가 완료되었어요");
    expect(container.querySelector(".coach-job-search-message")).toBeNull();
    expect(recommendSaraminJobs).not.toHaveBeenCalled();
    await setInputValue(container.querySelector("#coach-chat-input"), "이 README에서 공고와 연결할 경험은 무엇인가요?");
    await clickButton("보내기");
    expect(sendPreparationMessage).toHaveBeenLastCalledWith("user-token", expect.objectContaining({ current_stage: "readme", review_context: expect.objectContaining({ readme_analysis: expect.objectContaining({ source_url: "https://github.com/5Headers/team_project_backend" }) }) }));
    expect(recommendSaraminJobs).not.toHaveBeenCalled();
    await setInputValue(container.querySelector("#coach-chat-input"), "다음으로");
    expect(container.querySelector<HTMLButtonElement>(".coach-next-stage-button")?.disabled).toBe(false);
    expect(container.querySelector<HTMLInputElement>("#coach-chat-input")?.value).toBe("다음으로");
    await clickButton("보내기");
    expect(recommendSaraminJobs).toHaveBeenCalledTimes(1);
    expect(recommendSaraminJobs).toHaveBeenCalledWith(expect.objectContaining({ preparationConversationId: "conversation-1" }));
    expect(container.querySelector(".coach-next-stage-button")).toBeNull();
    const readmeTurn = container.querySelectorAll(".preparation-chat-turn")[2]!;
    const searchCard = container.querySelector(".coach-job-search-message")!;
    expect(readmeTurn.compareDocumentPosition(searchCard) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(container.querySelectorAll(".preparation-chat-turn")).toHaveLength(5);
    expect(ncsTurn.isConnected).toBe(true);
    expect(resumeTurn.isConnected).toBe(true);
  });

  it("이력서와 README를 모두 건너뛰어도 확인된 경험을 포함해 공고를 추천한다", async () => {
    await act(async () => root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><PracticePage isLoggedIn onLogin={vi.fn()} /></NavigationProvider>));
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료", false);
    await clickButton("건너뛰기", false, false);
    expect(analyzeResumePdf).not.toHaveBeenCalled();
    expect(container.textContent).toContain("이력서 제출을 건너뛰었어요");
    expect(container.querySelector("#coach-readme-url")).toBeNull();
    expect(container.querySelectorAll(".resume-confirmed-grid")).toHaveLength(0);
    await setInputValue(container.querySelector("#coach-chat-input"), "Redis 캐시 경험이 있어요.");
    await clickButton("보내기");
    await clickButton("다음 단계");
    expect(container.querySelector("#coach-readme-url")).not.toBeNull();
    await clickButton("건너뛰기", false, false);
    expect(recommendSaraminJobs).not.toHaveBeenCalled();
    await clickButton("다음 단계");
    expect(recommendSaraminJobs).toHaveBeenCalledWith(expect.objectContaining({ resumeProfile: null, readmeAnalysis: null, preparationConversationId: "conversation-1" }));
    expect(container.querySelector(".coach-job-search-message")).not.toBeNull();
  });

  it("README 건너뛰기도 사용자가 진행할 때까지 공고 검색을 시작하지 않는다", async () => {
    await act(async () => root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><PracticePage isLoggedIn onLogin={vi.fn()} /></NavigationProvider>));
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료");
    await clickButton("건너뛰기", false, false);
    expect(recommendSaraminJobs).not.toHaveBeenCalled();
    expect(container.textContent).toContain("README 제출을 건너뛰었어요");
    expect(container.querySelector(".coach-job-search-message")).toBeNull();
    await clickButton("다음 단계");
    expect(container.querySelector(".coach-job-search-message")).not.toBeNull();
    expect(recommendSaraminJobs).toHaveBeenCalledTimes(1);
  });

  it("NCS 안내 뒤 대화는 선택 완료 안내가 생겨도 앞으로 이동하지 않는다", async () => {
    await act(async () => root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><PracticePage isLoggedIn onLogin={vi.fn()} /></NavigationProvider>));
    await setInputValue(container.querySelector("#coach-chat-input"), "어떤 역량을 선택하면 되나요?");
    await clickButton("보내기");
    const firstTurn = container.querySelector(".preparation-chat-turn")!;
    expect(firstTurn).not.toBeNull();
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료", false, false);
    const selection = container.querySelector("#message\\:ncs")!;
    const guide = container.querySelector('[aria-label="다음 단계 진행 안내"]')!;
    expect(firstTurn.compareDocumentPosition(selection) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await setInputValue(container.querySelector("#coach-chat-input"), "선택한 역량을 설명해 주세요.");
    await clickButton("보내기");
    const secondTurn = container.querySelectorAll(".preparation-chat-turn")[1]!;
    expect(guide.compareDocumentPosition(secondTurn) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await clickButton("다음 단계");
    expect(guide.isConnected).toBe(true);
    const resume = container.querySelector(".coach-resume-message")!;
    expect(secondTurn.compareDocumentPosition(resume) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await setInputValue(container.querySelector("#coach-chat-input"), "제출 가능한 이력서 형식을 알려주세요.");
    await clickButton("보내기");
    const thirdTurn = container.querySelectorAll(".preparation-chat-turn")[2]!;
    expect(resume.compareDocumentPosition(thirdTurn) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await clickButton("건너뛰기", false, false);
    const guides = container.querySelectorAll('[aria-label="다음 단계 진행 안내"]');
    expect(thirdTurn.compareDocumentPosition(guides[1]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("README 요청 뒤 대화는 제출 및 검토 안내보다 먼저 유지된다", async () => {
    await act(async () => root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><PracticePage isLoggedIn onLogin={vi.fn()} /></NavigationProvider>));
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료");
    await setInputValue(container.querySelector("#coach-chat-input"), "어떤 프로젝트 링크를 제출하나요?");
    await clickButton("보내기");
    const turn = container.querySelector(".preparation-chat-turn")!;
    expect(container.querySelector(".coach-readme-message")!.compareDocumentPosition(turn) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await setInputValue(container.querySelector("#coach-readme-url"), "https://github.com/5Headers/team_project_backend");
    await clickButton("링크 제출", false, false);
    expect(turn.compareDocumentPosition(container.querySelector(".coach-readme-selection")!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("공고 목록 및 요구사항 뒤 일반 대화는 README 위로 올라가지 않는다", async () => {
    await act(async () => root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><PracticePage isLoggedIn onLogin={vi.fn()} /></NavigationProvider>));
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료");
    await clickButton("건너뛰기");
    const search = container.querySelector(".coach-job-search-message")!;
    let complete: (value: object) => void = () => {};
    sendPreparationMessage.mockImplementationOnce(() => new Promise(resolve => { complete = resolve; }));
    await setInputValue(container.querySelector("#coach-chat-input"), "이 내용으로 이력서 다시 작성해줘");
    await clickButton("보내기");
    const turn = container.querySelector(".preparation-chat-turn")!;
    expect(search.compareDocumentPosition(turn) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(turn.textContent).toContain("내용을 확인하고 있어요.");
    await act(async () => complete({ conversation_id: "conversation-1", message: "현재 단계에서 도와드릴게요.", action: "stay", status: "ok" }));
    expect(turn.isConnected).toBe(true);
    expect(turn.textContent).toContain("현재 단계에서 도와드릴게요.");
    await clickButton("공고 선택");
    const requirements = container.querySelector(".coach-requirement-message")!;
    expect(turn.compareDocumentPosition(requirements) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await setInputValue(container.querySelector("#coach-chat-input"), "이 요구사항은 무슨 의미인가요?");
    await clickButton("보내기");
    const secondTurn = container.querySelectorAll(".preparation-chat-turn")[1]!;
    expect(requirements.compareDocumentPosition(secondTurn) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await clickButton("REST API 서버 개발");
    await clickButton("이 공고로 질문 유형 고르기");
    await act(async () => container.querySelector<HTMLButtonElement>(".coach-question-type-list button")?.click());
    await setInputValue(container.querySelector("#coach-chat-input"), "질문을 고르는 방법을 알려주세요.");
    await clickButton("보내기");
    const thirdTurn = container.querySelectorAll(".preparation-chat-turn")[2]!;
    expect(container.querySelector(".coach-question-message")!.compareDocumentPosition(thirdTurn) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(secondTurn.isConnected).toBe(true);
  });

  it("채팅에서 선택한 reviewed 공고도 요구사항 선택과 질문 단계로 이어진다", async () => {
    await act(async () => root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><PracticePage isLoggedIn onLogin={vi.fn()} /></NavigationProvider>));
    await clickButton("서버 프로그램을 구현할 수 있어요");
    await clickButton("선택 완료");
    await clickButton("건너뛰기");
    sendPreparationMessage.mockResolvedValueOnce({
      conversation_id: "conversation-reviewed", message: "선택 변경을 저장하고 결과를 확인했어요.", action: "selection_updated", status: "ok",
      selection_revision: 1, execution_result: "verified",
      selection_state: { job_posting_id: "reviewed-job", requirement_ids: [], question_id: null, custom_question_text: null, selected_ncs_ids: ["skill-server"] },
      selection_job: { id: "reviewed-job", company: "검토 회사", title: "검토된 백엔드 공고", source_url: "https://example.invalid/reviewed",
        captured_at: "2026-10-08T00:00:00Z", data_origin: "reviewed", requirements: [{ id: "reviewed-req", code: "R1", text: "검토된 API 구현 경험", source_excerpt: "API 구현 경험", display_order: 1 }] },
    });
    await setInputValue(container.querySelector("#coach-chat-input"), "이 선택으로 변경해줘");
    await clickButton("보내기");
    expect(container.querySelector(".coach-requirement-message")?.textContent).toContain("검토된 API 구현 경험");
    await clickButton("검토된 API 구현 경험");
    await clickButton("이 공고로 질문 유형 고르기");
    expect(container.querySelector(".coach-question-message")).not.toBeNull();
  });

  it("리드미 변경 확인 후 선행 자료를 보존하고 새 리드미에서 곧바로 공고 검색으로 이어진다", async () => {
    await act(async () => root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><PracticePage isLoggedIn onLogin={vi.fn()} /></NavigationProvider>));
    await clickButton("서버 프로그램을 구현할 수 있어요"); await clickButton("선택 완료");
    await setInputValue(container.querySelector("#coach-readme-url"), "https://github.com/5Headers/team_project_backend"); await clickButton("링크 제출");
    let restart: object;
    sendPreparationMessage.mockImplementation(async (_token, input) => {
      if (input.restart_confirmation) return { conversation_id: "new-readme", status: "ok", action: "practice_restarted", execution_result: "verified", message: "재시작", follow_up_question: null, restart };
      restart = { token: "readme-token", target: "readme", new_graduate_only: false, materials: { ...input.review_context, readme_analysis: null }, selection: { job_posting_id: null, requirement_ids: [], question_id: null, custom_question_text: null } };
      return { conversation_id: "conversation-1", status: "ok", action: "stay", execution_result: "awaiting_confirmation", message: "이전 채팅은 삭제됩니다.", follow_up_question: "확인할까요?", restart };
    });
    await clickButton("리드미 교체"); await clickButton("확인하고 변경");
    expect(container.querySelector(".coach-ncs-message")).toBeNull(); expect(container.querySelector(".coach-resume-message")).toBeNull();
    expect(container.querySelectorAll(".workspace-evidence-card--reference")).toHaveLength(1);
    expect(container.querySelector(".coach-job-search-message")).toBeNull();
    await setInputValue(container.querySelector("#coach-readme-url"), "https://github.com/5Headers/team_project_backend");
    await clickButton("링크 제출", true, false);
    expect(container.querySelector(".coach-job-search-message")).toBeNull();
    await clickButton("다음 단계", true, false);
    expect(container.querySelector(".coach-job-search-message")).not.toBeNull();
  });

  it("신입 재선택은 동의 후 검증한 신입·경력무관 공고만 표시한다", async () => {
    const jobs = await recommendSaraminJobs();
    recommendSaraminJobs.mockResolvedValue([...jobs, { ...jobs[0], title: "경력 전용 제외 공고", experience: "경력 5년", source_url: "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=999" }, { ...jobs[0], title: "조건 미확인 제외 공고", experience: "", source_url: "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=888" }]);
    await act(async () => root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><PracticePage isLoggedIn onLogin={vi.fn()} /></NavigationProvider>));
    await clickButton("서버 프로그램을 구현할 수 있어요"); await clickButton("선택 완료");
    await setInputValue(container.querySelector("#coach-readme-url"), "https://github.com/5Headers/team_project_backend"); await clickButton("링크 제출");
    sendPreparationMessage.mockImplementation(async (_token, input) => ({ conversation_id: "new-jobs", status: "ok", action: "practice_restarted", execution_result: "verified", message: "재시작", follow_up_question: null, restart: { token: "jobs-token", target: "jobs", new_graduate_only: true, materials: input.review_context, selection: { job_posting_id: null, requirement_ids: [], question_id: null, custom_question_text: null } } }));
    await setInputValue(container.querySelector("#coach-chat-input"), "신입 공고만 보여줘"); await clickButton("보내기");
    expect(container.textContent).toContain("신입 지원 가능 공고만 표시 중");
    const activeJobs = container.querySelector(".coach-job-result-list")!;
    expect(activeJobs.textContent).not.toContain("경력 전용 제외 공고"); expect(activeJobs.textContent).not.toContain("조건 미확인 제외 공고");
    expect(container.querySelector(".coach-history-message")).not.toBeNull();
    expect(container.querySelector(".job-select-card")).toBeNull();
    expect(container.querySelector(".coach-readme-analysis-result")).toBeNull();
    expect(container.querySelector(".coach-job-result-list")?.textContent).toContain("신입 백엔드 개발자");
  });

  it("NCS 화면의 공고 선택 다시 요청은 검색 대신 준비 대화 안내를 표시한다", async () => {
    sendPreparationMessage.mockResolvedValue({ conversation_id: "guarded", message: "아직 공고 선택 단계를 진행하지 않아 변경할 수 없어요. 현재 NCS 선택을 완료해 주세요.", follow_up_question: null, action: "stay", status: "ok" });
    await act(async () => root.render(<NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><PracticePage isLoggedIn onLogin={vi.fn()} /></NavigationProvider>));
    await setInputValue(container.querySelector("#coach-chat-input"), "공고 선택 다시 할래"); await clickButton("보내기");
    expect(sendPreparationMessage).toHaveBeenLastCalledWith("user-token", expect.objectContaining({ ui_context: "ncs", message: "공고 선택 다시 할래" }));
    expect(interpretJobSearchMessage).not.toHaveBeenCalled();
    expect(container.textContent).toContain("아직 공고 선택 단계를 진행하지 않아");
    expect(container.textContent).not.toContain("확인하고 변경");
    expect(container.querySelector(".coach-ncs-message")).not.toBeNull();
  });

  async function clickButton(label: string, confirmResume = true, advance = true) {
    const button = Array.from(container.querySelectorAll<HTMLButtonElement>("button"))
      .find((candidate) => candidate.textContent?.includes(label));
    expect(button).not.toBeUndefined();
    await act(async () => { button?.click(); await Promise.resolve(); await Promise.resolve(); });
    if (advance && ["선택 완료", "확인하고 계속하기", "링크 제출", "건너뛰기"].includes(label)) {
      const next = container.querySelector<HTMLButtonElement>(".coach-next-stage-button");
      if (next) await act(async () => next.click());
    }
    if (label === "선택 완료" && confirmResume) {
      const input = container.querySelector<HTMLInputElement>(".coach-resume-message input[type=file]")!;
      Object.defineProperty(input, "files", { configurable: true, value: [new File(["%PDF-fake"], "resume.pdf", { type: "application/pdf" })] });
      await act(async () => input.dispatchEvent(new Event("change", { bubbles: true })));
      await clickButton("이력서 검토하기");
      await clickButton("확인하고 계속하기");
    }
  }

  async function setInputValue(element: HTMLInputElement | HTMLTextAreaElement | null, value: string) {
    expect(element).not.toBeNull();
    await act(async () => {
      const prototype = element instanceof HTMLTextAreaElement
        ? HTMLTextAreaElement.prototype
        : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
      setter?.call(element, value);
      element?.dispatchEvent(new Event("input", { bubbles: true }));
    });
  }
});
