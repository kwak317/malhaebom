import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AnswerRevision } from "../api/answerRevisions";
import type { CoachingResponse } from "../api/coaching";
import { useCoachThreadAutoScroll } from "../hooks/useCoachThreadAutoScroll";
import { CoachingResultPanel } from "./CoachingResultPanel";
import { WorkspaceHistory, WorkspaceLibrary, usePracticeWorkspace, answerMessageId, coachingMessageId, quoteEvidenceId, workspaceId } from "./PracticeWorkspace";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const revision: AnswerRevision = { answer_revision_id:"revision-1", analysis_job_id:"job-1", practice_session_id:"session-1", question_id:"preset-04", answer_segments:[{segment_id:"s1",text:"로그를 확인했습니다."}], confirmed_at:"2026-10-02T07:00:00Z", expires_at:"", job_snapshot_id:"snapshot-1" };
const result: CoachingResponse = {status:"needs_more_info", intent_assessment:{label:"partial",reason:"결과 설명을 보완해 주세요."}, job_alignment:[], criterion_assessments:[], evidence:[{source_type:"criterion_assessment",source_id:"own_action",segment_id:"s1",quote:"로그를 확인했습니다.",reason:"직접 행동"}], gaps:[{criterion_id:"result_verification",assessment:"not_observed",reason:"결과 없음",needed:"관찰 결과를 설명해 주세요."}], clarifying_question:null,next_actions:[],example_answer:"[관찰 결과]를 설명해 주세요."};
function Harness({ showNewResult = false }: { showNewResult?: boolean }) {
  const ref = useCoachThreadAutoScroll();
  const state = usePracticeWorkspace(ref);
  return <main className="coach-chat-layout"><aside><button onClick={() => {state.confirmed(revision,"1차");state.confirmed(revision,"1차",result);}}>등록</button><button onClick={() => {
    state.register({id:"task:ncs",messageId:"message:ncs",title:"역량 자기점검 완료",evidenceIds:[]});
    state.register({id:"task:readme:project",messageId:"message:readme:project",title:"README 분석 완료",evidenceIds:["evidence:readme:project"]}, [{id:"evidence:readme:project",taskId:"task:readme:project",messageId:"message:readme:project",title:"GitHub README",text:"Spring Boot",kind:"reference"}]);
  }}>준비 등록</button><button onClick={() => state.keepPreparation()}>공고 초기화</button><WorkspaceHistory tasks={state.tasks} selectedTaskId={state.selectedTaskId} onSelect={(task) => state.navigate(task.id,task.messageId)} onLatest={state.latest} /></aside><div ref={ref} className="coach-thread"><article id={answerMessageId(revision)}>확정 전사문</article><article id={coachingMessageId(revision)}><CoachingResultPanel revision={revision} result={result} onEvidenceSelect={state.navigate}/></article>{showNewResult && <article className="coach-coaching-result-message">새 결과</article>}</div><aside className="coach-context-panel"><WorkspaceLibrary items={state.evidence} selectedTaskId={state.selectedTaskId} selectedEvidenceId={state.selectedEvidenceId} onSelect={(item) => state.navigate(item.taskId,item.messageId,item.id)} /></aside></main>;
}
function PreparationHarness() {
  const ref = useCoachThreadAutoScroll();
  const workspace = usePracticeWorkspace(ref);
  const titles = ["역량 자기점검 완료", "채용 공고 선택", "공고 요구사항 선택 완료"];
  return <><button onClick={() => titles.forEach((title, index) => workspace.register({ id: `task:${index}`, messageId: `message:${index}`, title, evidenceIds: [] }))}>준비 항목 등록</button>
    <WorkspaceHistory tasks={workspace.tasks} selectedTaskId={workspace.selectedTaskId} onSelect={(task) => workspace.navigate(task.id, task.messageId)} onLatest={workspace.latest} />
    <div ref={ref} className="coach-thread">{titles.map((title, index) => <article key={title} id={`message:${index}`} className="coach-message coach-message-user">{title}</article>)}</div></>;
}
describe("작업·메시지·근거 연결", () => {
  let container: HTMLDivElement; let root: Root;
  beforeEach(() => {vi.useFakeTimers();container=document.createElement("div");document.body.append(container);root=createRoot(container);});
  afterEach(async () => {await act(async () => root.unmount());container.remove();vi.useRealTimers();});
  const click = async (text:string) => {const button=[...container.querySelectorAll<HTMLButtonElement>("button")].find((item)=>item.textContent?.includes(text));expect(button).toBeTruthy();await act(async()=>button!.click());};
  it("준비 항목의 사용자 채팅 강조를 새 메시지로 취급하지 않고 이동 위치를 유지한다", async () => {
    await act(async () => root.render(<PreparationHarness />));
    await click("준비 항목 등록");
    await act(async () => vi.runAllTimersAsync());
    const thread = container.querySelector<HTMLDivElement>(".coach-thread")!;
    const scrollTo = vi.fn(); thread.scrollTo = scrollTo;
    Object.defineProperty(thread, "scrollHeight", { value: 3000, configurable: true });
    thread.getBoundingClientRect = () => ({ top: 100 } as DOMRect);
    for (let index = 0; index < 3; index += 1) {
      const target = container.querySelector<HTMLElement>(`[id="message:${index}"]`)!;
      target.getBoundingClientRect = () => ({ top: 500 + index * 200 } as DOMRect);
      scrollTo.mockClear();
      await act(async () => container.querySelector<HTMLButtonElement>(`[data-task-id="task:${index}"]`)!.click());
      await act(async () => vi.runAllTimersAsync());
      expect(scrollTo).toHaveBeenCalledTimes(1);
      expect(scrollTo).toHaveBeenLastCalledWith({ top: 380 + index * 200, behavior: "smooth" });
      expect(thread.dataset.historyBrowsing).toBe("true");
      expect(target.classList.contains("workspace-message-selected")).toBe(true);
    }
  });
  it("참고 자료는 반복 문장과 이미지 주소를 요약에서 제외하고 원문을 보존한다", async () => {
    const text = "Spring Boot로 API를 구현했습니다.\n![Java](https://img.shields.io/badge/Java-17-red)\nSpring Boot로 API를 구현했습니다.\nMySQL을 사용했습니다.";
    await act(async () => root.render(<WorkspaceLibrary items={[{id:"readme",taskId:"readme-task",messageId:"readme-message",title:"GitHub README",text,kind:"reference"}]} selectedTaskId={null} selectedEvidenceId={null} onSelect={() => {}} />));
    expect(container.querySelector(".workspace-reference-excerpts")?.textContent).toBe("Spring Boot로 API를 구현했습니다.MySQL을 사용했습니다.");
    expect(container.querySelector(".workspace-reference-original p")?.textContent).toBe(text);
  });
  it("참고 자료의 핵심 요약을 표시하고 대화 이동 버튼과 팁은 제외한다", async () => {
    const text = "서비스 소개와 원문 기술 근거";
    const summaryLines = ["Spring Boot — REST API 서버", "MySQL — 관계형 데이터 저장", "OAuth2 — 소셜 로그인"];
    await act(async () => root.render(<WorkspaceLibrary items={[{id:"readme",taskId:"readme-task",messageId:"readme-message",title:"GitHub README",text,summaryLines,kind:"reference",sourceUrl:"https://github.com/example/project"}]} selectedTaskId={null} selectedEvidenceId={null} onSelect={() => {}} />));
    expect(container.querySelector(".workspace-reference-excerpts")?.textContent).toBe(summaryLines.join(""));
    expect(container.querySelector(".workspace-reference-original p")?.textContent).toBe(text);
    expect(container.textContent).not.toContain("관련 대화 · 인용 보기");
    expect(container.textContent).not.toContain("더 좋은 답변을 위한 팁");
    expect(container.querySelector("a")?.textContent).toContain("자료 원문 보기");
  });
  it("공고 초기화는 준비 기록만 남기고 답변·코칭·확인 사항을 제거한다", async () => {
    await act(async () => root.render(<Harness />));
    await click("준비 등록");
    await click("등록");
    expect(container.querySelectorAll(".workspace-evidence-card--answer")).toHaveLength(1);
    expect(container.querySelectorAll(".workspace-evidence-card--check")).toHaveLength(1);
    await click("공고 초기화");
    expect([...container.querySelectorAll(".workspace-timeline strong")].map((item) => item.textContent)).toEqual(["역량 자기점검 완료", "README 분석 완료"]);
    expect(container.querySelectorAll(".workspace-evidence-card--reference")).toHaveLength(1);
    expect(container.querySelectorAll(".workspace-evidence-card--answer, .workspace-evidence-card--check")).toHaveLength(0);
    expect(container.querySelector('[aria-current="true"]')).toBeNull();
  });
  it("작업 추가 시 왼쪽만 맨 아래로 이동하고 선택 변경만으로는 이동하지 않는다", async () => {
    const task = { id:"task-1", messageId:"message-1", title:"README 분석 완료", time:revision.confirmed_at, evidenceIds:[] };
    const renderHistory = (tasks: typeof task[], selectedTaskId: string | null = null) => <aside className="coach-sidebar"><WorkspaceHistory tasks={tasks} selectedTaskId={selectedTaskId} onSelect={() => {}} onLatest={() => {}} /></aside>;
    await act(async () => root.render(renderHistory([])));
    const sidebar = container.querySelector<HTMLElement>(".coach-sidebar")!;
    const scrollTo = vi.fn(); sidebar.scrollTo = scrollTo;
    Object.defineProperty(sidebar,"scrollHeight",{value:1200,configurable:true});
    await act(async () => root.render(renderHistory([task])));
    await act(async () => vi.runAllTimersAsync());
    expect(scrollTo).toHaveBeenLastCalledWith({top:1200,behavior:"smooth"});
    scrollTo.mockClear();
    await act(async () => root.render(renderHistory([task],task.id)));
    await act(async () => vi.runAllTimersAsync());
    expect(scrollTo).not.toHaveBeenCalled();
    Object.defineProperty(sidebar,"scrollHeight",{value:1500,configurable:true});
    await act(async () => root.render(renderHistory([task,{...task,id:"task-2"}])));
    await act(async () => vi.runAllTimersAsync());
    expect(scrollTo).toHaveBeenLastCalledWith({top:1500,behavior:"smooth"});
  });
  it("같은 분석 작업의 새 revision과 같은 문장 ID가 충돌하지 않는다",()=>{
    const second={...revision,answer_revision_id:"revision-2"};
    expect(answerMessageId(revision)).not.toBe(answerMessageId(second));
    expect(coachingMessageId(revision)).not.toBe(coachingMessageId(second));
    expect(quoteEvidenceId(revision,result.evidence[0])).not.toBe(quoteEvidenceId(second,result.evidence[0]));
  });
  it("원문은 처음부터 보이고 근거 클릭은 해당 작업을 선택하며 새 결과가 읽기 위치를 바꾸지 않는다",async()=>{
    await act(async()=>root.render(<Harness/>));await click("등록");
    await click("관련 대화 · 인용 보기"); // 전사문
    const quoteCard=container.querySelector<HTMLDetailsElement>(`[data-evidence-id="${quoteEvidenceId(revision,result.evidence[0])}"]`)!;
    await act(async()=>quoteCard.querySelector<HTMLButtonElement>("button")!.click());
    expect(container.querySelector("details.workspace-coaching-details")).toBeNull();
    expect(container.querySelector(".workspace-coaching-details")?.textContent).toContain("판정과 근거");
    expect(document.getElementById(quoteEvidenceId(revision,result.evidence[0]))?.classList.contains("workspace-message-selected")).toBe(true);
    expect(container.querySelector('[aria-current="true"]')?.getAttribute("data-task-id")).toBe(workspaceId("task",revision.analysis_job_id,revision.answer_revision_id,"coaching"));
    const thread=container.querySelector<HTMLDivElement>(".coach-thread")!;const scrollTo=vi.fn();thread.scrollTo=scrollTo;
    await act(async()=>root.render(<Harness showNewResult/>));await act(async()=>vi.runAllTimersAsync());expect(scrollTo).not.toHaveBeenCalled();
    await click("최신 대화로 이동");expect(thread.dataset.historyBrowsing).toBeUndefined();expect(scrollTo).toHaveBeenCalled();
  });
  it("중앙 인용 링크는 오른쪽 자료실을 펼치고 부족 항목도 정확한 위치로 이동한다",async()=>{
    await act(async()=>root.render(<Harness/>));await click("등록");await click("근거 자료실과 연결");
    expect(container.querySelectorAll(".workspace-evidence-card--answer")).toHaveLength(1);
    expect(container.querySelector(".workspace-evidence-card--answer")?.textContent).toContain("1차 답변 원문");
    expect(container.querySelector<HTMLDetailsElement>(".workspace-evidence-card--answer")?.open).toBe(true);
    const id=quoteEvidenceId(revision,result.evidence[0]);expect([...container.querySelectorAll<HTMLDetailsElement>("[data-evidence-id]")].find(item=>item.dataset.evidenceId===id)?.open).toBe(true);
    const gap=container.querySelector<HTMLDetailsElement>(`[data-evidence-id="${workspaceId("check",revision.answer_revision_id,"result_verification")}"]`)!;
    await act(async()=>gap.querySelector<HTMLButtonElement>("button")!.click());
    expect(document.getElementById(workspaceId("check",revision.answer_revision_id,"result_verification"))?.classList.contains("workspace-message-selected")).toBe(true);
  });
});
