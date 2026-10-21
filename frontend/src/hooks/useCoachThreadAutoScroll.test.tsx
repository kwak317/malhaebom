import { act, type ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useCoachThreadAutoScroll } from "./useCoachThreadAutoScroll";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

function CoachThread({ coachMessageCount, showCoachingResult = false, showReadmeResult = false, nestedCount = 0 }: { coachMessageCount: number; showCoachingResult?: boolean; showReadmeResult?: boolean; nestedCount?: number }) {
  const threadRef = useCoachThreadAutoScroll();
  return <div className="coach-thread" ref={threadRef}>
    {Array.from({ length: coachMessageCount }, (_, index) => (
      <article className="coach-message-assistant" key={index}>코치 답변</article>
    ))}
    {showCoachingResult && <article className="coach-message-assistant coach-coaching-result-message">코칭 결과</article>}
    {showReadmeResult && <article className="coach-message-assistant coach-readme-analysis-result">README 분석 결과</article>}
    <section>{Array.from({length:nestedCount}, (_, index) => <article className="coach-message-assistant" key={index}>면접 대화</article>)}</section>
  </div>;
}

describe("useCoachThreadAutoScroll", () => {
  let root: Root;
  let container: HTMLDivElement;

  beforeEach(() => {
    vi.useFakeTimers();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  it("이력서 종류 선택은 사용자 말풍선의 하단 이동보다 초안 상단을 우선한다", async () => {
    await act(async () => root.render(<Thread><article>비교 결과</article></Thread>));
    const thread = container.firstElementChild as HTMLDivElement;
    const scrollTo = vi.fn();
    Object.defineProperties(thread, {
      scrollHeight: { configurable: true, value: 4000 },
      clientHeight: { configurable: true, value: 600 },
      scrollTop: { configurable: true, writable: true, value: 500 },
      scrollTo: { configurable: true, value: scrollTo },
    });
    thread.getBoundingClientRect = () => new DOMRect(0, 100, 700, 600);
    thread.dataset.historyBrowsing = "manual";
    await act(async () => root.render(<Thread><article>비교 결과</article><article className="coach-message-user">경력 중심 이력서</article><article className="coach-message-assistant resume-draft-message">이력서 초안</article></Thread>));
    thread.querySelector<HTMLElement>(".resume-draft-message")!.getBoundingClientRect = () => new DOMRect(0, 450, 700, 1600);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 826, behavior: "smooth" });
    expect(thread.dataset.historyBrowsing).toBeUndefined();
    scrollTo.mockClear();
    await act(async () => root.render(<Thread><article>비교 결과</article><article className="coach-message-user">경력 중심 이력서</article><article className="coach-message-assistant resume-draft-message">이력서 초안 수정</article></Thread>));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it("비교 카드 뒤에 중첩된 대화도 따라가되 이전 내용을 읽을 때는 이동하지 않는다", async () => {
    await act(async () => root.render(<CoachThread coachMessageCount={0} />));
    const thread = container.querySelector<HTMLDivElement>(".coach-thread")!;
    const scrollTo = vi.fn();
    Object.defineProperties(thread, {
      scrollHeight: { configurable:true, value:1_000 },
      clientHeight: { configurable:true, value:300 },
      scrollTop: { configurable:true, writable:true, value:700 },
      scrollTo: { configurable:true, value:scrollTo },
    });
    thread.dispatchEvent(new Event("scroll"));
    await act(async () => { await vi.runAllTimersAsync(); });
    scrollTo.mockClear();
    await act(async () => root.render(<CoachThread coachMessageCount={0} nestedCount={1} />));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).toHaveBeenCalledWith({top:1_000, behavior:"smooth"});
    scrollTo.mockClear();
    thread.scrollTop = 0;
    thread.dispatchEvent(new Event("scroll"));
    await act(async () => root.render(<CoachThread coachMessageCount={0} nestedCount={2} />));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it("다음 단계 이동은 이전 대화 읽기를 해제하고 새 단계의 맨 아래로 이동한다", async () => {
    await act(async () => root.render(<CoachThread coachMessageCount={1} />));
    const thread = container.querySelector<HTMLDivElement>(".coach-thread")!;
    const scrollTo = vi.fn();
    Object.defineProperties(thread, {
      scrollHeight: { configurable: true, value: 1400 },
      clientHeight: { configurable: true, value: 300 },
      scrollTop: { configurable: true, writable: true, value: 0 },
      scrollTo: { configurable: true, value: scrollTo },
    });
    thread.dataset.historyBrowsing = "manual";
    thread.dispatchEvent(new Event("workspace-browse"));
    await act(async () => { await vi.runAllTimersAsync(); });
    scrollTo.mockClear();
    thread.dispatchEvent(new Event("workspace-next-stage"));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(thread.dataset.historyBrowsing).toBeUndefined();
    expect(scrollTo).toHaveBeenCalledWith({ top: 1400, behavior: "instant" });
  });

  it.each([1, 2])("%i차 표준어 완료 후 해당 결과 상단으로 이동한다", async (attempt) => {
    const content = (completed: boolean, later = false) => <Thread>
      {attempt === 2 && <article className="coach-message-assistant coach-transcript-normalized-result">1차 이전 결과</article>}
      <article className={`coach-message-assistant coach-transcript-message${completed ? " coach-transcript-normalized-result" : ""}`}>{attempt}차 전사문</article>
      {later && <article className="coach-message-assistant">추가 안내</article>}
    </Thread>;
    await act(async () => root.render(content(false)));
    const thread = container.firstElementChild as HTMLDivElement;
    const scrollTo = vi.fn();
    Object.defineProperties(thread, {
      scrollHeight: { configurable: true, value: 3000 },
      clientHeight: { configurable: true, value: 600 },
      scrollTop: { configurable: true, writable: true, value: 1800 },
      scrollTo: { configurable: true, value: scrollTo },
    });
    thread.getBoundingClientRect = () => new DOMRect(0, 100, 700, 600);
    thread.querySelector<HTMLElement>(".coach-transcript-message")!.getBoundingClientRect = () => new DOMRect(0, -600, 700, 1200);
    thread.dispatchEvent(new Event("workspace-next-stage"));
    await act(async () => { await vi.runAllTimersAsync(); });
    scrollTo.mockClear();
    await act(async () => root.render(content(true)));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 1076, behavior: "smooth" });
    scrollTo.mockClear();
    await act(async () => root.render(content(true, true)));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it("2차 변환 시작은 로딩 영역 상단으로 이동하고 진행 내용 갱신 동안 유지한다", async () => {
    await act(async () => root.render(<Thread><article>2차 전사문</article></Thread>));
    const thread = container.firstElementChild as HTMLDivElement;
    const scrollTo = vi.fn();
    Object.defineProperties(thread, {
      scrollHeight: { configurable: true, value: 3000 },
      clientHeight: { configurable: true, value: 600 },
      scrollTop: { configurable: true, writable: true, value: 2000 },
      scrollTo: { configurable: true, value: scrollTo },
    });
    thread.getBoundingClientRect = () => new DOMRect(0, 100, 700, 600);
    thread.dispatchEvent(new Event("workspace-next-stage"));
    await act(async () => { await vi.runAllTimersAsync(); });
    scrollTo.mockClear();
    await act(async () => root.render(<Thread><article>2차 전사문<div className="coach-transcript-second-loading">변환 중</div></article></Thread>));
    thread.querySelector<HTMLElement>(".coach-transcript-second-loading")!.getBoundingClientRect = () => new DOMRect(0, -200, 700, 150);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 1676, behavior: "smooth" });
    scrollTo.mockClear();
    await act(async () => root.render(<Thread><article>2차 전사문<div className="coach-transcript-second-loading">의미 검토 중</div></article></Thread>));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it("공고 검색 완료 시 결과 카드 상단을 보여주고 후속 안내에도 유지한다", async () => {
    await act(async () => root.render(<Thread><article className="coach-message-assistant coach-job-search-message">검색 중</article></Thread>));
    const thread = container.firstElementChild as HTMLDivElement;
    const scrollTo = vi.fn();
    Object.defineProperties(thread, {
      scrollHeight: { configurable: true, value: 3400 },
      clientHeight: { configurable: true, value: 600 },
      scrollTop: { configurable: true, writable: true, value: 2000 },
      scrollTo: { configurable: true, value: scrollTo },
    });
    thread.getBoundingClientRect = () => new DOMRect(0, 100, 700, 600);
    thread.firstElementChild!.getBoundingClientRect = () => new DOMRect(0, -300, 700, 1600);
    thread.dispatchEvent(new Event("workspace-next-stage"));
    await act(async () => { await vi.runAllTimersAsync(); });
    scrollTo.mockClear();
    await act(async () => root.render(<Thread><article className="coach-message-assistant coach-search-message coach-job-search-message">공고 검색 결과</article></Thread>));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 1576, behavior: "smooth" });
    scrollTo.mockClear();
    await act(async () => root.render(<Thread><article className="coach-message-assistant coach-search-message coach-job-search-message">공고 검색 결과</article><article className="coach-message-assistant">공고를 골라 주세요</article></Thread>));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).not.toHaveBeenCalled();
    thread.dispatchEvent(new Event("workspace-next-stage"));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 3400, behavior: "instant" });
  });

  it("README 결과를 읽다가 공고 검색이 시작되면 하단을 따라가고 완료 시 결과 상단으로 이동한다", async () => {
    const content = (state: "readme" | "loading" | "result") => <Thread>
      <article className="coach-message-assistant coach-readme-analysis-result">README 결과</article>
      {state === "loading" && <article className="coach-message-assistant coach-job-search-message coach-analysis-loading">검색 중</article>}
      {state === "result" && <article className="coach-message-assistant coach-job-search-message coach-search-message">공고 결과</article>}
    </Thread>;
    await act(async () => root.render(content("readme")));
    const thread = container.firstElementChild as HTMLDivElement;
    const scrollTo = vi.fn();
    Object.defineProperties(thread, {
      scrollHeight: { configurable: true, value: 3500 },
      clientHeight: { configurable: true, value: 600 },
      scrollTop: { configurable: true, writable: true, value: 1200 },
      scrollTo: { configurable: true, value: scrollTo },
    });
    thread.getBoundingClientRect = () => new DOMRect(0, 100, 700, 600);
    await act(async () => { await vi.runAllTimersAsync(); });
    scrollTo.mockClear();
    thread.dataset.historyBrowsing = "manual";
    await act(async () => root.render(content("loading")));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(thread.dataset.historyBrowsing).toBeUndefined();
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 3500, behavior: "instant" });
    scrollTo.mockClear();
    await act(async () => root.render(content("result")));
    thread.querySelector<HTMLElement>(".coach-search-message")!.getBoundingClientRect = () => new DOMRect(0, 500, 700, 1800);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 1576, behavior: "smooth" });
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    vi.useRealTimers();
  });

  it("직접 과거로 스크롤한 동안 새 코칭과 README 결과도 읽기 위치를 유지한다", async () => {
    await act(async () => root.render(<CoachThread coachMessageCount={0} />));
    const thread = container.querySelector<HTMLDivElement>(".coach-thread")!;
    const scrollTo = vi.fn();
    Object.defineProperties(thread, { scrollHeight: { configurable:true, value:2000 }, clientHeight: { configurable:true,value:300 }, scrollTop: { configurable:true,writable:true,value:200 }, scrollTo: {configurable:true,value:scrollTo} });
    thread.dispatchEvent(new Event("scroll"));
    await act(async () => root.render(<CoachThread coachMessageCount={1} showCoachingResult showReadmeResult />));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).not.toHaveBeenCalled();
    expect(thread.dataset.historyBrowsing).toBe("manual");
  });

  it("코치 메시지가 도착하면 하단 근처에서만 부드럽게 최신 메시지로 이동한다", async () => {
    await act(async () => root.render(<CoachThread coachMessageCount={0} />));
    const thread = container.querySelector<HTMLDivElement>(".coach-thread");
    if (!thread) throw new Error("채팅 스레드가 필요합니다.");

    const scrollTo = vi.fn();
    Object.defineProperties(thread, {
      scrollHeight: { configurable: true, value: 1_000 },
      clientHeight: { configurable: true, value: 300 },
      scrollTop: { configurable: true, writable: true, value: 0 },
      scrollTo: { configurable: true, value: scrollTo },
    });
    await act(async () => { await vi.runAllTimersAsync(); });
    scrollTo.mockClear();

    thread.dispatchEvent(new Event("scroll"));
    await act(async () => root.render(<CoachThread coachMessageCount={1} />));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).not.toHaveBeenCalled();

    thread.scrollTop = 700;
    thread.dispatchEvent(new Event("scroll"));
    await act(async () => root.render(<CoachThread coachMessageCount={2} />));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).toHaveBeenCalledWith({ top: 1_000, behavior: "smooth" });
  });

  it("코칭 결과가 도착하면 결과 카드의 시작 지점으로 이동한다", async () => {
    await act(async () => root.render(<CoachThread coachMessageCount={0} />));
    const thread = container.querySelector<HTMLDivElement>(".coach-thread");
    if (!thread) throw new Error("채팅 스레드가 필요합니다.");

    const scrollTo = vi.fn();
    Object.defineProperties(thread, {
      scrollHeight: { configurable: true, value: 1_800 },
      clientHeight: { configurable: true, value: 300 },
      scrollTop: { configurable: true, writable: true, value: 1_000 },
      scrollTo: { configurable: true, value: scrollTo },
    });
    thread.getBoundingClientRect = () => new DOMRect(0, 100, 700, 300);
    await act(async () => { await vi.runAllTimersAsync(); });
    scrollTo.mockClear();

    await act(async () => root.render(<CoachThread coachMessageCount={0} showCoachingResult />));
    const result = container.querySelector<HTMLElement>(".coach-coaching-result-message");
    if (!result) throw new Error("코칭 결과 메시지가 필요합니다.");
    result.getBoundingClientRect = () => new DOMRect(0, 500, 700, 900);
    await act(async () => { await vi.runAllTimersAsync(); });

    expect(scrollTo).toHaveBeenCalledWith({ top: 1_376, behavior: "smooth" });
  });

  it("이력서 검토는 카드 상단을 보여주고 확인하면 과거를 읽던 중에도 맨 아래로 이동한다", async () => {
    await act(async () => root.render(<Thread><article className="coach-message-assistant coach-resume-message">업로드</article></Thread>));
    const thread = container.firstElementChild as HTMLDivElement;
    const result = thread.querySelector<HTMLElement>(".coach-resume-message")!;
    const scrollTo = vi.fn();
    Object.defineProperties(thread, {
      scrollTop: { configurable: true, writable: true, value: 1000 },
      scrollHeight: { configurable: true, value: 2400 },
      clientHeight: { configurable: true, value: 600 },
      scrollTo: { configurable: true, value: scrollTo },
    });
    thread.getBoundingClientRect = () => new DOMRect(0, 100, 700, 600);
    result.getBoundingClientRect = () => new DOMRect(0, 500, 700, 900);
    await act(async () => { await vi.runAllTimersAsync(); });
    scrollTo.mockClear();
    await act(async () => root.render(<Thread><article className="coach-message-assistant coach-resume-message coach-resume-analysis-result">검토 결과</article></Thread>));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 1376, behavior: "smooth" });
    scrollTo.mockClear();
    thread.dataset.historyBrowsing = "manual";
    await act(async () => root.render(<Thread><article className="coach-message-assistant coach-resume-message coach-resume-confirmed-result">확인 완료</article><article className="coach-message-assistant">README 안내</article></Thread>));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 2400, behavior: "smooth" });
    expect(thread.dataset.historyBrowsing).toBeUndefined();
    scrollTo.mockClear();
    await act(async () => root.render(<Thread><article className="coach-message-assistant coach-resume-message coach-resume-confirmed-result">확인 완료</article><article className="coach-message-assistant">README 안내</article><article className="coach-message-assistant">후속 안내</article></Thread>));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 2400, behavior: "smooth" });
    scrollTo.mockClear();
    thread.dataset.historyBrowsing = "manual";
    await act(async () => root.render(<Thread><article className="coach-message-assistant coach-resume-message coach-resume-analysis-result">새 검토</article></Thread>));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it("긴 README 분석 결과가 도착하면 카드의 시작 지점으로 이동한다", async () => {
    await act(async () => root.render(<CoachThread coachMessageCount={0} />));
    const thread = container.querySelector<HTMLDivElement>(".coach-thread");
    if (!thread) throw new Error("채팅 스레드가 필요합니다.");
    const scrollTo = vi.fn();
    Object.defineProperties(thread, {
      scrollHeight: { configurable: true, value: 1_800 },
      clientHeight: { configurable: true, value: 300 },
      scrollTop: { configurable: true, writable: true, value: 1_000 },
      scrollTo: { configurable: true, value: scrollTo },
    });
    thread.getBoundingClientRect = () => new DOMRect(0, 100, 700, 300);
    await act(async () => { await vi.runAllTimersAsync(); });
    scrollTo.mockClear();

    await act(async () => root.render(<CoachThread coachMessageCount={0} showReadmeResult />));
    const result = container.querySelector<HTMLElement>(".coach-readme-analysis-result");
    if (!result) throw new Error("README 분석 결과 메시지가 필요합니다.");
    result.getBoundingClientRect = () => new DOMRect(0, 500, 700, 900);
    await act(async () => { await vi.runAllTimersAsync(); });

    expect(scrollTo).toHaveBeenCalledWith({ top: 1_376, behavior: "smooth" });
  });

  it("README 검토 완료는 강제 하단 이동을 해제하고 후속 안내가 와도 결과 상단을 유지한다", async () => {
    await act(async () => root.render(<CoachThread coachMessageCount={1} />));
    const thread = container.querySelector<HTMLDivElement>(".coach-thread")!;
    const scrollTo = vi.fn();
    Object.defineProperties(thread, {
      scrollHeight: { configurable: true, value: 2400 },
      clientHeight: { configurable: true, value: 600 },
      scrollTop: { configurable: true, writable: true, value: 1000 },
      scrollTo: { configurable: true, value: scrollTo },
    });
    thread.getBoundingClientRect = () => new DOMRect(0, 100, 700, 600);
    thread.dispatchEvent(new Event("workspace-next-stage"));
    await act(async () => { await vi.runAllTimersAsync(); });
    scrollTo.mockClear();

    await act(async () => root.render(<CoachThread coachMessageCount={1} showReadmeResult />));
    const result = thread.querySelector<HTMLElement>(".coach-readme-analysis-result")!;
    result.getBoundingClientRect = () => new DOMRect(0, 500, 700, 1200);
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 1376, behavior: "smooth" });

    scrollTo.mockClear();
    await act(async () => root.render(<CoachThread coachMessageCount={1} showReadmeResult nestedCount={1} />));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).not.toHaveBeenCalled();

    thread.dispatchEvent(new Event("workspace-next-stage"));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 2400, behavior: "instant" });
  });
});

function Thread({ children }: { children?: ReactNode }) {
  const ref = useCoachThreadAutoScroll();
  return <div ref={ref}>{children}</div>;
}

describe("코칭 채팅 자동 스크롤", () => {
  let container: HTMLDivElement;
  let root: Root;
  let thread: HTMLDivElement;
  let scrollTo: ReturnType<typeof vi.fn>;

  const render = async (children?: ReactNode) => {
    await act(async () => { root.render(<Thread>{children}</Thread>); });
  };

  const flushScroll = async () => {
    await act(async () => { await vi.runOnlyPendingTimersAsync(); });
  };

  beforeEach(async () => {
    vi.useFakeTimers();
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
      const top = Number(this.dataset.top ?? 100);
      return { top, bottom: top + 100, left: 0, right: 100, width: 100, height: 100, x: 0, y: top, toJSON: () => ({}) };
    });
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    await render();
    thread = container.firstElementChild as HTMLDivElement;
    Object.defineProperties(thread, {
      scrollHeight: { configurable: true, value: 2000 },
      clientHeight: { configurable: true, value: 500 },
    });
    scrollTo = vi.fn();
    thread.scrollTo = scrollTo;
    await flushScroll();
    scrollTo.mockClear();
  });

  it("기존 이력서 가져오기로 열린 입력 폼은 이전 위치와 무관하게 맨 아래로 이동한다", async () => {
    thread.scrollTop = 600;
    thread.dataset.historyBrowsing = "manual";
    await render(<article className="coach-message-assistant resume-completion-form-message resume-import-form-message" data-top="450">가져온 정보 입력 폼</article>);
    await flushScroll();
    expect(thread.dataset.historyBrowsing).toBeUndefined();
    expect(scrollTo).toHaveBeenLastCalledWith({top:2000,behavior:"instant"});
  });

  it("재구성한 이력서와 사용자 요청이 함께 추가되면 새 이력서 상단을 보여준다", async () => {
    thread.scrollTop = 600;
    thread.dataset.historyBrowsing = "manual";
    await render(<><article className="coach-message-user">재구성하기</article><article className="coach-message-assistant resume-document-message" data-top="450">새 이력서</article></>);
    await flushScroll();
    expect(thread.dataset.historyBrowsing).toBeUndefined();
    expect(scrollTo).toHaveBeenLastCalledWith({top:926,behavior:"smooth"});
    scrollTo.mockClear();
    await render(<><article className="coach-message-user">재구성하기</article><article className="coach-message-assistant resume-document-message" data-top="450">새 이력서</article><article className="coach-message-assistant">확인 안내</article></>);
    await flushScroll();
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it("다음 단계 이동은 이전 대화 읽기를 해제하고 새 단계의 맨 아래로 이동한다", async () => {
    await act(async () => root.render(<CoachThread coachMessageCount={1} />));
    const thread = container.querySelector<HTMLDivElement>(".coach-thread")!;
    const scrollTo = vi.fn();
    Object.defineProperties(thread, {
      scrollHeight: { configurable: true, value: 1400 },
      clientHeight: { configurable: true, value: 300 },
      scrollTop: { configurable: true, writable: true, value: 0 },
      scrollTo: { configurable: true, value: scrollTo },
    });
    thread.dataset.historyBrowsing = "manual";
    thread.dispatchEvent(new Event("workspace-browse"));
    await act(async () => { await vi.runAllTimersAsync(); });
    scrollTo.mockClear();
    thread.dispatchEvent(new Event("workspace-next-stage"));
    await act(async () => { await vi.runAllTimersAsync(); });
    expect(thread.dataset.historyBrowsing).toBeUndefined();
    expect(scrollTo).toHaveBeenCalledWith({ top: 1400, behavior: "instant" });
  });

  afterEach(async () => {
    await act(async () => { root.unmount(); });
    container.remove();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("재답변 비교 로딩이 나타나면 읽기 위치를 해제하고 맨 아래로 이동한다", async () => {
    thread.scrollTop = 0;
    thread.dataset.historyBrowsing = "manual";
    thread.dispatchEvent(new Event("workspace-browse"));
    await render(<article className="coach-message-assistant coach-comparison-loading">비교 중</article>);
    await flushScroll();
    expect(thread.dataset.historyBrowsing).toBeUndefined();
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 2000, behavior: "instant" });
    scrollTo.mockClear();
    thread.dispatchEvent(new Event("wheel"));
    thread.scrollTop = 0;
    thread.dispatchEvent(new Event("scroll"));
    await render(<article className="coach-message-assistant coach-comparison-loading">재답변을 분석하고 있어요</article>);
    await flushScroll();
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it("비교 완료는 카드 상단을 유지하고 후속 면접 메시지가 위치를 밀지 않는다", async () => {
    thread.scrollTop = 600;
    const comparison = <article key="comparison" className="coach-message-assistant coach-inline-comparison" data-top="450"><h2>1차 답변과 재답변을 비교했어요.</h2></article>;
    await render(comparison);
    await render(<>{comparison}<article className="coach-message-assistant">첫 면접 질문</article></>);
    await flushScroll();

    expect(scrollTo).toHaveBeenCalledTimes(1);
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 950, behavior: "smooth" });
    await render(<>{comparison}<article className="coach-message-assistant">완성된 면접 질문</article><article className="coach-message-assistant">후속 메시지</article></>);
    await flushScroll();
    expect(scrollTo).toHaveBeenCalledTimes(1);
  });

  it("비교를 읽은 뒤 사용자가 메시지를 보내면 최신 하단 이동을 재개한다", async () => {
    thread.scrollTop = 600;
    const comparison = <article key="comparison" className="coach-message-assistant coach-inline-comparison" data-top="450">비교 완료</article>;
    await render(comparison);
    await flushScroll();
    expect(scrollTo).toHaveBeenLastCalledWith({top:950,behavior:"smooth"});
    await render(<>{comparison}<article className="coach-message-user">다음 질문에 답해요</article></>);
    await flushScroll();
    expect(scrollTo).toHaveBeenLastCalledWith({top:2000,behavior:"instant"});
  });

  it("과거 대화를 읽다가 채팅을 보내면 읽기 위치를 해제하고 맨 아래로 이동한다", async () => {
    thread.scrollTop = 0;
    thread.dataset.historyBrowsing = "manual";
    thread.dispatchEvent(new Event("workspace-browse"));
    await render(<article className="coach-message-user">Redis 캐시 적용 경험을 추가하고 싶어요.</article>);
    await flushScroll();
    expect(thread.dataset.historyBrowsing).toBeUndefined();
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 2000, behavior: "instant" });
  });

  it("전송 후 늦게 늘어난 말풍선도 하단을 유지하고 사용자의 위 스크롤은 존중한다", async () => {
    thread.dispatchEvent(new Event("workspace-next-stage"));
    await render(<article className="coach-message-user">경험 추가</article>);
    await flushScroll();
    scrollTo.mockClear();
    Object.defineProperty(thread, "scrollHeight", { configurable: true, value: 3000 });
    thread.dispatchEvent(new Event("scroll"));
    await render(<article className="coach-message-user">경험 추가 내용이 길어졌어요.</article>);
    await flushScroll();
    expect(thread.dataset.historyBrowsing).toBeUndefined();
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 3000, behavior: "instant" });
    scrollTo.mockClear();
    thread.dispatchEvent(new Event("wheel"));
    thread.scrollTop = 0;
    thread.dispatchEvent(new Event("scroll"));
    await render(<><article className="coach-message-user">경험 추가 내용이 길어졌어요.</article><article className="coach-message-assistant">응답 도착</article></>);
    await flushScroll();
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it("입력 중 말풍선이 같은 DOM 요소의 비교 결과로 바뀌어도 상단으로 이동한다", async () => {
    await render(<article className="coach-message-assistant coach-typing-message" data-top="450"><div>비교 중</div></article>);
    await flushScroll();
    scrollTo.mockClear();
    thread.scrollTop = 600;
    const typingMessage = thread.firstElementChild;
    await render(<article className="coach-message-assistant coach-inline-comparison" data-top="450"><div>비교 완료</div></article>);
    expect(thread.firstElementChild).toBe(typingMessage);
    await flushScroll();
    expect(scrollTo).toHaveBeenCalledTimes(1);
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 950, behavior: "smooth" });
  });

  it("이전 코칭 결과가 있어도 가장 최근 결과의 상단으로 이동한다", async () => {
    const first = <article key="first" className="coach-message-assistant coach-coaching-result-message" data-top="150">이전 코칭</article>;
    await render(first);
    await flushScroll();
    scrollTo.mockClear();
    thread.scrollTop = 600;
    await render(<>{first}<article className="coach-message-assistant coach-coaching-result-message" data-top="450">새 코칭</article></>);
    await flushScroll();
    expect(scrollTo).toHaveBeenCalledTimes(1);
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 926, behavior: "smooth" });
  });

  it("1차 코칭 완료 후 안내 메시지가 추가돼도 결과 카드 상단을 유지한다", async () => {
    thread.scrollTop = 600;
    const result = <article key="result" className="coach-message-assistant coach-coaching-result-message" data-top="450">코칭 결과</article>;
    await render(result);
    await render(<>{result}<article className="coach-message-assistant">다시 답변해 볼까요?</article></>);
    await flushScroll();
    expect(scrollTo).toHaveBeenCalledTimes(1);
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 926, behavior: "smooth" });
    await render(<>{result}<article className="coach-message-assistant">다시 답변해 볼까요?</article><article className="coach-message-assistant">재녹음 안내</article></>);
    await flushScroll();
    expect(scrollTo).toHaveBeenCalledTimes(1);
  });

  it("일반 채팅은 하단을 따라가되 위로 스크롤한 읽기 위치를 유지하고 하단 복귀 시 재개한다", async () => {
    const first = <article key="first" className="coach-message-assistant">첫 메시지</article>;
    await render(first);
    await flushScroll();
    expect(scrollTo).toHaveBeenCalledTimes(1);
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 2000, behavior: "smooth" });

    thread.scrollTop = 600;
    thread.dispatchEvent(new Event("scroll"));
    const second = <article key="second" className="coach-message-assistant">두 번째 메시지</article>;
    await render(<>{first}{second}</>);
    await flushScroll();
    expect(scrollTo).toHaveBeenCalledTimes(1);

    thread.scrollTop = 1500;
    thread.dispatchEvent(new Event("scroll"));
    await render(<>{first}{second}<article className="coach-message-assistant">세 번째 메시지</article></>);
    await flushScroll();
    expect(scrollTo).toHaveBeenCalledTimes(2);
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 2000, behavior: "smooth" });
  });

  it("비교 분석을 다시 선택하면 기록 탐색 중에도 비교 카드 상단으로 이동한다", async () => {
    thread.scrollTop = 600;
    await render(<article className="coach-message-assistant coach-inline-comparison" data-top="450">비교 결과</article>);
    await flushScroll();
    scrollTo.mockClear();
    thread.dataset.historyBrowsing = "true";
    thread.dispatchEvent(new Event("workspace-browse"));
    thread.dispatchEvent(new Event("workspace-comparison"));
    await flushScroll();
    expect(thread.dataset.historyBrowsing).toBeUndefined();
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 950, behavior: "smooth" });
    thread.dispatchEvent(new Event("workspace-comparison"));
    await flushScroll();
    expect(scrollTo).toHaveBeenCalledTimes(2);
  });

  it("README 분석 완료 시 기존 결과 상단 이동을 유지한다", async () => {
    thread.scrollTop = 600;
    await render(<article className="coach-message-assistant coach-readme-analysis-result" data-top="450">README 분석</article>);
    await flushScroll();
    expect(scrollTo).toHaveBeenCalledTimes(1);
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 926, behavior: "smooth" });
  });
});
