import "../styles/resume-chat.css";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { InterviewFollowUpChat } from "./InterviewFollowUpChat";
import { ResumeDraftChat, type ResumeCompletion, type ResumeDraftLayout, type ResumeDraftMaterials } from "./ResumeDraftChat";
import { importResumeInformation } from "../api/resumeAssistance";
import { ResumeCompletionChat } from "./ResumeCompletionChat";

import { ResumeDocumentChat } from "./ResumeDocumentChat";
import { buildResumeDocument, type ResumeDocument } from "../resume/document";

type Entry = { kind: "user" | "assistant"; message: string }
  | { kind: "layouts" }
  | { kind: "document"; document: ResumeDocument }
  | { kind: "draft"; layout: ResumeDraftLayout; completion?: ResumeCompletion; materials?: ResumeDraftMaterials };

export function PostComparisonActions({ practiceSessionId, materials }: { practiceSessionId: string; materials?: ResumeDraftMaterials }) {
  const [request, setRequest] = useState<string | null>(null);
  const [finishRequested, setFinishRequested] = useState(false);
  const [input, setInput] = useState("");
  const [entries, setEntries] = useState<Entry[]>([]);
  const [complement, setComplement] = useState<{ index: number; agreed: boolean; imported?: ResumeCompletion; materials?: ResumeDraftMaterials; polish?: boolean } | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [savedDocuments, setSavedDocuments] = useState<ResumeDocument[]>([]);
  const downloadLock = useRef(false);
  const [pendingImportIndex, setPendingImportIndex] = useState<number | null>(null);
  const [replacementFile, setReplacementFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");
  const importController = useRef<AbortController | null>(null);
  useEffect(() => () => importController.current?.abort(), []);
  const busy = Boolean(request || complement || downloading || importing);
  const reconstruct = (index: number) => {
    const draft = entries[index];
    if (busy || draft?.kind !== "draft" || !draft.completion) return;
    const document = buildResumeDocument(draft.layout, draft.materials, draft.completion);
    setEntries(previous => [...previous, { kind: "user", message: "이력서 형식에 맞게 재구성하기" }, { kind: "document", document }]);
  };
  const download = async (document: ResumeDocument) => {
    if (downloadLock.current || request || complement) return;
    downloadLock.current = true; setDownloading(true);
    try { const { downloadResumePdf } = await import("../resume/pdf"); await downloadResumePdf(document); setSavedDocuments(previous => previous.includes(document) ? previous : [...previous, document]); }
    catch { setEntries(previous => [...previous, { kind: "assistant", message: "PDF 다운로드를 완료하지 못했어요. 잠시 후 다운로드 버튼으로 다시 시도해 주세요." }]); }
    finally { downloadLock.current = false; setDownloading(false); }
  };
  const activeDraft = complement ? entries[complement.index] : undefined;
  const askConsent = (index: number, polish = false) => {
    if (busy) return;
    setInput("");
    setEntries((previous) => [...previous, { kind: "user", message: "이력서 보완하기" }]);
    setComplement({ index, agreed: false, polish });
  };
  const importInformation = async (index: number, fileOverride?: File) => {
    if (busy || importController.current) return;
    const sourceFile = fileOverride ?? replacementFile ?? materials?.resumeFile;
    const hasSubmittedInformation = Boolean(materials?.resumeProfile?.facts.length || materials?.readmeAnalysis || materials?.confirmedExperiences?.length);
    const consent = "제출한 이력서, README와 채팅으로 추가한 경력·경험 등 제출한 정보를 가져와 이력서 초안을 채웁니다. 이미 수정한 내용은 유지합니다." + (sourceFile ? "\n이력서 원문 텍스트는 외부 AI 서비스의 데이터 미보관 경로로 처리하며, 가져온 개인정보는 현재 화면에서만 사용합니다." : "\n확인된 자료를 현재 화면에서 사용합니다.") + "\n동의하시겠습니까?";
    if (!window.confirm(consent)) return;
    if (!sourceFile && !hasSubmittedInformation) { setPendingImportIndex(index); return; }
    if (sourceFile && (sourceFile.size > 5 * 1024 * 1024 || !sourceFile.name.toLowerCase().endsWith(".pdf"))) { setImportError("5MB 이하 PDF를 첨부해 주세요."); return; }
    const controller = new AbortController(); importController.current = controller;
    setImporting(true); setImportError(""); setPendingImportIndex(null); setReplacementFile(sourceFile ?? null);
    try {
      const result = sourceFile ? await importResumeInformation(sourceFile, controller.signal) : {items: [], omitted_items: 0};
      if (controller.signal.aborted) return;
      const draft = entries[index]; if (draft?.kind !== 'draft') return;
      const imported: ResumeCompletion = {};
      for (const category of ["role", "career", "technology", "project", "education", "qualification"] as const) {
        imported[category] = (materials?.resumeProfile?.facts ?? []).filter(fact => fact.category === category).map(fact => fact.value).join("\n");
      }
      imported.repository = /^https?:\/\//i.test(materials?.readmeAnalysis?.source_url ?? "") ? materials!.readmeAnalysis!.source_url : "";
      Object.assign(imported, draft.completion);
      for (const item of result.items) if (!Object.prototype.hasOwnProperty.call(draft.completion ?? {}, item.field) && !imported[item.field]) imported[item.field] = item.value;
      const firstImport = !draft.completion;
      setEntries(previous => [...previous, {kind:'user',message:'제출한 정보 가져오기'}, ...(result.omitted_items ? [{kind:'assistant' as const,message:'원문에서 확인된 정보만 가져왔어요. 일부 항목은 근거를 확인하지 못해 제외했으니 빈칸을 확인하고 직접 채워 주세요.'}] : []),
        ...(firstImport ? [{kind:'draft' as const,layout:draft.layout,completion:imported,materials}] : [])]);
      if (!firstImport) setComplement({index,agreed:true,imported,materials});
    } catch (error) { if (!controller.signal.aborted) setImportError(error instanceof Error ? error.message : "기존 정보를 가져오지 못했어요."); }
    finally { if (!controller.signal.aborted) setImporting(false); if (importController.current === controller) importController.current = null; }
  };
  const cancelComplement = () => {
    setInput(""); setComplement(null);
    setEntries((previous) => [...previous, { kind: "assistant", message: "이력서 보완을 취소했어요. 이번 보완에서 입력한 내용은 반영하지 않았어요." }]);
  };
  const completeComplement = (completion: ResumeCompletion) => {
    if (!complement?.agreed) return;
    setEntries((previous) => {
      const draft = previous[complement.index];
      if (draft?.kind !== "draft") return previous;
      const importedMaterials = complement.materials ?? draft.materials;
      return [...previous.map((entry, index) => index === complement.index && entry.kind === "draft" ? { ...entry, completion, materials: importedMaterials } : entry),
        { kind: "assistant", message: "입력한 내용을 반영한 이력서 초안을 다시 보내드릴게요." },
        { kind: "draft", layout: draft.layout, completion, materials: importedMaterials }];
    });
    setComplement(null);
  };

  const chooseLayout = (layout: ResumeDraftLayout, message: string) => {
    if (busy) return;
    setEntries((previous) => [...previous, { kind: "user", message }, { kind: "draft", layout }]);
  };
  const showLayouts = (message: string) => {
    if (busy) return;
    setEntries((previous) => [...previous, { kind: "user", message }, { kind: "layouts" }]);
  };
  const startFollowUp = (message: string) => {
    if (busy) return;
    setEntries((previous) => [...previous, { kind: "user", message }]);
    setRequest(message);
  };
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = input.trim();
    if (!message || busy) return;
    setInput("");
    const command = message.replace(/[\s.!?。！？]/g, "");
    if (/^(?:그만(?:하기|해|해줘|할게)?|(?:연습|면접)(?:종료|종료하기|끝|끝내기|마치기|마칠게)|종료|종료하기)$/.test(command)) {
      setEntries(previous => [...previous, {kind:"user",message}]);
      setFinishRequested(true); setRequest(message);
      return;
    }
    if (/^이력서문장(?:을)?다듬(?:기|어줘|어주세요)?$/.test(command)) {
      let index = entries.length - 1; while (index >= 0 && entries[index].kind !== 'draft') index -= 1;
      if (index >= 0) askConsent(index, true);
      else setEntries(previous => [...previous, {kind:'assistant',message:'먼저 이력서 초안을 작성하고 보완 내용을 입력해 주세요.'}]);
      return;
    }
    if (/^이력서(?:PDF)?(?:를|을)?다운로드(?:하기|해줘|해주세요)?$/i.test(command)) {
      let index = entries.length - 1;
      while (index >= 0 && entries[index].kind !== "document") index -= 1;
      const target = entries[index];
      setEntries(previous => [...previous, { kind: "user", message }]);
      if (target?.kind === "document") void download(target.document);
      else setEntries(previous => [...previous, { kind: "assistant", message: "보완을 마친 초안의 ‘이력서 형식에 맞게 재구성하기’를 먼저 눌러 주세요." }]);
      return;
    }
    if (/^이력서(?:초안)?(?:을|를)?보완(?:하기|해줘|해주세요|하자|할래|할게)?$/.test(command)) {
      let index = entries.length - 1;
      while (index >= 0 && entries[index].kind !== "draft") index -= 1;
      if (index >= 0) askConsent(index);
      else setEntries((previous) => [...previous, { kind: "user", message }, { kind: "assistant", message: "먼저 이력서 초안을 작성해 주세요. 초안 아래의 ‘보완하기’를 누르면 동의 안내가 나와요." }]);
      return;
    }
    if (/^(?:꼬리질문|추가질문)(?:으로|을|를)?(?:(?:연습|생성|시작|진행)(?:하기|해줘|해주세요|하자|할래|할게|해볼래)?|해줘|해주세요|만들어줘|만들어주세요)?$/.test(command)) {
      startFollowUp(message);
      return;
    }
    const layout = /^(프로젝트|경력)중심(?:이력서)?(?:로|으로)?(?:(?:선택|작성|생성)(?:하기|해줘|해주세요|할래|할게)?|보여줘|보여주세요)?$/.exec(command);
    if (layout) {
      chooseLayout(layout[1] === "프로젝트" ? "project" : "career", message);
      return;
    }
    if (/^이력서(?:초안)?(?:을|를)?(?:(?:작성|생성)(?:하기|해줘|해주세요|할래|할게)?|만들어줘|만들어주세요|보여줘|보여주세요)?$/.test(command)) {
      showLayouts(message);
      return;
    }
    setEntries((previous) => [...previous, { kind: "user", message }, { kind: "assistant", message: "‘꼬리질문 해줘’ 또는 ‘이력서 초안 작성해줘’라고 입력해 주세요. ‘프로젝트 중심 이력서’나 ‘경력 중심 이력서’를 입력하면 해당 초안을 바로 볼 수 있어요." }]);
  };

  return <>
    <article className="coach-message coach-message-assistant coach-next-message">
      <span className="coach-message-avatar" aria-hidden="true">✦</span>
      <div>
        <strong>말해봄 코치</strong>
        <h3>다음으로 무엇을 해볼까요?</h3>
        <p>답변을 바탕으로 추가 질문을 연습하거나, 확인한 경험을 이력서 초안으로 정리할 수 있어요.</p>
        <div className="post-comparison-actions">
          <button className="coach-recording-button" type="button" disabled={busy}
            onClick={() => startFollowUp("꼬리질문으로 연습하기")}>꼬리질문으로 연습하기</button>
          <button className="post-comparison-resume-button" type="button" disabled={busy}
            onClick={() => showLayouts("이력서 초안 작성하기")}>이력서 초안 작성하기</button>
        </div>
      </div>
    </article>
    {entries.map((entry, index) => entry.kind === "layouts"
      ? <article key={index} className="coach-message coach-message-assistant">
          <span className="coach-message-avatar" aria-hidden="true">✦</span>
          <div><strong>말해봄 코치</strong><h3>어떤 이력서 양식으로 정리할까요?</h3>
            <p>프로젝트 중심은 프로젝트 경험을, 경력 중심은 경력·활동을 먼저 보여줘요.</p>
            <div className="post-comparison-actions">
              <button className="coach-recording-button" type="button" disabled={busy} onClick={() => chooseLayout("project", "프로젝트 중심 이력서")}>프로젝트 중심 이력서</button>
              <button className="post-comparison-resume-button" type="button" disabled={busy} onClick={() => chooseLayout("career", "경력 중심 이력서")}>경력 중심 이력서</button>
            </div>
          </div>
        </article>
      : entry.kind === "draft" ? <ResumeDraftChat key={index} layout={entry.layout} materials={entry.materials} completion={entry.completion} onImport={() => { void importInformation(index); }} onComplement={() => askConsent(index)} complementDisabled={busy} onReconstruct={() => reconstruct(index)} />
      : entry.kind === "document" ? <ResumeDocumentChat key={index} document={entry.document} saved={savedDocuments.includes(entry.document)} onDownload={() => { void download(entry.document); }} disabled={busy} />
      : entry.kind === "user" ? <article key={index} className="coach-message coach-message-user coach-message-user-input"><div><span>나</span><strong>{entry.message}</strong></div></article>
      : <article key={index} className="coach-message coach-message-assistant"><span className="coach-message-avatar" aria-hidden="true">✦</span><div><strong>말해봄 코치</strong><p>{entry.message}</p></div></article>)}
    {pendingImportIndex !== null && <article className="coach-message coach-message-assistant resume-import-upload-message"><div>
      <strong>기존 이력서 PDF를 다시 첨부해 주세요.</strong>
      <p>개인정보 보호를 위해 원본 파일은 저장하지 않아요. 새로고침한 경우 다시 첨부해야 합니다.</p>
      <div className="resume-import-upload-actions">
        <label className="resume-file-label" htmlFor="resume-import-file">
          <span className="resume-file-icon" aria-hidden="true">PDF</span>
          <span className="resume-file-info"><strong>기존 이력서 PDF 선택</strong><span>첨부하면 정보 가져오기를 시작해요.</span></span>
          <input className="resume-file-input" id="resume-import-file" type="file" accept="application/pdf" aria-label="기존 이력서 PDF" onChange={event => { const file=event.target.files?.[0]; if (file) { void importInformation(pendingImportIndex,file); } }} />
        </label>
        <button className="post-comparison-resume-button" type="button" onClick={() => setPendingImportIndex(null)}>취소</button>
      </div>
    </div></article>}
    {importing && <article className="coach-message coach-message-assistant" role="status"><div><strong>제출한 정보를 가져오고 있어요.</strong><p>원문에 있는 정보만 가져옵니다. 완료 후 빈칸을 확인해 주세요.</p></div></article>}
    {importError && <p className="resume-completion-error" role="alert">{importError}</p>}
    {complement && !complement.agreed && <article className="coach-message coach-message-assistant" aria-label="이력서 보완 개인정보 동의 안내">
      <span className="coach-message-avatar" aria-hidden="true">✦</span><div><strong>이력서 보완 전 확인해 주세요</strong>
        <p>이력서 보완 작성 시 이름, 이메일, 경력 정보와 증명사진 등 개인정보를 입력할 수 있습니다. 입력 항목은 선택 사항입니다.</p>
        <p>입력한 개인정보는 이력서 보완에만 사용되며, 서버나 브라우저 저장소에 저장되지 않습니다. 현재 화면에서만 임시로 사용하고 새로고침하거나 화면을 나가면 사라집니다.</p>
        <p>동의하시겠습니까? 동의하지 않아도 기존 초안은 확인할 수 있습니다.</p>
        <div className="post-comparison-actions"><button type="button" className="post-comparison-resume-button" onClick={() => { setInput(""); setComplement({ ...complement, agreed: true }); }}>동의하고 보완하기</button><button type="button" className="post-comparison-resume-button" onClick={cancelComplement}>동의하지 않기</button></div>
      </div></article>}
    {complement?.agreed && <ResumeCompletionChat onComplete={completeComplement} onCancel={cancelComplement} materials={materials} scrollToBottom={Boolean(complement.imported)} autoPolish={complement.polish} initial={complement.imported ?? (activeDraft?.kind === "draft" ? activeDraft.completion : undefined)} />}
    {request ? <InterviewFollowUpChat practiceSessionId={practiceSessionId} finishOnStart={finishRequested} />
      : !complement && <form className="coach-composer interview-followup-composer" onSubmit={submit}>
        <label className="sr-only" htmlFor="post-comparison-chat-input">비교 후 다음 활동 요청</label>
        <input id="post-comparison-chat-input" type="text" value={input} maxLength={300}
          placeholder="꼬리질문 또는 이력서 초안 작성을 요청해 보세요."
          onChange={(event) => setInput(event.target.value)} />
        <button type="submit" disabled={!input.trim()}>보내기 ↑</button>
      </form>}
  </>;
}
