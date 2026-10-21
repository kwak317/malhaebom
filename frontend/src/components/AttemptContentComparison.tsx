import type {
  ComparisonAssessment,
  ComparisonChange,
  PracticeComparison,
  PracticeContentAssessment,
} from "../api/practiceHistory";
import type { ReactNode } from "react";
import "../styles/attempt-comparison.css";

type AttemptContentComparisonProps = {
  comparison: PracticeComparison | null;
  isLoading?: boolean;
  loadError?: boolean;
};

const assessmentLabels: Record<ComparisonAssessment, string> = {
  met: "답변에서 확인됨",
  partial: "일부만 확인됨",
  not_observed: "답변에서 확인되지 않음",
  undetermined: "판정 확인 필요",
};

const changeLabels: Record<ComparisonChange, string> = {
  added: "2차에 추가됨",
  unchanged: "상태 동일",
  no_longer_observed: "2차에서 확인되지 않음",
  changed: "상태 변경",
};

export function AttemptContentComparison({ comparison, isLoading = false, loadError = false }: AttemptContentComparisonProps) {
  if (isLoading) return <p className="comparison-notice">기준별 비교 결과를 불러오고 있어요.</p>;
  if (loadError) return <p className="comparison-notice">기준별 비교 결과를 불러오지 못했어요. 전달력 수치는 아래에서 확인할 수 있어요.</p>;
  if (!comparison) return <p className="comparison-notice">저장된 기준별 분석 결과가 없어 내용 비교를 표시할 수 없어요.</p>;
  if (!comparison.content_available) return <p className="comparison-notice">{comparison.content_notice || "같은 기준으로 분석된 두 답변이 있어야 내용 상태를 비교할 수 있어요."}</p>;

  const allCriteriaConfirmed = comparison.criteria.length > 0
    && comparison.criteria.every((criterion) => criterion.second.assessment === "met")
    && comparison.still_missing.length === 0
    && !comparison.contradictions.some((item) => item.attempt_no === 2);

  return (
    <>
      <div className="comparison-table-view">
        {allCriteriaConfirmed ? (
          <section className="comparison-status comparison-confirmed-card" aria-label="내용 확인 결과">
            <strong>모든 기준을 확인했어요</strong>
            <span>2차 답변에서 필요한 설명이 모두 확인됐어요.</span>
            <span className="comparison-confirmed-badge">남은 보완 사항 없음</span>
          </section>
        ) : <SummaryCard title="여전히 부족한 설명" emptyText="기준별 확인 결과를 아래에서 확인해 주세요.">
          {comparison.still_missing.map((item) => (
            <article key={item.criterion_id}>
              <strong>{item.description}</strong>
              <p>{item.assessment === "undetermined" ? "설명이 상충해 확인이 필요해요." : item.needed || "답변에서 아직 확인되지 않았어요."}</p>
            </article>
          ))}
        </SummaryCard>}
        <div className="comparison-table-heading" aria-hidden="true">
          <span>비교 항목</span><span>1차 답변</span><span>2차 답변</span><span>변화</span>
        </div>
        <div className="comparison-criteria-list">
          {comparison.criteria.map((criterion) => (
            <details className="comparison-criterion" key={criterion.criterion_id}>
              <summary className="comparison-table-row">
                <strong className="comparison-criterion-name">{criterion.description}</strong>
                <span className="comparison-cell is-first"><small>1차 · {assessmentLabels[criterion.first.assessment]}</small><span>{briefReason(criterion.first.reason)}</span></span>
                <span className="comparison-cell is-second"><small>2차 · {assessmentLabels[criterion.second.assessment]}</small><span>{briefReason(criterion.second.reason)}</span></span>
                <span className={`comparison-change is-${criterion.change}`}>{changeLabels[criterion.change]}</span>
              </summary>
              <div className="criterion-attempts">
                <Assessment label="1차" value={criterion.first} />
                <Assessment label="2차" value={criterion.second} />
              </div>
            </details>
          ))}
        </div>
        <details className="comparison-added-details">
          <summary>2차에 추가된 설명과 근거 보기</summary>
          <SummaryCard title="2차에 추가된 설명" emptyText="새로 확인된 설명이 없어요.">
            {comparison.added_explanations.map((item) => (
              <article key={item.criterion_id}><strong>{item.description}</strong><Evidence evidence={item.evidence} /></article>
            ))}
          </SummaryCard>
        </details>
      </div>

      {comparison.contradictions.length > 0 && (
        <div className="comparison-contradictions">
          <h3>확인이 필요한 상충 설명</h3>
          {comparison.contradictions.map((item) => (
            <article key={`${item.attempt_no}-${item.criterion_id}`}>
              <strong>{item.attempt_no}차 답변 · {item.description}</strong>
              <p>{item.reason}</p>
              <Evidence evidence={item.evidence} />
            </article>
          ))}
        </div>
      )}
    </>
  );
}

function SummaryCard({ title, emptyText, children }: { title: string; emptyText: string; children: ReactNode }) {
  const hasChildren = Array.isArray(children) ? children.length > 0 : Boolean(children);
  return <section className="comparison-summary-card"><h3>{title}</h3>{hasChildren ? children : <p>{emptyText}</p>}</section>;
}

function Assessment({ label, value }: { label: string; value: PracticeContentAssessment }) {
  return (
    <div className="criterion-attempt">
      <span>{label} · {assessmentLabels[value.assessment]}</span>
      <p>{value.reason}</p>
      <Evidence evidence={value.evidence} />
      {value.needed && <small>더 필요한 설명: {value.needed}</small>}
    </div>
  );
}

function Evidence({ evidence }: { evidence: string[] }) {
  if (evidence.length === 0) return null;
  return <ul className="comparison-evidence">{evidence.map((quote, index) => <li key={`${quote}-${index}`}>“{quote}”</li>)}</ul>;
}

function briefReason(value: string) {
  const text = value.replace(/\s+/g, " ").trim();
  return text.length > 48 ? `${text.slice(0, 48)}…` : text;
}
