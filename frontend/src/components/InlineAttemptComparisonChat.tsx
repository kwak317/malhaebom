import { useEffect, useState } from "react";
import {
  fetchPracticeRecord,
  type PracticeComparison,
  type PracticeHistoryRecord,
  type PracticeMetricChange,
} from "../api/practiceHistory";
import { supabase } from "../api/supabaseAuth";
import type { AnalysisResult } from "../mocks/analysisMock";
import type { PracticeQuestion } from "../pages/PracticePage";
import { ComparisonAnswerSources } from "./ComparisonAnswerSources";
import { AttemptContentComparison } from "./AttemptContentComparison";
import { ComparisonFeedbackSummary } from "./ComparisonFeedbackSummary";
import { PostComparisonActions } from "./PostComparisonActions";
import type { ResumeDraftMaterials } from "./ResumeDraftChat";

type InlineAttemptComparisonChatProps = {
  question: PracticeQuestion;
  firstResult: AnalysisResult;
  secondResult: AnalysisResult;
  resumeDraftMaterials?: ResumeDraftMaterials;
};

type LoadState = "loading" | "ready" | "error";

const MIN_COMPARISON_TYPING_DURATION_MS = 450;

export function InlineAttemptComparisonChat({
  question,
  firstResult,
  secondResult,
  resumeDraftMaterials,
}: InlineAttemptComparisonChatProps) {
  const [comparison, setComparison] = useState<PracticeComparison | null>(null);
  const [record, setRecord] = useState<PracticeHistoryRecord | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    setLoadState("loading");
    let isCurrent = true;
    const startedAt = Date.now();
    const finish = async (state: LoadState) => {
      const remaining = MIN_COMPARISON_TYPING_DURATION_MS - (Date.now() - startedAt);
      if (remaining > 0) await new Promise((resolve) => window.setTimeout(resolve, remaining));
      if (isCurrent) setLoadState(state);
    };

    if (!question.practiceSessionId) {
      void finish("ready");
      return () => { isCurrent = false; };
    }

    void supabase().auth.getSession()
      .then(({ data, error }) => {
        if (error || !data.session?.access_token) throw new Error("로그인 세션을 찾을 수 없습니다.");
        return fetchPracticeRecord(question.practiceSessionId!, data.session.access_token);
      })
      .then((nextRecord) => {
        if (!isCurrent) return;
        setRecord(nextRecord);
        setComparison(nextRecord.comparison ?? null);
        return finish("ready");
      })
      .catch(() => {
        void finish("error");
      });

    return () => { isCurrent = false; };
  }, [question.practiceSessionId, retryCount]);

  if (loadState === "loading") {
    return (
      <article className="coach-message coach-message-assistant coach-typing-message" role="status" aria-live="polite">
        <span className="coach-message-avatar" aria-hidden="true">✦</span>
        <div>
          <strong>말해봄 코치</strong>
          <span className="coach-typing-label">1차 답변과 재답변을 비교하고 있어요.</span>
          <span className="coach-typing-dots" aria-label="코치가 입력 중입니다."><i /><i /><i /></span>
        </div>
      </article>
    );
  }

  const delivery = comparison?.delivery ?? fallbackDelivery(firstResult, secondResult);
  const firstTranscript = record?.attempts.find((attempt) => attempt.attempt_no === 1)?.transcript || firstResult.transcript;
  const secondTranscript = record?.attempts.find((attempt) => attempt.attempt_no === 2)?.transcript || secondResult.transcript;

  return (
    <><article className="coach-message coach-message-assistant coach-inline-comparison" aria-live="polite">
      <span className="coach-message-avatar" aria-hidden="true">✦</span>
      <div>
        <strong>말해봄 코치</strong>
        <h2>1차 답변과 재답변을 비교했어요.</h2>
        <p>코칭 후 답변에서 달라진 내용과 전달 방식을 같은 기준으로 확인해 보세요.</p>

        <div className="workspace-summary-grid"><article><span>새로 확인된 설명</span><strong>{comparison?.content_available ? `${comparison.added_explanations.length}개` : "비교 자료 확인 필요"}</strong></article><article><span>남은 보완 사항</span><strong>{comparison?.content_available ? `${comparison.still_missing.length}개` : "비교 자료 확인 필요"}</strong></article></div>
        <section className="workspace-comparison-details" aria-label="두 답변과 기준별 변화">
        <ComparisonAnswerSources firstTranscript={firstTranscript} secondTranscript={secondTranscript}
          feedback={record?.attempts.find((attempt) => attempt.attempt_no === 1)?.feedback
            ?? firstResult.feedback.map((item) => item.nextPractice)} />

        <section className="inline-comparison-section">
          <h3>내용 변화</h3>
          <AttemptContentComparison comparison={comparison} loadError={loadState === "error"} />
        </section>

        <section className="inline-comparison-section">
          <h3>전달력 변화</h3>
          <div className="inline-comparison-metrics">
            <Metric label="말하기 속도" metric={delivery.cpm} suffix=" 음절/분" />
            <Metric label="긴 침묵" metric={delivery.long_silence_count} suffix="회" />
            <Metric label="반복 표현" metric={delivery.repetition_count} suffix="회" />
          </div>
        </section>

        </section>
        <p className="inline-comparison-caution">답변에 드러난 설명과 전달력 수치만 비교하며, 실제 역량이나 경험의 사실 여부는 판정하지 않아요.</p>
        <ComparisonFeedbackSummary comparison={loadState === "ready" ? comparison : null} />
        {loadState === "error" && <button type="button" onClick={() => setRetryCount((count) => count + 1)}>비교 다시 불러오기</button>}
      </div>
    </article>
    {loadState === "ready" && comparison?.content_available && question.practiceSessionId
      ? <PostComparisonActions key={question.practiceSessionId} practiceSessionId={question.practiceSessionId} materials={resumeDraftMaterials} />
      : <p className="interview-followup-finished">두 답변의 내용 비교를 확인한 뒤 면접 대화를 이어갈 수 있어요.</p>}
    </>
  );
}

function Metric({ label, metric, suffix }: { label: string; metric: PracticeMetricChange; suffix: string }) {
  return (
    <div>
      <strong>{label}</strong>
      <p><span>1차</span>{formatMetric(metric.first, suffix)}</p>
      <p><span>재답변</span>{formatMetric(metric.second, suffix)}</p>
      <small>{describeMetricChange(label, metric, suffix)}</small>
    </div>
  );
}

function fallbackDelivery(first: AnalysisResult, second: AnalysisResult): PracticeComparison["delivery"] {
  return {
    cpm: metricChange(first.speakingRate, second.speakingRate),
    long_silence_count: metricChange(first.longSilence, second.longSilence),
    repetition_count: metricChange(first.repeatedExpressions, second.repeatedExpressions),
  };
}

function metricChange(first: number | null, second: number | null): PracticeMetricChange {
  if (first === null || second === null) return { first, second, direction: "unavailable" };
  return { first, second, direction: second > first ? "increased" : second < first ? "decreased" : "same" };
}

function formatMetric(value: number | null, suffix: string): string {
  return value === null ? "확인 불가" : `${Math.round(value)}${suffix}`;
}

function describeMetricChange(label: string, metric: PracticeMetricChange, suffix: string): string {
  if (metric.direction === "unavailable" || metric.first === null || metric.second === null) return `${label} 변화는 확인할 수 없어요.`;
  if (metric.direction === "same") return `${label}: 두 답변이 같아요 (${formatMetric(metric.first, suffix)}).`;
  return `${label}: ${formatMetric(metric.first, suffix)}에서 ${formatMetric(metric.second, suffix)}로 ${metric.direction === "increased" ? "증가" : "감소"}했어요.`;
}
