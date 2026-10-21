import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { PracticeHistoryItem } from "../services/practiceHistoryMapper";
import { NavigationProvider } from "../navigation";
const fetchHistory = vi.hoisted(() => vi.fn());
vi.mock("../api/practiceHistory", () => ({ fetchPreparationChatHistory: fetchHistory }));
vi.mock("../api/supabaseAuth", () => ({ supabase: () => ({ auth: { getSession: async () => ({ data: { session: { access_token: "test-token" } } }) } }) }));
import { HistoryExperienceChat } from "./HistoryExperienceChat";
import HistoryResultPage from "../pages/HistoryResultPage";
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root; let container: HTMLDivElement;
beforeEach(() => { container = document.createElement("div"); document.body.append(container); root = createRoot(container); fetchHistory.mockReset(); });
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });
async function render(sessionId = "session-1") { await act(async () => root.render(<HistoryExperienceChat sessionId={sessionId} />)); }
async function expand() { await act(async () => { const fold = container.querySelector("details")!; fold.open = true; fold.dispatchEvent(new Event("toggle")); }); }

describe("경력·경험 추가 대화", () => {
  it("펼칠 때 해당 연습의 대화를 가져와 발화와 확인 질문을 순서대로 표시한다", async () => {
    fetchHistory.mockResolvedValue([{role:"user",message:"Redis 캐시를 적용한 경험을 추가해줘",follow_up_question:null},{role:"assistant",message:"연습 참고정보 후보: Redis 캐시 적용",follow_up_question:"이 내용을 반영할까요?"},{role:"user",message:"ㅇㅇ",follow_up_question:null},{role:"assistant",message:"저장 완료",follow_up_question:null}]);
    await render(); expect(fetchHistory).not.toHaveBeenCalled(); await expand();
    expect(fetchHistory).toHaveBeenCalledWith("session-1", "test-token");
    const messages = container.querySelectorAll(".history-chat-message"); expect(messages).toHaveLength(4);
    expect(messages[0].textContent).toContain("Redis 캐시를 적용한 경험");
    expect(messages[1].textContent).toContain("이 내용을 반영할까요?");
    expect(messages[2].textContent).toContain("ㅇㅇ"); expect(messages[3].textContent).toContain("저장 완료");
  });
  it("대화가 없는 과거 기록은 빈 상태를 표시한다", async () => {
    fetchHistory.mockResolvedValue([]); await render(); await expand();
    expect(container.textContent).toContain("저장된 경력·경험 추가 및 준비 대화가 없어요.");
  });
  it("조회 오류를 빈 기록으로 표시하지 않고 재시도한다", async () => {
    fetchHistory.mockRejectedValueOnce(new Error()).mockResolvedValueOnce([]); await render(); await expand();
    expect(container.querySelector('[role="alert"]')).not.toBeNull();
    await act(async () => container.querySelector<HTMLButtonElement>('[role="alert"] button')!.click());
    expect(fetchHistory).toHaveBeenCalledTimes(2); expect(container.querySelector('[role="alert"]')).toBeNull();
  });
  it("다른 연습으로 바뀐 뒤 이전 요청의 응답이 도착해도 섞이지 않는다", async () => {
    let resolveOld!: (value: unknown[]) => void;
    fetchHistory.mockReturnValueOnce(new Promise(resolve => { resolveOld = resolve; })).mockResolvedValueOnce([{role:"user",message:"현재 연습의 경험",follow_up_question:null}]);
    await render(); await expand(); await render("session-2");
    await act(async () => resolveOld([{role:"user",message:"이전 연습의 경험",follow_up_question:null}]));
    expect(container.textContent).toContain("현재 연습의 경험"); expect(container.textContent).not.toContain("이전 연습의 경험");
  });
  it("연습 결과에서 꼬리질문 대화 바로 아래에 표시한다", async () => {
    const metrics = {speakingRate:300,longSilence:0,repeatedExpressions:0};
    const item: PracticeHistoryItem = {id:"session-1",question:"문제 해결 경험",practicedAt:"2026.10.10",status:"2차 연습 완료",resultType:"comparison",attempt1Transcript:"첫 답변",attempt2Transcript:"두 번째 답변",attempt1Metrics:metrics,attempt2Metrics:metrics,feedback:[]};
    await act(async () => root.render(<NavigationProvider active="history" isLoggedIn navigate={vi.fn()} logout={vi.fn()}><HistoryResultPage item={item} onBack={vi.fn()} onDetail={vi.fn()} /></NavigationProvider>));
    expect([...container.querySelectorAll('.history-result-folds summary')].map(node => node.textContent).slice(-2)).toEqual(['꼬리질문 대화','경력·경험 추가 대화']);
    expect(fetchHistory).not.toHaveBeenCalled();
  });
});
