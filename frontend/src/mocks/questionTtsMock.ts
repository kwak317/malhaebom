export type QuestionTtsState =
  | "idle"
  | "loading"
  | "ready"
  | "playing"
  | "completed"
  | "error";

export type QuestionTtsMock = {
  originalText: string;
  normalizedText: string;
  audioUrl: string | null;
  state: QuestionTtsState;
};

// 실제 Backend TTS API 연결 전 질문 TTS 화면 흐름 확인용 Mock입니다.
// audioUrl에는 이후 Backend가 반환하는 WAV URL 또는 정적 audio asset 경로를 넣습니다.
export const MOCK_QUESTION_TTS: QuestionTtsMock = {
  originalText: "본인의 강점을 말씀해 주세요.",
  normalizedText: "본인의 강점을 말씀해 주세요.",
  audioUrl: null,
  state: "idle",
};
