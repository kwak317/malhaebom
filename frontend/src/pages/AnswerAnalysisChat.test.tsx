import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AnswerAnalysisChat } from "./AnalysisPage";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

const getSession = vi.fn();

vi.mock("../api/supabaseAuth", () => ({
  supabase: () => ({ auth: { getSession } }),
}));

describe("답변 분석 채팅", () => {
  let root: Root;
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    getSession.mockImplementation(() => new Promise(() => undefined));
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    vi.clearAllMocks();
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("별도 분석 화면 대신 기존 연습 채팅 안에서 입력 중 말풍선을 보여준다", async () => {
    await act(async () => {
      root.render(
        <div className="practice-page"><div className="coach-thread"><AnswerAnalysisChat
          isLoggedIn
          onLogin={vi.fn()}
          onBack={vi.fn()}
          onComplete={vi.fn()}
          question={{
            questionType: "preset",
            question: "프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?",
            questionId: "preset-04",
            practiceSessionId: "session-1",
          }}
          attemptNo={1}
          audio={new File(["audio"], "answer.wav", { type: "audio/wav" })}
          practiceSessionId="session-1"
        /></div></div>,
      );
      await Promise.resolve();
    });

    expect(container.querySelector(".practice-page")).not.toBeNull();
    expect(container.querySelector(".flow-page")).toBeNull();
    expect(container.textContent).toContain("WAV 파일을 보냈어요.");
    expect(container.textContent).toContain("보낸 답변을 분석하고 있어요.");
    expect(container.querySelector(".coach-typing-message")).not.toBeNull();
    expect(container.querySelector('img[alt="답변을 전사하는 말해봄 코치"]')).not.toBeNull();
  });
  it("부모 완료 콜백이 바뀌어도 분석을 재생성하지 않고 최신 콜백에 결과를 전달한다", async () => {
    vi.useFakeTimers();
    getSession.mockResolvedValue({ data: { session: { access_token: "test-token" } } });
    let completePoll: (response: Response) => void = () => undefined;
    const fetchMock = vi.fn((url: string, options?: RequestInit) => {
      if (options?.method === "POST") return Promise.resolve(new Response(JSON.stringify({ job_id: "job-1" }), { status: 202 }));
      return new Promise<Response>((resolve) => { completePoll = resolve; });
    });
    vi.stubGlobal("fetch", fetchMock);
    const question = { questionType: "preset" as const, question: "문제를 어떻게 해결했나요?", questionId: "preset-04", practiceSessionId: "session-1" };
    const audio = new File(["audio"], "answer.wav", { type: "audio/wav" });
    const firstCallback = vi.fn();
    const latestCallback = vi.fn();
    const render = (onComplete: typeof firstCallback) => root.render(<AnswerAnalysisChat
      isLoggedIn onLogin={vi.fn()} onBack={vi.fn()} onComplete={onComplete}
      question={question} audio={audio} attemptNo={1} practiceSessionId="session-1"
    />);
    await act(async () => render(firstCallback));
    await act(async () => render(latestCallback));
    expect(fetchMock.mock.calls.filter(([, options]) => options?.method === "POST")).toHaveLength(1);
    await act(async () => {
      completePoll(new Response(JSON.stringify({ status: "completed", result: { text: "확인한 답변" }, practice_session_id: "session-1" }), { status: 200 }));
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(firstCallback).not.toHaveBeenCalled();
    expect(latestCallback).toHaveBeenCalledTimes(1);
    expect(latestCallback).toHaveBeenCalledWith(expect.objectContaining({ transcript: "확인한 답변", analysisJobId: "job-1" }));
  });

});
