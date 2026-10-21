import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { AnalysisResult } from "../mocks/analysisMock";
import { NavigationProvider } from "../navigation";
import ResultPage from "./ResultPage";


const result: AnalysisResult = {
  attemptNo: 2,
  transcript: "문제를 확인하고 수정한 뒤 테스트했습니다.",
  answerDurationSec: 20,
  speakingRate: 300,
  longSilence: 0,
  repeatedExpressions: 0,
  feedback: [],
  prosodyReferenceAvailable: true,
  referenceMetrics: {
    pace: { value: 320 },
    longSilenceCount: { value: 2.48 },
    repetitionCount: { value: 0.41 },
  },
  contentFeedback: { text: "현재 답변의 구체성을 유지해 보세요." },
};


describe("ResultPage", () => {
  it("전사문을 다음 채팅에서 수정할 수 있게 표시한다", () => {
    const markup = renderToStaticMarkup(
      <NavigationProvider
        active="practice"
        isLoggedIn
        navigate={() => undefined}
        logout={() => undefined}
      >
        <ResultPage
          question={{
            questionType: "preset",
            question: "문제 해결 경험을 말씀해주세요.",
            questionId: "preset-04",
          }}
          result={result}
          stepLabel="2차"
          nextLabel="1·2차 답변 비교하기"
          onNext={() => undefined}
        />
      </NavigationProvider>,
    );

    expect(markup).toContain("2차 분석 결과");
    expect(markup).toContain("이 전사문으로 확정하기");
    expect(markup).toContain("확정할 전사문");
  });
});
