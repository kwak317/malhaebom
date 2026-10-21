import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NavigationProvider } from "../navigation";
import ResultPage, { CoachingChatMessages } from "./ResultPage";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

const getSession = vi.fn();
const confirmAnswerRevision = vi.fn();
const requestCoaching = vi.fn();
const normalizeTranscript = vi.fn();
vi.mock("../api/transcriptNormalization", () => ({ normalizeTranscript: (...args: unknown[]) => normalizeTranscript(...args) }));

vi.mock("../api/supabaseAuth", () => ({
  supabase: () => ({ auth: { getSession } }),
}));

vi.mock("../api/answerRevisions", () => ({
  confirmAnswerRevision: (...args: unknown[]) => confirmAnswerRevision(...args),
}));

vi.mock("../api/coaching", () => ({
  requestCoaching: (...args: unknown[]) => requestCoaching(...args),
}));

describe("ResultPage 전사·코칭 채팅 흐름", () => {
  let root: Root;
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    getSession.mockResolvedValue({ data: { session: { access_token: "user-token" } } });
    confirmAnswerRevision.mockResolvedValue({
      answer_revision_id: "revision-1",
      analysis_job_id: "analysis-1",
      practice_session_id: "session-1",
      question_id: "preset-04",
      answer_segments: [{ segment_id: "segment-1", text: "전사문" }],
      confirmed_at: "2026-09-22T00:00:00Z",
      expires_at: "2026-09-23T00:00:00Z",
      job_snapshot_id: "snapshot-1",
    });
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  const renderNormalization = async (attemptNo: 1 | 2 = 1, comparisonOnly = false) => {
    await act(async () => root.render(<CoachingChatMessages comparisonOnly={comparisonOnly}
      question={{ questionType: "preset", question: "질문", questionId: "preset-04" }}
      result={{ attemptNo, analysisJobId: "analysis-1", prosodyReferenceAvailable: true, transcript: "서버가 딸리나 싶었는데 까보니", speakingRate: 300, longSilence: 0, repeatedExpressions: 0, feedback: [], referenceMetrics: { pace: { value: 320 }, longSilenceCount: { value: 2 }, repetitionCount: { value: 1 } }, contentFeedback: { text: "" } }}
      stepLabel="1차" nextLabel="다음" onNext={vi.fn()} />));
  };

  it.each([1, 2] as const)("%i차 전사문 확정 버튼은 즉시 하단 이동을 요청하고 완료 스크롤 상태를 해제한다", async (attemptNo) => {
    container.classList.add("coach-thread");
    const scrollRequest = vi.fn();
    container.addEventListener("workspace-next-stage", scrollRequest);
    normalizeTranscript.mockResolvedValueOnce({ transcript: "정리한 답변", edit_log: [], confirmations: [], meaning_preservation_check: "확인" });
    await renderNormalization(attemptNo);
    await clickButton(container, "표준어로 변경하기");
    expect(container.querySelector(".coach-transcript-normalized-result, .coach-transcript-second-completed")).not.toBeNull();
    scrollRequest.mockClear();
    confirmAnswerRevision.mockImplementationOnce(() => new Promise(() => undefined));
    await clickButton(container, "이 전사문으로 확정하기");
    expect(scrollRequest).toHaveBeenCalledTimes(1);
    expect(container.querySelector(".coach-transcript-normalized-result, .coach-transcript-second-completed")).toBeNull();
    expect(confirmAnswerRevision).toHaveBeenCalled();
  });

  it.each([[2, false], [1, true]] as const)("2차 변환 완료는 API attempt=%i, 비교 단계=%s에서도 직접 결과 상단 이동을 요청한다", async (attemptNo, comparisonOnly) => {
    container.classList.add("coach-thread");
    const scrollRequest = vi.fn();
    container.addEventListener("workspace-transcript-result", scrollRequest);
    let finish: ((value: object) => void) | undefined;
    normalizeTranscript.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
    await renderNormalization(attemptNo, comparisonOnly);
    await clickButton(container, "표준어로 변경하기");
    expect(container.querySelector(".coach-transcript-second-loading")).not.toBeNull();
    scrollRequest.mockClear();
    finish?.({ transcript: "2차 변환 결과", edit_log: [], confirmations: [], meaning_preservation_check: "확인" });
    await act(async () => { await Promise.resolve(); });
    expect(container.querySelector(".coach-transcript-normalized-result")).not.toBeNull();
    expect(scrollRequest).toHaveBeenCalledTimes(1);
  });

  it("코칭 시작 버튼은 즉시 하단 이동을 요청한다", async () => {
    container.classList.add("coach-thread");
    const scrollRequest = vi.fn();
    container.addEventListener("workspace-next-stage", scrollRequest);
    await renderNormalization();
    await clickButton(container, "이 전사문으로 확정하기");
    scrollRequest.mockClear();
    requestCoaching.mockImplementationOnce(() => new Promise(() => undefined));
    await clickButton(container, "코칭 시작");
    expect(scrollRequest).toHaveBeenCalledTimes(1);
    expect(requestCoaching).toHaveBeenCalled();
  });

  it("표준어 변환 중 편집·확정을 막고 추정 수정과 원문을 표시한다", async () => {
    let finish: ((value: object) => void) | undefined;
    normalizeTranscript.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
    await renderNormalization();
    await clickButton(container, "표준어로 변경하기");
    expect((container.querySelector("textarea") as HTMLTextAreaElement).disabled).toBe(true);
    expect(Array.from(container.querySelectorAll("button")).find(b => b.textContent === "이 전사문으로 확정하기")?.disabled).toBe(true);
    expect(confirmAnswerRevision).not.toHaveBeenCalled();
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(container.querySelector('.transcript-loading[role="status"]')).not.toBeNull();
    expect(container.querySelector(".coach-transcript-normalized-result")).toBeNull();
    finish?.({ transcript: "서버 성능이 부족한 줄 알았는데 확인해 보니", edit_log: [], confirmations: [{ original: "딸리나", replacement: "부족한", reason: "확인 필요", applied: true }], meaning_preservation_check: "의미 확인", prompt_name: "test", prompt_version: 1, trace_id: "t" });
    await act(async () => { await Promise.resolve(); });
    expect((container.querySelector("textarea") as HTMLTextAreaElement).value).toBe("서버 성능이 부족한 줄 알았는데 확인해 보니");
    expect(container.querySelector(".transcript-loading")).toBeNull();
    expect(container.querySelector(".coach-transcript-normalized-result")).not.toBeNull();
    expect(container.querySelector('[aria-busy="true"]')).toBeNull();
    expect(container.textContent).toContain("추정한 표현 1개");
    expect(container.textContent).toContain("STT 원문 보기");
    expect(container.textContent).toContain("서버가 딸리나 싶었는데 까보니");
  });

  it("진행 단계와 예상 시간을 갱신하고 초과 시 완료로 오해시키지 않는다", async () => {
    vi.useFakeTimers();
    normalizeTranscript.mockImplementationOnce(() => new Promise(() => undefined));
    await renderNormalization();
    await clickButton(container, "표준어로 변경하기");
    expect(container.textContent).toContain("예상 남은 시간 약 35초");
    await act(async () => {
      window.dispatchEvent(new CustomEvent("coach-request-progress", { detail: { path: "/analysis-jobs/analysis-1/normalize-transcript", stage: "원문 의미와 수정 내역을 검토하고 있어요…" } }));
      vi.advanceTimersByTime(10000);
    });
    expect(container.textContent).toContain("예상 남은 시간 약 25초");
    expect(container.textContent).toContain("경과 10초");
    expect(container.querySelector('.coach-loading-progress .is-current')?.textContent).toContain("원문 의미와 수정 내역");
    await act(async () => { vi.advanceTimersByTime(30000); });
    expect(container.textContent).toContain("예상보다 오래 걸리고 있어요");
    expect(container.textContent).toContain("경과 40초");
    expect((container.querySelector("textarea") as HTMLTextAreaElement).disabled).toBe(true);
  });

  it("변환 실패 시 원문과 재시도 버튼을 유지한다", async () => {
    normalizeTranscript.mockRejectedValueOnce(new Error("변환 실패"));
    await renderNormalization();
    await clickButton(container, "표준어로 변경하기");
    await act(async () => { await Promise.resolve(); });
    expect((container.querySelector("textarea") as HTMLTextAreaElement).value).toBe("서버가 딸리나 싶었는데 까보니");
    expect(container.textContent).toContain("변환 실패");
    expect((container.querySelector("textarea") as HTMLTextAreaElement).disabled).toBe(false);
  });

  it("전사문을 확정한 뒤 입력 중 효과를 거쳐 코칭과 예시 답안을 표시한다", async () => {
    let resolveCoaching: ((value: object) => void) | undefined;
    const onCoachingReady = vi.fn();
    requestCoaching.mockImplementationOnce(() => new Promise((resolve) => {
      resolveCoaching = resolve;
    }));

    await act(async () => {
      root.render(
        <NavigationProvider active="practice" isLoggedIn navigate={vi.fn()} logout={vi.fn()}>
          <ResultPage
            question={{ questionType: "preset", question: "문제 해결 경험을 말씀해주세요.", questionId: "preset-04" }}
            result={{
              attemptNo: 1,
              analysisJobId: "analysis-1",
              practiceSessionId: "session-1",
              transcript: "문제를 확인하고 수정한 뒤 테스트했습니다.",
              answerDurationSec: 20,
              speakingRate: 300,
              longSilence: 0,
              repeatedExpressions: 0,
              feedback: [],
              prosodyReferenceAvailable: true,
              referenceMetrics: { pace: { value: 320 }, longSilenceCount: { value: 2.48 }, repetitionCount: { value: 0.41 } },
              contentFeedback: { text: "" },
            }}
            stepLabel="1차"
            nextLabel="재녹음 하기"
            onNext={vi.fn()}
            onCoachingReady={onCoachingReady}
          />
        </NavigationProvider>,
      );
    });

    await clickButton(container, "이 전사문으로 확정하기");
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    expect(confirmAnswerRevision).toHaveBeenCalledWith({
      analysisJobId: "analysis-1",
      confirmedText: "문제를 확인하고 수정한 뒤 테스트했습니다.",
      accessToken: "user-token",
    });
    expect(container.textContent).toContain("코칭 시작");

    await clickButton(container, "코칭 시작");
    await act(async () => { await Promise.resolve(); });
    expect(container.querySelector(".coach-typing-message")).not.toBeNull();
    expect(requestCoaching).toHaveBeenCalledWith({
      request: { action: "analyze", question_id: "preset-04", answer_revision_id: "revision-1", job_snapshot_id: "snapshot-1" },
      accessToken: "user-token",
    });

    resolveCoaching?.({
      status: "ok",
      job_alignment: [{ requirement_id: "req-1", label: "related", reason: "문제 해결 경험과 연결돼요." }],
      intent_assessment: { label: "aligned", reason: "질문 의도에 맞아요." },
      criterion_assessments: [{ criterion_id: "own_action", assessment: "met", reason: "수정 행동이 보여요.", needed: null }],
      evidence: [],
      gaps: [],
      clarifying_question: null,
      next_actions: [{ target_type: "criterion", target_id: "own_action", action: "수정 기준을 덧붙여 보세요." }],
      example_answer: "문제를 확인한 뒤 원인을 좁히고 수정과 테스트를 진행했습니다.",
    });
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });

    expect(container.textContent).toContain("코칭 적용 예시");
    expect(container.textContent).toContain("문제를 확인한 뒤 원인을 좁히고 수정과 테스트를 진행했습니다.");
    expect(container.textContent).toContain("말하기 속도");
    expect(container.textContent).toContain("나의 결과");
    expect(container.querySelector(".metric-track-list")).not.toBeNull();
    expect(onCoachingReady).toHaveBeenCalledOnce();
  });

  it("2차 답변은 비교용 분석을 저장한 뒤 코칭 결과 없이 비교 버튼을 표시한다", async () => {
    const onNext = vi.fn();
    let resolveComparison: ((value: object) => void) | undefined;
    requestCoaching.mockImplementationOnce(() => new Promise((resolve) => {
      resolveComparison = resolve;
    }));
    await act(async () => {
      root.render(
        <CoachingChatMessages
          question={{ questionType: "preset", question: "문제 해결 경험을 말씀해주세요.", questionId: "preset-04" }}
          result={{
            attemptNo: 2,
            analysisJobId: "analysis-2",
            practiceSessionId: "session-1",
            transcript: "원인을 좁힌 뒤 수정하고 재현 테스트로 결과를 확인했습니다.",
            answerDurationSec: 20,
            speakingRate: 300,
            longSilence: 0,
            repeatedExpressions: 0,
            feedback: [],
            prosodyReferenceAvailable: true,
            referenceMetrics: { pace: { value: 320 }, longSilenceCount: { value: 2.48 }, repetitionCount: { value: 0.41 } },
            contentFeedback: { text: "" },
          }}
          stepLabel="2차"
          nextLabel="1·2차 답변 비교하기"
          onNext={onNext}
          comparisonOnly
        />,
      );
    });

    await clickButton(container, "이 전사문으로 확정하기");
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });

    expect(container.textContent).toContain("1차 답변과 비교할 내용을 정리하고 있어요");
    expect(requestCoaching).toHaveBeenCalledWith({
      request: { action: "analyze", question_id: "preset-04", answer_revision_id: "revision-1", job_snapshot_id: "snapshot-1" },
      accessToken: "user-token",
    });

    resolveComparison?.({
      status: "ok",
      job_alignment: [],
      intent_assessment: { label: "aligned", reason: "비교 기준을 만들었어요." },
      criterion_assessments: [],
      evidence: [],
      gaps: [],
      clarifying_question: null,
      next_actions: [],
      example_answer: "화면에 노출하지 않는 비교용 예시입니다.",
    });
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });

    expect(container.textContent).toContain("1차 답변과 코칭 후 재답변의 변화를 비교해 볼까요?");
    expect(container.textContent).not.toContain("화면에 노출하지 않는 비교용 예시입니다.");
    await clickButton(container, "1·2차 답변 비교하기");
    expect(onNext).toHaveBeenCalledOnce();
  });
});

async function clickButton(container: HTMLElement, label: string) {
  const button = Array.from(container.querySelectorAll<HTMLButtonElement>("button"))
    .find((item) => item.textContent?.includes(label));
  if (!button) throw new Error(`${label} 버튼을 찾지 못했습니다.`);
  await act(async () => button.click());
}
