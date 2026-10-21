import type { PracticeComparison, PracticeHistoryAttempt, PracticeHistoryRecord, PracticeInterviewChatHistory } from "../api/practiceHistory";
import { getPresetQuestionText } from "../catalog/presetQuestions";

export type PracticeHistoryItem = {
  id: string;
  question: string;
  practicedAt: string;
  status: string;
  resultType: "comparison" | "result";
  attempt1Transcript: string;
  attempt2Transcript?: string;
  attempt1Metrics: { speakingRate: number; longSilence: number; repeatedExpressions: number };
  attempt2Metrics?: { speakingRate: number; longSilence: number; repeatedExpressions: number };
  feedback: string[];
  changes?: string[];
  comparison?: PracticeComparison;
  interviewChat?: PracticeInterviewChatHistory;
};

export function toPracticeHistoryItem(record: PracticeHistoryRecord): PracticeHistoryItem {
  const attempts = [...record.attempts].sort((left, right) => left.attempt_no - right.attempt_no);
  const first = attempts.find((attempt) => attempt.attempt_no === 1) ?? attempts[0];
  if (!first) throw new Error("완료된 연습 시도가 없습니다.");
  const second = attempts.find((attempt) => attempt.attempt_no === 2);
  const attempt1Metrics = toMetrics(first);
  const attempt2Metrics = second ? toMetrics(second) : undefined;
  const question = record.question_type === "preset"
    ? getPresetQuestionText(record.question_id) ?? "기본 면접 질문"
    : record.custom_question_text?.trim() || "내 면접 질문";

  return {
    id: record.practice_session_id,
    question,
    practicedAt: formatPracticedAt(record.practiced_at),
    status: second ? "2차 연습 완료" : "1차 분석 완료",
    resultType: second ? "comparison" : "result",
    attempt1Transcript: first.transcript,
    attempt2Transcript: second?.transcript,
    attempt1Metrics,
    attempt2Metrics,
    feedback: first.feedback,
    comparison: record.comparison,
    interviewChat: record.interview_chat,
    changes: second && attempt2Metrics ? [
      countChange("긴 침묵", attempt1Metrics.longSilence, attempt2Metrics.longSilence),
      countChange("반복 표현", attempt1Metrics.repeatedExpressions, attempt2Metrics.repeatedExpressions),
      speedChange(attempt1Metrics.speakingRate, attempt2Metrics.speakingRate),
    ] : undefined,
  };
}

function countChange(label: string, before: number, after: number): string {
  if (after < before) return `${label}이 ${before}회에서 ${after}회로 줄었어요.`;
  if (after > before) return `${label}이 ${before}회에서 ${after}회로 늘었어요.`;
  return `${label}은 1차와 같아요.`;
}

function speedChange(before: number, after: number): string {
  if (after === before) return "말하기 속도는 1차와 같아요.";
  return `말하기 속도가 ${before}에서 ${after} 음절/분으로 변화했어요.`;
}

function toMetrics(attempt: PracticeHistoryAttempt) {
  return {
    speakingRate: Math.round(attempt.metrics.cpm ?? 0),
    longSilence: attempt.metrics.long_silence_count,
    repeatedExpressions: attempt.metrics.repetition_count,
  };
}

function formatPracticedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(date).replace(/\. /g, ".").replace(/\.$/, "");
}
