export type BrowserQuestionTtsHandle = {
  cancel: () => void;
};

type BrowserQuestionTtsOptions = {
  text: string;
  onStart: () => void;
  onEnd: () => void;
  onError: () => void;
  synthesis?: SpeechSynthesis;
  createUtterance?: (text: string) => SpeechSynthesisUtterance;
};

export function playBrowserQuestionTts({
  text,
  onStart,
  onEnd,
  onError,
  synthesis = window.speechSynthesis,
  createUtterance = (value) => new SpeechSynthesisUtterance(value),
}: BrowserQuestionTtsOptions): BrowserQuestionTtsHandle {
  if (!synthesis || typeof createUtterance !== "function") {
    throw new Error("BROWSER_TTS_UNAVAILABLE");
  }

  const utterance = createUtterance(text);
  utterance.lang = "ko-KR";
  utterance.rate = 0.95;
  utterance.onstart = onStart;
  utterance.onend = onEnd;
  utterance.onerror = onError;
  synthesis.cancel();
  synthesis.speak(utterance);

  return {
    cancel: () => {
      utterance.onstart = null;
      utterance.onend = null;
      utterance.onerror = null;
      synthesis.cancel();
    },
  };
}
