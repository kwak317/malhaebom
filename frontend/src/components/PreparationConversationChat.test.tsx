import { act } from "react";
import { PreparationSelectionConflict } from "../api/preparationConversation";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PreparationConversationChat, usePreparationConversation } from "./PreparationConversationChat";

const send = vi.fn();
const bind = vi.fn();
const confirmed = vi.fn();
const onRerecord = vi.fn();
const onSelection = vi.fn();
vi.mock("../api/preparationConversation", async (importOriginal) => ({ ...await importOriginal<typeof import("../api/preparationConversation")>(), sendPreparationMessage: (...args: unknown[]) => send(...args), bindPreparationConversation: (...args: unknown[]) => bind(...args), getConfirmedPreparationExperiences: (...args: unknown[]) => confirmed(...args) }));
vi.mock("../api/supabaseAuth", () => ({ supabase: () => ({ auth: { getSession: async () => ({ data: { session: { access_token: "fixture" } } }) } }) }));
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function Harness({ generation = 0 }: { generation?: number }) {
  const chat = usePreparationConversation(true, generation);
  return <><button onClick={() => void chat.send("왜 이렇게 평가했어?", "first_coaching", "session-1", { selected_ncs_ids: [], readme_analysis: null, resume_profile: null }, onRerecord, "first_coaching", undefined, onSelection)}>질문</button>
    <button onClick={() => chat.appendUserMessage("다음으로", "ncs", "ncs_review")}>다음</button>
    <button onClick={() => void chat.bind("session-1", "fixture")}>연결</button>
    <span data-testid="confirmed">{chat.confirmedExperiences.map((item) => item.facts.map((fact) => fact.value).join(", ")).join("; ")}</span><PreparationConversationChat turns={chat.turns} /></>;
}

describe("준비 대화 표시·세션 연결", () => {
  let root: Root;
  let container: HTMLDivElement;
  beforeEach(async () => {
    container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
    confirmed.mockResolvedValue([]);
    send.mockResolvedValue({ conversation_id: "conversation-1", status: "ok", action: "stay", message: "원래 답변에 결과 확인 설명이 부족해요.", follow_up_question: null });
    await act(async () => root.render(<Harness />));
  });
  it("다음 명령은 사용자 말풍선만 남기고 API를 호출하지 않으며 초기화하면 지운다", async () => {
    await click("다음");
    expect(container.querySelector(".coach-message-user p")?.textContent).toBe("다음으로");
    expect(container.querySelector(".coach-message-assistant")).toBeNull();
    expect(send).not.toHaveBeenCalled();
    expect(confirmed).not.toHaveBeenCalled();
    await act(async () => root.render(<Harness generation={1} />));
    expect(container.querySelector(".coach-message-user")).toBeNull();
  });
  it("확인 질문을 본문과 구분해 굵게 표시한다", async () => {
    await act(async () => root.render(<PreparationConversationChat turns={[{ requestId: "follow-up", stage: "resume", placement: "resume_review", userMessage: "Redis 캐시 경험을 정리해줘", response: { conversation_id: "test", status: "ok", action: "stay", message: "Redis 캐시 적용 경험으로 이해했어요.", follow_up_question: "직접 수행하셨나요?" } }]} />));
    expect(container.querySelector(".preparation-follow-up strong")?.textContent).toBe("직접 수행하셨나요?");
  });
  it("응답 대기 중에는 변경 확인 버튼을 표시하지 않는다", async () => {
    await act(async () => root.render(<PreparationConversationChat turns={[{ requestId: "pending", stage: "readme", placement: "readme", userMessage: "리드미 교체해줘" }]} onConfirm={vi.fn()} />));
    expect(container.textContent).not.toContain("확인하고 변경");
  });
  it("서버에서 확인 후 저장한 경험을 조회하고 새 연습에서는 지운다", async () => {
    confirmed.mockResolvedValue([{ id: "draft-1", source_type: "user_chat", user_confirmed: true, facts: [{ kind: "action", value: "Redis 캐시 적용 및 API 응답 시간 비교", source_excerpt: "Redis 캐시를 적용했어요.", source_message_id: "message-1" }] }]);
    await click("질문");
    expect(confirmed).toHaveBeenCalledWith("fixture", "conversation-1");
    expect(container.querySelector('[data-testid="confirmed"]')?.textContent).toContain("Redis 캐시 적용");
    await act(async () => root.render(<Harness generation={1} />));
    expect(container.querySelector('[data-testid="confirmed"]')?.textContent).toBe("");
  });
  afterEach(async () => { await act(async () => root.unmount()); container.remove(); vi.clearAllMocks(); });
  async function click(label: string) { await act(async () => { Array.from(container.querySelectorAll("button")).find((b) => b.textContent === label)?.click(); await Promise.resolve(); }); }

  it("코칭 질문의 답변을 표시하고 자동 재답변은 시작하지 않는다", async () => {
    await click("질문");
    expect(container.textContent).toContain("원래 답변에 결과 확인 설명이 부족해요.");
    expect(send.mock.calls[0][1]).toMatchObject({ current_stage: "first_coaching", practice_session_id: "session-1" });
    expect(onRerecord).not.toHaveBeenCalled();
  });
  it("명시적인 재답변 action을 받으면 입력 화면을 연다", async () => {
    send.mockResolvedValueOnce({ conversation_id: "conversation-1", status: "ok", action: "request_rerecord", message: "재답변으로 이어갈게요.", follow_up_question: null });
    await click("질문"); expect(onRerecord).toHaveBeenCalledOnce();
  });
  it("저장된 준비 대화를 세션에 연결한다", async () => {
    await click("질문"); await click("연결");
    expect(bind).toHaveBeenCalledWith("fixture", "conversation-1", "session-1");
  });
  it("응답 실패는 오류로 표시하고 진행하지 않는다", async () => {
    send.mockRejectedValueOnce(new Error("저장 실패")); await click("질문");
    expect(container.textContent).toContain("저장 실패"); expect(onRerecord).not.toHaveBeenCalled();
  });
  it("연습 초기화 후 늦은 응답은 표시하거나 실행하지 않는다", async () => {
    let resolve: (value: object) => void = () => {};
    send.mockImplementationOnce(() => new Promise((done) => { resolve = done; }));
    await click("질문"); await act(async () => root.render(<Harness generation={1} />));
    await act(async () => resolve({ conversation_id: "old", status: "ok", action: "request_rerecord", message: "오래된 응답", follow_up_question: null }));
    expect(container.textContent).not.toContain("오래된 응답"); expect(onRerecord).not.toHaveBeenCalled();
  });
  const selected = { job_posting_id: null, requirement_ids: [], question_id: null, custom_question_text: null, selected_ncs_ids: ["skill-server"] };
  it("선택 충돌은 최신 서버 선택으로 복구하고 다음 요청에서 새 버전을 쓴다", async () => {
    send.mockRejectedValueOnce(new PreparationSelectionConflict("선택이 바뀌었어요. 다시 요청해 주세요.", selected, 3, null));
    await click("질문");
    expect(onSelection).toHaveBeenCalledWith(selected, null);
    expect(container.textContent).toContain("선택이 바뀌었어요");
    await click("질문");
    expect(send.mock.calls[1][1].selection_revision).toBe(3);
  });
  it("서버 검증 완료한 선택 변경만 적용한다", async () => {
    send.mockResolvedValueOnce({ conversation_id: "conversation-1", status: "ok", action: "selection_updated", message: "선택 변경 확인", follow_up_question: null,
      execution_result: "verified", selection_state: selected, selection_revision: 1 });
    await click("질문");
    expect(onSelection).toHaveBeenCalledWith(selected, undefined);
    await click("질문");
    expect(send.mock.calls[1][1].selection_revision).toBe(1);
  });
  it("일반 설명과 미확인·실패 응답은 화면 선택을 바꾸지 않는다", async () => {
    for (const extra of [{ action: "stay", execution_result: "verified" },
                         { action: "selection_updated", execution_result: "awaiting_confirmation" },
                         { action: "selection_updated", execution_result: "failed", status: "unavailable" }]) {
      send.mockResolvedValueOnce({ conversation_id: "conversation-1", status: "ok", message: "응답", follow_up_question: null,
        selection_state: selected, selection_revision: 1, ...extra });
      await click("질문");
    }
    expect(onSelection).not.toHaveBeenCalled();
  });
  it("낮은 선택 버전은 적용하거나 다음 요청 버전으로 사용하지 않는다", async () => {
    const response = { conversation_id: "conversation-1", status: "ok", action: "selection_updated", message: "응답", follow_up_question: null,
      execution_result: "verified", selection_state: selected };
    send.mockResolvedValueOnce({ ...response, selection_revision: 5 }); await click("질문");
    send.mockResolvedValueOnce({ ...response, selection_revision: 2 }); await click("질문");
    await click("질문");
    expect(onSelection).toHaveBeenCalledOnce();
    expect(send.mock.calls[2][1].selection_revision).toBe(5);
  });
  it("화면에서 더 최신 선택을 했다면 적용 보류 안내를 표시한다", async () => {
    onSelection.mockReturnValueOnce(false);
    send.mockResolvedValueOnce({ conversation_id: "conversation-1", status: "ok", action: "selection_updated", message: "변경 완료", follow_up_question: null,
      execution_result: "verified", selection_state: selected, selection_revision: 1 });
    await click("질문");
    expect(container.textContent).toContain("화면 선택이 그 사이 바뀌었어요");
  });
  it("초기화 후 늦은 선택 응답은 적용하지 않는다", async () => {
    let resolve: (value: object) => void = () => {};
    send.mockImplementationOnce(() => new Promise((done) => { resolve = done; }));
    await click("질문"); await act(async () => root.render(<Harness generation={1} />));
    await act(async () => resolve({ conversation_id: "old", status: "ok", action: "selection_updated", message: "오래된 응답", follow_up_question: null,
      execution_result: "verified", selection_state: selected, selection_revision: 1 }));
    expect(onSelection).not.toHaveBeenCalled();
  });

});
