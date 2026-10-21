/* @vitest-environment jsdom */

import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  deleteAll: vi.fn(),
  deleteOne: vi.fn(),
  fetchAll: vi.fn(),
  fetchOne: vi.fn(),
}));

vi.mock("../api/practiceHistory", () => ({
  deleteAllPracticeRecords: api.deleteAll,
  deletePracticeRecord: api.deleteOne,
  fetchPracticeRecord: api.fetchOne,
  fetchPracticeRecords: api.fetchAll,
}));

vi.mock("../api/supabaseAuth", () => ({
  supabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "access-token" } }, error: null }),
    },
  }),
}));

import { NavigationProvider } from "../navigation";
import HistoryPage from "./HistoryPage";
import HistoryResultPage from "./HistoryResultPage";
import type { PracticeHistoryItem } from "../services/practiceHistoryMapper";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const record = {
  practice_session_id: "session-1",
  question_type: "preset" as const,
  question_id: "preset-01",
  custom_question_text: null,
  practiced_at: "2026-08-24T10:00:00+09:00",
  attempts: [
    { attempt_no: 1 as const, job_id: "job-1", transcript: "첫 답변", metrics: { cpm: 330, long_silence_count: 1, repetition_count: 0 }, feedback: [] },
  ],
};

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.clearAllMocks();
});

function buttonByText(text: string): HTMLButtonElement {
  const button = [...(container?.querySelectorAll("button") ?? [])].find((element) => element.textContent === text);
  if (!(button instanceof HTMLButtonElement)) throw new Error(`${text} 버튼을 찾을 수 없습니다.`);
  return button;
}

function HistoryFlow({ onView }: { onView: (item: PracticeHistoryItem) => void }) {
  const [selected, setSelected] = useState<PracticeHistoryItem | null>(null);
  return <NavigationProvider active="history" isLoggedIn navigate={() => undefined} logout={() => undefined}>
    {selected
      ? <HistoryResultPage item={selected} onDetail={() => undefined} onBack={() => setSelected(null)} />
      : <HistoryPage isLoggedIn onLogin={() => undefined} onStartPractice={() => undefined} onView={(item) => { onView(item); setSelected(item); }} />}
  </NavigationProvider>;
}

describe("HistoryPage", () => {
  it("결과 보기로 들어가야 비교와 꼬리질문을 펼칠 수 있다", async () => {
    const comparison = {
      ...record,
      attempts: [...record.attempts, { ...record.attempts[0], attempt_no: 2 as const, job_id: "job-2", transcript: "둘째 답변" }],
      interview_chat: { conversation_id: "chat-1", completed_at: record.practiced_at, messages: [
        { role: "assistant" as const, message: "로그를 확인했군요.", follow_up_question: "결과는 어떻게 검증했나요?", summary: null },
        { role: "user" as const, message: "같은 조건으로 반복했습니다.", follow_up_question: null, summary: null },
        { role: "assistant" as const, message: "검증 조건을 정리했어요.", follow_up_question: null, summary: { clarified_points: ["같은 조건의 반복 검증"], next_practice: ["검증 결과를 설명해 보세요."] } },
      ] },
    };
    api.fetchAll.mockResolvedValue([comparison, { ...record, practice_session_id: "first-only" }]);
    api.fetchOne.mockResolvedValue(comparison);
    const onView = vi.fn();
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    await act(async () => {
      root?.render(<HistoryFlow onView={onView} />);
    });
    expect(container.querySelectorAll("details")).toHaveLength(0);
    expect(container.textContent).not.toContain("둘째 답변");
    expect(container.textContent).not.toContain("같은 조건으로 반복했습니다.");
    expect(api.fetchOne).not.toHaveBeenCalled();
    await act(async () => { buttonByText("결과 보기→").click(); });
    expect(onView).toHaveBeenCalledWith(expect.objectContaining({ interviewChat: comparison.interview_chat }));
    expect(api.fetchOne).toHaveBeenCalledOnce();
    const folds = [...container.querySelectorAll<HTMLDetailsElement>("details.history-fold")];
    expect(folds).toHaveLength(3);
    expect(folds.every((fold) => !fold.open)).toBe(true);
    const comparisonFold = folds[0];
    const chatFold = folds[1];
    await act(async () => { comparisonFold.querySelector("summary")!.click(); });
    expect(comparisonFold.open).toBe(true);
    expect(chatFold.open).toBe(false);
    expect(comparisonFold.textContent).toContain("둘째 답변");
    await act(async () => { chatFold.querySelector("summary")!.click(); });
    expect(chatFold.open).toBe(true);
    expect(chatFold.textContent).toContain("같은 조건으로 반복했습니다.");
    expect(chatFold.textContent).toContain("검증 결과를 설명해 보세요.");
    await act(async () => { comparisonFold.querySelector("summary")!.click(); });
    expect(comparisonFold.open).toBe(false);
    expect(chatFold.open).toBe(true);
    await act(async () => { buttonByText("연습 기록으로 돌아가기").click(); });
    expect(container.querySelectorAll("details")).toHaveLength(0);
    expect(container.textContent).not.toContain("같은 조건으로 반복했습니다.");
  });

  it("개별 삭제가 실패하면 다시 시도로 같은 삭제 요청을 재전송한다", async () => {
    api.fetchAll.mockResolvedValue([record]);
    api.deleteOne.mockRejectedValueOnce(new Error("storage failed")).mockResolvedValueOnce(undefined);
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);

    await act(async () => {
      root?.render(
        <NavigationProvider active="history" isLoggedIn navigate={() => undefined} logout={() => undefined}>
          <HistoryPage isLoggedIn onLogin={() => undefined} onStartPractice={() => undefined} onView={() => undefined} />
        </NavigationProvider>,
      );
      await Promise.resolve();
    });
    await act(async () => { buttonByText("삭제").click(); });
    await act(async () => {
      buttonByText("삭제하기").click();
      await Promise.resolve();
    });

    await act(async () => {
      buttonByText("다시 시도").click();
      await Promise.resolve();
    });

    expect(api.deleteOne).toHaveBeenCalledTimes(2);
    expect(container.textContent).toContain("아직 연습 기록이 없어요.");
  });
});
