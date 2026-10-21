import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { ComparisonAssessment, PracticeComparison } from "../api/practiceHistory";
import { AttemptContentComparison } from "./AttemptContentComparison";

function comparison(assessment: ComparisonAssessment = "met"): PracticeComparison {
  return {
    content_available: true,
    content_notice: null,
    criteria: [{ criterion_id: "own_action", description: "본인 행동", change: "added",
      first: { assessment: "not_observed", reason: "설명 없음", evidence: [], needed: "행동 설명" },
      second: { assessment, reason: "답변 확인", evidence: ["로직을 수정했습니다."], needed: null } }],
    added_explanations: [{ criterion_id: "own_action", description: "본인 행동", evidence: ["로직을 수정했습니다."] }],
    still_missing: [],
    contradictions: [],
    delivery: { cpm: { first: 300, second: 300, direction: "same" },
      long_silence_count: { first: 0, second: 0, direction: "same" },
      repetition_count: { first: 0, second: 0, direction: "same" } },
  };
}
const render = (value: PracticeComparison) => renderToStaticMarkup(<AttemptContentComparison comparison={value} />);

describe("모든 내용 기준 확인 카드", () => {
  it("모든 2차 기준이 확인됐을 때 간결한 완료 상태·완료 배지를 표시한다", () => {
    const markup = render(comparison());
    expect(markup).toContain("comparison-status");
    expect(markup).toContain("내용 확인 결과");
    expect(markup.indexOf("내용 확인 결과")).toBeLessThan(markup.indexOf("2차에 추가된 설명"));
    expect(markup).toContain("모든 기준을 확인했어요");
    expect(markup).toContain("남은 보완 사항 없음");
    expect(markup).not.toContain("여전히 부족한 설명");
    expect(markup).toContain("로직을 수정했습니다.");
  });
  it.each(["partial", "not_observed", "undetermined"] as const)("부족 목록이 비어도 %s 기준이 있으면 완료로 표시하지 않는다", (status) => {
    expect(render(comparison(status))).not.toContain("comparison-confirmed-card");
  });
  it("남은 보완 항목은 기존 목록에 유지한다", () => {
    const value = comparison("partial");
    value.still_missing = [{ criterion_id: "own_action", description: "본인 행동", assessment: "partial", needed: "직접 수행한 행동을 설명해 주세요." }];
    const markup = render(value);
    expect(markup).toContain("여전히 부족한 설명");
    expect(markup.indexOf("여전히 부족한 설명")).toBeLessThan(markup.indexOf("2차에 추가된 설명"));
    expect(markup).toContain("직접 수행한 행동을 설명해 주세요.");
    expect(markup).not.toContain("comparison-confirmed-card");
  });
  it("활성 기준이 없거나 비교가 불가능할 때 완료를 주장하지 않는다", () => {
    expect(render({ ...comparison(), criteria: [] })).not.toContain("모든 기준을 확인했어요");
    expect(render({ ...comparison(), content_available: false })).not.toContain("모든 기준을 확인했어요");
  });
  it("2차 상충 설명은 완료를 막고 1차에만 있던 상충은 완료를 막지 않는다", () => {
    const value = comparison();
    value.contradictions = [{ attempt_no: 2, criterion_id: "own_action", description: "본인 행동", reason: "설명 상충", evidence: [] }];
    expect(render(value)).not.toContain("comparison-confirmed-card");
    value.contradictions[0].attempt_no = 1;
    expect(render(value)).toContain("comparison-confirmed-card");
  });
});

describe("접힌 요약 표와 상세 근거", () => {
  it("6개 기준을 모두 유지하고 상세 이유·인용·필요 설명은 펼침 영역에 보존한다", () => {
    const value = comparison();
    value.criteria = Array.from({ length: 6 }, (_, index) => ({
      ...value.criteria[0], criterion_id: `criterion-${index}`, description: `기준 ${index + 1}`,
      first: { ...value.criteria[0].first, reason: `긴 설명 ${index}: ${"원문 내용 ".repeat(30)}` },
      second: { ...value.criteria[0].second, evidence: [`근거 ${index}`, `추가 근거 ${index}`] },
    }));
    const markup = render(value);
    const container = document.createElement("div");
    container.innerHTML = markup;
    const rows = container.querySelectorAll<HTMLDetailsElement>("details.comparison-criterion");
    expect(rows).toHaveLength(6);
    rows.forEach((row, index) => {
      expect(row.open).toBe(false);
      expect(row.querySelector("summary")?.textContent).toContain(`기준 ${index + 1}`);
      expect(row.querySelector("summary")?.textContent).toContain("…");
      expect(row.querySelector(".criterion-attempts")?.textContent).toContain(value.criteria[index].first.reason);
      expect(row.querySelector(".criterion-attempts")?.textContent).toContain(`추가 근거 ${index}`);
      expect(row.querySelector(".criterion-attempts")?.textContent).toContain("행동 설명");
    });
  });
});
