import { useEffect, useRef, useState } from "react";
import { ChatMessageText } from "./ChatMessageText";
import { supabase } from "../api/supabaseAuth";
import { PreparationSelectionConflict, bindPreparationConversation, sendPreparationMessage, getConfirmedPreparationExperiences, type ConfirmedPreparationExperience, type PracticeRestart, type PreparationResponse, type PreparationStage, type PreparationMaterials, type PreparationSelection, type PreparationSelectionState } from "../api/preparationConversation";

export type PreparationChatPlacement = PreparationStage | "ncs_review" | "resume_review" | "readme_review" | "jobs" | "requirements" | "questions";

type Turn = { requestId: string; stage: PreparationStage; placement: PreparationChatPlacement; userMessage: string; localOnly?: boolean; response?: PreparationResponse; error?: string };

export function usePreparationConversation(isLoggedIn: boolean, generation: number | string) {
  const conversationId = useRef<string | null>(null);
  const epoch = useRef(0);
  const selectionRevision = useRef<number | null>(null);
  const busy = useRef(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [confirmedExperiences, setConfirmedExperiences] = useState<ConfirmedPreparationExperience[]>([]);
  const [confirmedError, setConfirmedError] = useState("");

  function clear(nextConversationId: string | null = null) {
    epoch.current += 1;
    conversationId.current = nextConversationId;
    selectionRevision.current = null;
    busy.current = false;
    setTurns([]);
    setConfirmedExperiences([]);
    setConfirmedError("");
    setLoading(false);
  }
  useEffect(() => clear(), [isLoggedIn, generation]);

  async function token() {
    const { data } = await supabase().auth.getSession();
    if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
    return data.session.access_token;
  }

  const lastResponse = [...turns].reverse().find((turn) => turn.response)?.response;
  useEffect(() => {
    if (!lastResponse) return;
    let active = true;
    void token().then((accessToken) => getConfirmedPreparationExperiences(accessToken, lastResponse.conversation_id))
      .then((items) => { if (active) { setConfirmedExperiences(items); setConfirmedError(""); } })
      .catch((error) => { if (active) setConfirmedError(error instanceof Error ? error.message : "확인한 경험을 불러오지 못했어요."); });
    return () => { active = false; };
  }, [lastResponse]);

  function appendUserMessage(message: string, stage: PreparationStage, placement: PreparationChatPlacement) {
    setTurns((current) => [...current, { requestId: crypto.randomUUID(), stage, placement, userMessage: message, localOnly: true }]);
  }

  async function bind(sessionId: string, accessToken: string) {
    if (conversationId.current) await bindPreparationConversation(accessToken, conversationId.current, sessionId);
  }

  async function send(message: string, stage: PreparationStage, sessionId: string | null,
    materials: PreparationMaterials, onRerecord: () => void, placement: PreparationChatPlacement = stage,
    selection?: PreparationSelection,
    onSelection?: (selection: PreparationSelectionState, job: PreparationResponse["selection_job"]) => boolean | void,
    onRestart?: (restart: PracticeRestart, message: string) => void,
    restartConfirmation?: { token: string; confirm: boolean }) {
    if (busy.current) return;
    const version = epoch.current;
    const requestId = crypto.randomUUID();
    busy.current = true;
    setLoading(true);
    setTurns((current) => [...current, { requestId, stage, placement, userMessage: message }]);
    try {
      const response = await sendPreparationMessage(await token(), {
        request_id: requestId, conversation_id: conversationId.current, practice_session_id: sessionId,
        current_stage: stage, message, review_context: materials, ...(selection ? { selection } : {}),
        selection_revision: selectionRevision.current, ui_context: placement,
        ...(restartConfirmation ? { restart_confirmation: restartConfirmation } : {}),
      });
      if (epoch.current !== version) return;
      if (response.status === "ok" && response.action === "practice_restarted" && response.execution_result === "verified" && response.restart) {
        onRestart?.(response.restart, response.message);
        clear(response.conversation_id);
        selectionRevision.current = 0;
        return;
      }
      conversationId.current = response.conversation_id;
      const currentRevision = selectionRevision.current;
      const staleSelection = response.selection_revision != null && currentRevision != null && response.selection_revision < currentRevision;
      if (response.status === "ok" && response.selection_revision != null && !staleSelection) selectionRevision.current = response.selection_revision;
      if (response.status === "ok" && response.action === "selection_updated" && response.execution_result === "verified" && response.selection_state && !staleSelection) {
        if (onSelection?.(response.selection_state, response.selection_job) === false) {
          response.message = "서버에서 선택 변경을 처리했지만 화면 선택이 그 사이 바뀌었어요. 현재 선택을 확인하고 다시 요청해 주세요.";
        }
      }
      setTurns((current) => current.map((turn) => turn.requestId === requestId ? { ...turn, response } : turn));
      if (response.status === "ok" && response.action === "request_rerecord") onRerecord();
    } catch (error) {
      if (epoch.current !== version) return;
      if (error instanceof PreparationSelectionConflict && (selectionRevision.current == null || error.revision >= selectionRevision.current)) {
        selectionRevision.current = error.revision;
        onSelection?.(error.selection, error.job);
      }
      setTurns((current) => current.map((turn) => turn.requestId === requestId ? {
        ...turn, error: error instanceof Error ? error.message : "대화에 연결하지 못했어요.",
      } : turn));
    } finally {
      if (epoch.current === version) { busy.current = false; setLoading(false); }
    }
  }

  return { turns, loading, confirmedExperiences, confirmedError, appendUserMessage, send, bind, clear, getConversationId: () => conversationId.current };
}

export function PreparationConversationChat({ turns, pendingToken, disabled, onConfirm }: { turns: Turn[]; pendingToken?: string; disabled?: boolean; onConfirm?: (token: string, confirm: boolean) => void }) {
  return <>{turns.map((turn) => <div key={turn.requestId} id={`message:preparation:${encodeURIComponent(turn.requestId)}`} className="preparation-chat-turn">
    <article className="coach-message coach-message-user"><div><span>나</span><p>{turn.userMessage}</p></div></article>
    {!turn.localOnly && <article className={`coach-message coach-message-assistant${!turn.response && !turn.error ? " coach-typing-message" : ""}`} role={!turn.response && !turn.error ? "status" : undefined} aria-live="polite">
      <span className="coach-message-avatar" aria-hidden="true">✦</span><div><strong>말해봄 코치</strong>
        <ChatMessageText text={turn.response?.message ?? turn.error ?? "내용을 확인하고 있어요."} />
        {!turn.response && !turn.error && <span className="coach-typing-dots" aria-hidden="true"><i /><i /><i /></span>}
        {turn.response?.follow_up_question && <p className="preparation-follow-up"><strong>{turn.response.follow_up_question}</strong></p>}
        {pendingToken && turn.response?.restart?.token === pendingToken && onConfirm && <div className="preparation-restart-actions"><button type="button" disabled={disabled} onClick={() => onConfirm(pendingToken!, true)}>확인하고 변경</button><button type="button" disabled={disabled} onClick={() => onConfirm(pendingToken!, false)}>취소</button></div>}
      </div>
    </article>}
  </div>)}</>;
}
