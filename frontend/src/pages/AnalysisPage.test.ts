import { describe, expect, it } from "vitest";

import type { PracticeQuestion } from "./PracticePage";
import { buildAnalysisJobForm } from "./AnalysisPage";

const question: PracticeQuestion = {
  questionType: "preset",
  question: "프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?",
  questionId: "preset-04",
};
const audio = new Blob(["audio"], { type: "audio/webm" });

describe("buildAnalysisJobForm", () => {
  it("2차 요청에 1차와 같은 practice_session_id를 포함한다", () => {
    const form = buildAnalysisJobForm({
      question,
      attemptNo: 2,
      audio,
      practiceSessionId: "session-1",
      sourceId: "source-2",
    });

    expect(form.get("attempt_no")).toBe("2");
    expect(form.get("practice_session_id")).toBe("session-1");
    expect(form.get("question_id")).toBe("preset-04");
  });

  it("2차 요청에 세션 ID가 없으면 요청 생성을 차단한다", () => {
    expect(() => buildAnalysisJobForm({
      question,
      attemptNo: 2,
      audio,
      sourceId: "source-2",
    })).toThrow("첫 번째 답변의 연습 세션을 찾지 못했습니다.");
  });

  it("공고 선택에서 만든 1차 practice_session_id를 그대로 보낸다", () => {
    const form = buildAnalysisJobForm({
      question,
      attemptNo: 1,
      audio,
      practiceSessionId: "ignored-session",
      sourceId: "source-1",
    });

    expect(form.get("practice_session_id")).toBe("ignored-session");
  });
});
