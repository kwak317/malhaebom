import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { ComparisonAnswerSources } from "./ComparisonAnswerSources";
import { HistoryConversationPanels } from "./HistoryConversationPanels";
import type { PracticeHistoryItem } from "../services/practiceHistoryMapper";

it("원문과 피드백 전체를 처음 닫힌 영역에 보존한다", () => {
  const html = renderToStaticMarkup(<ComparisonAnswerSources firstTranscript="1차 원문" secondTranscript="2차 원문" feedback={["피드백 1", "피드백 2", "피드백 3"]} />);
  expect(html).toContain("1차 원문");
  expect(html).toContain("2차 원문");
  expect(html).toContain("피드백 3");
  expect(html).not.toContain(" open");
});

it("저장 기록에도 동일한 원문 펼침 컴포넌트를 사용한다", () => {
  const item = { resultType: "comparison", attempt1Transcript: "저장된 1차", attempt2Transcript: "저장된 2차",
    attempt1Metrics: { speakingRate: 300, longSilence: 0, repeatedExpressions: 0 },
    attempt2Metrics: { speakingRate: 280, longSilence: 0, repeatedExpressions: 0 }, feedback: ["저장된 피드백"] } as PracticeHistoryItem;
  const html = renderToStaticMarkup(<HistoryConversationPanels item={item} />);
  expect(html).toContain("comparison-answer-sources");
  expect(html).toContain("저장된 피드백");
  expect(html).toContain("저장된 기준별 분석 결과가 없어");
});
