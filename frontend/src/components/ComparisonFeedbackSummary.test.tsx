import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { PracticeComparison } from "../api/practiceHistory";
import { ComparisonFeedbackSummary } from "./ComparisonFeedbackSummary";

const value: PracticeComparison = {
  content_available: true, content_notice: null,
  criteria: [{ criterion_id: "own_action", description: "본인 행동", change: "added",
    first: { assessment: "not_observed", reason: "행동 누락", evidence: [], needed: "직접 한 행동을 설명해 주세요." },
    second: { assessment: "met", reason: "수정 행동 확인", evidence: ["제가 요청 로직을 수정했습니다."], needed: null } }],
  added_explanations: [], still_missing: [], contradictions: [],
  delivery: { cpm: { first: null, second: null, direction: "unavailable" }, long_silence_count: { first: 0, second: 0, direction: "same" }, repetition_count: { first: 0, second: 0, direction: "same" } },
};
const render = (comparison: PracticeComparison | null) => renderToStaticMarkup(<ComparisonFeedbackSummary comparison={comparison} />);
describe("재답변 피드백 요약", () => {
  it("최초 필요한 설명과 보완된 실제 인용을 마지막 요약으로 표시한다", () => {
    const html = render(value);
    expect(html).toContain("직접 한 행동을 설명해 주세요.");
    expect(html).toContain("제가 요청 로직을 수정했습니다.");
    expect(html).toContain("설명 보완 확인");
    expect(html).toContain("남은 보완 사항이 없어요");
  });
  it("동일 상태와 인용 없는 met은 새로운 보완으로 주장하지 않는다", () => {
    const criterion = value.criteria[0];
    expect(render({ ...value, criteria: [{ ...criterion, first: criterion.second }] })).not.toContain("설명 보완 확인");
    expect(render({ ...value, criteria: [{ ...criterion, second: { ...criterion.second, evidence: [] } }] })).not.toContain("설명 보완 확인");
  });
  it("partial은 일부 보완과 남은 필요 설명을 함께 표시한다", () => {
    const criterion = value.criteria[0];
    const html = render({ ...value, criteria: [{ ...criterion, second: { ...criterion.second, assessment: "partial", needed: "수정 범위도 설명해 주세요." } }] });
    expect(html).toContain("일부 보완");
    expect(html).toContain("수정 범위도 설명해 주세요.");
    expect(html).not.toContain("남은 보완 사항이 없어요");
  });
  it("2차 상충 설명은 완료를 막고 1차 판단 어려움은 새로 확인됨으로만 표현한다", () => {
    const criterion = value.criteria[0];
    const html = render({ ...value, contradictions: [{ attempt_no: 2, criterion_id: "own_action", description: "본인 행동", reason: "상충", evidence: [] }] });
    expect(html).toContain("상충해 확인이 필요해요");
    expect(html).not.toContain("설명 보완 확인");
    expect(html).not.toContain("남은 보완 사항이 없어요");
    expect(render({ ...value, criteria: [{ ...criterion, first: { ...criterion.first, assessment: "undetermined" } }] })).toContain("새로 확인된 설명");
  });
  it("비교 불가와 빈 기준에서는 보완 완료를 주장하지 않는다", () => {
    for (const comparison of [null, { ...value, content_available: false }, { ...value, criteria: [] }]) {
      const html = render(comparison);
      expect(html).toContain("두 답변 분석을 확인한 뒤");
      expect(html).not.toContain("남은 보완 사항이 없어요");
    }
  });
});

it("6개 기준과 긴 인용을 생략하지 않고 요약에 모두 표시한다", () => {
  const quote = "수정과 재검증 내용을 설명한 문장입니다. ".repeat(12);
  const criteria = Array.from({ length: 6 }, (_, index) => ({ ...value.criteria[0],
    criterion_id: `criterion-${index}`, description: `확인 기준 ${index + 1}`,
    second: { ...value.criteria[0].second, evidence: [quote] },
  }));
  const html = render({ ...value, criteria });
  expect(html).toContain("확인 기준 6");
  expect(html).toContain(quote);
  expect(html).not.toContain("외 3개");
});
