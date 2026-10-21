import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { InlineAttemptComparisonChat } from "./InlineAttemptComparisonChat";
import { InterviewChatApiError } from "../api/interviewChat";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

const getSession = vi.fn();
const fetchPracticeRecord = vi.fn();
const requestInterviewChat = vi.fn();

vi.mock("../api/interviewChat", async () => ({
  ...await vi.importActual("../api/interviewChat"),
  requestInterviewChat: (...args: unknown[]) => requestInterviewChat(...args),
}));

vi.mock("../api/supabaseAuth", () => ({
  supabase: () => ({ auth: { getSession } }),
}));

vi.mock("../api/practiceHistory", () => ({
  fetchPracticeRecord: (...args: unknown[]) => fetchPracticeRecord(...args),
}));

describe("채팅 내 답변 비교", () => {
  let root: Root;
  let container: HTMLDivElement;

  beforeEach(() => {
    vi.useFakeTimers();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    getSession.mockResolvedValue({ data: { session: { access_token: "user-token" } }, error: null });
    requestInterviewChat.mockResolvedValue({ conversation_id: "chat-1", status: "active", message: "비교 뒤에 대화를 이어가요.", follow_up_question: "결과를 확인한 조건은 무엇인가요?", summary: null });
    fetchPracticeRecord.mockResolvedValue({
      practice_session_id: "session-1",
      question_type: "preset",
      question_id: "preset-04",
      custom_question_text: null,
      practiced_at: "2026-09-22T00:00:00Z",
      attempts: [
        { attempt_no: 1, job_id: "analysis-1", transcript: "1차 답변", metrics: { cpm: 320, long_silence_count: 2, repetition_count: 1 }, feedback: [] },
        { attempt_no: 2, job_id: "analysis-2", transcript: "재답변", metrics: { cpm: 300, long_silence_count: 1, repetition_count: 0 }, feedback: [] },
      ],
      comparison: {
        content_available: false,
        content_notice: "기준별 내용 비교는 준비 중이에요.",
        criteria: [],
        added_explanations: [],
        still_missing: [],
        contradictions: [],
        delivery: {
          cpm: { first: 320, second: 300, direction: "decreased" },
          long_silence_count: { first: 2, second: 1, direction: "decreased" },
          repetition_count: { first: 1, second: 0, direction: "decreased" },
        },
      },
    });
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("비교를 불러오는 동안 입력 중 말풍선을 보이고 같은 채팅에 결과를 추가한다", async () => {
    await act(async () => {
      root.render(
        <div className="coach-thread"><InlineAttemptComparisonChat
          question={{ questionType: "preset", question: "문제 해결 경험을 말씀해주세요.", questionId: "preset-04", practiceSessionId: "session-1" }}
          firstResult={result(1, "첫 답변")}
          secondResult={result(2, "두 번째 답변")}
        /></div>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(container.textContent).toContain("1차 답변과 재답변을 비교하고 있어요.");
    await act(async () => { await vi.advanceTimersByTimeAsync(450); });

    expect(fetchPracticeRecord).toHaveBeenCalledWith("session-1", "user-token");
    expect(container.textContent).toContain("1차 답변과 재답변을 비교했어요.");
    expect(container.textContent).toContain("재답변");
    expect(container.querySelector(".workspace-comparison-details")?.tagName).toBe("SECTION");
    expect(container.querySelector(".comparison-answer-sources summary")?.textContent).toBe("답변 원문과 1차 피드백 보기");
    expect(container.querySelector(".comparison-answer-sources")?.hasAttribute("open")).toBe(false);
    expect(container.textContent).toContain("전달력 변화");
    expect(requestInterviewChat).not.toHaveBeenCalled();
  });

  it("내용 비교 후 선택을 기다리고 버튼을 누른 뒤에만 첫 질문과 면접 입력창을 연결한다", async () => {
    const record = await fetchPracticeRecord();
    fetchPracticeRecord.mockResolvedValue({ ...record, comparison: { ...record.comparison, content_available: true } });
    await act(async () => root.render(<InlineAttemptComparisonChat
      question={{ questionType: "preset", question: "문제 해결 경험", questionId: "preset-04", practiceSessionId: "session-1" }}
      firstResult={result(1, "첫 답변")} secondResult={result(2, "두 번째 답변")} />));
    expect(requestInterviewChat).not.toHaveBeenCalled();
    await act(async () => { await vi.advanceTimersByTimeAsync(450); });
    expect(requestInterviewChat).not.toHaveBeenCalled();
    expect(container.textContent).toContain("다음으로 무엇을 해볼까요?");
    expect(container.querySelector<HTMLButtonElement>(".post-comparison-resume-button")?.disabled).toBe(false);
    expect(container.querySelector("#post-comparison-chat-input")).not.toBeNull();
    await act(async () => container.querySelector<HTMLButtonElement>(".post-comparison-actions .coach-recording-button")!.click());
    expect(requestInterviewChat).toHaveBeenCalledWith({ action: "start", request_id: expect.any(String), practice_session_id: "session-1" }, "user-token");
    expect(container.textContent).toContain("결과를 확인한 조건은 무엇인가요?");
    expect(container.querySelector("#interview-chat-input")).not.toBeNull();
    expect(container.querySelector("#coach-chat-input")).toBeNull();
  });

  it("내용 비교가 있는 과거 기록의 start 409에서도 비교 카드와 두 답변을 유지한다", async () => {
    const record = await fetchPracticeRecord();
    fetchPracticeRecord.mockResolvedValue({ ...record, comparison: { ...record.comparison, content_available: true } });
    requestInterviewChat.mockRejectedValueOnce(new InterviewChatApiError("두 답변의 코칭을 먼저 완료해 주세요.", 409));
    await act(async () => root.render(<InlineAttemptComparisonChat
      question={{ questionType: "preset", question: "문제 해결 경험", questionId: "preset-04", practiceSessionId: "session-1" }}
      firstResult={result(1, "첫 답변")} secondResult={result(2, "두 번째 답변")} />));
    await act(async () => { await vi.advanceTimersByTimeAsync(450); });
    await act(async () => container.querySelector<HTMLButtonElement>(".post-comparison-actions .coach-recording-button")!.click());
    expect(container.textContent).toContain("1차 답변과 재답변을 비교했어요.");
    expect(container.textContent).toContain("1차 답변");
    expect(container.textContent).toContain("재답변");
    expect(container.textContent).toContain("현재 기록으로는 면접 대화를 이어갈 수 없어요.");
    expect(container.querySelector('[role="alert"]')).toBeNull();
    expect(container.querySelector("#interview-chat-input")).toBeNull();
    expect(container.textContent).not.toContain("다시 시도");
    expect(requestInterviewChat).toHaveBeenCalledTimes(1);
  });

  it.each(["꼬리질문 해줘", "꼬리 질문으로 연습하기", "추가 질문 만들어 주세요"])("채팅 요청 '%s'도 기존 꼬리질문 흐름을 한 번 시작한다", async (message) => {
    await renderReadyComparison();
    await sendNextAction(message);
    expect(requestInterviewChat).toHaveBeenCalledTimes(1);
    expect(container.querySelector("#post-comparison-chat-input")).toBeNull();
    expect(container.querySelector("#interview-chat-input")).not.toBeNull();
    expect(container.textContent).toContain(message);
  });

  it("질문 설명이나 이력서 요청은 꼬리질문을 자동 생성하지 않는다", async () => {
    await renderReadyComparison();
    await sendNextAction("꼬리질문이 뭐야?");
    await sendNextAction("이력서 초안 작성해줘");
    expect(requestInterviewChat).not.toHaveBeenCalled();
    expect(container.textContent).toContain("어떤 이력서 양식으로 정리할까요?");
    expect(container.querySelector("#post-comparison-chat-input")).not.toBeNull();
    await sendNextAction("꼬리질문 시작해줘");
    expect(requestInterviewChat).toHaveBeenCalledTimes(1);
  });

  it("이력서 양식 선택만으로 제출 자료를 자동으로 가져오지 않는다", async () => {
    await renderReadyComparison();
    await act(async () => container.querySelector<HTMLButtonElement>(".post-comparison-resume-button")!.click());
    expect(container.textContent).toContain("프로젝트 중심 이력서");
    expect(container.textContent).toContain("경력 중심 이력서");
    await clickLayout("프로젝트 중심 이력서");
    const draft = container.querySelector('.resume-draft-message')!;
    expect(draft.textContent).toContain("제출한 정보 가져오기");
    expect(draft.textContent).toContain("[프로젝트명·기간·팀 규모 입력]");
    expect(draft.textContent).not.toContain("확인한 프로젝트 경험");
    expect(draft.textContent).not.toContain("확인한 인턴 경력");
    expect(draft.textContent).not.toContain("프로젝트 JWT 인증");
    expect(draft.textContent).not.toContain("가상테크");
    expect([...draft.querySelectorAll('[data-resume-section]')].map((element) => element.getAttribute('data-resume-section'))).toEqual(["skills", "project", "career"]);
    await clickLayout("경력 중심 이력서");
    const drafts = container.querySelectorAll('.resume-draft-message');
    expect(drafts).toHaveLength(2);
    expect([...drafts[1].querySelectorAll('[data-resume-section]')].map((element) => element.getAttribute('data-resume-section'))).toEqual(["career", "skills", "project"]);
    expect(requestInterviewChat).not.toHaveBeenCalled();
    expect(container.querySelector("#post-comparison-chat-input")).not.toBeNull();
  });

  it.each(["프로젝트 중심 이력서", "경력 중심으로 작성해줘"])("채팅으로 양식 '%s'를 직접 선택한다", async (message) => {
    await renderReadyComparison();
    await sendNextAction(message);
    expect(container.querySelector('.resume-draft-message')).not.toBeNull();
    expect(container.textContent).toContain(message.startsWith("프로젝트") ? "프로젝트 중심 이력서 초안" : "경력 중심 이력서 초안");
    expect(requestInterviewChat).not.toHaveBeenCalled();
  });

  async function clickLayout(label: string) {
    const button = [...container.querySelectorAll<HTMLButtonElement>("button")].find((element) => element.textContent === label)!;
    await act(async () => button.click());
  }

  async function renderReadyComparison() {
    const record = await fetchPracticeRecord();
    fetchPracticeRecord.mockResolvedValue({ ...record, comparison: { ...record.comparison, content_available: true } });
    await act(async () => root.render(<InlineAttemptComparisonChat
      question={{ questionType: "preset", question: "문제 해결 경험", questionId: "preset-04", practiceSessionId: "session-1" }}
      firstResult={result(1, "첫 답변")} secondResult={result(2, "두 번째 답변")}
      resumeDraftMaterials={{ resumeProfile: { facts: [
        { category: "project", value: "확인한 프로젝트 경험", keyword: null },
        { category: "career", value: "확인한 인턴 경력", keyword: null },
      ] }, readmeAnalysis: { source_url: "https://github.com/example/project", readme_sha: "abc", model: "test",
        project_flow: [{ description: "프로젝트 JWT 인증", source_excerpt: "JWT" }], technology_stack: [] } }} />));
    await act(async () => { await vi.advanceTimersByTimeAsync(450); });
  }

  async function sendNextAction(message: string) {
    const input = container.querySelector<HTMLInputElement>("#post-comparison-chat-input")!;
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, message);
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await act(async () => input.closest("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
  }
});

function result(attemptNo: 1 | 2, transcript: string) {
  return {
    attemptNo,
    analysisJobId: `analysis-${attemptNo}`,
    practiceSessionId: "session-1",
    transcript,
    speakingRate: 300,
    longSilence: 1,
    repeatedExpressions: 0,
    feedback: [],
    prosodyReferenceAvailable: true,
    referenceMetrics: { pace: { value: 320 }, longSilenceCount: { value: 2.48 }, repetitionCount: { value: 0.41 } },
    contentFeedback: { text: "" },
  };
}
