import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { CoachingResponse } from "../api/coaching";
import { CoachingResultPanel } from "./CoachingResultPanel";

const result: CoachingResponse = {
  status: "needs_more_info",
  job_alignment: [{ requirement_id: "J01-R1", label: "related", reason: "오류 처리 경험이 관련됩니다." }],
  intent_assessment: { label: "partial", reason: "결과 확인이 빠졌습니다." },
  criterion_assessments: [{ criterion_id: "result_verification", assessment: "not_observed", reason: "결과가 없습니다.", needed: "확인 방법" }],
  evidence: [{ source_type: "job_alignment", source_id: "J01-R1", segment_id: "s1", quote: "로그를 확인했습니다.", reason: "근거" }],
  gaps: [{ criterion_id: "result_verification", assessment: "not_observed", reason: "결과가 없습니다.", needed: "수정 후 확인 방법과 결과" }],
  clarifying_question: "수정 결과를 어떻게 확인했나요?",
  next_actions: [{ target_type: "criterion", target_id: "result_verification", action: "확인한 수치를 덧붙여 보세요." }],
  example_answer: "로그를 확인해 원인을 좁히고 코드를 수정했습니다. 이후 [실제로 확인한 방법과 결과]를 덧붙이겠습니다.",
};

describe("CoachingResultPanel", () => {
  it("다른 질문의 기준을 문제 해결 기준과 구분해 표시한다", () => {
    const intro = {
      ...result,
      criterion_assessments: ["professional_identity", "core_strength", "supporting_experience"].map((criterion_id) => ({
        criterion_id, assessment: "not_observed", reason: "추가 설명이 필요합니다.", needed: "구체적 설명",
      })),
      gaps: [],
      next_actions: [],
    };
    const markup = renderToStaticMarkup(<CoachingResultPanel result={intro} />);
    expect(markup).toContain("직무 정체성");
    expect(markup).toContain("핵심 강점");
    expect(markup).toContain("근거 경험");
    expect(markup).not.toContain("professional_identity");
    expect(markup).not.toContain("원인 판단");
    expect(markup).not.toContain("답변 구성");
  });

  it("판정·근거·부족 항목·확인 질문·다음 행동을 모두 표시한다", () => {
    const markup = renderToStaticMarkup(<CoachingResultPanel result={result} />);

    expect(markup).toContain("공고 요구와 관련 있음");
    expect(markup).toContain("로그를 확인했습니다.");
    expect(markup).toContain("수정 후 확인 방법과 결과");
    expect(markup).toContain("수정 결과를 어떻게 확인했나요?");
    expect(markup).toContain("확인한 수치를 덧붙여 보세요.");
    expect(markup).toContain("코칭 적용 예시");
    expect(markup).toContain("실제로 확인한 방법과 결과");
    expect(markup).toContain("정답이나 대필 답변이 아닙니다.");
    expect(markup).toContain("coaching-status--partial");
    expect(markup).toContain("coaching-assessment--partial");
    expect(markup).toContain("coaching-assessment--missing");
  });

  it("내부 ID를 한글 이름으로 바꾸고 동일한 근거는 한 번만 표시한다", () => {
    const duplicated = {
      ...result,
      evidence: [result.evidence[0], { ...result.evidence[0], source_type: "criterion_assessment" as const }],
    };

    const markup = renderToStaticMarkup(<CoachingResultPanel result={duplicated} />);

    expect(markup).toContain("결과 확인");
    expect(markup).toContain("선택한 공고 요구사항 1");
    expect(markup).toContain("답변 근거 1");
    expect(markup).not.toContain("result_verification");
    expect(markup).not.toContain("segment-");
    expect(markup.match(/로그를 확인했습니다\./g)).toHaveLength(1);
  });

  it("영어 설명과 none 행동을 사용자에게 그대로 노출하지 않는다", () => {
    const invalidLanguage = {
      ...result,
      intent_assessment: { label: "partial", reason: "The answer needs more detail." },
      criterion_assessments: [{ ...result.criterion_assessments[0], reason: "No result was provided." }],
      next_actions: [{ target_type: "criterion", target_id: "result_verification", action: "none" }],
    };

    const markup = renderToStaticMarkup(<CoachingResultPanel result={invalidLanguage} />);

    expect(markup).not.toContain("The answer needs more detail.");
    expect(markup).not.toContain("No result was provided.");
    expect(markup).not.toContain("none");
    expect(markup).toContain("질문 의도와 관련되지만 일부 설명을 보완할 필요가 있습니다.");
    expect(markup).toContain("현재 답변의 근거 구조를 유지하면서 같은 질문에 다시 답해 보세요.");
  });
  it("상세 세 항목은 처음 접혀 있고 원문을 보존하며 마지막에 요약을 표시한다", () => {
    const container = document.createElement("div");
    container.innerHTML = renderToStaticMarkup(<CoachingResultPanel result={result} />);
    const folds = [...container.querySelectorAll<HTMLDetailsElement>("details.coaching-fold")];
    expect(folds).toHaveLength(3);
    expect(folds.every((item) => !item.open)).toBe(true);
    expect(folds[0].querySelector("summary")?.textContent).toContain("질문 의도와 공고 연결");
    expect(folds[1].querySelector("summary")?.textContent).toContain("판정과 근거");
    expect(folds[1].textContent).toContain("로그를 확인했습니다.");
    expect(folds[2].querySelector("summary")?.textContent).toContain("보완하면 좋은 항목");
    expect(folds[2].textContent).toContain("수정 후 확인 방법과 결과");
    const summary = container.querySelector(".coaching-panel")?.lastElementChild;
    expect(summary?.getAttribute("aria-label")).toBe("전체 코칭 피드백 요약");
    expect(summary?.textContent).toContain("결과 확인 설명을 더 구체적으로 보완해 주세요.");
    expect(summary?.textContent).toContain("확인한 수치를 덧붙여 보세요.");
    expect(summary?.textContent).not.toContain("모든 활성 기준의 설명이 확인됐어요.");
  });

  it("모든 기준 충족과 근거 부족을 구분하고 보완 없는 드롭다운은 만들지 않는다", () => {
    const container = document.createElement("div");
    const complete = { ...result, status: "ok" as const, gaps: [],
      criterion_assessments: [{ ...result.criterion_assessments[0], assessment: "met" }] };
    container.innerHTML = renderToStaticMarkup(<CoachingResultPanel result={complete} />);
    expect(container.querySelectorAll("details.coaching-fold")).toHaveLength(2);
    expect(container.querySelector(".coaching-feedback-summary")?.textContent).toContain("모든 활성 기준의 설명이 확인됐어요.");
    expect(container.querySelector(".coaching-feedback-summary")?.textContent).toContain("결과 확인 설명이 확인됐어요.");
    container.innerHTML = renderToStaticMarkup(<CoachingResultPanel result={{ ...complete,
      criterion_assessments: [{ ...complete.criterion_assessments[0], assessment: "undetermined" }] }} />);
    expect(container.querySelector(".coaching-feedback-summary")?.textContent).not.toContain("모든 활성 기준의 설명이 확인됐어요.");
  });

  it("긴 판정 이유는 요약에서 짧게 줄이고 상세에는 그대로 남긴다", () => {
    const container = document.createElement("div");
    const longReason = "결과를 확인한 방법을 더 구체적으로 설명해 주세요. ".repeat(15);
    container.innerHTML = renderToStaticMarkup(<CoachingResultPanel result={{ ...result,
      intent_assessment: { ...result.intent_assessment, reason: longReason } }} />);
    expect(container.querySelector(".coaching-feedback-summary > p")?.textContent?.length).toBeLessThanOrEqual(141);
    expect(container.querySelector(".coaching-intent-card p")?.textContent).toBe(longReason);
  });

});
