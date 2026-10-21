/* @vitest-environment jsdom */
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NavigationProvider } from "../navigation";
import type { PracticeHistoryItem } from "../services/practiceHistoryMapper";
const fetchHistory = vi.hoisted(() => vi.fn());
vi.mock("../api/practiceHistory", () => ({ fetchPreparationChatHistory: fetchHistory }));
vi.mock("../api/supabaseAuth", () => ({ supabase: () => ({ auth: { getSession: async () => ({ data: { session: { access_token: "token" } } }) } }) }));
import HistoryDetailPage from "./HistoryDetailPage";
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const item: PracticeHistoryItem = { id: "session-1", question: "문제를 어떻게 해결했나요?", practicedAt: "2026.10.07", status: "2차 연습 완료", resultType: "comparison", attempt1Transcript: "첫 답변", attempt1Metrics: { speakingRate: 300, longSilence: 0, repeatedExpressions: 0 }, feedback: [] };
let root: Root; let container: HTMLDivElement;
beforeEach(() => { container = document.createElement("div"); document.body.append(container); root = createRoot(container); fetchHistory.mockReset(); });
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });
async function render() { await act(async () => { root.render(<NavigationProvider active="history" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><HistoryDetailPage item={item} onBack={vi.fn()} /></NavigationProvider>); }); }
describe("채팅 내역", () => {
  it("연습의 자유질문과 경력 추가 확인 대화를 순서대로 보여준다", async () => {
    fetchHistory.mockResolvedValue([{ role: "user", message: "Redis 캐시 구현 경험을 추가할게요.", follow_up_question: null }, { role: "assistant", message: "정리한 경험을 반영할까요?", follow_up_question: "내용이 맞나요?" }]);
    await render(); expect(fetchHistory).toHaveBeenCalledWith("session-1", "token");
    const messages = container.querySelectorAll(".history-chat-message"); expect(messages).toHaveLength(2);
    expect(messages[0].textContent).toContain("Redis 캐시"); expect(messages[1].textContent).toContain("내용이 맞나요?");
    expect(container.textContent).not.toContain("1·2차 답변 비교");
  });
  it("저장 대화 없는 예전 기록은 빈 상태를 보여준다", async () => {
    fetchHistory.mockResolvedValue([]); await render(); expect(container.textContent).toContain("저장된 채팅 내역이 없어요.");
  });
  it("조회 실패를 빈 기록으로 표시하지 않고 재시도한다", async () => {
    fetchHistory.mockRejectedValueOnce(new Error()).mockResolvedValueOnce([]); await render(); expect(container.querySelector('[role="alert"]')).not.toBeNull();
    await act(async () => { container.querySelector<HTMLButtonElement>('[role="alert"] button')?.click(); });
    expect(fetchHistory).toHaveBeenCalledTimes(2); expect(container.textContent).toContain("저장된 채팅 내역이 없어요.");
  });
});
