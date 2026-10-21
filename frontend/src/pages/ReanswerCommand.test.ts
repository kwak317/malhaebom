import { expect, it } from "vitest";
import { isReanswerCommand } from "./PracticePage";
it("명시적인 재답변 요청을 구분한다", () => {
  for (const text of ["재답변하기", "다시 답할게요", "다시 답변할게요", "다시 녹음하기", "재답변 해주세요", "다음으로", "다음 단계", "  재답변하기!  "]) expect(isReanswerCommand(text), text).toBe(true);
  for (const text of ["재답변하기 전에 질문 있어요", "다시 답변하기 싫어요", "재답변하기 버튼은 어디 있나요?", "다음 답변은 어떻게 하면 좋아요?", "말하기 속도를 어떻게 개선하죠?", ""]) expect(isReanswerCommand(text), text).toBe(false);
});
