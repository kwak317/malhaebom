import { describe, expect, it } from "vitest";

import {
  getCustomQuestionTtsEndpoint,
  getQuestionTtsStreamEndpoint,
  getPresetQuestionPlaybackUrl,
} from "./RecordingPage";

describe("getPresetQuestionPlaybackUrl", () => {
  it("일반 API URL로 기본 질문을 재생한다", () => {
    expect(getPresetQuestionPlaybackUrl(
      { questionType: "preset", question: "자기소개를 해주세요.", questionId: "preset-01" },
      "https://api.example.com/",
    )).toBe("https://api.example.com/api/preset-questions/preset-01/audio");
  });

  it("내 질문에는 URL을 만들지 않는다", () => {
    expect(getPresetQuestionPlaybackUrl(
      { questionType: "custom", question: "내 질문", questionId: null },
      "https://api.example.com",
    )).toBeNull();
  });

  it("직접 질문은 질문 전용 스트리밍 API를 사용한다", () => {
    expect(getCustomQuestionTtsEndpoint(
      { questionType: "custom", question: "내 질문", questionId: null },
      "https://api.example.com/",
    )).toBe("https://api.example.com/api/questions/tts/stream");
    expect(getCustomQuestionTtsEndpoint(
      { questionType: "preset", question: "자기소개를 해주세요.", questionId: "preset-01" },
      "https://api.example.com",
    )).toBeNull();
  });

  it("새 문구의 핵심 기본 질문도 설정된 동적 TTS API를 사용한다", () => {
    expect(getQuestionTtsStreamEndpoint(
      {
        questionType: "preset",
        question: "프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?",
        questionId: "preset-04",
      },
      "https://api.example.com/",
    )).toBe("https://api.example.com/api/questions/tts/stream");
  });
});
