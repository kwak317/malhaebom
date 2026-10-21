import { useEffect, useState } from "react";
import { supabase } from "../api/supabaseAuth";
import { fetchPreparationChatHistory, type PreparationHistoryMessage } from "../api/practiceHistory";

export function HistoryExperienceChat({ sessionId }: { sessionId: string }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<PreparationHistoryMessage[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    if (!open) return;
    let active = true;
    setState("loading");
    setMessages([]);
    void supabase().auth.getSession().then(({ data }) => {
      if (!data.session) throw new Error("로그인이 필요해요.");
      return fetchPreparationChatHistory(sessionId, data.session.access_token);
    }).then((history) => {
      if (active) { setMessages(history); setState("ready"); }
    }).catch(() => { if (active) setState("error"); });
    return () => { active = false; };
  }, [sessionId, open, retry]);

  return <details className="history-fold" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>경력·경험 추가 대화</summary>
    <div className="history-fold-content">
      <p className="history-chat-description">경력·경험 추가와 반영 확인을 포함해, 준비 과정과 1차 코칭 후 나눈 채팅 내역이에요.</p>
      {state === "loading" ? <p className="history-chat-empty" role="status">채팅 내역을 불러오고 있어요.</p>
        : state === "error" ? <div className="history-chat-empty" role="alert"><p>채팅 내역을 불러오지 못했어요.</p><button className="history-view-button" type="button" onClick={() => setRetry(value => value + 1)}>다시 불러오기</button></div>
          : messages.length === 0 ? <p className="history-chat-empty">저장된 경력·경험 추가 및 준비 대화가 없어요.</p>
            : <div className="history-chat-messages" aria-label="경력·경험 추가 및 준비 채팅 내역">{messages.map((message, index) =>
              <article key={index} className={`history-chat-message ${message.role}`}>
                <strong className="history-chat-speaker">{message.role === "user" ? "나" : "말해봄 코치"}</strong>
                <p>{message.message}</p>
                {message.follow_up_question && <p className="history-chat-question">{message.follow_up_question}</p>}
              </article>)}</div>}
    </div>
  </details>;
}
