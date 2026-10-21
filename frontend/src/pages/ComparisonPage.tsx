import { useEffect, useState } from "react";
import { fetchPracticeRecord, type ComparisonDirection, type PracticeComparison, type PracticeHistoryRecord, type PracticeMetricChange } from "../api/practiceHistory";
import { supabase } from "../api/supabaseAuth";
import { ComparisonAnswerSources } from "../components/ComparisonAnswerSources";
import { ComparisonFeedbackSummary } from "../components/ComparisonFeedbackSummary";
import { AttemptContentComparison } from "../components/AttemptContentComparison";
import type { AnalysisResult } from "../mocks/analysisMock";
import { AppHeader } from "../navigation";
import "../styles/flow-pages.css";
import type { PracticeQuestion } from "./PracticePage";

type ComparisonPageProps = {
  question: PracticeQuestion;
  firstResult: AnalysisResult;
  secondResult: AnalysisResult;
  onReturnHome: () => void;
  initialComparison?: PracticeComparison;
};

function ComparisonPage({ question, firstResult, secondResult, onReturnHome, initialComparison }: ComparisonPageProps) {
  const [comparison, setComparison] = useState<PracticeComparison | null>(initialComparison ?? null);
  const [record, setRecord] = useState<PracticeHistoryRecord | null>(null);
  const [loadState, setLoadState] = useState<"idle" | "loading" | "ready" | "error">(initialComparison ? "ready" : "idle");

  useEffect(() => {
    if (initialComparison || !question.practiceSessionId) return;
    let isCurrent = true;
    setLoadState("loading");
    void supabase().auth.getSession()
      .then(({ data, error }) => {
        if (error || !data.session?.access_token) throw new Error("로그인 세션을 찾을 수 없습니다.");
        return fetchPracticeRecord(question.practiceSessionId!, data.session.access_token);
      })
      .then((record) => {
        if (!isCurrent) return;
        setRecord(record);
        setComparison(record.comparison ?? null);
        setLoadState("ready");
      })
      .catch(() => {
        if (isCurrent) setLoadState("error");
      });
    return () => { isCurrent = false; };
  }, [initialComparison, question.practiceSessionId]);

  const delivery = comparison?.delivery ?? fallbackDelivery(firstResult, secondResult);
  const firstTranscript = record?.attempts.find((attempt) => attempt.attempt_no === 1)?.transcript || firstResult.transcript;
  const secondTranscript = record?.attempts.find((attempt) => attempt.attempt_no === 2)?.transcript || secondResult.transcript;

  return (
    <div className="flow-page">
      <AppHeader />
      <main className="flow-main result-main">
        <section className="flow-card result-card">
          <p className="flow-eyebrow">2차 분석 결과 / 비교</p>
          <h1>두 답변에서 확인된 변화를 살펴보세요.</h1>
          <div className="flow-question"><span>선택한 질문</span><strong>{question.question}</strong></div>

          <ComparisonAnswerSources firstTranscript={firstTranscript} secondTranscript={secondTranscript}
            feedback={record?.attempts.find((attempt) => attempt.attempt_no === 1)?.feedback
              ?? firstResult.feedback.map((item) => item.nextPractice)} />

          <section className="result-section">
            <h2>기준별 내용 비교</h2>
            <p className="comparison-section-description">각 답변에서 실제로 확인된 문장만 같은 기준으로 비교합니다.</p>
            <AttemptContentComparison comparison={comparison} isLoading={loadState === "loading"} loadError={loadState === "error"} />
          </section>

          <section className="result-section">
            <h2>전달력 수치 비교</h2>
            <div className="comparison-grid">
              <div /><strong>1차</strong><strong>2차</strong>
              <span>말하기 속도</span><span>{formatMetric(delivery.cpm.first, " 음절/분")}</span><span>{formatMetric(delivery.cpm.second, " 음절/분")}</span>
              <span>긴 침묵</span><span>{formatMetric(delivery.long_silence_count.first, "회")}</span><span>{formatMetric(delivery.long_silence_count.second, "회")}</span>
              <span>반복 표현</span><span>{formatMetric(delivery.repetition_count.first, "회")}</span><span>{formatMetric(delivery.repetition_count.second, "회")}</span>
            </div>
            <div className="delivery-change-list">
              <p>{describeMetricChange("말하기 속도", delivery.cpm, " 음절/분")}</p>
              <p>{describeMetricChange("긴 침묵", delivery.long_silence_count, "회")}</p>
              <p>{describeMetricChange("반복 표현", delivery.repetition_count, "회")}</p>
            </div>
          </section>

          <ComparisonFeedbackSummary comparison={comparison} />
          <p className="comparison-caution">이 비교는 답변에 드러난 설명과 전달력 수치의 변화만 보여줍니다. 합격 가능성, 실제 역량 향상 또는 경험의 사실 여부를 판정하지 않습니다.</p>
          <button className="flow-primary-button" type="button" onClick={onReturnHome}>첫 화면으로 돌아가기</button>
        </section>
      </main>
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
  let direction: ComparisonDirection = "unavailable";
  if (first !== null && second !== null) direction = second > first ? "increased" : second < first ? "decreased" : "same";
  return { first, second, direction };
}

function formatMetric(value: number | null, suffix: string): string {
  return value === null ? "확인 불가" : `${Math.round(value)}${suffix}`;
}

export function describeMetricChange(label: string, metric: PracticeMetricChange, suffix: string): string {
  if (metric.direction === "unavailable" || metric.first === null || metric.second === null) return `${label} 변화는 확인할 수 없어요.`;
  const before = formatMetric(metric.first, suffix);
  const after = formatMetric(metric.second, suffix);
  if (metric.direction === "same") return `${label}: 1차와 2차가 동일해요 (${before}).`;
  return `${label}: ${before}에서 ${after}로 ${metric.direction === "increased" ? "증가했어요" : "감소했어요"}.`;
}

export default ComparisonPage;
