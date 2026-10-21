import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { polishResumeInformation, POLISH_FIELDS, type Clarification, type PolishField } from "../api/resumeAssistance";
import type { ResumeCompletion, ResumeDraftMaterials } from "./ResumeDraftChat";

const groups = [
  { title: "기본 정보", fields: [["name", "이름", false], ["email", "이메일", false], ["role", "지원 직무", false], ["github", "GitHub 프로필 주소", false], ["portfolio", "포트폴리오 주소", false], ["intro", "소개", true]] },
  { title: "경력 및 기술", fields: [["career", "경력 (회사·직무·기간)", true], ["careerDetails", "경력별 담당 업무와 확인한 결과", true], ["technology", "기술 스택과 활용 경험", true]] },
  { title: "프로젝트 경험", fields: [["project", "프로젝트명·기간·팀 규모", true], ["projectRole", "본인이 담당한 기능과 구현 범위", true], ["problem", "발생한 문제", true], ["action", "본인이 수행한 행동", true], ["result", "실제로 확인한 결과와 확인 방법", true], ["outcome", "성과 또는 관찰한 변화", true], ["repository", "프로젝트 GitHub / README 주소", false]] },
  { title: "교육 및 자격", fields: [["education", "학교·전공 또는 교육 과정·기간", true], ["qualification", "보유 자격", true]] },
] as const;

// Identity and photo stay in component memory; experience text is sent only after AI consent.
export function ResumeCompletionChat({ onComplete, onCancel, initial = {}, autoPolish = false, scrollToBottom = false }: { onComplete: (value: ResumeCompletion) => void; onCancel: () => void; materials?: ResumeDraftMaterials; initial?: ResumeCompletion; autoPolish?: boolean; scrollToBottom?: boolean }) {
  const [values, setValues] = useState<ResumeCompletion>(() => ({ ...initial }));
  const [error, setError] = useState<{field: keyof ResumeCompletion; message: string} | null>(null);
  const cardRef = useRef<HTMLElement>(null);
  const photoRequest = useRef(0);
  const aiController = useRef<AbortController | null>(null);
  const autoStarted = useRef(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [aiError, setAiError] = useState("");
  const [questions, setQuestions] = useState<Clarification[]>([]);
  const [answer, setAnswer] = useState("");
  const [changes, setChanges] = useState<{field: PolishField; before: string; after: string}[]>([]);
  const [dialogue, setDialogue] = useState<{question:string;answer:string}[]>([]);
  const fieldLabel = (field: string) => { for (const group of groups) for (const item of group.fields) if (item[0] === field) return item[1]; return field; };
  const polish = async (target?: Clarification) => {
    if (aiController.current || readingPhoto) return;
    if (!target && !window.confirm("말해봄 에이전트가 경험 설명을 다듬습니다. 사실 확인이 필요하면 질문하며, 답변한 항목만 다시 정리합니다.\n경험 설명은 외부 AI 서비스로 전달됩니다. 이름·연락처·사진은 전송하지 않으며, 처리 내용은 저장하지 않습니다. 경험 설명에 개인정보를 적지 마세요. 동의하시겠습니까?")) return;
    const request = new AbortController(); aiController.current = request;
    setAiBusy(true); setAiError("");
    const input: ResumeCompletion = target ? {[target.field]: `${values[target.field] || ''}\n사용자가 확인한 보완: ${answer.trim()}`} : values;
    if (target) setDialogue(previous => [...previous,{question:target.question,answer:answer.trim()}]);
    try {
      const result = await polishResumeInformation(input, request.signal);
      if (request.signal.aborted) return;
      const allowedItems=result.items.filter(item => POLISH_FIELDS.includes(item.field as PolishField) && (!target || item.field === target.field));
      const nextChanges=allowedItems.map(item => ({field:item.field as PolishField,before:values[item.field] || '',after:item.value}));
      setValues(previous => { const next={...previous}; for (const item of allowedItems) next[item.field]=item.value; return next; });
      setChanges(nextChanges);
      setQuestions(previous => [...(target ? previous.filter(item => item.field !== target.field) : []),...(result.questions || []).filter(item => !target || item.field === target.field)]);
      setAnswer("");
    } catch (error) { if (!request.signal.aborted) setAiError(error instanceof Error ? error.message : "문장을 다듬지 못했어요. 작성한 내용은 유지했습니다."); }
    finally { if (!request.signal.aborted) setAiBusy(false); if (aiController.current === request) aiController.current = null; }
  };
  useEffect(() => { if (autoPolish && !autoStarted.current) { autoStarted.current = true; void polish(); } }, [autoPolish]);
  const [photoError, setPhotoError] = useState("");
  const [readingPhoto, setReadingPhoto] = useState(false);
  useEffect(() => { cardRef.current?.scrollIntoView?.({ block: scrollToBottom ? "end" : "start" }); return () => { photoRequest.current += 1; aiController.current?.abort(); }; }, []);
  const attachPhoto = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]; event.target.value = "";
    if (!file) return;
    const request = ++photoRequest.current;
    setReadingPhoto(false); setPhotoError("");
    if (!["image/jpeg", "image/png"].includes(file.type) || file.size > 5 * 1024 * 1024) { setPhotoError("5MB 이하의 JPG 또는 PNG 사진을 선택해 주세요."); return; }
    setReadingPhoto(true);
    const failed = () => { if (request === photoRequest.current) { setPhotoError("사진을 읽지 못했어요. 다른 JPG 또는 PNG 파일을 선택해 주세요."); setReadingPhoto(false); } };
    const reader = new FileReader(); reader.onerror = failed;
    reader.onload = () => {
      if (request !== photoRequest.current) return;
      const url = String(reader.result);
      if (!(file.type === "image/png" ? /^data:image\/png;base64,iVBORw0KGgo/.test(url) : /^data:image\/jpeg;base64,\/9j\//.test(url))) { failed(); return; }
      const image = new Image(); image.onerror = failed;
      image.onload = () => { if (request === photoRequest.current) { setValues(previous => ({...previous, photoDataUrl: url})); setReadingPhoto(false); } };
      image.src = url;
    };
    reader.readAsDataURL(file);
  };
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (readingPhoto || aiBusy || questions.length) return;
    const completed: ResumeCompletion = {};
    for (const group of groups) for (const [field] of group.fields) completed[field] = (values[field] ?? "").trim();
    completed.photoDataUrl = values.photoDataUrl || "";
    if (completed.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(completed.email)) {
      setError({field: "email", message: "이메일 형식을 확인해 주세요."}); cardRef.current?.querySelector<HTMLInputElement>("#resume-completion-email")?.focus(); return;
    }
    for (const field of ["github", "portfolio", "repository"] as const) if (completed[field]) {
      try { const url = new URL(completed[field]!); if (!["http:", "https:"].includes(url.protocol)) throw new Error(); }
      catch { setError({field, message: "http:// 또는 https://로 시작하는 올바른 주소를 입력해 주세요."}); cardRef.current?.querySelector<HTMLInputElement>(`#resume-completion-${field}`)?.focus(); return; }
    }
    onComplete(completed);
  };
  return <article ref={cardRef} className={`coach-message coach-message-assistant resume-completion-form-message${scrollToBottom ? " resume-import-form-message" : ""}`} aria-label="이력서 보완 입력 폼">
    <span className="coach-message-avatar" aria-hidden="true">✦</span><div><strong>말해봄 코치</strong><h3>이력서 내용을 한 번에 보완해 주세요.</h3>
      <p>기존 내용을 확인하고 빈 항목을 채우거나 수정해 주세요. 모든 항목은 선택 사항이며, 해당 사항이 없으면 비워 둘 수 있어요.</p>
      <p>실제로 확인한 경험만 작성해 주세요. 성과 수치를 모르면 관찰한 변화로 적어 주세요.</p>
      <form className="resume-completion-form" onSubmit={submit} noValidate>
        <fieldset><legend>증명사진 (선택)</legend><div className="resume-photo-upload">
          <div className="resume-photo-slot">{values.photoDataUrl ? <img src={values.photoDataUrl} alt="첨부할 증명사진 미리보기" /> : <span>증명사진</span>}</div>
          <div><label htmlFor="resume-completion-photo">증명사진 첨부</label><input id="resume-completion-photo" type="file" accept="image/jpeg,image/png" onChange={attachPhoto} aria-describedby="resume-photo-help" />
          <p id="resume-photo-help">JPG·PNG, 최대 5MB. 사진은 현재 화면에서만 사용하고 서버에 업로드하지 않아요.</p>
          {readingPhoto && <p role="status">사진을 읽고 있어요.</p>}{photoError && <p role="alert">{photoError}</p>}
          {values.photoDataUrl && <button type="button" className="post-comparison-resume-button" onClick={() => { photoRequest.current += 1; setReadingPhoto(false); setPhotoError(""); setValues(previous => ({...previous, photoDataUrl: ""})); }}>사진 삭제</button>}</div>
        </div></fieldset>
        {groups.map(group => <fieldset disabled={aiBusy} key={group.title}><legend>{group.title}</legend>{group.fields.map(([field, label, multiline]) => {
          const id = `resume-completion-${field}`;
          const common = { id, name: field, value: values[field] ?? "", maxLength: 2000, autoComplete: "off", onChange: (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => { setValues(previous => ({...previous, [field]: event.target.value})); if (error?.field === field) setError(null); }, "aria-invalid": error?.field === field, "aria-describedby": error?.field === field ? "resume-completion-error" : undefined };
          return <div className="resume-completion-field" key={field}><label htmlFor={id}>{label}</label>{multiline ? <textarea {...common} rows={3} /> : <input {...common} type={field === "email" ? "email" : "text"} />}{error?.field === field && <p id="resume-completion-error" role="alert">{error.message}</p>}</div>;
        })}</fieldset>)}
        <section className="resume-polish-section" aria-label="이력서 문장 다듬기">
          <h4>이력서 문장 다듬기</h4><p>작성한 경험을 이력서 문장으로 정리해요. 사실 확인이 필요하면 질문하고 답변한 항목만 다시 다듬어요.</p>
          <button type="button" className="post-comparison-resume-button" disabled={aiBusy || readingPhoto || questions.length > 0} onClick={() => { void polish(); }}>이력서 문장 다듬기</button>
          {aiBusy && <p role="status">{questions.length ? '답변한 항목만 다시 다듬고 있어요…' : '작성한 문장을 다듬고 있어요…'}</p>}
          {aiError && <p role="alert">{aiError}</p>}
          {changes.length > 0 && <details className="resume-polish-changes"><summary>다듬은 문장 확인 · {changes.length}개 항목</summary>{changes.map(change => <div key={change.field}><strong>{fieldLabel(change.field)}</strong><p>기존: {change.before}</p><p>정리: {change.after}</p></div>)}<button type="button" disabled={aiBusy} onClick={() => { setValues(previous => { const next={...previous}; for (const change of changes) if (next[change.field] === change.after) next[change.field]=change.before; return next; }); setChanges([]); }}>이번 다듬기 되돌리기</button></details>}
          {dialogue.map((turn,index) => <div key={index}><p><strong>말해봄 코치</strong> · {turn.question}</p><p><strong>나</strong> · {turn.answer}</p></div>)}
          {questions[0] && <div className="resume-fact-question" aria-live="polite"><strong>말해봄 코치 · {fieldLabel(questions[0].field)} 확인</strong><p>{questions[0].question}</p><label htmlFor="resume-fact-answer">사실 확인 답변</label><textarea id="resume-fact-answer" rows={3} maxLength={1000} disabled={aiBusy} value={answer} onChange={event => setAnswer(event.target.value)} placeholder="본인이 확인한 내용을 답해주세요. 모르면 모른다고 적어도 괜찮아요." /><div className="post-comparison-actions"><button type="button" disabled={aiBusy || !answer.trim()} onClick={() => { void polish(questions[0]); }}>답변 보내고 이 항목 다듬기</button><button type="button" disabled={aiBusy} onClick={() => { setQuestions(previous => previous.slice(1)); setAnswer(''); }}>원문 유지하고 건너뛰기</button></div></div>}
        </section>
        <p className="resume-draft-source">입력한 개인정보는 현재 화면에서만 사용하며, 새로고침하거나 이 화면을 나가면 사라져요.</p>
        <div className="post-comparison-actions"><button type="submit" className="coach-recording-button" disabled={readingPhoto || aiBusy || questions.length > 0}>이력서에 반영하기</button><button type="button" className="post-comparison-resume-button" onClick={onCancel}>보완 취소</button></div>
      </form>
    </div></article>;
}
