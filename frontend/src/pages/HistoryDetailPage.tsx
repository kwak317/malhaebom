import { useEffect, useState } from "react";
import { AppHeader } from "../navigation";
import { supabase } from "../api/supabaseAuth";
import { fetchPreparationChatHistory, type PreparationHistoryMessage } from "../api/practiceHistory";
import type { PracticeHistoryItem } from "../services/practiceHistoryMapper";
import "../styles/history-page.css";

function HistoryDetailPage({ item, onBack }: { item: PracticeHistoryItem; onBack: () => void }) {
  const [messages, setMessages] = useState<PreparationHistoryMessage[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    setState("loading");
    setMessages([]);
    void supabase().auth.getSession().then(({ data }) => {
      if (!data.session) throw new Error("로그인이 필요해요.");
      return fetchPreparationChatHistory(item.id, data.session.access_token);
    }).then((history) => {
      if (active) { setMessages(history); setState("ready"); }
    }).catch(() => { if (active) setState("error"); });
    return () => { active = false; };
  }, [item.id, retry]);

  return <div className="history-page"><AppHeader /><main className="history-main">
    <section className="flow-card history-detail-card history-chat-card">
      <header className="history-result-heading"><div><p className="flow-eyebrow">연습 중 나눈 대화</p><h1>채팅 내역</h1></div>
        <button className="history-back-button" type="button" onClick={onBack}>결과로 돌아가기</button></header>
      <div className="history-detail-question"><span>이 연습의 질문</span><strong>{item.question}</strong><small>{item.practicedAt}</small></div>
      <p className="history-chat-description">준비 과정과 1차 코칭 후 나눈 자유질문, 경력·경험 추가 및 반영 확인 대화예요.</p>
      {state === "loading" ? <p className="history-chat-empty" role="status">채팅 내역을 불러오고 있어요.</p>
        : state === "error" ? <div className="history-chat-empty" role="alert"><p>채팅 내역을 불러오지 못했어요.</p><button className="history-view-button" type="button" onClick={() => setRetry((value) => value + 1)}>다시 불러오기</button></div>
          : messages.length === 0 ? <div className="history-chat-empty"><strong>저장된 채팅 내역이 없어요.</strong><p>이 연습에 연결된 자유질문이나 경력·경험 추가 대화가 없습니다.</p></div>
            : <ol className="history-chat-messages" aria-label="준비 및 코칭 채팅 내역">{messages.map((message, index) =>
              <li key={index} className={`history-chat-message history-chat-message-${message.role}`}>
                <span className="history-chat-message-speaker">{message.role === "assistant" && <span aria-hidden="true">✦</span>}{message.role === "user" ? "나" : "말해봄 코치"}</span>
                <div className="history-chat-message-bubble">
                  {message.message.split(/\n\s*\n|\n/).filter((paragraph) => paragraph.trim()).map((paragraph, paragraphIndex) => <p key={paragraphIndex}>{paragraph}</p>)}
                  {message.follow_up_question && <p className="history-chat-follow-up">{message.follow_up_question}</p>}
                </div>
              </li>)}</ol>}
    </section>
  </main></div>;
}

export default HistoryDetailPage;
