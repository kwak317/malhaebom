import { useCallback, useEffect, useState } from "react";
import { CoachingApiError, requestCoaching, type CoachingResponse } from "../api/coaching";
import { supabase } from "../api/supabaseAuth";
import { CoachingResultPanel } from "../components/CoachingResultPanel";
import "../styles/coaching-demo.css";

const DEMO_REQUEST = {
  action: "analyze" as const,
  question_id: "preset-04",
  answer_revision_id: "00000000-0000-0000-0000-000000000101",
  job_snapshot_id: "00000000-0000-0000-0000-000000000201",
};

export default function CoachingDemoPage() {
  const [result, setResult] = useState<CoachingResponse | null>(null);
  const [failure, setFailure] = useState<CoachingApiError | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setFailure(null);
    try {
      const demoToken = import.meta.env.VITE_COACHING_DEMO_TOKEN?.trim();
      const accessToken = demoToken || (await supabase().auth.getSession()).data.session?.access_token;
      if (!accessToken) throw new CoachingApiError("auth_error", "로그인이 필요하거나 세션이 만료되었습니다.", false, 401);
      setResult(await requestCoaching({ request: DEMO_REQUEST, accessToken }));
    } catch (error) {
      setFailure(error instanceof CoachingApiError ? error : new CoachingApiError("provider_error", "코칭 서버에 연결하지 못했습니다.", true, null));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return <main className="coaching-demo-page">
    {loading && <section className="coaching-state" aria-live="polite"><span className="coaching-spinner" />코칭 결과를 확인하고 있어요.</section>}
    {failure && <section className="coaching-state coaching-state--error" role="alert">
      <strong>{failure.message}</strong><span>상태: {failure.state}</span>
      {failure.retryable && <button type="button" onClick={() => void load()}>다시 시도</button>}
    </section>}
    {result && <CoachingResultPanel result={result} />}
  </main>;
}
