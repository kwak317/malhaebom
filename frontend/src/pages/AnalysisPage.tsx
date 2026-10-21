import { LoadingProgress } from "../components/LoadingProgress";
import { useEffect, useRef, useState } from "react";
import type { PracticeQuestion } from "./PracticePage";
import type { AnalysisResult } from "../mocks/analysisMock";
import { supabase } from "../api/supabaseAuth";
import "../styles/flow-pages.css";
import "../styles/practice-page.css";
import { AppHeader } from "../navigation";
import { API_BASE_URL } from "../config/apiBase";
import coachTranscribing from "../assets/coach-transcribing.png";

type Props = {
  question: PracticeQuestion;
  attemptNo: 1 | 2;
  audio: Blob;
  practiceSessionId?: string;
  onComplete: (result: AnalysisResult) => void;
  isLoggedIn: boolean;
  onLogin: () => void;
  onBack: () => void;
  showSubmittedAnswer?: boolean;
};
type DeliveryFeedback = { action?: string; code?: string; evidence?: string };
const base = API_BASE_URL;
const DATA_REFERENCE_METRICS = {
  pace: { value: 320 },
  longSilenceCount: { value: 2.48 },
  repetitionCount: { value: 0.41 },
};
const ANALYSIS_STATUS_POLL_INTERVAL_MS = 350;
// 응답이 즉시 완료돼도 사용자가 분석 중임을 인지할 수 있도록 말풍선을 잠시 유지한다.
const MIN_ANALYSIS_TYPING_DURATION_MS = 450;

function feedbackTitle(item: DeliveryFeedback, index: number) {
  if (item.code === "SPEED_FAST" || item.code === "SPEED_SLOW") return "말하기 속도";
  if (item.code === "LONG_SILENCE") return "긴 침묵";
  if (item.code === "FILLER_REPEAT") return "반복 표현";
  return `분석 피드백 ${index + 1}`;
}

async function getApiError(response: Response, fallback: string) {
  try {
    const payload: unknown = await response.json();
    if (typeof payload !== "object" || payload === null || !("detail" in payload)) return fallback;
    const detail = payload.detail;
    if (typeof detail === "string") return detail;
    if (typeof detail === "object" && detail !== null && "message" in detail && typeof detail.message === "string") return detail.message;
  } catch {
    // 오류 응답이 JSON이 아니면 공통 안내를 표시한다.
  }
  return fallback;
}

type AnalysisJobFormInput = {
  question: PracticeQuestion;
  attemptNo: 1 | 2;
  audio: Blob;
  practiceSessionId?: string;
  sourceId?: string;
};

export function buildAnalysisJobForm({
  question,
  attemptNo,
  audio,
  practiceSessionId,
  sourceId = crypto.randomUUID(),
}: AnalysisJobFormInput): FormData {
  const sessionId = (practiceSessionId || question.practiceSessionId)?.trim();
  if (attemptNo === 2 && !sessionId) {
    throw new Error(
      "첫 번째 답변의 연습 세션을 찾지 못했습니다. 첫 답변부터 다시 진행해 주세요.",
    );
  }

  const form = new FormData();
  form.set("source_id", sourceId);
  form.set("question_type", question.questionType);
  form.set("attempt_no", String(attemptNo));
  if (sessionId) {
    form.set("practice_session_id", sessionId);
  }
  if (question.questionType === "preset") {
    form.set("question_id", question.questionId || "");
  } else {
    form.set("custom_question_text", question.question);
  }
  form.set("audio", audio, audio instanceof File ? audio.name : "answer.webm");
  return form;
}

export function AnswerAnalysisChat({ question, attemptNo, audio, practiceSessionId, onComplete, isLoggedIn, onLogin, onBack, showSubmittedAnswer = true }: Props) {
  const onCompleteRef = useRef(onComplete);
  useEffect(() => { onCompleteRef.current = onComplete; }, [onComplete]);
  const [error, setError] = useState("");
  const [analysisStage, setAnalysisStage] = useState("보낸 답변을 분석하고 있어요.");
  const visibleAnalysisStage = analysisStage;
  useEffect(() => {
    if (!isLoggedIn) return undefined;
    const abort = new AbortController();
    const analysisStartedAt = Date.now();
    void (async () => {
      const form = buildAnalysisJobForm({ question, attemptNo, audio, practiceSessionId });
      const { data } = await supabase().auth.getSession();
      if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
      const created = await fetch(`${base}/analysis-jobs`, { method: "POST", headers: { Authorization: `Bearer ${data.session.access_token}` }, body: form, signal: abort.signal });
      if (!created.ok) throw new Error(await getApiError(created, "분석 요청에 실패했습니다.")); const job = await created.json();
      for (;;) {
        const response = await fetch(`${base}/analysis-jobs/${job.job_id}`, {
          headers: { Authorization: `Bearer ${data.session.access_token}` },
          signal: abort.signal,
        });
        if (!response.ok) throw new Error(await getApiError(response, "분석 상태를 확인하지 못했습니다."));

        const current = await response.json();
        if (typeof current.progress?.stage === "string" && current.progress.stage.trim()) {
          setAnalysisStage(current.progress.stage);
        }
        if (current.status === "completed") {
          const remainingTypingTime = MIN_ANALYSIS_TYPING_DURATION_MS - (Date.now() - analysisStartedAt);
          if (remainingTypingTime > 0) {
            await new Promise((resolve) => window.setTimeout(resolve, remainingTypingTime));
          }
          if (abort.signal.aborted) return;

          const metrics = current.delivery?.metrics || {};
          const feedback = (Array.isArray(current.delivery?.feedback) ? current.delivery.feedback : [])
            .slice(0, 2)
            .map((item: DeliveryFeedback, index: number) => ({
              title: feedbackTitle(item, index),
              measurement: item.evidence || "측정 결과를 확인하지 못했어요.",
              nextPractice: item.action || "다음 답변에서 다시 점검해 보세요.",
            }));
          onCompleteRef.current({
            attemptNo,
            analysisJobId: String(job.job_id),
            practiceSessionId: String(current.practice_session_id || job.practice_session_id || ""),
            transcript: current.result?.text || "",
            answerDurationSec: metrics.answer_duration_sec,
            speakingRate: Math.round(metrics.cpm || 0),
            longSilence: metrics.long_silences?.length || 0,
            repeatedExpressions: metrics.repetitions?.length || 0,
            feedback,
            prosodyReferenceAvailable: true,
            referenceMetrics: DATA_REFERENCE_METRICS,
            contentFeedback: { text: "" },
          });
          return;
        }
        if (current.status === "failed") throw new Error(current.error?.message || "분석에 실패했습니다.");
        await new Promise((resolve) => window.setTimeout(resolve, ANALYSIS_STATUS_POLL_INTERVAL_MS));
      }
    })().catch((cause) => { if (!abort.signal.aborted) setError(cause instanceof Error ? cause.message : "분석에 실패했습니다."); });
    return () => abort.abort();
  }, [audio, attemptNo, isLoggedIn, practiceSessionId, question]);
  const submittedAnswer = audio instanceof File ? "WAV 파일을 보냈어요." : "답변 녹음을 보냈어요.";

  return <>
    {showSubmittedAnswer && <article className="coach-message coach-message-user coach-audio-message">
      <div>
        <span>나 · 답변 분석</span>
        <strong>{submittedAnswer}</strong>
      </div>
    </article>}
    {!isLoggedIn ? (
      <article className="coach-message coach-message-assistant coach-recording-message" role="alert">
        <span className="coach-message-avatar" aria-hidden="true">✦</span>
        <div className="coach-recording-panel"><strong>말해봄 코치</strong><p>답변을 분석하려면 로그인이 필요해요.</p><button className="coach-recording-button" type="button" onClick={onLogin}>로그인하기</button></div>
      </article>
    ) : error ? (
      <article className="coach-message coach-message-assistant coach-recording-message" role="alert">
        <span className="coach-message-avatar" aria-hidden="true">✦</span>
        <div className="coach-recording-panel"><strong>말해봄 코치</strong><p>답변을 분석하지 못했어요. {error}</p><button className="coach-recording-button" type="button" onClick={onBack}>다시 녹음하기</button></div>
      </article>
    ) : (
      <article className="coach-message coach-message-assistant coach-typing-message coach-analysis-loading" role="status" aria-live="polite">
        <span className="coach-message-avatar" aria-hidden="true">✦</span>
        <div className="coach-analysis-status">
          <img className="coach-state-mascot" src={coachTranscribing} alt="답변을 전사하는 말해봄 코치" />
          <div className="coach-analysis-copy">
            <span className="coach-analysis-badge"><span className="coach-typing-dots" aria-hidden="true"><i /><i /><i /></span>{visibleAnalysisStage.includes("전사") ? "전사 중" : "분석 중"}</span>
            <strong className="coach-analysis-title">{visibleAnalysisStage.includes("전사") ? "말씀하신 내용을 글로 옮기고 있어요" : visibleAnalysisStage}</strong>
            <p>완료되면 전사문을 확인하고<br />직접 수정할 수 있어요.</p>
          </div>
          <LoadingProgress stage={analysisStage} />
        </div>
      </article>
    )}
  </>;
}

function AnalysisPage(props: Props) {
  return (
    <div className="flow-page">
      <AppHeader />
      <main className="flow-main">
        <section className="flow-card analysis-card" aria-live="polite">
          <div className="coach-thread">
            <AnswerAnalysisChat {...props} />
          </div>
        </section>
      </main>
    </div>
  );
}
export default AnalysisPage;
