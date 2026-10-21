import { act, StrictMode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { beforeEach, afterEach, describe, it, expect, vi } from "vitest";
import { InterviewFollowUpChat } from "./InterviewFollowUpChat";
import { InterviewChatApiError, type InterviewChatResponse } from "../api/interviewChat";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const requestChat = vi.fn();
const getSession = vi.fn();
vi.mock("../api/interviewChat", async () => ({ ...await vi.importActual("../api/interviewChat"), requestInterviewChat: (...args: unknown[]) => requestChat(...args) }));
vi.mock("../api/supabaseAuth", () => ({ supabase: () => ({ auth: { getSession } }) }));
const active = { conversation_id: "conversation-1", status: "active", message: "2차 답변에 연결해 연습해 봐요.", follow_up_question: "수정 결과를 어떻게 확인했나요?", summary: null };

describe("비교 후 면접 대화", () => {
  let root: Root;
  let container: HTMLDivElement;
  beforeEach(() => {
    container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
    getSession.mockResolvedValue({ data: { session: { access_token: "user-token" } }, error: null });
    requestChat.mockResolvedValue(active);
  });
  afterEach(async () => { await act(async () => root.unmount()); container.remove(); vi.clearAllMocks(); });
  const render = async () => { await act(async () => { root.render(<InterviewFollowUpChat practiceSessionId="session-1" />); }); };
  const click = async (text: string) => { const button = [...container.querySelectorAll("button")].find((b) => b.textContent?.includes(text)); expect(button).toBeDefined(); await act(async () => button!.click()); };
  const fill = async (text: string) => { const input = container.querySelector("input")!; await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input,text); input.dispatchEvent(new Event("input", { bubbles:true })); }); };

  it("이력서 화면의 종료 요청은 질문을 표시하지 않고 기존 종료 요약과 이동 버튼으로 연결한다", async () => {
    requestChat.mockResolvedValueOnce(active).mockResolvedValueOnce({...active,status:"finished",follow_up_question:null,summary:{clarified_points:["확인한 설명"],next_practice:["검증 과정 연습"]}});
    await act(async () => root.render(<InterviewFollowUpChat practiceSessionId="session-1" finishOnStart />));
    expect(requestChat).toHaveBeenLastCalledWith({action:"finish",request_id:expect.any(String),practice_session_id:"session-1",conversation_id:"conversation-1"},"user-token");
    expect(container.textContent).not.toContain(active.follow_up_question);
    expect(container.textContent).toContain("확인한 설명");
    expect(container.textContent).toContain("다시 면접하기");
    expect(container.textContent).toContain("홈으로 가기");
  });

  it("첫 질문 자동 시작, 답변과 자유 질문, 종료 요약을 같은 채팅에 표시한다", async () => {
    await render();
    expect(container.textContent).toContain(active.follow_up_question);
    expect(container.querySelector('.interview-followup-exit-actions')).toBeNull();
    expect(requestChat).toHaveBeenCalledWith({ action:"start",request_id:expect.any(String),practice_session_id:"session-1" },"user-token");
    requestChat.mockResolvedValue({ ...active, message:"같은 조건으로 확인했다는 설명을 추가했네요." });
    await fill("같은 조건으로 반복 테스트했어요."); await click("보내기");
    expect(container.textContent).toContain("같은 조건으로 반복 테스트했어요.");
    requestChat.mockResolvedValue({ ...active, message:"자기소개에도 활용할 수 있어요.",follow_up_question:null });
    await fill("이 경험을 자기소개에 써도 될까요?"); await click("보내기");
    expect(container.textContent).toContain("자기소개에도 활용할 수 있어요.");
    requestChat.mockResolvedValue({ ...active,status:"finished",follow_up_question:null,summary:{ clarified_points:["검증 조건을 정리했어요."],next_practice:["선택 이유를 연습해 보세요."] } });
    await click("연습 마치기");
    expect(container.textContent).toContain("검증 조건을 정리했어요.");
    expect(container.textContent).toContain("선택 이유를 연습해 보세요.");
    expect(container.querySelector("form")).toBeNull();
    const exitActions = container.querySelector('nav[aria-label="면접 연습 종료 후 이동"]')!;
    expect(exitActions.querySelector('a[href="/app/practice"]')?.textContent).toBe("다시 면접하기");
    expect(exitActions.querySelector('a[href="/app/"]')?.textContent).toBe("홈으로 가기");
    expect(exitActions.previousElementSibling?.textContent).toContain("면접 대화를 마쳤어요.");
    expect(requestChat.mock.calls.at(-1)![0]).toEqual({ action:"finish", request_id:expect.any(String), practice_session_id:"session-1",conversation_id:"conversation-1" });
  });

  it("연습 마치기의 대기 안내와 종료 요약이 표시될 때 채팅 맨 아래로 이동한다", async () => {
    await act(async () => root.render(<div className="coach-thread"><InterviewFollowUpChat practiceSessionId="session-1" /></div>));
    const thread = container.querySelector<HTMLDivElement>(".coach-thread")!;
    const scrollTo = vi.fn();
    const latest = vi.fn();
    thread.scrollTo = scrollTo;
    Object.defineProperty(thread, "scrollHeight", { configurable: true, get: () => thread.querySelector(".interview-followup-completion") ? 2400 : 1800 });
    thread.dataset.historyBrowsing = "manual";
    thread.addEventListener("workspace-latest", latest);
    let complete!: (response: InterviewChatResponse) => void;
    requestChat.mockImplementationOnce(() => new Promise((resolve) => { complete = resolve; }));
    await click("연습 마치기");
    const loading = thread.querySelector('[aria-label="연습 종료 정리 중"]')!;
    expect(loading.textContent).toContain("면접 연습 내용을 정리하고 있어요");
    expect(loading.querySelector("img")?.getAttribute("src")).toContain("coach-finishing.png");
    expect(loading.querySelector(".coach-loading-progress")).not.toBeNull();
    expect(thread.dataset.historyBrowsing).toBeUndefined();
    expect(latest).toHaveBeenCalled();
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 1800, behavior: "smooth" });
    await act(async () => complete({ ...active, status: "finished", follow_up_question: null }));
    expect(thread.querySelector(".interview-followup-completion")).not.toBeNull();
    expect(thread.querySelector('[aria-label="연습 종료 정리 중"]')).toBeNull();
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 2400, behavior: "smooth" });
  });

  it("StrictMode 재실행에도 첫 질문 요청은 한 번이다", async () => {
    await act(async () => root.render(<StrictMode><InterviewFollowUpChat practiceSessionId="session-1" /></StrictMode>));
    expect(requestChat).toHaveBeenCalledTimes(1);
    expect(container.textContent).toContain(active.follow_up_question);
  });

  it("start 409는 재시도 오류와 입력 폼 대신 대화 불가 상태를 안내한다", async () => {
    requestChat.mockRejectedValueOnce(new InterviewChatApiError("두 답변의 코칭을 먼저 완료해 주세요.", 409));
    await render();
    expect(container.textContent).toContain("현재 기록으로는 면접 대화를 이어갈 수 없어요.");
    expect(container.querySelector('[role="status"]')?.textContent).toContain("동일한 기준");
    expect(container.querySelector('[role="alert"]')).toBeNull();
    expect(container.querySelector("form")).toBeNull();
    expect(container.querySelectorAll("button")).toHaveLength(0);
    expect(requestChat).toHaveBeenCalledTimes(1);
  });

  it("진행 중 409는 기존 새 대화 복구를 유지한다", async () => {
    await render();
    requestChat.mockRejectedValueOnce(new InterviewChatApiError("답변이 변경되었습니다.", 409));
    await fill("결과를 확인했어요."); await click("보내기");
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("답변이 변경되었습니다.");
    expect(container.textContent).toContain("새 대화 시작");
    expect(container.textContent).not.toContain("현재 기록으로는 면접 대화를 이어갈 수 없어요.");
  });

  it("종료 요청 실패에는 이동 버튼 없이 재시도하고 성공 후 표시한다", async () => {
    await render();
    requestChat.mockRejectedValueOnce(new Error("종료 요청 실패"));
    await click("연습 마치기");
    expect(container.querySelector('.interview-followup-exit-actions')).toBeNull();
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("종료 요청 실패");
    requestChat.mockResolvedValue({ ...active, status: "finished", follow_up_question: null,
      summary: { clarified_points: [], next_practice: ["다음 답변을 연습해 보세요."] } });
    await click("다시 시도");
    expect(container.querySelectorAll('.interview-followup-exit-actions a')).toHaveLength(2);
  });

  it("실패한 메시지를 보존하고 재시도 시 사용자 말풍선을 중복하지 않는다", async () => {
    await render();
    requestChat.mockRejectedValueOnce(new Error("잠시 연결 실패"));
    await fill("서버 로그를 확인했어요."); await click("보내기");
    expect(container.querySelector("input")!.value).toBe("서버 로그를 확인했어요.");
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("잠시 연결 실패");
    const failedRequest = requestChat.mock.calls.at(-1)![0];
    await click("다시 시도");
    expect(requestChat.mock.calls.at(-1)![0]).toEqual(failedRequest);
    expect(container.querySelectorAll(".coach-message-user")).toHaveLength(1);
    expect(container.querySelector("input")!.value).toBe("");
  });

  it("서버의 대화가 사라지면 새 대화를 시작하고 이전 메시지를 보내지 않는다", async () => {
    await render();
    const firstRequest = requestChat.mock.calls[0][0];
    requestChat.mockRejectedValueOnce(new InterviewChatApiError("대화가 만료됐어요.", 404));
    await fill("결과를 다시 확인했어요."); await click("보내기");
    expect(container.textContent).toContain("새 대화 시작");
    requestChat.mockResolvedValue({ ...active, conversation_id:"conversation-2" });
    await click("새 대화 시작");
    const restarted = requestChat.mock.calls.at(-1)![0];
    expect(restarted.action).toBe("start");
    expect(restarted.request_id).not.toBe(firstRequest.request_id);
    expect(restarted.message).toBeUndefined();
    expect(container.querySelectorAll(".coach-message-user")).toHaveLength(0);
    await click("보내기");
    expect(requestChat.mock.calls.at(-1)![0].conversation_id).toBe("conversation-2");
  });

  it("대화 중 요약을 표시한 후에도 다음 메시지를 보낼 수 있다", async () => {
    await render();
    requestChat.mockResolvedValueOnce({ ...active, follow_up_question: null,
      summary: { clarified_points: ["고유 키 선택 이유를 보완했어요."], next_practice: ["원인 판단을 설명해 보세요."] } });
    await fill("오늘 연습 요약해줘"); await click("보내기");
    expect(container.querySelector(".interview-followup-summary")?.textContent).toContain("고유 키 선택 이유");
    expect(container.querySelector("input")!.disabled).toBe(false);
    expect(container.querySelector(".interview-followup-exit-actions")).toBeNull();
    await fill("달라진 부분도 설명해줘"); await click("보내기");
    expect(requestChat.mock.calls.at(-1)![0].action).toBe("message");
  });

  it("시작 실패는 다시 시도할 수 있고 중복 전송은 비활성화한다", async () => {
    requestChat.mockRejectedValueOnce(new Error("첫 질문 실패"));
    await render();
    expect(container.querySelector("input")!.disabled).toBe(true);
    await click("다시 시도");
    expect(container.querySelector("input")!.disabled).toBe(false);
    let resolve!: (value: typeof active) => void;
    requestChat.mockImplementationOnce(() => new Promise((done) => { resolve=done; }));
    await fill("개발용 답변"); await click("보내기");
    expect(container.querySelector("input")!.disabled).toBe(true);
    expect([...container.querySelectorAll("button")].every((b) => b.disabled)).toBe(true);
    await act(async () => resolve(active));
  });
});
