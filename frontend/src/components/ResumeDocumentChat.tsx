import {useEffect,useRef} from "react";
import type {ResumeDocument} from '../resume/document';
import '../styles/resume-document.css';
export function ResumeDocumentChat({document,onDownload,disabled,saved=false}:{document:ResumeDocument;onDownload:()=>void;disabled:boolean;saved?:boolean}){
 const previewRef=useRef<HTMLElement>(null);
 useEffect(()=>{previewRef.current?.scrollIntoView?.({block:"start"});},[]);
 return <article ref={previewRef} className="coach-message coach-message-assistant resume-document-message" aria-label="재구성한 이력서"><span className="coach-message-avatar" aria-hidden="true">✦</span><div>
  <div className="resume-document-sheet"><header className="resume-document-header"><strong>말해봄 · {document.layout==='career'?'경력':'프로젝트'} 중심 이력서</strong><span>사용자 검토용</span></header><div className="resume-photo-slot">{document.photoDataUrl ? <img src={document.photoDataUrl} alt="이력서 증명사진" /> : <span>증명사진</span>}</div><h2>{document.name}</h2><p className="resume-document-role">{document.role}</p><p className="resume-document-contacts">{document.contacts.join(' · ')}</p><p className="resume-document-intro">{document.intro}</p>
  {document.sections.map(section=><section key={section.title}><h3>{section.title}</h3>{section.paragraphs.map((paragraph,index)=><p key={index} className={paragraph.includes('확인 필요')?'resume-document-missing':undefined}>{paragraph}</p>)}<small>{section.source}</small></section>)}
  </div><p className="resume-draft-source">내용을 검토한 뒤 다운로드하세요. PDF 생성은 브라우저에서 처리하며, 다운로드한 파일은 기기에 저장됩니다.</p><div className="post-comparison-actions"><button type="button" className="post-comparison-resume-button" disabled={disabled} onClick={onDownload}>{disabled?'처리 중…':saved?'저장 완료':'이력서 PDF 다운로드'}</button></div>
 </div></article>;
}
