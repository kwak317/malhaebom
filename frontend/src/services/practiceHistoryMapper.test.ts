import { describe, expect, it } from "vitest";

import type { PracticeHistoryRecord } from "../api/practiceHistory";
import { toPracticeHistoryItem } from "./practiceHistoryMapper";

const comparisonRecord: PracticeHistoryRecord = {
  practice_session_id: "session-1",
  question_type: "preset",
  question_id: "preset-01",
  custom_question_text: null,
  practiced_at: "2026-08-24T10:00:00+09:00",
  attempts: [
    { attempt_no: 1, job_id: "job-1", transcript: "첫 답변", metrics: { cpm: 330, long_silence_count: 2, repetition_count: 1 }, feedback: ["속도를 낮춰 보세요."] },
    { attempt_no: 2, job_id: "job-2", transcript: "두 번째 답변", metrics: { cpm: 310, long_silence_count: 1, repetition_count: 0 }, feedback: ["더 자연스럽게 말해 보세요."] },
  ],
  comparison: {
    content_available: false,
    content_notice: "두 답변의 구조화 내용 분석이 필요해요.",
    criteria: [],
    added_explanations: [],
    still_missing: [],
    contradictions: [],
    delivery: {
      cpm: { first: 330, second: 310, direction: "decreased" },
      long_silence_count: { first: 2, second: 1, direction: "decreased" },
      repetition_count: { first: 1, second: 0, direction: "decreased" },
    },
  },
};

describe("toPracticeHistoryItem", () => {
  it("기본 질문의 두 시도를 비교 화면 데이터로 바꾼다", () => {
    expect(toPracticeHistoryItem(comparisonRecord)).toMatchObject({
      id: "session-1",
      question: "자기소개를 해주세요.",
      status: "2차 연습 완료",
      resultType: "comparison",
      attempt1Transcript: "첫 답변",
      attempt2Transcript: "두 번째 답변",
      attempt1Metrics: { speakingRate: 330, longSilence: 2, repeatedExpressions: 1 },
      attempt2Metrics: { speakingRate: 310, longSilence: 1, repeatedExpressions: 0 },
      changes: [
        "긴 침묵이 2회에서 1회로 줄었어요.",
        "반복 표현이 1회에서 0회로 줄었어요.",
        "말하기 속도가 330에서 310 음절/분으로 변화했어요.",
      ],
      comparison: comparisonRecord.comparison,
    });
  });

  it("저장된 대화 순서와 종료 요약을 기록 화면에 전달하고 예전 기록은 허용한다", () => {
    const interview_chat: NonNullable<PracticeHistoryRecord["interview_chat"]> = {
      conversation_id: "chat-1", completed_at: comparisonRecord.practiced_at,
      messages: [
        { role: "user", message: "반복 검증했어요.", follow_up_question: null, summary: null },
        { role: "assistant", message: "정리했어요.", follow_up_question: null, summary: { clarified_points: ["반복 검증"], next_practice: ["결과 설명"] } },
      ],
    };
    expect(toPracticeHistoryItem({ ...comparisonRecord, interview_chat }).interviewChat).toEqual(interview_chat);
    expect(toPracticeHistoryItem(comparisonRecord).interviewChat).toBeUndefined();
  });

  it("내 질문은 원문을 표시하고 알 수 없는 기본 질문은 안전한 문구로 바꾼다", () => {
    const custom = toPracticeHistoryItem({
      ...comparisonRecord,
      practice_session_id: "session-custom",
      question_type: "custom",
      question_id: null,
      custom_question_text: "협업 경험을 설명해 주세요.",
      attempts: [comparisonRecord.attempts[0]],
    });
    const unknownPreset = toPracticeHistoryItem({ ...comparisonRecord, question_id: "preset-99" });

    expect(custom).toMatchObject({ question: "협업 경험을 설명해 주세요.", status: "1차 분석 완료", resultType: "result" });
    expect(unknownPreset.question).toBe("기본 면접 질문");
  });

  it("악화되었거나 같은 비교 수치는 실제 변화만 설명한다", () => {
    const item = toPracticeHistoryItem({
      ...comparisonRecord,
      attempts: [
        comparisonRecord.attempts[0],
        { attempt_no: 2, job_id: "job-2", transcript: "두 번째 답변", metrics: { cpm: 330, long_silence_count: 3, repetition_count: 1 }, feedback: [] },
      ],
    });

    expect(item.changes).toEqual([
      "긴 침묵이 2회에서 3회로 늘었어요.",
      "반복 표현은 1차와 같아요.",
      "말하기 속도는 1차와 같아요.",
    ]);
  });
});
