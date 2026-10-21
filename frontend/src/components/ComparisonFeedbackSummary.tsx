import type { PracticeComparison } from "../api/practiceHistory";
import "../styles/attempt-comparison.css";

export function ComparisonFeedbackSummary({ comparison }: { comparison: PracticeComparison | null }) {
  if (!comparison?.content_available || !comparison.criteria.length) {
    return <section className="comparison-feedback-summary" aria-label="재답변 피드백 요약">
      <h3>재답변 피드백 요약</h3><p>같은 기준의 두 답변 분석을 확인한 뒤 보완된 부분을 정리할 수 있어요.</p>
    </section>;
  }
  const feedback = comparison.criteria.filter((item) => item.first.assessment !== "met")
    .map((item) => `${item.description}: ${item.first.needed || item.first.reason}`);
  const conflicts = new Set(comparison.contradictions.filter((item) => item.attempt_no === 2).map((item) => item.criterion_id));
  const improved = comparison.criteria.filter((item) => !conflicts.has(item.criterion_id)
    && item.first.assessment !== "met" && item.second.evidence.some((quote) => quote.trim())
    && (item.second.assessment === "met" || (item.first.assessment === "not_observed" && item.second.assessment === "partial")))
    .map((item) => `${item.description}: ${item.second.assessment === "partial" ? "일부 보완" : item.first.assessment === "undetermined" ? "새로 확인된 설명" : "설명 보완 확인"} — “${item.second.evidence.find((quote) => quote.trim())!}”`);
  const remaining = comparison.criteria.filter((item) => item.second.assessment !== "met" || conflicts.has(item.criterion_id))
    .map((item) => `${item.description}: ${conflicts.has(item.criterion_id) || item.second.assessment === "undetermined"
      ? "설명이 불명확하거나 상충해 확인이 필요해요."
      : item.second.needed || "구체적인 근거와 설명을 더 보완해 주세요."}`);

  return <section className="comparison-feedback-summary" aria-label="재답변 피드백 요약">
    <h3>재답변 피드백 요약</h3>
    <dl>
      <SummaryRow title="처음 피드백한 내용" items={feedback} empty="1차 답변에서 모든 활성 기준의 설명이 확인됐어요." />
      <SummaryRow title="재답변에서 보완된 부분" items={improved} empty="새로 보완된 설명은 확인되지 않았어요. 상태가 같은 기준은 상세 비교에서 확인해 주세요." />
      <SummaryRow title="다음에 보완할 부분" items={remaining} empty="현재 활성 기준에 남은 보완 사항이 없어요. 확인된 설명을 다음 답변에서도 유지해 주세요." />
    </dl>
  </section>;
}

function SummaryRow({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return <div><dt>{title}</dt><dd>{items.length ? <ul>{items.map((item, index) => <li key={index}>{item}</li>)}</ul> : empty}</dd></div>;
}
