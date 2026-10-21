import { useLoadingProgress } from "../api/loadingProgress";
import { LoadingProgress } from "../components/LoadingProgress";
import { useEffect, useRef, useState } from "react";
import { normalizeTranscript, type NormalizationResult } from "../api/transcriptNormalization";
import type { PracticeQuestion } from "./PracticePage";
import type { AnalysisResult } from "../mocks/analysisMock";
import { supabase } from "../api/supabaseAuth";
import "../styles/flow-pages.css";
import "../styles/coaching-demo.css";
import "../styles/practice-page.css";
import { AppHeader } from "../navigation";
import { confirmAnswerRevision, type AnswerRevision } from "../api/answerRevisions";
import { requestCoaching, type CoachingResponse } from "../api/coaching";
import { CoachingResultPanel } from "../components/CoachingResultPanel";
import { answerMessageId, coachingMessageId, quoteEvidenceId, workspaceId } from "../components/PracticeWorkspace";
import { useCoachThreadAutoScroll } from "../hooks/useCoachThreadAutoScroll";
import coachCoaching from "../assets/coach-coaching.png";
import coachComparing from "../assets/coach-comparing.png";

type ResultPageProps = {
  question: PracticeQuestion;
  result: AnalysisResult;
  stepLabel: "1차" | "2차";
  nextLabel: string;
  onNext: () => void;
  onCoachingReady?: () => void;
  comparisonOnly?: boolean;
  onWorkspaceReady?: (revision: AnswerRevision, coaching?: CoachingResponse) => void;
  onEvidenceSelect?: (taskId: string, messageId: string, evidenceId?: string) => void;
  showNextAction?: boolean;
};
function ResultPage({ question, result, stepLabel, nextLabel, onNext, onCoachingReady, comparisonOnly = false, showNextAction = true }: ResultPageProps) {
  const coachThreadRef = useCoachThreadAutoScroll();
  return (
    <div className="practice-page coach-chat-page result-chat-page">
      <AppHeader />
      <main className="coach-chat-layout result-chat-layout">
        <aside className="coach-sidebar" aria-label="연습 진행 단계">
          <div className="coach-sidebar-intro"><span className="coach-avatar" aria-hidden="true">✦</span><div><strong>면접 코치</strong><span>답변을 함께 다듬어요</span></div></div>
          <ol className="coach-step-list"><li className="is-complete"><span>01</span><strong>연습 조건</strong><i aria-hidden="true">✓</i></li><li className="is-complete"><span>02</span><strong>질문 선택</strong><i aria-hidden="true">✓</i></li><li className="is-complete"><span>03</span><strong>답변 녹음</strong><i aria-hidden="true">✓</i></li><li className="is-current"><span>04</span><strong>코칭 확인</strong></li></ol>
          <p className="coach-sidebar-note">수정해 확정한 전사문을 기준으로 코칭과 예시 답안을 만들어요.</p>
        </aside>
        <section className="coach-chat-panel" aria-labelledby="result-chat-title">
          <header className="coach-chat-header"><div><p>말해봄 AI 코치</p><h1 id="result-chat-title">답변을 함께 다듬어볼까요?</h1></div><span className="coach-online-status"><i aria-hidden="true" />코칭 준비 중</span></header>
          <div className="coach-thread" ref={coachThreadRef}>
            <article className="coach-message coach-message-user"><div><span>나 · {stepLabel} 답변</span><strong>답변 분석을 보냈어요.</strong></div></article>
            <CoachingChatMessages question={question} result={result} stepLabel={stepLabel} nextLabel={nextLabel} onNext={onNext} onCoachingReady={onCoachingReady} comparisonOnly={comparisonOnly} showNextAction={showNextAction} />
          </div>
        </section>
      </main>
    </div>
  );
}

export function CoachingChatMessages({ question, result, stepLabel, nextLabel, onNext, onCoachingReady, comparisonOnly = false, onWorkspaceReady, onEvidenceSelect, showNextAction = true }: ResultPageProps) {
  const [nextActionReady, setNextActionReady] = useState(false);
  // 실제 API의 answerDurationSec가 없는 오래된 mock은 절대 횟수만 표시하고 참고 기준은 숨깁니다.
  const longSilencesPerMinute = perMinute(result.longSilence, result.answerDurationSec);
  const repetitionsPer100Words = per100Words(result.repeatedExpressions, result.transcript);
  const longSilenceValue = longSilencesPerMinute ?? safeCount(result.longSilence);
  const repetitionValue = repetitionsPer100Words ?? 0;
  return <>
    <article id={workspaceId("message", result.analysisJobId || "unavailable", "analysis")} className="coach-message coach-message-assistant coach-result-message"><span className="coach-message-avatar" aria-hidden="true">✦</span><div><strong>말해봄 코치</strong><p><b>{stepLabel} 분석 결과</b>예요. STT가 인식한 전사문을 확인하고, 오인식된 표현이 있으면 수정해 주세요.</p><div className="coach-result-question"><span>선택한 질문</span><strong>{question.question}</strong></div></div></article>
    <TranscriptConfirmationSection onWorkspaceReady={onWorkspaceReady} onEvidenceSelect={onEvidenceSelect} result={result} comparisonOnly={comparisonOnly} onNextActionReady={() => {
      setNextActionReady(true);
      onCoachingReady?.();
    }} />
    {nextActionReady && !comparisonOnly && <article className="coach-message coach-message-assistant coach-delivery-message"><span className="coach-message-avatar" aria-hidden="true">✦</span><div><strong>말해봄 코치</strong><p>전달 방식도 함께 확인했어요.</p><div className="analysis-metrics-grid"><VerticalBarCard label="말하기 속도" value={result.speakingRate} reference={result.referenceMetrics.pace.value} valueUnit=" CPM" /><VerticalBarCard label="긴 침묵" value={longSilenceValue} reference={longSilencesPerMinute === null ? undefined : result.referenceMetrics.longSilenceCount.value} valueUnit={longSilencesPerMinute === null ? "회" : "회/분"} referenceUnit="회/분" referenceUnavailableLabel="비교 불가" /><VerticalBarCard label="반복 표현" value={repetitionValue} reference={result.referenceMetrics.repetitionCount.value} valueUnit="회/100어절" referenceUnit="회/100어절" /></div>{result.feedback.length > 0 ? <div className="action-feedback-list">{result.feedback.slice(0, 2).map((item) => <article className="action-feedback" key={item.title}><h3>{item.title}</h3><p>{item.nextPractice}</p></article>)}</div> : <p>현재 분석 기준에서 우선 바꿀 전달 방식이 없어요.</p>}</div></article>}
    {nextActionReady && <article className="coach-message coach-message-assistant coach-next-message"><span className="coach-message-avatar" aria-hidden="true">✦</span><div><strong>말해봄 코치</strong><p>{comparisonOnly ? "2차 전사문을 확인했어요. 1차 답변과 코칭 후 재답변의 변화를 비교해 볼까요?" : showNextAction ? "코칭 내용을 바탕으로 다시 연습해 볼까요?" : "코칭 내용에서 궁금한 점은 채팅으로 물어보세요. 준비되면 ‘재답변하기’라고 입력하거나 보내기 옆 재답변하기 버튼을 눌러주세요."}</p>{showNextAction && <button className="coach-recording-button" type="button" onClick={onNext}>{nextLabel}</button>}</div></article>}
  </>;
}

function perMinute(count: number | undefined, answerDurationSec?: number): number | null {
  if (typeof count !== "number" || typeof answerDurationSec !== "number" || !Number.isFinite(count) || !Number.isFinite(answerDurationSec) || answerDurationSec <= 0) return null;
  return roundToTwoDecimals((count / answerDurationSec) * 60);
}

function per100Words(count: number | undefined, transcript: string | undefined): number | null {
  const wordCount = transcript?.trim().split(/\s+/).filter(Boolean).length ?? 0;
  if (typeof count !== "number" || !Number.isFinite(count) || wordCount === 0) return null;
  return roundToTwoDecimals((count / wordCount) * 100);
}

function safeCount(value: number | undefined): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function roundToTwoDecimals(value: number): number {
  return Math.round(value * 100) / 100;
}

function VerticalBarCard({ label, value, reference, valueUnit, referenceUnit = valueUnit, referenceUnavailableLabel = "-" }: { label: string; value: number; reference?: number; valueUnit: string; referenceUnit?: string; referenceUnavailableLabel?: string }) {
  const hasReference = typeof reference === "number" && Number.isFinite(reference);
  const max = Math.max(value, hasReference ? reference : 0, 1);
  const currentPercent = Math.max((value / max) * 100, 8);
  const referencePercent = hasReference ? Math.max((reference / max) * 100, 8) : 0;
  return <article className="metric-visual-card metric-comparison-card">
    <div className="metric-card-heading"><h3>{label}</h3></div>
    <div className="metric-reading-list">
      <MetricReading label="나의 결과" value={value} unit={valueUnit} tone="current" />
      <MetricReading label="참고 기준" value={reference} unit={referenceUnit} tone="reference" fallback={referenceUnavailableLabel} />
    </div>
    <div className="metric-track-list" aria-hidden="true">
      <span className="metric-track metric-track--current"><i style={{ width: `${currentPercent}%` }} /></span>
      <span className="metric-track metric-track--reference"><i style={{ width: `${referencePercent}%` }} /></span>
    </div>
  </article>;
}

function MetricReading({ label, value, unit, tone, fallback = "-" }: { label: string; value?: number; unit: string; tone: "current" | "reference"; fallback?: string }) {
  const hasValue = typeof value === "number" && Number.isFinite(value);
  return <div className={`metric-reading metric-reading--${tone}`}>
    <span>{label}</span>
    <strong>{hasValue ? <><b>{value}</b><small>{unit.trim()}</small></> : fallback}</strong>
  </div>;
}

function TranscriptNormalizationProgress({ jobId }: { jobId: string }) {
  const stage = useLoadingProgress(`/analysis-jobs/${encodeURIComponent(jobId)}/normalize-transcript`, "전사문과 변환 요청을 확인하고 있어요…");
  const [startedAt] = useState(() => Date.now());
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setElapsed(Math.max(0, Math.floor((Date.now() - startedAt) / 1000))), 1000);
    return () => window.clearInterval(timer);
  }, [startedAt]);
  // Recent comparable calls took 11–32 seconds; allow five seconds of overhead.
  const remaining = Math.max(0, 35 - elapsed);
  return <><LoadingProgress stage={stage} /><small className="transcript-loading-estimate" aria-live="off">
    {remaining > 0 ? `예상 남은 시간 약 ${remaining}초` : "예상보다 오래 걸리고 있어요"} · 경과 {elapsed}초
  </small></>;
}

function TranscriptConfirmationSection({ result, comparisonOnly, onNextActionReady, onWorkspaceReady, onEvidenceSelect }: { result: AnalysisResult; comparisonOnly: boolean; onNextActionReady: () => void; onWorkspaceReady?: ResultPageProps["onWorkspaceReady"]; onEvidenceSelect?: ResultPageProps["onEvidenceSelect"] }) {
  const [confirmedText, setConfirmedText] = useState(result.transcript);
  const [phase, setPhase] = useState<"editing" | "confirming" | "confirmed" | "coaching" | "comparing" | "comparison-error" | "completed">("editing");
  const [revision, setRevision] = useState<AnswerRevision | null>(null);
  const [coaching, setCoaching] = useState<CoachingResponse | null>(null);
  const [error, setError] = useState("");

  const [normalizing, setNormalizing] = useState(false);
  const [normalization, setNormalization] = useState<NormalizationResult | null>(null);
  const transcriptRef = useRef<HTMLElement | null>(null);
  const isSecondAnswer = comparisonOnly || result.attemptNo === 2;
  useEffect(() => {
    if (!normalization || normalizing || phase !== "editing") return;
    transcriptRef.current?.closest(".coach-thread")?.dispatchEvent(new Event("workspace-transcript-result"));
  }, [normalization, normalizing, phase]);
  const convertTranscript = async () => {
    if (!result.analysisJobId || normalizing || phase !== "editing") return;
    setError("");
    setNormalizing(true);
    try {
      const { data } = await supabase().auth.getSession();
      if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
      const converted = await normalizeTranscript({ analysisJobId: result.analysisJobId, transcript: confirmedText, accessToken: data.session.access_token });
      setConfirmedText(converted.transcript);
      setNormalization(converted);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "표준어로 바꾸지 못했어요. 원문은 유지됩니다.");
    } finally { setNormalizing(false); }
  };

  const confirmTranscript = async () => {
    const text = confirmedText.trim();
    if (!revision && (!result.analysisJobId || !text)) {
      setError(result.analysisJobId ? "확정할 전사문을 입력해 주세요." : "분석 작업 ID를 확인하지 못했습니다.");
      return;
    }
    setError("");
    setPhase("confirming");
    try {
      const { data } = await supabase().auth.getSession();
      if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
      let activeRevision = revision;
      if (!revision) {
        const createdRevision = await confirmAnswerRevision({
          analysisJobId: result.analysisJobId as string,
          confirmedText: text,
          accessToken: data.session.access_token,
        });
        setRevision(createdRevision);
        onWorkspaceReady?.(createdRevision);
        activeRevision = createdRevision;
      }
      if (comparisonOnly) {
        await prepareComparisonAnalysis(activeRevision, data.session.access_token);
        return;
      }
      setPhase("confirmed");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "전사문을 확정하지 못했습니다.");
      setPhase("editing");
    }
  };

  const prepareComparisonAnalysis = async (activeRevision: AnswerRevision | null, accessToken: string) => {
    if (!activeRevision?.job_snapshot_id) {
      setError("이 연습에 선택한 공고 문맥이 없습니다. 공고 선택 단계부터 다시 시작해 주세요.");
      setPhase("comparison-error");
      return;
    }
    setError("");
    setPhase("comparing");
    try {
      // 재답변을 1차와 같은 기준으로 판정해 저장하지만, 2차 코칭 결과는 화면에 노출하지 않는다.
      const response = await requestCoaching({
        request: {
          action: "analyze",
          question_id: activeRevision.question_id,
          answer_revision_id: activeRevision.answer_revision_id,
          job_snapshot_id: activeRevision.job_snapshot_id,
        },
        accessToken,
      });
      if (response.status === "ok" || response.status === "needs_more_info") {
        if (activeRevision) onWorkspaceReady?.(activeRevision, response);
        setCoaching(response);
        setPhase("completed");
        onNextActionReady();
        return;
      }
      setError(toUserFacingCoachingError(new Error(response.intent_assessment.reason)));
      setPhase("comparison-error");
    } catch (cause) {
      setError(toUserFacingCoachingError(cause));
      setPhase("comparison-error");
    }
  };

  const retryComparisonAnalysis = async () => {
    const { data } = await supabase().auth.getSession();
    if (!data.session) {
      setError("로그인이 필요하거나 세션이 만료되었습니다.");
      return;
    }
    await prepareComparisonAnalysis(revision, data.session.access_token);
  };

  const startCoaching = async () => {
    if (!revision) return;
    setError("");
    setPhase("coaching");
    try {
      const { data } = await supabase().auth.getSession();
      if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
      if (!revision.job_snapshot_id) throw new Error("이 연습에 선택한 공고 문맥이 없습니다. 공고 선택 단계부터 다시 시작해 주세요.");
      const response = await requestCoaching({
        request: {
          action: "analyze",
          question_id: revision.question_id,
          answer_revision_id: revision.answer_revision_id,
          job_snapshot_id: revision.job_snapshot_id,
        },
        accessToken: data.session.access_token,
      });
      setCoaching(response);
      if (response.status === "ok" || response.status === "needs_more_info") {
        onWorkspaceReady?.(revision, response);
        setPhase("completed");
        onNextActionReady();
        return;
      }
      setError(toUserFacingCoachingError(new Error(response.intent_assessment.reason)));
      setPhase("confirmed");
    } catch (cause) {
      setError(toUserFacingCoachingError(cause));
      setPhase("confirmed");
    }
  };

  return <>
    <article ref={transcriptRef} id={revision ? answerMessageId(revision) : workspaceId("message", result.analysisJobId || "unavailable", "transcript")} data-revision-id={revision?.answer_revision_id} className={`coach-message coach-message-assistant coach-transcript-message${normalization && !normalizing && phase === "editing" ? " coach-transcript-normalized-result" : ""}`}>
      <span className="coach-message-avatar" aria-hidden="true">✦</span>
      <div className="transcript-review-card">
        <strong>말해봄 코치</strong>
        <div className="transcript-review-heading">
          <div><h3>{normalization ? "답변을 자연스럽게 다듬었어요" : "인식한 답변을 확인해 주세요"}</h3><p>내용을 확인하고, 필요한 부분은 직접 고쳐 주세요.</p></div>
          {normalization && <span className="transcript-review-badge">표준어 변환 완료</span>}
        </div>
        <div className={`transcript-editor-shell${normalizing ? " is-normalizing" : ""}`} aria-busy={normalizing}><textarea className="transcript-editor" value={confirmedText} maxLength={5000} disabled={phase !== "editing" || normalizing} aria-label="확정할 전사문" onChange={(event) => setConfirmedText(event.target.value)} /></div>
        <div className="transcript-meta"><span>{confirmedText.length} / 5000</span></div>
        {error && <p className="transcript-error" role="alert">{error}</p>}
        {normalizing && <div className={`transcript-loading${isSecondAnswer ? " coach-transcript-second-loading" : ""}`} role="status" aria-live="polite"><span>사투리 표현과 말투를 다듬고 있어요<span className="transcript-loading-dots" aria-hidden="true"><i /><i /><i /></span></span><TranscriptNormalizationProgress jobId={result.analysisJobId || ""} /></div>}
        {normalization && <div className="transcript-normalization-review">
          {normalization.confirmations.length > 0 && <details className="transcript-confirmation-fold" open>
            <summary><span className="transcript-review-warning">확인 필요</span><span>추정한 표현 {normalization.confirmations.length}개</span><span className="transcript-fold-chevron" aria-hidden="true">›</span></summary>
            <ul className="transcript-edit-rows">{normalization.confirmations.map((item, index) => <li key={index}>
              <div className="transcript-edit-pair"><span className="transcript-edit-original">{item.original}</span><span aria-hidden="true">→</span><b>{item.replacement || "삭제"}</b><span className="transcript-edit-applied">{item.applied ? "적용됨" : "미적용"}</span></div>
              <p>{item.reason}</p>
            </li>)}</ul>
          </details>}
          <div className="transcript-review-tools">
            <details className="transcript-detail-fold"><summary>STT 원문 보기</summary><p className="transcript-raw-text">{result.transcript}</p></details>
            <details className="transcript-detail-fold"><summary>전체 변경 내역</summary><ul className="transcript-edit-rows">{normalization.edit_log.map((item, index) => <li key={index}><div className="transcript-edit-pair"><span className="transcript-edit-original">{item.original}</span><span aria-hidden="true">→</span><b>{item.replacement || "삭제"}</b></div><p>{item.edit_type}: {item.reason}</p></li>)}</ul><p className="transcript-meaning-check">{normalization.meaning_preservation_check}</p></details>
          </div>
        </div>}
        {phase === "editing" && <div className="transcript-review-footer">
          <span>확정 후 이 전사문으로 답변을 분석해요.</span>
          <div className="transcript-actions">{result.analysisJobId && <button className="transcript-convert-button" type="button" disabled={normalizing || !confirmedText.trim()} onClick={(event) => { event.currentTarget.closest(".coach-thread")?.dispatchEvent(new Event("workspace-next-stage")); void convertTranscript(); }}>표준어로 변경하기</button>}<button className="transcript-confirm-button" type="button" disabled={normalizing || !confirmedText.trim()} onClick={(event) => { event.currentTarget.closest(".coach-thread")?.dispatchEvent(new Event("workspace-next-stage")); void confirmTranscript(); }}>이 전사문으로 확정하기</button></div>
        </div>}
      </div>
    </article>
    {phase === "confirming" && <CoachTypingBubble label="수정한 전사문을 저장하고 있어요" />}
    {phase === "confirmed" && <article className="coach-message coach-message-assistant coach-coaching-start-message"><span className="coach-message-avatar" aria-hidden="true">✦</span><div><strong>말해봄 코치</strong><p>전사문을 확인했어요. 이 답변을 기준으로 공고 요구사항과 답변 구조를 코칭할게요.</p><button className="coach-recording-button" type="button" onClick={(event) => { event.currentTarget.closest(".coach-thread")?.dispatchEvent(new Event("workspace-next-stage")); void startCoaching(); }}>코칭 시작</button></div></article>}
    {phase === "coaching" && <CoachTypingBubble label="답변을 코칭하고 예시 답안을 만들고 있어요" coaching />}
    {phase === "comparing" && <CoachTypingBubble label="1차 답변과 비교할 내용을 정리하고 있어요" comparing />}
    {phase === "comparison-error" && <article className="coach-message coach-message-assistant coach-next-message"><span className="coach-message-avatar" aria-hidden="true">✦</span><div><strong>말해봄 코치</strong><p className="transcript-error" role="alert">{error}</p><button className="coach-recording-button" type="button" onClick={() => void retryComparisonAnalysis()}>비교 분석 다시 준비하기</button></div></article>}
    {phase === "completed" && coaching && <article id={revision ? coachingMessageId(revision) : undefined} data-message-id={revision ? coachingMessageId(revision) : undefined} data-task-id={revision ? workspaceId("task", revision.analysis_job_id, revision.answer_revision_id, "coaching") : undefined} className="coach-message coach-message-assistant coach-coaching-result-message"><span className="coach-message-avatar" aria-hidden="true">✦</span>{coaching.status === "ok" || coaching.status === "needs_more_info" ? comparisonOnly ? <div className="workspace-comparison-evidence"><strong>재답변 비교용 근거</strong><p>같은 기준으로 평가한 2차 답변의 인용이에요. 상세 변화는 답변 비교에서 확인해 주세요.</p><details className="workspace-coaching-details"><summary>비교에 사용한 답변 근거 보기</summary>{revision && coaching.evidence.map((item) => <blockquote key={quoteEvidenceId(revision, item)} id={quoteEvidenceId(revision, item)}>{item.quote}{onEvidenceSelect && <button className="workspace-quote-link" type="button" onClick={() => onEvidenceSelect(workspaceId("task", revision.analysis_job_id, revision.answer_revision_id, "coaching"), coachingMessageId(revision), quoteEvidenceId(revision, item))}>근거 자료실과 연결 →</button>}</blockquote>)}{revision && coaching.gaps.map((gap) => <p key={gap.criterion_id} id={workspaceId("check", revision.answer_revision_id, gap.criterion_id)}>{gap.needed}{onEvidenceSelect && <button className="workspace-quote-link" type="button" onClick={() => onEvidenceSelect(workspaceId("task", revision.analysis_job_id, revision.answer_revision_id, "coaching"), coachingMessageId(revision), workspaceId("check", revision.answer_revision_id, gap.criterion_id))}>추가 확인 사항과 연결 →</button>}</p>)}</details></div> : <CoachingResultPanel result={coaching} revision={revision || undefined} onEvidenceSelect={onEvidenceSelect} /> : <div className="coaching-state coaching-state--error"><strong>현재 질문은 코칭할 수 없어요.</strong><p>{coaching.intent_assessment.reason}</p></div>}</article>}
  </>;
}

function toUserFacingCoachingError(cause: unknown): string {
  const message = cause instanceof Error ? cause.message : "";
  if (/공급자|MCP|Supabase|설정/.test(message)) {
    return "코칭 연결에 문제가 생겼어요. 잠시 후 다시 시도해 주세요.";
  }
  return message || "코칭 결과를 불러오지 못했습니다.";
}

function CoachTypingBubble({ label, coaching = false, comparing = false }: { label: string; coaching?: boolean; comparing?: boolean }) {
  const stage = useLoadingProgress("/api/agent", "분석 요청을 준비하고 있어요…");
  const visibleStage = comparing ? stage.replace("답변의 강점과 보완할 내용을", "재답변을 같은 기준으로").replace("코칭 결과", "재답변 분석 결과") : stage;
  if (coaching || comparing) return <article className={`coach-message coach-message-assistant coach-typing-message coach-analysis-loading${comparing ? " coach-comparison-loading" : ""}`} role="status" aria-live="polite">
    <span className="coach-message-avatar" aria-hidden="true">✦</span>
    <div className="coach-analysis-status">
      <img className="coach-state-mascot" src={comparing ? coachComparing : coachCoaching} alt={comparing ? "답변을 비교하는 말해봄 코치" : "답변을 코칭하는 말해봄 코치"} />
      <div className="coach-analysis-copy">
        <span className="coach-analysis-badge"><span className="coach-typing-dots" aria-hidden="true"><i /><i /><i /></span>{comparing ? "비교 중" : "코칭 중"}</span>
        <strong className="coach-analysis-title">{label}</strong>
        {comparing ? <p>두 답변을 같은 기준으로 비교하고 있어요.<br />완료되면 내용과 전달 방식의 변화를 확인할 수 있어요.</p> : <p>답변의 강점과 보완점을 정리하고 있어요.<br />완료되면 코칭과 예시 답안을 확인할 수 있어요.</p>}
      </div>
      <LoadingProgress stage={visibleStage} />
    </div>
  </article>;
  return <article className="coach-message coach-message-assistant coach-typing-message" role="status" aria-live="polite"><span className="coach-message-avatar" aria-hidden="true">✦</span><div><strong>말해봄 코치</strong><span className="coach-typing-label">{label}</span><span className="coach-typing-dots" aria-label="입력 중"><i /><i /><i /></span></div></article>;
}

export default ResultPage;
