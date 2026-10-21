import { act, useEffect, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { useNavigation } from "./navigation";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const mocks = vi.hoisted(() => ({ mount: vi.fn(), unmount: vi.fn(), signOut: vi.fn(), getSession: vi.fn(), authChange: undefined as undefined | ((_event: string, session: unknown) => void), signIn: vi.fn(), finishAnalysis: undefined as undefined | (() => void) }));
vi.mock("./api/supabaseAuth", () => ({
  isSupabaseConfigured: () => true,
  signInWithGoogle: (destination: string) => mocks.signIn(destination),
  supabase: () => ({ auth: {
    getSession: () => mocks.getSession(),
    onAuthStateChange: (callback: typeof mocks.authChange) => { mocks.authChange = callback; return { data: { subscription: { unsubscribe() {} } } }; },
  } }),
  signOut: () => mocks.signOut(),
}));
vi.mock("./pages/PracticePage", () => ({ default: function Practice() {
  const navigation = useNavigation();
  const [selection, setSelection] = useState("");
  const [complete, setComplete] = useState(false);
  useEffect(() => { mocks.mount(); mocks.finishAnalysis = () => setComplete(true); return () => { mocks.unmount(); }; }, []);
  return <section data-testid="practice"><button onClick={() => setSelection("공고 A · 질문 4")}>공고·질문 선택</button><p>{selection}</p><p>{complete ? "분석 완료" : "분석 진행 중"}</p><button onClick={() => navigation.navigate("history")}>연습 기록</button><button onClick={navigation.goBack} disabled={!navigation.canGoBack}>이전 페이지</button><button onClick={navigation.goForward} disabled={!navigation.canGoForward}>다음 페이지</button><button onClick={navigation.logout}>로그아웃</button></section>;
} }));
vi.mock("./pages/HistoryPage", () => ({ default: function History({ onStartPractice, onView }: {onStartPractice: () => void; onView: (item: unknown) => void}) {
  return <section data-testid="history"><button onClick={onStartPractice}>연습으로 복귀</button><button onClick={() => onView({ id: "record-1" })}>기록 열기</button></section>;
} }));
vi.mock("./pages/HistoryResultPage", () => ({ default: function HistoryResult({ onDetail }: {onDetail: () => void}) {
  const navigation = useNavigation();
  return <section data-testid="history-result"><button onClick={onDetail}>상세 열기</button><button onClick={() => navigation.navigate("practice")}>연습하기</button></section>;
} }));
vi.mock("./pages/HistoryDetailPage", () => ({ default: function HistoryDetail() {
  const navigation = useNavigation();
  return <section data-testid="history-detail"><button onClick={() => navigation.navigate("practice")}>연습하기</button></section>;
} }));

let container: HTMLDivElement;
let root: Root;
const click = async (text: string) => {
  const button = Array.from(container.querySelectorAll<HTMLButtonElement>("button")).find((item) => item.textContent === text && !item.closest("[hidden]"));
  if (!button) throw new Error(`버튼 없음: ${text}`);
  await act(async () => button.click());
};
beforeEach(async () => {
  mocks.mount.mockClear(); mocks.unmount.mockClear(); mocks.signOut.mockResolvedValue(undefined);
  container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
  window.history.replaceState(null, "", "/app/");
  mocks.getSession.mockResolvedValue({ data: { session: { user: { id: "test" } } }, error: null });
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });

describe("연습 기록 왕복 시 연습 세션 보존", () => {
  beforeEach(async () => { await act(async () => root.render(<App />)); await click("연습하기"); });
  it("기록 목록을 보고 복귀해도 선택 상태와 화면 인스턴스를 유지한다", async () => {
    await click("공고·질문 선택");
    const practice = container.querySelector('[data-testid="practice"]');
    await click("연습 기록");
    expect(practice?.closest("[hidden]")).not.toBeNull();
    await click("연습으로 복귀");
    expect(container.querySelector('[data-testid="practice"]')).toBe(practice);
    expect(practice?.textContent).toContain("공고 A · 질문 4");
    expect(practice?.closest("[hidden]")).toBeNull();
    expect(mocks.mount).toHaveBeenCalledTimes(1);
    expect(mocks.unmount).not.toHaveBeenCalled();
  });
  it("기록 상세를 보고 복귀해도 진행 상태를 유지한다", async () => {
    await click("공고·질문 선택"); await click("연습 기록"); await click("기록 열기"); await click("상세 열기"); await click("연습하기");
    expect(container.querySelector('[data-testid="practice"]')?.textContent).toContain("공고 A · 질문 4");
    expect(mocks.mount).toHaveBeenCalledTimes(1);
  });
  it("기록 화면에 있는 동안 완료된 분석 결과도 복귀 시 유지한다", async () => {
    await click("연습 기록");
    await act(async () => mocks.finishAnalysis?.());
    await click("연습으로 복귀");
    expect(container.querySelector('[data-testid="practice"]')?.textContent).toContain("분석 완료");
    expect(mocks.unmount).not.toHaveBeenCalled();
  });
  it("로그아웃 시 이전 선택과 분석 상태를 초기화한다", async () => {
    await click("공고·질문 선택"); await act(async () => mocks.finishAnalysis?.()); await click("로그아웃");
    expect(container.querySelector('[data-testid="practice"]')?.textContent).not.toContain("공고 A · 질문 4");
    expect(container.querySelector('[data-testid="practice"]')?.textContent).toContain("분석 진행 중");
    expect(mocks.mount).toHaveBeenCalledTimes(2);
    expect(mocks.unmount).toHaveBeenCalledTimes(1);
  });
});


describe("소개에서 연습 채팅으로 진입", () => {
  it("로그인 사용자는 직접 경로에서 홈을 거치지 않고 연습을 표시한다", async () => {
    window.history.replaceState(null, "", "/app/practice");
    await act(async () => root.render(<App />));
    expect(container.querySelector('[data-testid="practice"]')?.closest("[hidden]")).toBeNull();
    expect(container.textContent).not.toContain("면접을 말로");
  });
  it("미로그인 사용자는 로그인 후 같은 채팅 화면으로 복귀한다", async () => {
    window.history.replaceState(null, "", "/app/practice");
    mocks.getSession.mockResolvedValue({ data: { session: null }, error: null });
    await act(async () => root.render(<App />));
    expect(container.querySelector('h1')?.textContent).toBe("로그인");
    expect(container.textContent).toContain("로그인하면 바로 면접 연습 채팅");
    await click("Google로 계속하기");
    expect(mocks.signIn).toHaveBeenCalledWith("practice");
    await act(async () => mocks.authChange?.("SIGNED_IN", { user: { id: "test" } }));
    expect(container.querySelector('[data-testid="practice"]')?.closest("[hidden]")).toBeNull();
    expect(container.querySelector('h1')).toBeNull();
  });
  it("세션 확인 중에는 로그인이나 연습 화면을 먼저 표시하지 않는다", async () => {
    window.history.replaceState(null, "", "/app/practice");
    mocks.getSession.mockReturnValue(new Promise(() => {}));
    await act(async () => root.render(<App />));
    expect(container.querySelector('[role="status"]')?.textContent).toContain("로그인 상태를 확인");
    expect(container.querySelector('[data-testid="practice"]')).toBeNull();
    await act(async () => mocks.authChange?.("INITIAL_SESSION", null));
    expect(container.querySelector('h1')?.textContent).toBe("로그인");
  });
  it("세션 조회 실패는 무한 로딩 대신 재로그인 안내를 표시한다", async () => {
    window.history.replaceState(null, "", "/app/practice");
    mocks.getSession.mockRejectedValue(new Error("session lookup failed"));
    await act(async () => root.render(<App />));
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("로그인 상태를 확인하지 못했습니다");
  });
  it("OAuth 취소는 고정 오류 안내로 표시하고 원문 오류를 노출하지 않는다", async () => {
    window.history.replaceState(null, "", "/app/practice#error=access_denied&error_description=private-detail");
    mocks.getSession.mockResolvedValue({ data: { session: null }, error: null });
    await act(async () => root.render(<App />));
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("로그인을 완료하지 못했습니다");
    expect(container.textContent).not.toContain("private-detail");
    await act(async () => mocks.authChange?.("SIGNED_IN", { user: { id: "test" } }));
    await act(async () => mocks.authChange?.("SIGNED_OUT", null));
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });
  it("서비스 홈 진입과 뒤로가기에서 URL과 화면이 일치한다", async () => {
    await act(async () => root.render(<App />));
    expect(container.querySelector('#home-title')).not.toBeNull();
    await click("연습하기");
    expect(window.location.pathname).toBe("/app/practice");
    window.history.replaceState(null, "", "/app/");
    await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
    expect(container.querySelector('#home-title')).not.toBeNull();
  });
  it("늦은 세션 조회가 더 최신 로그인 이벤트를 덮어쓰지 않는다", async () => {
    let resolveSession!: (value: unknown) => void;
    mocks.getSession.mockReturnValue(new Promise(resolve => { resolveSession = resolve; }));
    window.history.replaceState(null, "", "/app/practice");
    await act(async () => root.render(<App />));
    await act(async () => mocks.authChange?.("SIGNED_IN", { user: { id: "test" } }));
    await act(async () => resolveSession({ data: { session: null }, error: null }));
    expect(container.querySelector('[data-testid="practice"]')?.closest("[hidden]")).toBeNull();
  });
});

describe("운영 내부 방문 기록과 URL 정합성", () => {
  it("브라우저 뒤로·앞으로 이동 시 선택 상태와 앱 방문 순서를 보존한다", async () => {
    await act(async () => root.render(<App />));
    await click("연습하기"); await click("공고·질문 선택");
    const practice = container.querySelector('[data-testid="practice"]');
    const practiceState = window.history.state;
    await click("연습 기록");
    const historyState = window.history.state;
    await act(async () => {
      window.history.replaceState(practiceState, "", "/app/practice");
      window.dispatchEvent(new PopStateEvent("popstate", { state: practiceState }));
    });
    expect(window.location.pathname).toBe("/app/practice");
    expect(practice?.closest("[hidden]")).toBeNull();
    expect(practice?.textContent).toContain("공고 A · 질문 4");
    expect(container.querySelector<HTMLButtonElement>('[data-testid="practice"] button:nth-last-child(2)')?.disabled).toBe(false);
    await act(async () => {
      window.history.replaceState(historyState, "", "/app/history");
      window.dispatchEvent(new PopStateEvent("popstate", { state: historyState }));
    });
    expect(container.querySelector('[data-testid="history"]')).not.toBeNull();
    expect(mocks.mount).toHaveBeenCalledTimes(1);
  });
  it("앱 이전·다음 버튼은 브라우저 기록을 이동시킨다", async () => {
    await act(async () => root.render(<App />)); await click("연습하기");
    const back = vi.spyOn(window.history, "back").mockImplementation(() => undefined);
    const forward = vi.spyOn(window.history, "forward").mockImplementation(() => undefined);
    await click("이전 페이지");
    expect(back).toHaveBeenCalledTimes(1);
    await click("연습 기록");
    await act(async () => {
      window.history.replaceState({ malhaebomVisit: 1 }, "", "/app/practice");
      window.dispatchEvent(new PopStateEvent("popstate", { state: { malhaebomVisit: 1 } }));
    });
    await click("다음 페이지"); expect(forward).toHaveBeenCalledTimes(1);
    back.mockRestore(); forward.mockRestore();
  });
});
