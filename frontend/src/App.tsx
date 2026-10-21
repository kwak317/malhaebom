import { useEffect, useRef, useState } from "react";
import PracticePage from "./pages/PracticePage";
import type { PracticeQuestion } from "./pages/PracticePage";
import ComparisonPage from "./pages/ComparisonPage";
import AuthPage from "./pages/AuthPage";
import HistoryPage from "./pages/HistoryPage";
import HistoryDetailPage from "./pages/HistoryDetailPage";
import HistoryResultPage from "./pages/HistoryResultPage";
import { type AnalysisResult } from "./mocks/analysisMock";
import { NavigationProvider, type AppDestination } from "./navigation";
import type { PracticeHistoryItem } from "./services/practiceHistoryMapper";
import { MOCK_ERROR_STATE } from "./mocks/errorStateMock";
import { isSupabaseConfigured, signOut, supabase } from "./api/supabaseAuth";
import { ThemeProvider } from "./theme/ThemeProvider";
import HomePage from "./pages/HomePage";

type AppScreen = "home" | "practice" | "comparison" | "history" | "history-result" | "history-detail" | "auth";

const appPaths: Record<AppDestination, string> = { home: "/app/", practice: "/app/practice", history: "/app/history", auth: "/app/auth" };
function entryScreen(): AppDestination {
  const path = window.location.pathname.replace(/\/$/, "");
  return path === "/app/practice" || path === "/practice" ? "practice" : path === "/app/history" ? "history" : path === "/app/auth" ? "auth" : "home";
}

function App() {
  const [pageHistory, setPageHistory] = useState<{ visits: { screen: AppScreen; detail: PracticeHistoryItem | null }[]; index: number }>({ visits: [{ screen: entryScreen(), detail: null }], index: 0 });
  const { screen, detail: historyDetail } = pageHistory.visits[pageHistory.index];
  const pageHistoryRef = useRef(pageHistory);
  pageHistoryRef.current = pageHistory;
  const pagePath = (destination: AppScreen) => appPaths[destination === "comparison" ? "practice" : destination === "history-result" || destination === "history-detail" ? "history" : destination];
  const setScreen = (next: AppScreen, detail: PracticeHistoryItem | null = historyDetail, replace = false) => {
    const current = pageHistoryRef.current;
    const visit = current.visits[current.index];
    if (visit.screen === next && visit.detail === detail) return;
    const visits = replace ? [...current.visits] : [...current.visits.slice(0, current.index + 1), { screen: next, detail }];
    if (replace) visits[current.index] = { screen: next, detail };
    const index = replace ? current.index : visits.length - 1;
    window.history[replace ? "replaceState" : "pushState"]({ malhaebomVisit: index }, "", pagePath(next));
    const updated = { visits, index };
    pageHistoryRef.current = updated;
    setPageHistory(updated);
  };
  const goBack = () => window.history.back();
  const goForward = () => window.history.forward();
  const [authReady, setAuthReady] = useState(!isSupabaseConfigured());
  const [loginDestination, setLoginDestination] = useState<"home" | "practice">(() => entryScreen() === "practice" ? "practice" : "home");
  const [authError, setAuthError] = useState(() => new URLSearchParams(window.location.hash.slice(1)).has("error") || new URLSearchParams(window.location.search).has("error") ? "로그인을 완료하지 못했습니다. 다시 시도해 주세요." : "");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [question, setQuestion] = useState<PracticeQuestion | null>(null);
  const [attemptNo, setAttemptNo] = useState<1 | 2>(1);
  const [firstResult, setFirstResult] = useState<AnalysisResult | null>(null);
  const [secondResult, setSecondResult] = useState<AnalysisResult | null>(null);
  const [practiceInstance, setPracticeInstance] = useState(0);
  const historyLoggedIn = isLoggedIn && MOCK_ERROR_STATE !== "auth-required-history";
  useEffect(() => {
    if (!isSupabaseConfigured()) return undefined;
    let active = true;
    let receivedEvent = false;
    const client = supabase();
    const { data: { subscription } } = client.auth.onAuthStateChange((_event, session) => {
      if (!active) return;
      receivedEvent = true;
      setIsLoggedIn(Boolean(session));
      if (session) setAuthError("");
      setAuthReady(true);
    });
    void client.auth.getSession().then(({ data, error }) => {
      if (!active || receivedEvent) return;
      setIsLoggedIn(Boolean(data.session));
      if (data.session) setAuthError("");
      if (error) setAuthError("로그인 상태를 확인하지 못했습니다. 다시 로그인해 주세요.");
      setAuthReady(true);
    }).catch(() => {
      if (!active || receivedEvent) return;
      setAuthError("로그인 상태를 확인하지 못했습니다. 다시 로그인해 주세요.");
      setAuthReady(true);
    });
    return () => { active = false; subscription.unsubscribe(); };
  }, []);
  useEffect(() => {
    window.history.replaceState({ malhaebomVisit: 0 }, "", window.location.href);
    const onPopState = (event: PopStateEvent) => {
      const current = pageHistoryRef.current;
      const index: unknown = event.state?.malhaebomVisit;
      if (typeof index === "number" && Number.isInteger(index) && index >= 0 && index < current.visits.length) {
        const updated = { ...current, index };
        pageHistoryRef.current = updated;
        setPageHistory(updated);
        if (current.visits[index].screen === "practice") setLoginDestination("practice");
      } else {
        const destination = entryScreen();
        if (destination === "practice") setLoginDestination("practice");
        const updated = { visits: [{ screen: destination, detail: null }], index: 0 };
        pageHistoryRef.current = updated;
        setPageHistory(updated);
      }
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);
  useEffect(() => {
    if (isLoggedIn && screen === "auth") {
      setScreen(loginDestination, null, true);
    }
  }, [isLoggedIn, screen, loginDestination]);

  const handlePracticeAnalysisComplete = (
    selectedQuestion: PracticeQuestion,
    result: AnalysisResult,
  ) => {
    setQuestion(selectedQuestion);
    setAttemptNo(result.attemptNo);
    if (result.attemptNo === 1) {
      setFirstResult(result);
      setSecondResult(null);
    } else {
      setSecondResult(result);
    }
  };

  const navigate = (destination: AppDestination) => {
    if (destination === "practice") setLoginDestination("practice");
    if (destination === "auth" && screen !== "practice") setLoginDestination("home");
    setScreen(destination);
  };

  const logout = () => {
    void signOut().catch(() => undefined).finally(() => { setIsLoggedIn(false); returnHome(); });
  };

  const returnHome = () => {
    setQuestion(null);
    setAttemptNo(1);
    setFirstResult(null);
    setSecondResult(null);
    setPracticeInstance((current) => current + 1);
    window.history.pushState({ malhaebomVisit: 0 }, "", appPaths.home);
    const updated = { visits: [{ screen: "home" as const, detail: null }], index: 0 };
    pageHistoryRef.current = updated;
    setPageHistory(updated);
  };

  const renderScreen = () => {
    if (screen === "home") return <HomePage onStartPractice={() => navigate("practice")} onViewHistory={() => navigate("history")} />;
    if (screen === "history") return <HistoryPage isLoggedIn={historyLoggedIn} onLogin={() => navigate("auth")} onStartPractice={() => navigate("practice")} onView={(item) => { setScreen("history-result", item); }} />;
    if (screen === "auth" || (screen === "practice" && !isLoggedIn)) return <AuthPage destination={loginDestination} initialError={authError} />;
    if (question && screen === "comparison" && firstResult && secondResult) return <ComparisonPage question={question} firstResult={firstResult} secondResult={secondResult} onReturnHome={returnHome} />;
    return null;
  };

  const active: AppDestination = screen === "history" || screen === "history-result" || screen === "history-detail" ? "history" : screen === "auth" ? "auth" : screen === "home" ? "home" : "practice";
  const showPractice = isLoggedIn && (screen === "practice" || (screen === "comparison" && !(question && firstResult && secondResult)));
  if (!authReady && (screen === "practice" || screen === "auth")) return <main className="account-main" role="status">로그인 상태를 확인하고 있어요…</main>;
  return <ThemeProvider><NavigationProvider active={active} isLoggedIn={isLoggedIn} navigate={navigate} logout={logout} canGoBack={pageHistory.index > 0} canGoForward={pageHistory.index < pageHistory.visits.length - 1} goBack={goBack} goForward={goForward}>
    <div className="practice-screen" hidden={!showPractice}>
      <PracticePage key={practiceInstance} isLoggedIn={isLoggedIn} onLogin={() => navigate("auth")} onAnalysisComplete={handlePracticeAnalysisComplete} />
    </div>
    {renderScreen()}
    {pageHistory.visits.filter((visit, index, visits) => visit.screen === "history-result" && visit.detail && !visits.slice(0, index).some(previous => previous.screen === "history-result" && previous.detail?.id === visit.detail?.id)).map(visit => <div key={`history-result:${visit.detail!.id}`} hidden={screen !== "history-result" || historyDetail?.id !== visit.detail!.id}>
      <HistoryResultPage item={visit.detail!} onDetail={() => setScreen("history-detail", visit.detail)} onBack={() => setScreen("history")} />
    </div>)}
    {pageHistory.visits.filter((visit, index, visits) => visit.screen === "history-detail" && visit.detail && !visits.slice(0, index).some(previous => previous.screen === "history-detail" && previous.detail?.id === visit.detail?.id)).map(visit => <div key={`history-detail:${visit.detail!.id}`} hidden={screen !== "history-detail" || historyDetail?.id !== visit.detail!.id}>
      <HistoryDetailPage item={visit.detail!} onBack={() => setScreen("history-result", visit.detail)} />
    </div>)}
  </NavigationProvider></ThemeProvider>;
}

export default App;
