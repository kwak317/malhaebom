import { describe, expect, it } from "vitest";

import { getPresetQuestionAudioUrl } from "./presetQuestionAudio";

describe("getPresetQuestionAudioUrl", () => {
  it("수용된 기본 질문 API URL만 만든다", () => {
    expect(getPresetQuestionAudioUrl("preset-01", "https://api.example.com/"))
      .toBe("https://api.example.com/api/preset-questions/preset-01/audio");
    expect(getPresetQuestionAudioUrl("preset-10", "https://api.example.com"))
      .toBe("https://api.example.com/api/preset-questions/preset-10/audio");
  });

  it("알 수 없는 질문 또는 API base가 없으면 URL을 만들지 않는다", () => {
    expect(getPresetQuestionAudioUrl("preset-11", "https://api.example.com"))
      .toBeNull();
    expect(getPresetQuestionAudioUrl("preset-01", ""))
      .toBeNull();
  });

  it("문구가 바뀐 핵심 질문은 오래된 WAV 대신 동적 TTS를 사용한다", () => {
    expect(getPresetQuestionAudioUrl("preset-04", "https://api.example.com"))
      .toBeNull();
  });
});
