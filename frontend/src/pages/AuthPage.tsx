import { useState } from "react";
import { isSupabaseConfigured, signInWithGoogle } from "../api/supabaseAuth";
import { AppHeader } from "../navigation";
import "../styles/account-pages.css";

function AuthPage({ destination = "home", initialError = "" }: { destination?: "home" | "practice"; initialError?: string }) {
  const [error, setError] = useState(initialError);
  const signIn = async () => { setError(""); try { await signInWithGoogle(destination); } catch (cause) { setError(cause instanceof Error ? cause.message : "Google 로그인을 시작하지 못했습니다."); } };
  return <div className="account-page"><AppHeader /><main className="account-main"><section className="account-card"><h1>로그인</h1><p>{destination === "practice" ? "로그인하면 바로 면접 연습 채팅으로 연결돼요." : "Google 계정으로 로그인하면 분석 결과를 안전하게 확인할 수 있어요."}</p>{!isSupabaseConfigured() && <p className="field-error server-error">Supabase URL과 publishable key를 설정해 주세요.</p>}{error && <p className="field-error server-error" role="alert">{error}</p>}<button className="flow-primary-button" type="button" onClick={() => void signIn()} disabled={!isSupabaseConfigured()}>Google로 계속하기</button></section></main></div>;
}
export default AuthPage;
