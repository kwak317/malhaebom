import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { PracticeComparison } from "../api/practiceHistory";
import { getMockAnalysisResult } from "../mocks/analysisMock";
import { NavigationProvider } from "../navigation";
import ComparisonPage, { describeMetricChange } from "./ComparisonPage";

const comparison: PracticeComparison = {
  content_available: true,
  content_notice: null,
  criteria: [
    {
      criterion_id: "result_verification",
      description: "결과 확인",
      first: { assessment: "not_observed", reason: "답변에서 확인되지 않았습니다.", evidence: [], needed: "결과 확인" },
      second: { assessment: "met", reason: "답변에서 설명이 확인됐습니다.", evidence: ["오류율이 3%로 내려간 것을 확인했습니다."], needed: null },
      change: "added",
    },
    {
      criterion_id: "own_action",
      description: "본인의 해결 행동",
      first: { assessment: "met", reason: "답변에서 설명이 확인됐습니다.", evidence: ["입력값 검증을 추가했습니다."], needed: null },
      second: { assessment: "undetermined", reason: "직접 했다는 설명과 하지 않았다는 설명이 함께 있습니다.", evidence: ["제가 검증을 추가했습니다.", "검증은 동료가 추가했습니다."], needed: "상충하는 설명을 실제 기록에 맞게 정리해 주세요." },
      change: "changed",
    },
  ],
  added_explanations: [{ criterion_id: "result_verification", description: "결과 확인", evidence: ["오류율이 3%로 내려간 것을 확인했습니다."] }],
  still_missing: [{ criterion_id: "own_action", description: "본인의 해결 행동", assessment: "undetermined", needed: "상충하는 설명을 실제 기록에 맞게 정리해 주세요." }],
  contradictions: [{ attempt_no: 2, criterion_id: "own_action", description: "본인의 해결 행동", reason: "직접 했다는 설명과 하지 않았다는 설명이 함께 있습니다.", evidence: ["제가 검증을 추가했습니다.", "검증은 동료가 추가했습니다."] }],
  delivery: {
    cpm: { first: 320, second: 320, direction: "same" },
    long_silence_count: { first: 1, second: 3, direction: "increased" },
    repetition_count: { first: 2, second: 1, direction: "decreased" },
  },
};

describe("ComparisonPage", () => {
  it("실제 인용 근거와 추가·부족·상충 상태를 같은 기준으로 표시한다", () => {
    const markup = renderToStaticMarkup(
      <NavigationProvider active="practice" isLoggedIn navigate={() => undefined} logout={() => undefined}>
        <ComparisonPage
          question={{ questionType: "preset", question: "프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?", questionId: "preset-04" }}
          firstResult={getMockAnalysisResult(1)}
          secondResult={getMockAnalysisResult(2)}
          initialComparison={comparison}
          onReturnHome={() => undefined}
        />
      </NavigationProvider>,
    );

    expect(markup).toContain("2차에 추가된 설명");
    expect(markup).toContain("오류율이 3%로 내려간 것을 확인했습니다.");
    expect(markup).toContain("여전히 부족한 설명");
    expect(markup).toContain("확인이 필요한 상충 설명");
    expect(markup).toContain("긴 침묵: 1회에서 3회로 증가했어요.");
    expect(markup).toContain("반복 표현: 2회에서 1회로 감소했어요.");
    expect(markup).toContain("말하기 속도: 1차와 2차가 동일해요 (320 음절/분).");
    expect(markup).not.toContain("줄었어요");
    expect(markup).toContain("합격 가능성, 실제 역량 향상 또는 경험의 사실 여부를 판정하지 않습니다.");
  });

  it("증가·감소·동일·확인 불가를 입력값 그대로 설명한다", () => {
    expect(describeMetricChange("긴 침묵", { first: 1, second: 2, direction: "increased" }, "회")).toContain("증가했어요");
    expect(describeMetricChange("긴 침묵", { first: 2, second: 1, direction: "decreased" }, "회")).toContain("감소했어요");
    expect(describeMetricChange("긴 침묵", { first: 1, second: 1, direction: "same" }, "회")).toContain("동일해요");
    expect(describeMetricChange("긴 침묵", { first: null, second: 1, direction: "unavailable" }, "회")).toContain("확인할 수 없어요");
  });
});
