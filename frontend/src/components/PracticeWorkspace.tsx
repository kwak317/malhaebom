import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import type { AnswerRevision } from "../api/answerRevisions";
import type { CoachingResponse, CoachingEvidence } from "../api/coaching";

export type WorkspaceEvidence = { id: string; taskId: string; messageId: string; title: string; text: string; summaryLines?: string[]; kind: "reference" | "answer" | "check"; sourceUrl?: string; segmentId?: string; revisionId?: string; time?: string };
export type WorkspaceTask = { id: string; messageId: string; title: string; time: string; evidenceIds: string[]; parentId?: string; text?: string };
export const workspaceId = (kind: string, ...parts: string[]) => [kind, ...parts.map(encodeURIComponent)].join(":");
export const answerMessageId = (revision: AnswerRevision) => workspaceId("message", revision.analysis_job_id, revision.answer_revision_id, "transcript");
export const coachingMessageId = (revision: AnswerRevision) => workspaceId("message", revision.analysis_job_id, revision.answer_revision_id, "coaching");
export const quoteEvidenceId = (revision: AnswerRevision, item: CoachingEvidence) => workspaceId("evidence", revision.answer_revision_id, item.source_type, item.source_id, item.segment_id, item.quote);

export function usePracticeWorkspace(threadRef: RefObject<HTMLDivElement>) {
  const [tasks, setTasks] = useState<WorkspaceTask[]>([]);
  const [evidence, setEvidence] = useState<WorkspaceEvidence[]>([]);
  const revisionReferences = useRef(new Map<string, string[]>());
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const reset = useCallback(() => {
    setTasks([]); setEvidence([]); setSelectedTaskId(null); setSelectedEvidenceId(null);
    revisionReferences.current.clear();
  }, []);
  const keepPreparation = useCallback((target: "ncs" | "resume" | "readme" | "jobs" | "questions" = "jobs") => {
    setTasks((previous) => previous.filter((item) => (target !== "ncs" && item.id === "task:ncs") || (!["ncs", "resume"].includes(target) && item.id === "task:resume") || (["jobs", "questions"].includes(target) && item.id.startsWith("task:readme:")) || (target === "questions" && (item.id.startsWith("task:job:") || item.id.startsWith("task:requirements:")))));
    setEvidence((previous) => previous.filter((item) => (!["ncs", "resume"].includes(target) && item.id === "evidence:resume") || (["jobs", "questions"].includes(target) && item.id.startsWith("evidence:readme:")) || (target === "questions" && (item.id.startsWith("evidence:job:") || item.id.startsWith("evidence:requirement:")))));
    revisionReferences.current.clear();
    setSelectedTaskId(null);
    setSelectedEvidenceId(null);
  }, []);
  const register = useCallback((task: Omit<WorkspaceTask, "time"> & { time?: string }, items: WorkspaceEvidence[] = []) => {
    setTasks((previous) => previous.some((item) => item.id === task.id) ? previous : [...previous, { ...task, time: task.time || new Date().toISOString() }]);
    setEvidence((previous) => {
      const added = items.filter((item) => !previous.some((entry) => entry.id === item.id));
      return added.length ? [...previous, ...added] : previous;
    });
  }, []);
  const navigate = useCallback((taskId: string, messageId: string, evidenceId?: string) => {
    const thread = threadRef.current;
    const target = thread && [...thread.querySelectorAll<HTMLElement>("[id]")].find((item) => item.id === (evidenceId || messageId));
    const fallback = thread && [...thread.querySelectorAll<HTMLElement>("[id]")].find((item) => item.id === messageId);
    const history = thread && [...thread.querySelectorAll<HTMLElement>("[data-history-message-id]")].reverse().find((item) => item.dataset.historyMessageId === messageId);
    const element = target || fallback || history;
    if (!thread) return;
    thread.dataset.historyBrowsing = "true";
    thread.dispatchEvent(new Event("workspace-browse"));
    let ancestor = element?.parentElement;
    while (ancestor && ancestor !== thread) {
      if (ancestor instanceof HTMLDetailsElement) ancestor.open = true;
      ancestor = ancestor.parentElement;
    }
    setSelectedTaskId(taskId);
    setSelectedEvidenceId(evidenceId || null);
    if (evidenceId) {
      const library = thread.closest(".coach-chat-layout")?.querySelector(".coach-context-panel");
      const card = library && [...library.querySelectorAll<HTMLDetailsElement>("[data-evidence-id]")].find((item) => item.dataset.evidenceId === evidenceId);
      if (card) {
        card.open = true;
        let parent = card.parentElement;
        while (parent && parent !== library) {
          if (parent instanceof HTMLDetailsElement) parent.open = true;
          parent = parent.parentElement;
        }
        card.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
      }
    }
    if (!element) return;
    thread.querySelectorAll(".workspace-message-selected").forEach((item) => item.classList.remove("workspace-message-selected"));
    element.classList.add("workspace-message-selected");
    const top = Math.max(0, thread.scrollTop + element.getBoundingClientRect().top - thread.getBoundingClientRect().top - 20);
    if (typeof thread.scrollTo === "function") thread.scrollTo({ top, behavior: "smooth" });
    else thread.scrollTop = top;
    element.tabIndex = -1;
    element.focus({ preventScroll: true });
  }, [threadRef]);
  const latest = useCallback(() => {
    const thread = threadRef.current;
    if (!thread) return;
    delete thread.dataset.historyBrowsing;
    thread.dispatchEvent(new Event("workspace-latest"));
    thread.querySelectorAll(".workspace-message-selected").forEach((item) => item.classList.remove("workspace-message-selected"));
    setSelectedTaskId(null);
    setSelectedEvidenceId(null);
    if (typeof thread.scrollTo === "function") thread.scrollTo({ top: thread.scrollHeight, behavior: "smooth" });
    else thread.scrollTop = thread.scrollHeight;
  }, [threadRef]);
  const confirmed = useCallback((revision: AnswerRevision, attempt: string, result?: CoachingResponse, referenceIds: string[] = []) => {
    if (!revisionReferences.current.has(revision.answer_revision_id)) revisionReferences.current.set(revision.answer_revision_id, referenceIds);
    const references = revisionReferences.current.get(revision.answer_revision_id) || [];
    const parentId = workspaceId("task", revision.analysis_job_id, revision.answer_revision_id);
    if (!result) {
      const id = workspaceId("evidence", revision.answer_revision_id, "transcript");
      register({ id: parentId, messageId: answerMessageId(revision), title: `${attempt} 전사문 확인`, time: revision.confirmed_at, evidenceIds: [id, ...references] }, [{ id, taskId: parentId, messageId: answerMessageId(revision), title: `${attempt} 확정 전사문`, text: revision.answer_segments.map((item) => item.text).join(" "), kind: "answer", revisionId: revision.answer_revision_id, time: revision.confirmed_at }]);
      return;
    }
    const taskId = workspaceId("task", revision.analysis_job_id, revision.answer_revision_id, "coaching");
    const messageId = coachingMessageId(revision);
    const items: WorkspaceEvidence[] = result.evidence.map((item) => ({ id: quoteEvidenceId(revision, item), taskId, messageId, title: `${attempt} · ${criterionLabel(item.source_id)}`, text: item.quote, kind: "answer", segmentId: item.segment_id, revisionId: revision.answer_revision_id, time: revision.confirmed_at }));
    for (const gap of result.gaps) items.push({ id: workspaceId("check", revision.answer_revision_id, gap.criterion_id), taskId, messageId, title: `${attempt} · ${criterionLabel(gap.criterion_id)}`, text: gap.needed, kind: "check", revisionId: revision.answer_revision_id, time: revision.confirmed_at });
    register({ id: taskId, parentId, messageId, title: `${attempt} 코칭 분석 완료`, evidenceIds: [...items.map((item) => item.id), ...references] }, items);
  }, [register]);
  return { tasks, evidence, reset, keepPreparation, register, confirmed, navigate, latest, selectedTaskId, selectedEvidenceId };
}

export function WorkspaceHistory({ tasks, selectedTaskId, onSelect, onLatest }: { tasks: WorkspaceTask[]; selectedTaskId: string | null; onSelect: (task: WorkspaceTask) => void; onLatest: () => void }) {
  const timelineRef = useRef<HTMLOListElement>(null);
  useEffect(() => {
    if (!tasks.length) return;
    const frame = requestAnimationFrame(() => {
      const sidebar = timelineRef.current?.closest<HTMLElement>(".coach-sidebar");
      if (!sidebar) return;
      if (typeof sidebar.scrollTo === "function") sidebar.scrollTo({ top: sidebar.scrollHeight, behavior: "smooth" });
      else sidebar.scrollTop = sidebar.scrollHeight;
    });
    return () => cancelAnimationFrame(frame);
  }, [tasks.length]);
  return <><div className="coach-sidebar-intro workspace-intro"><span className="coach-avatar" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="8.5"/><path d="M12 7v5h4" strokeLinecap="round" strokeLinejoin="round"/></svg></span><div><strong>작업 히스토리</strong><span>이번 연습의 수행 기록</span></div></div><ol ref={timelineRef} className="workspace-timeline">{tasks.map((task) => <li key={task.id} className={task.parentId ? "is-child" : ""}><button type="button" data-task-id={task.id} aria-current={selectedTaskId === task.id ? "true" : undefined} onClick={() => onSelect(task)}><span className="workspace-task-dot" aria-hidden="true">✓</span><strong>{task.title}</strong><time dateTime={task.time}>{new Date(task.time).toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}</time>{task.text && <small className="workspace-task-description">{task.text}</small>}</button></li>)}</ol>{!tasks.length && <p className="workspace-empty">선택과 분석을 완료하면 기록이 쌓여요.</p>}<button className="workspace-latest" type="button" onClick={onLatest}><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 19V5m-6 6 6-6 6 6" strokeLinecap="round" strokeLinejoin="round"/></svg><span>최신 대화로 이동</span></button></>;
}

export function WorkspaceLibrary({ items, selectedTaskId, selectedEvidenceId, relatedEvidenceIds = [], onSelect, onChangeJob }: { items: WorkspaceEvidence[]; selectedTaskId: string | null; selectedEvidenceId: string | null; relatedEvidenceIds?: string[]; onSelect: (item: WorkspaceEvidence) => void; onChangeJob?: () => void }) {
  const groups = (["reference", "answer", "check"] as const).map((kind) => {
    const grouped = new Map<string, WorkspaceEvidence[]>();
    for (const item of items.filter((entry) => entry.kind === kind)) {
      const key = kind === "reference" ? (item.title.startsWith("공고 요구사항") ? item.taskId : item.id) : item.revisionId || item.taskId;
      grouped.set(key, [...(grouped.get(key) || []), item]);
    }
    return { kind, entries: [...grouped.entries()] };
  });
  const isRelated = (item: WorkspaceEvidence) => selectedTaskId === item.taskId || relatedEvidenceIds.includes(item.id);
  const itemContent = (item: WorkspaceEvidence) => <>{item.kind === "reference" ? <><ul className="workspace-reference-excerpts">{referenceExcerpts(item.summaryLines?.join("\n") || item.text, item.summaryLines ? 5 : 3).map((text) => <li key={text}>{text}</li>)}</ul><details className="workspace-reference-original"><summary>전체 발췌 확인</summary><strong>{item.title}</strong><p>{item.text}</p></details></> : <p>{item.text}</p>}{onChangeJob && item.taskId.startsWith("task:job:") && <button type="button" onClick={onChangeJob}>공고 변경하기</button>}{item.kind !== "reference" && <button type="button" onClick={() => onSelect(item)}>관련 대화 · 인용 보기 →</button>}{/^https?:\/\//i.test(item.sourceUrl || "") && <a href={item.sourceUrl} target="_blank" rel="noreferrer">자료 원문 보기 ↗</a>}</>;
  return <>
    <div className="coach-sidebar-intro workspace-intro"><span className="coach-avatar" aria-hidden="true"><LibraryIcon /></span><div><strong>근거 자료실</strong><span>답변에 활용된 자료와 근거를 확인해요</span></div></div>
    {groups.map(({kind, entries}) => <section className="workspace-library-group" key={kind}>
      <h2><LibraryIcon />{kind === "reference" ? "참고 자료" : kind === "answer" ? "답변 근거" : "추가 확인 사항"}<small>{entries.length}</small></h2>
      {entries.map(([key, group]) => {
        const first = group[0];
        const attempt = first.title.split(" ")[0];
        const title = kind === "reference" ? (first.title.startsWith("공고 요구사항") ? "선택한 공고 요구사항" : first.title) : kind === "answer" ? `${attempt === "2차" ? "재답변" : attempt + " 답변"} 원문` : `${attempt} 답변 보완 사항`;
        const subtitle = kind === "reference" ? (first.title.includes("채팅으로") ? "사용자가 확인 후 저장한 경험·경력" : first.title.includes("이력서") ? "사용자가 확인한 기술 및 경험" : first.title.includes("README") ? "프로젝트 개요 및 기술 스택" : first.title.startsWith("공고 요구사항") ? `${group.length}개 선택한 요구사항` : "선택한 채용 공고") : kind === "answer" ? (first.time ? new Date(first.time).toLocaleString("ko-KR", {month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"}) : "확정 답변과 코칭 인용") : `${group.length}개 항목의 설명을 보완해 주세요`;
        const single = kind === "reference" && group.length === 1;
        return <details key={key} data-evidence-id={single ? first.id : undefined} className={`workspace-evidence-card workspace-evidence-card--${kind} ${kind === "answer" && attempt === "2차" ? "workspace-evidence-card--repeat" : ""} ${group.some(isRelated) ? "is-related" : ""} ${group.some((item) => selectedEvidenceId === item.id) ? "is-selected" : ""}`}>
          <summary><span className="workspace-card-icon" aria-hidden="true"><LibraryIcon warning={kind === "check"} /></span><span className="workspace-card-copy"><strong>{title}</strong><small>{subtitle}</small></span><span className="workspace-card-badge">{kind === "reference" ? "참고 자료" : kind === "answer" ? "원문 보기" : "추가 확인 필요"}</span><span className="workspace-card-chevron" aria-hidden="true">›</span></summary>
          {single ? itemContent(first) : <div className="workspace-group-content">{group.map((item) => <details key={item.id} data-evidence-id={item.id} className={`workspace-evidence-entry ${selectedEvidenceId === item.id ? "is-selected" : ""}`}><summary>{kind === "reference" ? `요구사항 ${group.indexOf(item) + 1}` : item.title}</summary>{itemContent(item)}</details>)}</div>}
        </details>;
      })}
      {!entries.length && <p className="workspace-empty">아직 연결된 자료가 없어요.</p>}
    </section>)}
  </>;
}

function referenceExcerpts(text: string, limit = 3): string[] {
  const cleaned = text.replace(/!\[[^\]]*\]\s*\([^)]*\)/g, "")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/https?:\/\/[^\s)]+/g, "")
    .replace(/<[^>]*>/g, "")
    .replace(/[`*_#]/g, "");
  const lines = [...new Set(cleaned.split(/\n+/).map((line) => line.trim().replace(/^[-|>\s]+/, "")).filter((line) => /[가-힣a-zA-Z0-9]/.test(line)))];
  return lines.slice(0, limit).map((line) => line.length > 90 ? `${line.slice(0, 90)}…` : line);
}

function LibraryIcon({ warning = false }: { warning?: boolean }) {
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">{warning ? <><circle cx="12" cy="12" r="9"/><path d="M12 6v7m0 4h.01" strokeLinecap="round"/></> : <path d="M7 3h7l4 4v14H7zM14 3v5h4M10 12h5M10 16h5" strokeLinecap="round" strokeLinejoin="round"/>}</svg>;
}

export function criterionLabel(id: string) {
  const labels: Record<string, string> = { problem_context: "문제 상황", cause_observation: "원인 관찰 신호", cause_inference: "원인 추론 연결", own_action: "본인 행동", action_rationale: "선택 이유", result_verification: "결과 검증", personal_role: "본인 역할", project_goal: "프로젝트 목적", project_outcome: "프로젝트 결과" };
  return labels[id] || "답변 설명";
}
