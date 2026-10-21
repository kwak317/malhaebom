import { useEffect, useRef, useState } from "react";
import { supabase } from "../api/supabaseAuth";
import { analyzeResumePdf, RESUME_CATEGORIES, type ResumeAnalysis, type ResumeFact, type ResumeProfile } from "../api/resume";
import "../styles/resume-chat.css";
import { LoadingProgress } from "./LoadingProgress";
import { useLoadingProgress } from "../api/loadingProgress";

function ResumeReviewProgress() {
  const stage = useLoadingProgress("/api/resume/analyze", "이력서 검토 요청을 준비하고 있어요…");
  const [startedAt] = useState(() => Date.now());
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setElapsed(Math.max(0, Math.floor((Date.now() - startedAt) / 1000))), 1000);
    return () => window.clearInterval(timer);
  }, [startedAt]);
  const remaining = Math.max(0, 35 - elapsed);
  return <div className="resume-loading-progress" role="status" aria-live="polite">
    <LoadingProgress stage={stage} />
    <small className="resume-loading-estimate" aria-live="off">{remaining > 0 ? `예상 남은 시간 약 ${remaining}초` : "예상보다 오래 걸리고 있어요"} · 경과 {elapsed}초</small>
  </div>;
}

function ResumeIcon({ kind }: { kind: "file" | "shield" | "upload" }) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {kind === "file" ? <><path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z" /><path d="M14 3v5h5M9 12h6M9 16h6" /></>
      : kind === "shield" ? <><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z" /><path d="m8.5 12 2.5 2.5 4.5-5" /></>
        : <><path d="M12 16V4m-4 4 4-4 4 4M4 16v4h16v-4" /></>}
  </svg>;
}

export function ResumeSubmissionChat({ profile, onConfirm, skipped = false, onSkip, onSourceFile }: { profile: ResumeProfile | null; onConfirm: (profile: ResumeProfile) => void; skipped?: boolean; onSkip?: () => void; onSourceFile?: (file: File | null) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<ResumeAnalysis | null>(null);
  const [facts, setFacts] = useState<ResumeFact[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);

  const submit = async () => {
    if (!file || loading || profile) return;
    if (!file.name.toLowerCase().endsWith(".pdf") || file.size > 5 * 1024 * 1024) {
      setError("5MB 이하 PDF 파일을 제출해 주세요."); return;
    }
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    setLoading(true); setError(""); setAnalysis(null); setFacts([]);
    try {
      const { data } = await supabase().auth.getSession();
      if (!data.session) throw new Error("로그인이 필요하거나 세션이 만료되었습니다.");
      if (request.signal.aborted) return;
      const result = await analyzeResumePdf(file, data.session.access_token, request.signal);
      if (!request.signal.aborted) { setAnalysis(result); setFacts(result.facts); }
    } catch (failure) {
      if (!request.signal.aborted) setError(failure instanceof Error ? failure.message : "이력서를 검토하지 못했습니다.");
    } finally {
      if (!request.signal.aborted) setLoading(false);
    }
  };
  const update = (index: number, patch: Partial<ResumeFact>) => setFacts((current) => current.map((fact, i) => i === index ? { ...fact, ...patch } : fact));
  const valid = facts.length > 0 && facts.every((fact) => fact.value.trim() && (fact.category !== "technology" || fact.keyword?.trim()));
  const confirm = () => {
    const privateText = /[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?<!\d)0\d{1,2}[- .]?\d{3,4}[- .]?\d{4}(?!\d)|\d{6}\s*-\s*[1-4]\d{6}/;
    if (facts.some((fact) => privateText.test(`${fact.value} ${fact.keyword ?? ""}`))) {
      setError("추천 정보에서 연락처·식별번호를 제거해 주세요."); return;
    }
    onSourceFile?.(file);
    onConfirm({ facts: facts.map(({ category, value, keyword }) => ({ category, value: value.trim(), keyword: category === "technology" ? keyword!.trim() : null })) });
  };

  if (skipped) return <article id="message:resume" className="coach-message coach-message-assistant coach-resume-message" aria-label="이력서 제출 건너뛰기">
    <span className="coach-message-avatar" aria-hidden="true">✦</span>
    <div><strong>이력서 제출을 건너뛰었어요.</strong><p>선택한 역량과 제출한 README, 채팅으로 확인한 경험을 참고해 공고를 찾아드릴게요.</p></div>
  </article>;

  return <article id="message:resume" className={`coach-message coach-message-assistant coach-resume-message${profile ? " coach-resume-confirmed-result" : analysis ? " coach-resume-analysis-result" : ""}`} aria-label="이력서 PDF 제출 및 확인">
    <span className="coach-message-avatar" aria-hidden="true">✦</span>
    <div>
      <div className="resume-heading">
        <span className="resume-heading-icon"><ResumeIcon kind="file" /></span>
        <div><strong>{profile ? "이력서 정보 확인 완료" : analysis ? "이력서 검토 결과" : "이력서를 보내주세요. (선택)"}</strong>
          <p>기술과 경험을 정리해 나에게 맞는 공고를 찾아드릴게요.</p></div>
      </div>
      <div className="resume-privacy"><ResumeIcon kind="shield" /><div>
        <strong>개인정보는 추천에 사용하지 않아요</strong>
        <p>이름·연락처·상세 주소·사진·생년월일·성별 등 개인정보는 검토·추천 평가에 사용하지 않습니다.</p>
      </div></div>
      {!profile && !analysis && <>
        <details className="resume-processing"><summary>파일 처리 안내</summary>
          <p>개인정보를 가린 파일 제출을 권장해요. PDF에서 추출한 텍스트는 AI 검토를 위해 OpenRouter를 통해 Gemini 3.1 Flash Lite에 전달되며, 분석 후 PDF 원본은 별도로 저장하지 않아요.</p>
        </details>
        <label className={`resume-file-label${file ? " has-file" : ""}${loading ? " is-loading" : ""}`}>
          <input className="resume-file-input" aria-label="이력서 PDF 선택" type="file" accept=".pdf,application/pdf" disabled={loading} onChange={(event) => {
            setFile(event.target.files?.[0] ?? null); setAnalysis(null); setFacts([]); setError("");
          }} />
          <span className="resume-file-icon"><ResumeIcon kind={file ? "file" : "upload"} /></span>
          <span className="resume-file-info"><strong title={file?.name}>{file ? file.name : "이력서 PDF를 선택해 주세요"}</strong>
            <span>{file ? `${file.size < 1024 * 1024 ? `${Math.max(1, Math.round(file.size / 1024))} KB` : `${(file.size / 1024 / 1024).toFixed(1)} MB`} · PDF` : "텍스트를 선택할 수 있는 PDF"}</span>
          </span>
          <span className="resume-file-action">{loading ? "검토 중" : file ? "파일 변경" : "파일 선택"}</span>
        </label>
        <div className="resume-submit-row"><span className="resume-file-limit">PDF · 5MB 이하 · 최대 10페이지</span>
          <button className="resume-submit-button" type="button" disabled={!file || loading} onClick={(event) => { event.currentTarget.closest(".coach-thread")?.dispatchEvent(new Event("workspace-next-stage")); void submit(); }}>{loading && <span className="resume-spinner" aria-hidden="true" />}{loading ? "이력서 검토 중…" : "이력서 검토하기"}</button>
        </div>
        {loading && <ResumeReviewProgress />}
      </>}
      {!profile && onSkip && <div className="resume-review-actions"><button className="resume-secondary-button" type="button" disabled={loading} onClick={onSkip}>건너뛰기</button></div>}
      {error && <p className="resume-error" role="alert">{error}</p>}
      {analysis && !profile && <section className="resume-review" aria-label="이력서 추출 정보 확인">
        <h3>추천에 사용할 정보를 확인해 주세요.</h3>
        <p className="resume-review-description">이력서에 적힌 정보만 정리했어요. 잘못 읽힌 내용은 수정하거나 삭제해 주세요.</p>
        <div className="resume-category-grid">
        {(Object.entries(RESUME_CATEGORIES)).map(([category, label]) => <section className="resume-category" key={category}>
          <div className="resume-category-heading"><h4>{label}</h4><span>{facts.filter((fact) => fact.category === category).length}개</span></div>
          {!facts.some((fact) => fact.category === category) ? <p className="resume-empty">기재된 정보 없음</p> : <>
          <ul className="resume-category-preview">{facts.filter((fact) => fact.category === category).slice(0, 3).map((fact, index) => <li key={index} title={fact.value}>{fact.value}</li>)}</ul>
          <details className="resume-category-editor"><summary>수정·근거 보기{facts.filter((fact) => fact.category === category).length > 3 ? ` · 전체 ${facts.filter((fact) => fact.category === category).length}개` : ""}</summary>
          {facts.map((fact, index) => fact.category === category && <div className="resume-fact" key={`${category}-${index}`}>
            <label>{label} 내용 {index + 1}<textarea maxLength={500} value={fact.value} onChange={(event) => update(index, { value: event.target.value })} /></label>
            {category === "technology" && <label>추천에 사용할 기술명 {index + 1}<input maxLength={80} value={fact.keyword ?? ""} onChange={(event) => update(index, { keyword: event.target.value })} /></label>}
            <details><summary>원래 PDF 근거 · {fact.page}페이지</summary><p>{fact.source_excerpt}</p></details>
            <button type="button" onClick={() => setFacts((current) => current.filter((_, i) => i !== index))}>{label} 항목 {index + 1} 삭제</button>
          </div>)}
          </details></>}
        </section>)}
        </div>
        {!valid && <p>최소 한 항목을 남기고 내용과 기술명을 입력해 주세요. 추출 항목이 없으면 PDF를 다시 제출해 주세요.</p>}
        <div className="resume-review-actions"><button className="resume-secondary-button" type="button" onClick={() => { setAnalysis(null); setFacts([]); setError(""); }}>다른 파일 제출</button>
          <button type="button" disabled={!valid} onClick={confirm}>확인하고 계속하기</button></div>
      </section>}
      {profile && <div className="resume-category-grid resume-confirmed-grid">
        {Object.entries(RESUME_CATEGORIES).map(([category, label]) => {
          const items = profile.facts.filter((fact) => fact.category === category);
          return <section className="resume-category" key={category}>
            <div className="resume-category-heading"><h4>{label}</h4><span>{items.length}개</span></div>
            {items.length ? <><ul className="resume-category-preview">{items.slice(0, 3).map((fact, index) => <li key={index} title={fact.value}>{fact.value}</li>)}</ul>
              <details className="resume-category-editor"><summary>전체 내용 보기</summary><ul>{items.map((fact, index) => <li key={index}>{fact.value}{fact.keyword ? ` · ${fact.keyword}` : ""}</li>)}</ul></details></>
              : <p className="resume-empty">기재된 정보 없음</p>}
          </section>;
        })}
      </div>}
    </div>
  </article>;
}
