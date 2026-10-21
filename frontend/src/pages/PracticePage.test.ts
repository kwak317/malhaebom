import { describe, expect, it } from "vitest";

import { PRESET_QUESTIONS } from "./PracticePage";

describe("PRESET_QUESTIONS", () => {
  it("화면의 기본 질문을 Storage 카탈로그와 같은 ID로 전달한다", () => {
    expect(PRESET_QUESTIONS).toEqual([
      { id: "preset-01", text: "자기소개를 해주세요." },
      { id: "preset-02", text: "지원한 이유를 말씀해주세요." },
      { id: "preset-03", text: "본인의 장점을 말씀해주세요." },
      { id: "preset-04", text: "프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?" },
      { id: "preset-05", text: "협업 중 갈등을 해결했던 경험을 말씀해주세요." },
      { id: "preset-06", text: "실패 경험과 배운 점을 말씀해주세요." },
      { id: "preset-07", text: "가장 기억에 남는 프로젝트를 소개해주세요." },
      { id: "preset-08", text: "본인이 맡았던 역할을 설명해주세요." },
      { id: "preset-09", text: "입사 후 어떤 개발자가 되고 싶은가요?" },
      { id: "preset-10", text: "마지막으로 하고 싶은 말을 말씀해주세요." },
    ]);
  });
});
