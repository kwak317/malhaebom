import { describe, expect, it, vi } from "vitest";

import { playBrowserQuestionTts } from "./browserQuestionTts";

describe("playBrowserQuestionTts", () => {
  it("한국어·면접 속도로 브라우저 음성을 재생한다", () => {
    const utterance = {} as SpeechSynthesisUtterance;
    const synthesis = {
      cancel: vi.fn(),
      speak: vi.fn(),
    } as unknown as SpeechSynthesis;

    const handle = playBrowserQuestionTts({
      text: "프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?",
      onStart: vi.fn(),
      onEnd: vi.fn(),
      onError: vi.fn(),
      synthesis,
      createUtterance: () => utterance,
    });

    expect(utterance.lang).toBe("ko-KR");
    expect(utterance.rate).toBe(0.95);
    expect(synthesis.speak).toHaveBeenCalledWith(utterance);
    handle.cancel();
    expect(synthesis.cancel).toHaveBeenCalledTimes(2);
  });
});
