export type PracticeChatHistoryMessage = {
  speaker: "user" | "assistant";
  text: string;
  sourceId?: string;
};

// Capture the displayed conversation before a verified restart clears its UI state.
// Keep text only: old controls and markup must never execute in the new stage.
export function capturePracticeChat(thread: HTMLElement | null): PracticeChatHistoryMessage[] {
  if (!thread) return [];
  return [...thread.querySelectorAll<HTMLElement>(".coach-message")].flatMap((message) => {
    if (message.closest("[data-practice-chat-history]") || message.parentElement?.closest(".coach-message")
      || message.classList.contains("coach-typing-message")) return [];
    const copy = message.cloneNode(true) as HTMLElement;
    copy.querySelectorAll("button, input, textarea, select, script, style, [aria-hidden='true'], [hidden], .sr-only, .coach-message-avatar, time").forEach((node) => node.remove());
    copy.querySelectorAll("strong, span").forEach((node) => {
      if (["말해봄 코치", "나"].includes(node.textContent?.trim() || "")) node.remove();
    });
    copy.querySelectorAll("p, li, h2, h3, h4, section, summary, br").forEach((node) => {
      node.prepend("\n"); node.append("\n");
    });
    const text = (copy.textContent || "").replace(/[ \t]+/g, " ").replace(/ *\n */g, "\n").replace(/\n{3,}/g, "\n\n").trim();
    if (!text) return [];
    return [{ speaker: message.classList.contains("coach-message-user") ? "user" as const : "assistant" as const,
      text, sourceId: message.id || message.closest(".preparation-chat-turn")?.id || undefined }];
  });
}

export function PracticeChatHistory({ messages }: { messages: PracticeChatHistoryMessage[] }) {
  if (!messages.length) return null;
  return <section data-practice-chat-history aria-label="단계 변경 전 대화">
    {messages.map((message, index) => <article key={index} data-history-message-id={message.sourceId}
      className={`coach-message coach-message-${message.speaker} coach-history-message`}>
      {message.speaker === "assistant" && <span className="coach-message-avatar" aria-hidden="true">✦</span>}
      <div>{message.speaker === "user" ? <span>나 · 이전 대화</span> : <strong>말해봄 코치 · 이전 대화</strong>}
        <p style={{ whiteSpace: "pre-line" }}>{message.text}</p>
      </div>
    </article>)}
    <p className="coach-history-boundary">이전 대화는 그대로 남겨두고, 아래에서 변경한 단계를 이어가요.</p>
  </section>;
}
