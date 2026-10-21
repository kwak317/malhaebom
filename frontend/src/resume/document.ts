import type {ResumeCompletion,ResumeDraftLayout,ResumeDraftMaterials} from '../components/ResumeDraftChat';
export type ResumeDocument = {layout:ResumeDraftLayout;name:string;role:string;contacts:string[];intro:string;photoDataUrl?:string;sections:{title:string;paragraphs:string[];source:string}[]};
export function buildResumeDocument(layout:ResumeDraftLayout,materials:ResumeDraftMaterials={},completion:ResumeCompletion={}):ResumeDocument{
 const values=(category:string)=>(materials.resumeProfile?.facts??[]).filter(f=>f.category===category).map(f=>f.value);
 const combine=(category:string,value?:string)=>Object.prototype.hasOwnProperty.call(completion,category)?(value?[value]:[]):values(category);
 const missing=(value:string|undefined,label:string)=>value||`[${label} 확인 필요]`;
 const source='제공한 이력서 정보 · 사용자가 보완한 내용';
 const career={title:'경력 및 활동',paragraphs:[...combine('career',completion.career),missing(completion.careerDetails,'담당 업무와 확인한 결과')],source};
 if(!combine('career',completion.career).length)career.paragraphs.unshift('[회사·직무·기간 확인 필요]');
 const skills={title:'기술 스택',paragraphs:combine('technology',completion.technology),source};
 if(!skills.paragraphs.length)skills.paragraphs.push('[직접 사용한 기술과 활용 경험 확인 필요]');
 const readme=materials.readmeAnalysis;
 const project={title:'프로젝트 경험',paragraphs:[...combine('project',completion.project),`본인이 담당한 구현: ${missing(completion.projectRole,'개인 담당 기능')}`,`문제: ${missing(completion.problem,'발생한 문제')}`,`행동: ${missing(completion.action,'본인이 수행한 행동')}`,`결과: ${missing(completion.result,'실제로 확인한 결과')}`,`성과: ${missing(completion.outcome,'관찰한 변화 또는 측정 근거')}`,`저장소: ${missing(Object.prototype.hasOwnProperty.call(completion,'repository')?completion.repository:readme?.source_url,'GitHub / README 링크')}`],source};
 if(!combine('project',completion.project).length)project.paragraphs.unshift('[프로젝트명·기간·팀 규모 확인 필요]');
 if(readme?.project_flow.length)project.paragraphs.push('README에 기재된 프로젝트 설명 (개인 구현 범위와 별도):',...readme.project_flow.map(item=>item.description));
 const education={title:'교육 및 자격',paragraphs:[...combine('education',completion.education),...combine('qualification',completion.qualification)],source};
 if(!education.paragraphs.length)education.paragraphs.push('[교육·자격 확인 필요 / 해당 사항이 없으면 제외]');
 const sections=layout==='career'?[career,skills,project,education]:[skills,project,career,education];
 if(materials.confirmedExperiences?.length)sections.push({title:'추가 확인 경험',paragraphs:materials.confirmedExperiences,source:'사용자가 확인한 채팅 경험 · 해당 경력/프로젝트와의 연결은 최종 확인 필요'});
 return {layout,name:missing(completion.name,'이름'),role:combine('role',completion.role).join(' · ')||'[지원 직무 확인 필요]',contacts:[completion.email||'[이메일 확인 필요]',completion.github||'[GitHub 주소 확인 필요]',completion.portfolio||'[포트폴리오 주소 확인 필요]'],intro:missing(completion.intro,'자기소개'),photoDataUrl:completion.photoDataUrl,sections};
}
