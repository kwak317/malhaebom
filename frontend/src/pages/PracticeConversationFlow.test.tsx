import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NavigationProvider } from "../navigation";
import PracticePage from "./PracticePage";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

const listJobPostings = vi.fn();
const getNcsBackendCompetencies = vi.fn();
const createPracticeSession = vi.fn();
const getSession = vi.fn();
const confirmAnswerRevision = vi.fn();
const requestCoaching = vi.fn();
const sendPreparationMessage = vi.fn();
vi.mock("../api/preparationConversation", () => ({ sendPreparationMessage: (...args: unknown[]) => sendPreparationMessage(...args), getConfirmedPreparationExperiences: async () => [], bindPreparationConversation: async () => {}, PreparationSelectionConflict: class extends Error {} }));
vi.mock("../api/answerRevisions", () => ({ confirmAnswerRevision: (...args: unknown[]) => confirmAnswerRevision(...args) }));
vi.mock("../api/coaching", () => ({ requestCoaching: (...args: unknown[]) => requestCoaching(...args) }));


vi.mock("../api/practiceSetup", () => ({
  listJobPostings: (...args: unknown[]) => listJobPostings(...args),
  getNcsBackendCompetencies: (...args: unknown[]) => getNcsBackendCompetencies(...args),
  createPracticeSession: (...args: unknown[]) => createPracticeSession(...args),
  searchAlioRecruitments: vi.fn(),
  analyzeAlioRecruitment: vi.fn(),
}));

vi.mock("../api/supabaseAuth", () => ({
  supabase: () => ({ auth: { getSession } }),
}));

describe("연습 채팅 안의 분석 결과", () => {
  let root: Root;
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    sendPreparationMessage.mockResolvedValue({ conversation_id: "conversation-1", status: "ok", action: "stay", message: "현재 연습의 이전 채팅·녹음·코칭 내역은 삭제됩니다.", follow_up_question: "확인할까요?", execution_result: "awaiting_confirmation", restart: { token: "token-1", target: "jobs", new_graduate_only: false, materials: { selected_ncs_ids: [], resume_profile: null, readme_analysis: null }, selection: { job_posting_id: null, requirement_ids: [], question_id: null, custom_question_text: null } } });
    getSession.mockResolvedValue({ data: { session: { access_token: "user-token" } } });
    confirmAnswerRevision.mockResolvedValue({ answer_revision_id: "revision-1", analysis_job_id: "analysis-1", practice_session_id: "session-1", question_id: "preset-04", job_snapshot_id: "snapshot-1", answer_segments: [] });
    requestCoaching.mockResolvedValue({ status: "ok", job_alignment: [], intent_assessment: { label: "aligned", reason: "질문에 맞아요" }, criterion_assessments: [], evidence: [], gaps: [], clarifying_question: null, next_actions: [], example_answer: "테스트로 결과를 확인했습니다." });

    getNcsBackendCompetencies.mockResolvedValue({ job_name: "응용SW엔지니어링", source_url: "https://www.data.go.kr/data/15128213/openapi.do", options: [] });
    listJobPostings.mockResolvedValue([{
      id: "job-1",
      company: "가상 회사",
      title: "연습용 백엔드 공고",
      source_url: "https://example.invalid/job",
      captured_at: "2026-09-17T00:00:00Z",
      data_origin: "demo",
      requirements: [{ id: "req-1", code: "R1", text: "API 오류 분석", source_excerpt: null, display_order: 1 }],
    }]);
    createPracticeSession.mockResolvedValue({ practice_session_id: "session-1" });
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ job_id: "analysis-1", practice_session_id: "session-1" }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        status: "completed",
        progress: { stage: "결과를 정리하고 있어요", percent: 95 },
        practice_session_id: "session-1",
        result: { text: "API 오류 원인을 분석하고 해결했습니다." },
        delivery: { metrics: { cpm: 280, long_silences: [], repetitions: [] }, feedback: [] },
      }), { status: 200 })));
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("분석 완료 후에도 원래 대화를 유지한 채 결과를 아래에 추가한다", async () => {
    vi.useFakeTimers();
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage isLoggedIn onLogin={vi.fn()} />
        </NavigationProvider>,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    await clickButton("연습용 백엔드 공고");
    const requirement = container.querySelector<HTMLInputElement>('input[type="checkbox"]');
    await act(async () => requirement?.click());
    await clickButton("질문 선택으로 이동");
    await clickButton("기본 질문");
    await clickButton("프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?");

    const wavInput = container.querySelector<HTMLInputElement>(".coach-upload-input");
    const wavFile = new File(["wav"], "answer.wav", { type: "audio/wav" });
    Object.defineProperty(wavInput, "files", { configurable: true, value: [wavFile] });
    await act(async () => {
      wavInput?.dispatchEvent(new Event("change", { bubbles: true }));
      await Promise.resolve();
      await Promise.resolve();
    });
    await clickButton("분석 시작");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(container.querySelector(".coach-typing-message")?.textContent).toContain("보낸 답변을 분석하고 있어요.");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(450);
    });

    expect(container.querySelector(".flow-page")).toBeNull();
    expect(container.textContent).toContain("안녕하세요. 지원할 공고와 연결할 요구사항을 먼저 정해볼게요.");
    expect(container.textContent).toContain("연습용 백엔드 공고");
    expect(container.textContent).toContain("WAV 파일을 보냈어요.");
    expect(container.textContent).toContain("1차 분석 결과");
    expect(container.querySelector(".coach-result-message")).not.toBeNull();
    await clickButton("이 전사문으로 확정하기");
    await clickButton("코칭 시작");
    const thread = container.querySelector<HTMLDivElement>(".coach-thread")!;
    const scrollTo = vi.fn();
    Object.defineProperties(thread, {
      scrollTo: { configurable: true, value: scrollTo },
      scrollHeight: { configurable: true, get: () => container.querySelector(".coach-recording-message") ? 2400 : 1800 },
    });
    thread.dataset.historyBrowsing = "true";
    thread.dispatchEvent(new Event("workspace-browse"));
    expect(container.textContent).toContain("궁금한 점은 채팅으로");
    const chat = container.querySelector<HTMLInputElement>("#coach-chat-input")!;
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(chat, "재답변하기");
      chat.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await act(async () => { chat.closest("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })); });
    expect(container.querySelector(".coach-recording-message")).not.toBeNull();
    expect(thread.dataset.historyBrowsing).toBeUndefined();
    expect(scrollTo).toHaveBeenCalledWith({ top: 2400, behavior: "smooth" });
    await clickButton("공고 변경하기");
    expect(container.textContent).toContain("이전 채팅·녹음·코칭 내역은 삭제됩니다.");
    expect(container.querySelector(".coach-result-message")).not.toBeNull();
    sendPreparationMessage.mockResolvedValueOnce({ conversation_id: "conversation-1", status: "ok", action: "stay", message: "변경 취소", follow_up_question: null });
    await clickButton("취소");
    expect(container.querySelector(".coach-result-message")).not.toBeNull();
    await clickButton("공고 변경하기");
    sendPreparationMessage.mockRejectedValueOnce(new Error("초기화 실패"));
    await clickButton("확인하고 변경");
    expect(container.querySelector(".coach-result-message")).not.toBeNull();
    await clickButton("공고 변경하기");
    const proposal = sendPreparationMessage.mock.results.at(-1)!;
    const pending = await proposal.value;
    sendPreparationMessage.mockResolvedValueOnce({ ...pending, conversation_id: "new-conversation", action: "practice_restarted", execution_result: "verified", message: "새 연습" });
    await clickButton("확인하고 변경");
    expect(sendPreparationMessage.mock.calls.at(-1)?.[1].restart_confirmation).toEqual({ token: "token-1", confirm: true });
    expect(container.querySelector(".coach-result-message")).toBeNull();
    expect(container.querySelector(".coach-audio-message")).toBeNull();
    expect(container.querySelector(".workspace-timeline")?.textContent).not.toContain("1차");
    expect(container.querySelectorAll(".workspace-evidence-card--answer")).toHaveLength(0);
    expect(container.querySelectorAll(".workspace-evidence-card--check")).toHaveLength(0);
  });

  it("2차 WAV 답변 뒤에는 비교 분석 중인 코치 말풍선을 이어서 표시한다", async () => {
    vi.useFakeTimers();
    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <PracticePage
            isLoggedIn
            onLogin={vi.fn()}
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
    const thread = container.querySelector<HTMLDivElement>(".coach-thread")!;
    const scrollTo = vi.fn();
    Object.defineProperties(thread, {
      scrollTo: { configurable: true, value: scrollTo },
      scrollHeight: { configurable: true, value: 2400 },
    });
    thread.dataset.historyBrowsing = "true";
    thread.dispatchEvent(new Event("workspace-browse"));
    await clickButton("분석 시작");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(thread.dataset.historyBrowsing).toBeUndefined();
    expect(scrollTo).toHaveBeenCalledWith(expect.objectContaining({ top: 2400 }));
    expect(container.textContent).toContain("나 · 2차 답변");
    expect(container.querySelector(".coach-typing-message")?.textContent)
      .toContain("결과를 정리하고 있어요");

    const secondRecording = Array.from(container.querySelectorAll<HTMLButtonElement>(".coach-followup-menu button"))
      .find((button) => button.textContent?.includes("2차 녹음"));
    expect(secondRecording?.className).toContain("is-current");
    expect(secondRecording?.textContent).toContain("2차 답변을 녹음하고 있어요");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(450);
    });

    expect(secondRecording?.className).toContain("is-complete");
    expect(secondRecording?.textContent).toContain("✓");
    expect(secondRecording?.textContent).toContain("2차 답변 녹음 완료");
  });

  async function clickButton(label: string) {
    const button = Array.from(container.querySelectorAll<HTMLButtonElement>("button"))
      .find((candidate) => candidate.textContent?.includes(label));
    expect(button).not.toBeUndefined();
    await act(async () => button?.click());
  }
});
