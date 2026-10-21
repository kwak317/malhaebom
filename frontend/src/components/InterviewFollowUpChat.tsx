import { useEffect, useRef, useState, type FormEvent } from "react";
import { InterviewChatApiError, requestInterviewChat, type InterviewChatRequest, type InterviewChatResponse } from "../api/interviewChat";
import { supabase } from "../api/supabaseAuth";

import { CoachLoadingCard } from "./CoachLoadingCard";
import { ChatMessageText } from "./ChatMessageText";
import coachFinishing from "../assets/coach-finishing.png";

type ChatEntry = { role: "user"; message: string } | { role: "assistant"; response: InterviewChatResponse };

export function InterviewFollowUpChat({ practiceSessionId, finishOnStart = false }: { practiceSessionId: string; finishOnStart?: boolean }) {
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(true);
  const [finished, setFinished] = useState(false);
  const [error, setError] = useState("");
  const [startRetry, setStartRetry] = useState(0);
  const [failedAction, setFailedAction] = useState<InterviewChatRequest["action"] | null>(null);
  const [canRestart, setCanRestart] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const startRequestId = useRef(crypto.randomUUID());
  const turnRequest = useRef<InterviewChatRequest | null>(null);
  const startPromise = useRef<Promise<InterviewChatResponse> | null>(null);
  const pending = useRef(false);
  const chatRef = useRef<HTMLElement | null>(null);
  const mounted = useRef(false);

  useEffect(() => {
    if (!finishOnStart && !finished && turnRequest.current?.action !== "finish") return;
    const thread = chatRef.current?.closest<HTMLDivElement>(".coach-thread");
    if (!thread) return;
    delete thread.dataset.historyBrowsing;
    thread.dispatchEvent(new Event("workspace-latest"));
    if (typeof thread.scrollTo === "function") {
      thread.scrollTo({ top: thread.scrollHeight, behavior: "smooth" });
    } else {
      thread.scrollTop = thread.scrollHeight;
    }
  }, [busy, finished, finishOnStart]);

  const call = async (request: InterviewChatRequest) => {
    const { data, error: authError } = await supabase().auth.getSession();
    if (authError || !data.session?.access_token) throw new Error("로그인 세션을 확인해 주세요.");
    return requestInterviewChat(request, data.session.access_token);
  };

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  useEffect(() => {
    let current = true;
    setBusy(true);
    setError("");
    setUnavailable(false);
    if (!startPromise.current) {
      startPromise.current = call({ action: "start", request_id: startRequestId.current, practice_session_id: practiceSessionId });
    }
    void startPromise.current.then(async (response) => {
      if (!current) return;
      setConversationId(response.conversation_id);
      let result = response;
      if (finishOnStart && response.status !== "finished") {
        const request: InterviewChatRequest = turnRequest.current ?? {action:"finish",request_id:crypto.randomUUID(),practice_session_id:practiceSessionId,conversation_id:response.conversation_id};
        turnRequest.current = request;
        result = await call(request);
        if (!current) return;
        turnRequest.current = null;
      }
      setEntries([{ role: "assistant", response: result }]);
      setFinished(result.status === "finished");
    }).catch((reason) => {
      if (!current) return;
      if (reason instanceof InterviewChatApiError && reason.status === 409) {
        setFailedAction(null);
        setUnavailable(true);
        return;
      }
      setFailedAction(turnRequest.current?.action === "finish" ? "finish" : "start");
      setError(reason instanceof Error ? reason.message : "첫 질문을 준비하지 못했습니다.");
    }).finally(() => { if (current) setBusy(false); });
    return () => { current = false; };
  }, [practiceSessionId, startRetry, finishOnStart]);

  const send = async (action: "message" | "finish") => {
    const message = input.trim();
    if (!conversationId || pending.current || finished || (action === "message" && !message)) return;
    pending.current = true;
    setBusy(true);
    setError("");
    setCanRestart(false);
    try {
      const previous = turnRequest.current;
      const request: InterviewChatRequest = previous && previous.action === action && previous.message === (action === "message" ? message : undefined)
        ? previous
        : { action, request_id: crypto.randomUUID(), practice_session_id: practiceSessionId,
            conversation_id: conversationId, ...(action === "message" ? { message } : {}) };
      turnRequest.current = request;
      const response = await call(request);
      if (!mounted.current) return;
      setEntries((previous) => [...previous,
        { role: "user", message: action === "finish" ? "연습 마치기" : message },
        { role: "assistant", response }]);
      setFailedAction(null);
      turnRequest.current = null;
      if (action === "message") setInput("");
      setFinished(response.status === "finished");
    } catch (reason) {
      if (!mounted.current) return;
      setFailedAction(action);
      setCanRestart(reason instanceof InterviewChatApiError && (reason.status === 404 || reason.status === 409));
      setError(reason instanceof Error ? reason.message : "면접 대화를 진행하지 못했습니다.");
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(false);
    }
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void send("message");
  };
  const retry = () => {
    if (failedAction === "start") {
      startPromise.current = null;
      setStartRetry((count) => count + 1);
    } else if (failedAction) {
      void send(failedAction);
    }
  };

  const restart = () => {
    startRequestId.current = crypto.randomUUID();
    startPromise.current = null;
    turnRequest.current = null;
    setConversationId(null);
    setEntries([]);
    setCanRestart(false);
    setStartRetry((count) => count + 1);
  };

  return <section ref={chatRef} className="interview-followup-chat" aria-label="비교 후 면접 대화">
    <div className="interview-followup-messages" aria-live="polite">
      {entries.map((entry, index) => entry.role === "user"
        ? <article key={index} className="coach-message coach-message-user coach-message-user-input">
            <div><span>나</span><strong>{entry.message}</strong></div>
          </article>
        : <article key={index} className="coach-message coach-message-assistant">
            <span className="coach-message-avatar" aria-hidden="true">✦</span>
            <div><strong>말해봄 코치</strong><ChatMessageText text={entry.response.message} />
              {entry.response.follow_up_question && <p className="interview-followup-question"><strong>{entry.response.follow_up_question}</strong></p>}
              {entry.response.summary && <div className="interview-followup-summary">
                <h3>함께 정리한 설명</h3>
                {entry.response.summary.clarified_points.length
                  ? <ul>{entry.response.summary.clarified_points.map((point, i) => <li key={i}>{point}</li>)}</ul>
                  : <p>이번 대화에서 추가로 정리한 설명은 없어요.</p>}
                <h3>다음에 연습할 내용</h3>
                <ul>{entry.response.summary.next_practice.map((point, i) => <li key={i}>{point}</li>)}</ul>
              </div>}
            </div>
          </article>)}
      {busy && (finishOnStart || turnRequest.current?.action === "finish") ? <CoachLoadingCard
        label="연습 종료 정리 중"
        badge="연습 정리 중"
        title="면접 연습 내용을 정리하고 있어요"
        mascot={coachFinishing}
        progressPath="/api/agent/chat"
        progressFallback="면접 대화의 종료 요약을 기다리고 있어요…"
      >대화에서 보완한 설명과 다음에 연습할 내용을 정리해 드릴게요.</CoachLoadingCard> : busy && <article className="coach-message coach-message-assistant coach-typing-message" role="status">
        <span className="coach-message-avatar" aria-hidden="true">✦</span>
        <div><strong>말해봄 코치</strong><p>{conversationId ? "대화를 이어갈 내용을 정리하고 있어요." : "비교 결과를 바탕으로 첫 질문을 준비하고 있어요."}</p>
          <span className="coach-typing-dots" aria-hidden="true"><i /><i /><i /></span></div>
      </article>}
      {error && <div className="interview-followup-error" role="alert">
        <p>{error}</p><button type="button" onClick={retry} disabled={busy}>다시 시도</button>
        {canRestart && <button type="button" onClick={restart} disabled={busy}>새 대화 시작</button>}
      </div>}
    </div>
    {unavailable && <p className="interview-followup-finished" role="status">
      현재 기록으로는 면접 대화를 이어갈 수 없어요. 두 답변의 전사문을 확정하고 동일한 기준으로 코칭한 뒤 다시 비교해 주세요. 비교 결과는 계속 확인할 수 있어요.
    </p>}
    {!finished && !unavailable && <form className="coach-composer interview-followup-composer" onSubmit={submit}>
      <label className="sr-only" htmlFor="interview-chat-input">면접 코치에게 답변 또는 질문</label>
      <input id="interview-chat-input" type="text" value={input} maxLength={2000}
        placeholder="질문에 답하거나 면접 준비에 대해 물어보세요."
        disabled={busy || !conversationId} onChange={(event) => setInput(event.target.value)} />
      <button type="submit" disabled={busy || !conversationId || !input.trim()}>보내기 ↑</button>
      <button type="button" className="interview-finish-button" disabled={busy || !conversationId}
        onClick={() => { void send("finish"); }}>연습 마치기</button>
    </form>}
    {finished && <div className="interview-followup-completion">
      <p className="interview-followup-finished" role="status">면접 대화를 마쳤어요. 정리한 내용을 다음 답변에 활용해 보세요.</p>
      <nav className="interview-followup-exit-actions" aria-label="면접 연습 종료 후 이동">
        <a className="interview-restart-link" href="/app/practice">다시 면접하기</a>
        <a href="/app/">홈으로 가기</a>
      </nav>
    </div>}
  </section>;
}
