import { createContext, useContext, useState, type ReactNode } from "react";
import brandLogo from "./assets/malhaebom-detail-logo.png";
import "./styles/page-navigation.css";
import { ThemeToggle } from "./components/ThemeToggle";

export type AppDestination = "home" | "practice" | "history" | "auth";
type NavigationContextValue = { active: AppDestination; isLoggedIn: boolean; navigate: (destination: AppDestination) => void; logout: () => void; canGoBack?: boolean; canGoForward?: boolean; goBack?: () => void; goForward?: () => void };

const NavigationContext = createContext<NavigationContextValue | null>(null);

export function NavigationProvider({ active, isLoggedIn, navigate, logout, canGoBack, canGoForward, goBack, goForward, children }: NavigationContextValue & { children: ReactNode }) {
  return <NavigationContext.Provider value={{ active, isLoggedIn, navigate, logout, canGoBack, canGoForward, goBack, goForward }}>{children}</NavigationContext.Provider>;
}

export function useNavigation() {
  const value = useContext(NavigationContext);
  if (!value) throw new Error("NavigationProvider is missing");
  return value;
}

export function AppHeader() {
  const { active, isLoggedIn, navigate, logout, canGoBack, canGoForward, goBack, goForward } = useNavigation();
  const [accountOpen, setAccountOpen] = useState(false);
  return (
    <header className={`site-header${goBack ? " has-page-navigation" : ""}`}>
      {goBack && <div className="page-history-controls" role="group" aria-label="사이트 내 페이지 이동">
        <button type="button" aria-label="이전 페이지" title="이전 페이지" disabled={!canGoBack} onClick={goBack}><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M20 12H4m8-8-8 8 8 8" /></svg></button>
        <button type="button" aria-label="다음 페이지" title="다음 페이지" disabled={!canGoForward} onClick={goForward}><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M4 12h16m-8-8 8 8-8 8" /></svg></button>
      </div>}
      <button className="brand" type="button" onClick={() => navigate("home")} aria-label="말해봄 홈"><img className="brand-logo-image" src={brandLogo} alt="말해봄" /></button>
      <nav className="site-nav" aria-label="주요 메뉴">
        <button className={active === "practice" ? "nav-link is-active" : "nav-link"} type="button" onClick={() => navigate("practice")}>연습하기</button>
        <button className={active === "history" ? "nav-link is-active" : "nav-link"} type="button" onClick={() => navigate("history")}>연습 기록</button>
        {isLoggedIn ? <div className="account-menu"><button className="login-button" type="button" onClick={() => setAccountOpen((open) => !open)}>내 계정</button>{accountOpen && <div className="account-popover"><button type="button" onClick={() => { setAccountOpen(false); logout(); }}>로그아웃</button></div>}</div> : <button className="login-button" type="button" onClick={() => navigate("auth")}>로그인/회원가입</button>}
        <ThemeToggle />
      </nav>
    </header>
  );
}
