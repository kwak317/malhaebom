export type MockErrorState =
  | "none"
  | "mic-permission-denied"
  | "mic-unavailable"
  | "recording-failed"
  | "too-short"
  | "analysis-failed"
  | "no-speech"
  | "question-tts-failed"
  | "question-tts-unavailable"
  | "coach-audio-unavailable"
  | "coach-audio-error"
  | "auth-required-analysis"
  | "auth-required-history"
  | "history-load-failed"
  | "history-delete-failed"
  | "login-failed"
  | "signup-failed"
  | "signup-email-exists";

// 개발 중 한 곳의 값만 바꿔 오류 화면을 확인합니다. 운영 UI에는 노출하지 않습니다.
export const MOCK_ERROR_STATE: MockErrorState = "none";
