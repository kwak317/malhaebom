import { describe, expect, it, vi } from "vitest";

import {
  analyzeGithubReadme,
  analyzeRecommendedJob,
  recommendSaraminJobs,
  createPracticeSession,
  getNcsBackendCompetencies,
  listJobPostings,
  analyzeAlioRecruitment,
  analyzeMofeRecruitment,
  analyzePublicEmploymentRecruitment,
  interpretJobSearchMessage,
  searchAlioRecruitments,
  searchMofeRecruitments,
  searchPublicEmploymentRecruitments,
} from "./practiceSetup";

describe("practice setup API", () => {
  it("저장 경험은 본문 대신 준비 대화 ID로 조회하도록 요청한다", async () => {
    const id = "22222222-2222-4222-8222-222222222222";
    const fetchImpl = vi.fn(async (_url, init) => {
      expect(JSON.parse(String(init?.body))).toEqual({
        selected_ncs_ids: ["skill-server"], readme_analysis: null,
        preparation_conversation_id: id,
      });
      return new Response(JSON.stringify({ recommendations: [] }), { status: 200 });
    });
    await recommendSaraminJobs({ accessToken: "token", selectedNcsIds: ["skill-server"],
      readmeAnalysis: null, preparationConversationId: id, fetchImpl });
  });

  it("선택한 추천 공고 URL만 서버 검토에 보내고 검토된 요구사항을 받는다", async () => {
    const sourceUrl = "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=123";
    const fetchImpl = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      expect(String(url)).toContain("/api/job-search/recommendations/analyze");
      expect(init?.headers).toEqual({ Authorization: "Bearer user-token", "Content-Type": "application/json" });
      expect(JSON.parse(String(init?.body))).toEqual({ source_url: sourceUrl });
      return new Response(JSON.stringify({
        id: "10000000-0000-4000-8000-000000000020",
        company: "예시기업", title: "신입 백엔드 개발자",
        source_url: sourceUrl, captured_at: "2026-09-23T00:00:00Z",
        data_origin: "private_job",
        requirements: [{
          id: "20000000-0000-4000-8000-000000000020", code: "PRIVATE-SARAMIN-123-R1",
          text: "REST API 개발", source_excerpt: "REST API 개발", display_order: 1,
        }],
      }), { status: 201 });
    });
    const posting = await analyzeRecommendedJob({
      accessToken: "user-token", sourceUrl, fetchImpl: fetchImpl as typeof fetch,
    });
    expect(posting.data_origin).toBe("private_job");
    expect(posting.requirements[0].source_excerpt).toBe("REST API 개발");
  });

  it("NCS·README 근거로 공고 검색을 요청한다", async () => {
    const analysis = {
      source_url: "https://github.com/5Headers/team_project_backend",
      readme_sha: "a".repeat(40), model: "google/gemini-3.8-flash",
      technology_stack: [{ name: "Spring Boot", description: "서버 개발", source_excerpt: "Spring Boot" }],
      project_flow: [{ description: "API 제공", source_excerpt: "REST API" }],
    };
    const fetchImpl = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      expect(String(url)).toContain("/api/job-search/recommendations");
      expect(init?.headers).toEqual({ Authorization: "Bearer user-token", "Content-Type": "application/json" });
      expect(JSON.parse(String(init?.body))).toEqual({ selected_ncs_ids: ["skill-server"], readme_analysis: analysis });
      return new Response(JSON.stringify({ recommendations: [{
        company: "예시기업", title: "신입 백엔드 개발자",
        source_url: "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=123",
        deadline: "2026-10-01", experience: "신입",
        matched_technologies: ["Spring Boot"], matched_project_flows: ["REST API"],
        matched_ncs_labels: ["서버 프로그램을 구현할 수 있어요"], source_excerpt: "Spring Boot API 개발",
      }], searched_at: "2026-09-23T14:00:00+09:00" }), { status: 200 });
    });
    const result = await recommendSaraminJobs({
      accessToken: "user-token", selectedNcsIds: ["skill-server"],
      readmeAnalysis: analysis, fetchImpl: fetchImpl as typeof fetch,
    });
    expect(result[0].matched_project_flows).toEqual(["REST API"]);
  });

  it("채용 시 마감 공고의 null 마감일을 허용하고 마감일 필드 누락은 거부한다", async () => {
    const job = {
      company: "예시기업", title: "백엔드 개발자",
      source_url: "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=123",
      deadline: null, experience: "경력 무관",
      matched_technologies: [], matched_project_flows: [],
      matched_ncs_labels: ["서버 프로그램을 구현할 수 있어요"], source_excerpt: "서버 개발",
    };
    const fetchImpl = vi.fn(async () => new Response(JSON.stringify({ recommendations: [job] }), { status: 200 }));
    const request = { accessToken: "user-token", selectedNcsIds: ["skill-server"], readmeAnalysis: null, fetchImpl: fetchImpl as typeof fetch };
    const result = await recommendSaraminJobs(request);
    expect(result[0].deadline).toBeNull();
    fetchImpl.mockImplementationOnce(async () => new Response(JSON.stringify({
      recommendations: [{ ...job, deadline: undefined }],
    }), { status: 200 }));
    await expect(recommendSaraminJobs(request)).rejects.toThrow("공고 검색 응답 형식");
  });

  it("인증 토큰과 GitHub 주소로 README 분석을 요청하고 근거가 있는 응답을 받는다", async () => {
    const fetchImpl = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      expect(String(url)).toContain("/api/github/readme/analyze");
      expect(init?.method).toBe("POST");
      expect(init?.headers).toEqual({
        Authorization: "Bearer user-token",
        "Content-Type": "application/json",
      });
      expect(JSON.parse(String(init?.body))).toEqual({ source_url: "https://github.com/5Headers/team_project_backend" });
      return new Response(JSON.stringify({
        source_url: "https://github.com/5Headers/team_project_backend",
        readme_sha: "8c4b0a5",
        model: "google/gemini-3.8-flash",
        technology_stack: [{ name: "Spring Boot", description: "백엔드 API", source_excerpt: "Spring Boot" }],
        project_flow: [{ description: "견적을 생성한다", source_excerpt: "견적 생성" }],
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    });

    const result = await analyzeGithubReadme({
      accessToken: "user-token",
      sourceUrl: "https://github.com/5Headers/team_project_backend",
      fetchImpl: fetchImpl as typeof fetch,
    });

    expect(result.model).toBe("google/gemini-3.8-flash");
    expect(result.technology_stack[0].source_excerpt).toBe("Spring Boot");
  });

  it("NCS 역량 조회에 사용자 토큰을 쓰고 응답 형식을 검증한다", async () => {
    const fetchImpl = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      expect(String(url)).toContain("/api/ncs/backend-competencies");
      expect(init?.headers).toEqual({ Authorization: "Bearer user-token" });
      return new Response(JSON.stringify({
        job_name: "응용SW엔지니어링",
        source_url: "https://www.data.go.kr/data/15128213/openapi.do",
        options: [{ id: "skill-server", category: "skill", label: "서버 프로그램을 구현할 수 있어요", ncs_unit_code: "2001020211_23v6", ncs_unit_name: "서버프로그램 구현" }],
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    });

    const result = await getNcsBackendCompetencies({ accessToken: "user-token", fetchImpl: fetchImpl as typeof fetch });

    expect(result.options[0].ncs_unit_name).toBe("서버프로그램 구현");
  });
  it("인증 토큰으로 검토 공고 목록을 불러온다", async () => {
    const fetchImpl = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
      expect(init?.headers).toEqual({ Authorization: "Bearer user-token" });
      return new Response(JSON.stringify({
        job_postings: [{
          id: "job-1",
          company: "가상 회사",
          title: "백엔드 개발자",
          source_url: "https://example.invalid/job-1",
          captured_at: "2026-09-17T00:00:00Z",
          data_origin: "demo",
          requirements: [{ id: "req-1", code: "R1", text: "API 오류 분석", source_excerpt: null, display_order: 1 }],
        }],
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    });

    const postings = await listJobPostings({ accessToken: "user-token", fetchImpl: fetchImpl as typeof fetch });

    expect(postings[0].requirements[0].code).toBe("R1");
  });

  it("선택한 공고·요구사항·질문으로 세션을 만든다", async () => {
    const fetchImpl = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
      expect(init?.method).toBe("POST");
      expect(JSON.parse(String(init?.body))).toEqual({
        job_posting_id: "job-1",
        requirement_ids: ["req-1", "req-2"],
        question_type: "preset",
        question_id: "preset-04",
        custom_question_text: null,
      });
      return new Response(JSON.stringify({
        practice_session_id: "session-1",
        expires_at: "2026-09-18T00:00:00Z",
      }), { status: 201, headers: { "Content-Type": "application/json" } });
    });

    const session = await createPracticeSession({
      accessToken: "user-token",
      input: {
        job_posting_id: "job-1",
        requirement_ids: ["req-1", "req-2"],
        question_type: "preset",
        question_id: "preset-04",
        custom_question_text: null,
      },
      fetchImpl: fetchImpl as typeof fetch,
    });

    expect(session.practice_session_id).toBe("session-1");
  });

  it("인증 토큰을 사용해 ALIO 공고를 검색한다", async () => {
    const fetchImpl = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      expect(String(url)).toContain("/api/alio/recruitments?query=%EB%B0%B1%EC%97%94%EB%93%9C&page=1");
      expect(init?.headers).toEqual({ Authorization: "Bearer user-token" });
      return new Response(JSON.stringify({
        query: "백엔드",
        page: 1,
        page_size: 10,
        total_count: 1,
        recruitments: [{
          announcement_id: 123,
          company: "한국 예시 공사",
          title: "신입 백엔드 개발자",
          source_url: "https://example.invalid/job-1",
          announced_at: "2026-09-21",
          deadline: "2026-10-06",
          location: "서울",
          employment_type: "정규직",
          recruitment_type: "신입",
        }],
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    });

    const result = await searchAlioRecruitments({
      accessToken: "user-token",
      query: "백엔드",
      fetchImpl: fetchImpl as typeof fetch,
    });

    expect(result.totalCount).toBe(1);
    expect(result.recruitments[0].announcement_id).toBe(123);
  });

  it("ALIO 공고 원문을 AI 분석 요청으로 저장한다", async () => {
    const fetchImpl = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      expect(String(url)).toContain("/api/alio/recruitments/analyze");
      expect(init?.method).toBe("POST");
      expect(init?.headers).toEqual({
        Authorization: "Bearer user-token",
        "Content-Type": "application/json",
      });
      expect(JSON.parse(String(init?.body))).toEqual({
        announcement_id: 123,
        company: "한국 예시 공사",
        title: "신입 백엔드 개발자",
        source_url: "https://www.alio.go.kr/recruitment/123",
      });
      return new Response(JSON.stringify({
        id: "alio-job-1",
        company: "한국 예시 공사",
        title: "신입 백엔드 개발자",
        source_url: "https://www.alio.go.kr/recruitment/123",
        captured_at: "2026-09-21T00:00:00Z",
        data_origin: "alio",
        requirements: [{
          id: "alio-req-1",
          code: "ALIO-123-R1",
          text: "API 오류 분석 경험",
          source_excerpt: "지원자격: API 오류 원인 분석 및 개선 경험 보유자",
          display_order: 1,
        }],
      }), { status: 201, headers: { "Content-Type": "application/json" } });
    });

    const posting = await analyzeAlioRecruitment({
      accessToken: "user-token",
      input: {
        announcement_id: 123,
        company: "한국 예시 공사",
        title: "신입 백엔드 개발자",
        source_url: "https://www.alio.go.kr/recruitment/123",
      },
      fetchImpl: fetchImpl as typeof fetch,
    });

    expect(posting.data_origin).toBe("alio");
    expect(posting.requirements[0].source_excerpt).toContain("오류 원인");
  });

  it("인증 토큰을 사용해 공공취업정보 공고를 검색한다", async () => {
    const fetchImpl = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      expect(String(url)).toContain("/api/public-employment/recruitments?query=%EA%B0%9C%EB%B0%9C&page=1");
      expect(init?.headers).toEqual({ Authorization: "Bearer user-token" });
      return new Response(JSON.stringify({
        query: "개발",
        page: 1,
        page_size: 10,
        total_count: 1,
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
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    });

    const result = await searchPublicEmploymentRecruitments({
      accessToken: "user-token",
      query: "개발",
      fetchImpl: fetchImpl as typeof fetch,
    });

    expect(result.recruitments[0].announcement_id).toBe(456);
  });

  it("공공취업정보 공고는 서버가 확보한 원문으로 AI 분석을 요청한다", async () => {
    const fetchImpl = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      expect(String(url)).toContain("/api/public-employment/recruitments/analyze");
      expect(init?.method).toBe("POST");
      expect(JSON.parse(String(init?.body))).toEqual({
        announcement_id: 456,
        company: "인사혁신처 예시 기관",
        title: "계약직 개발자 공고",
      });
      return new Response(JSON.stringify({
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
      }), { status: 201, headers: { "Content-Type": "application/json" } });
    });

    const posting = await analyzePublicEmploymentRecruitment({
      accessToken: "user-token",
      input: {
        announcement_id: 456,
        company: "인사혁신처 예시 기관",
        title: "계약직 개발자 공고",
      },
      fetchImpl: fetchImpl as typeof fetch,
    });

    expect(posting.data_origin).toBe("public_job");
  });

  it("재정경제부 공공기관 채용정보 공고를 인증 토큰으로 검색한다", async () => {
    const fetchImpl = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      expect(String(url)).toContain("/api/mofe/recruitments?query=%EB%B0%B1%EC%97%94%EB%93%9C&page=1");
      expect(init?.headers).toEqual({ Authorization: "Bearer user-token" });
      return new Response(JSON.stringify({
        query: "백엔드",
        page: 1,
        page_size: 10,
        total_count: 1,
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
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    });

    const result = await searchMofeRecruitments({
      accessToken: "user-token",
      query: "백엔드",
      fetchImpl: fetchImpl as typeof fetch,
    });

    expect(result.recruitments[0].announcement_id).toBe(305259);
  });

  it("재정경제부 공고는 서버가 재조회한 원문으로 AI 분석을 요청한다", async () => {
    const fetchImpl = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      expect(String(url)).toContain("/api/mofe/recruitments/analyze");
      expect(init?.method).toBe("POST");
      expect(JSON.parse(String(init?.body))).toEqual({
        announcement_id: 305259,
        company: "한국전력공사",
        title: "전문인력 백엔드 개발 채용공고",
      });
      return new Response(JSON.stringify({
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
      }), { status: 201, headers: { "Content-Type": "application/json" } });
    });

    const posting = await analyzeMofeRecruitment({
      accessToken: "user-token",
      input: {
        announcement_id: 305259,
        company: "한국전력공사",
        title: "전문인력 백엔드 개발 채용공고",
      },
      fetchImpl: fetchImpl as typeof fetch,
    });

    expect(posting.data_origin).toBe("mofe_job");
  });

  it("채팅 메시지를 서버 LLM 의도 분류에 전달한다", async () => {
    const fetchImpl = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      expect(String(url)).toContain("/api/job-search-intent");
      expect(init?.method).toBe("POST");
      expect(init?.headers).toEqual({
        Authorization: "Bearer user-token",
        "Content-Type": "application/json",
      });
      expect(JSON.parse(String(init?.body))).toEqual({ message: "백엔드 관련 공고" });
      return new Response(JSON.stringify({
        should_search: true,
        query: "백엔드",
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    });

    const intent = await interpretJobSearchMessage({
      accessToken: "user-token",
      message: "백엔드 관련 공고",
      fetchImpl: fetchImpl as typeof fetch,
    });

    expect(intent).toEqual({ should_search: true, query: "백엔드" });
  });
});

it("NCS DB 재시도는 source=database로 요청한다", async () => {
  const fetchImpl = vi.fn(async (url: RequestInfo | URL) => {
    expect(String(url)).toContain("/api/ncs/backend-competencies?source=database");
    return new Response(JSON.stringify({ job_name: "응용SW엔지니어링", source_url: "https://www.data.go.kr/data/15128213/openapi.do", data_source: "cached", fetched_at: "2026-10-06T19:11:28Z", options: [] }), { status: 200 });
  });
  expect((await getNcsBackendCompetencies({ accessToken: "user-token", source: "database", fetchImpl: fetchImpl as typeof fetch })).data_source).toBe("cached");
});
