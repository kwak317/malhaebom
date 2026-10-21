import type { GithubReadmeAnalysis } from "../api/practiceSetup";
import type { ResumeProfile } from "../api/resume";

export type ResumeDraftLayout = "project" | "career";
export type ResumeDraftMaterials = {
  resumeProfile?: ResumeProfile | null;
  resumeFile?: File | null;
  readmeAnalysis?: GithubReadmeAnalysis | null;
  confirmedExperiences?: string[];
  ncsLabels?: string[];
};

export type ResumeCompletion = Partial<Record<
  "name" | "email" | "career" | "role" | "github" | "portfolio" | "intro" | "technology" |
  "project" | "projectRole" | "problem" | "action" | "result" | "outcome" | "repository" |
  "careerDetails" | "education" | "qualification" | "photoDataUrl", string>>;

export function ResumeDraftChat({ layout, materials = {}, completion, onComplement, complementDisabled, onReconstruct, onImport }: { layout: ResumeDraftLayout; materials?: ResumeDraftMaterials; completion?: ResumeCompletion; onComplement?: () => void; complementDisabled?: boolean; onReconstruct?: () => void; onImport?: () => void }) {
  const facts = materials.resumeProfile?.facts ?? [];
  const hasImportedMaterials = Boolean(facts.length || materials.readmeAnalysis || materials.confirmedExperiences?.length);
  const values = (category: keyof ResumeCompletion) => completion && Object.prototype.hasOwnProperty.call(completion, category) ? (completion[category] ? [completion[category]!] : []) : facts.filter((fact) => fact.category === category).map((fact) => fact.value);
  const role = values("role");
  const projects = values("project");
  const careers = values("career");
  const technology = values("technology");
  const education = values("education");
  const qualification = values("qualification");
  const readme = materials.readmeAnalysis;
  const projectSection = <section key="project" className="resume-draft-section" data-resume-section="project">
    <h4>프로젝트 경험</h4>
    <FactList values={projects} placeholder="[프로젝트명·기간·팀 규모 입력]" />
    {readme && <>
      <h5>README에 기재된 프로젝트 내용</h5>
      <ul>{readme.project_flow.map((item, index) => <li key={index}>{item.description}</li>)}</ul>
      <ul>{readme.technology_stack.map((item, index) => <li key={index}>{item.name} — {item.description}</li>)}</ul>
      <p className="resume-draft-source">README 내용은 프로젝트 설명입니다. 개인 구현 범위는 별도로 확인해 주세요.</p>
    </>}
    <p>{completion?.projectRole || "[본인이 담당한 기능·구현 범위 입력]"}</p>
    <p>{completion?.problem || "[발생한 문제]"} → {completion?.action || "[본인이 수행한 행동]"} → {completion?.result || "[확인한 결과]"}</p>
    <p>{completion?.outcome || "[근거가 있는 성과 또는 관찰한 변화 입력]"}</p>
    <p>저장소: {completion && Object.prototype.hasOwnProperty.call(completion, "repository") ? completion.repository || "[GitHub / README 링크 입력]" : (readme && /^https?:\/\//i.test(readme.source_url) ? <a href={readme.source_url} target="_blank" rel="noreferrer noopener">{readme.source_url}</a> : "[GitHub / README 링크 입력]")}</p>
  </section>;
  const careerSection = <section key="career" className="resume-draft-section" data-resume-section="career">
    <h4>경력 및 활동</h4>
    <FactList values={careers} placeholder="[회사·직무·기간 입력 / 경력이 없으면 제외]" />
    <p>{completion?.careerDetails || "[각 경력에서 본인이 수행한 업무와 확인한 결과 입력]"}</p>
  </section>;

  return <article className="coach-message coach-message-assistant resume-draft-message" aria-label={layout === "project" ? "프로젝트 중심 이력서 초안" : "경력 중심 이력서 초안"}>
    <span className="coach-message-avatar" aria-hidden="true">✦</span>
    <div>
      <strong>말해봄 코치</strong>
      <h3>{layout === "project" ? "프로젝트 중심 이력서 초안" : "경력 중심 이력서 초안"}</h3>
      <p className="resume-draft-source">{hasImportedMaterials ? "동의하고 가져온 자료와 입력한 내용으로 정리한 검토용 초안이에요." : "직접 입력하거나 ‘제출한 정보 가져오기’로 빈칸을 채워 주세요."} 대괄호 항목은 추가 확인이 필요해요.</p>
      <section className="resume-draft-section">
        <div className="resume-photo-slot">{completion?.photoDataUrl ? <img src={completion.photoDataUrl} alt="첨부한 증명사진" /> : <span>증명사진</span>}</div>
        <h4>{completion?.name || "[이름 입력]"}</h4>
        <FactList values={role} placeholder="[지원 직무 입력]" />
        <p>{completion?.email || "[이메일 입력]"} · {completion?.github || "[GitHub 주소 입력]"} · {completion?.portfolio || "[포트폴리오 주소 입력]"}</p>
        <h5>소개</h5><p>{completion?.intro || "[확인한 경력·프로젝트를 바탕으로 핵심 경험을 2~3문장으로 입력]"}</p>
      </section>
      {layout === "career" && careerSection}
      <section className="resume-draft-section" data-resume-section="skills">
        <h4>기술 스택 및 활용 경험</h4>
        <FactList values={technology} placeholder="[직접 사용한 기술과 활용 경험 입력]" />
      </section>
      {projectSection}
      {layout === "project" && careerSection}
      {!!materials.confirmedExperiences?.length && <section className="resume-draft-section">
        <h4>채팅에서 확인한 추가 경험</h4>
        <FactList values={materials.confirmedExperiences} placeholder="" />
        <p className="resume-draft-source">해당하는 경력 또는 프로젝트에 연결해 주세요.</p>
      </section>}
      <section className="resume-draft-section">
        <h4>교육 및 자격</h4>
        <FactList values={education} placeholder="[학교·전공 / 교육 과정·기간 입력]" />
        <FactList values={qualification} placeholder="[보유 자격 입력 / 없으면 제외]" />
      </section>
      <p className="resume-draft-source">{hasImportedMaterials ? "가져온 이력서 정보와 사용자가 확인한 채팅 경험을 반영했어요." : "제출한 자료는 가져오기에 동의한 뒤 반영해요."} 미확인 역할이나 성과 수치는 추가하지 않았어요.</p>
      {!!materials.ncsLabels?.length && <details className="resume-draft-ncs"><summary>작성 참고용으로 선택한 NCS 항목</summary>
        <FactList values={materials.ncsLabels} placeholder="" />
        <p>선택한 항목은 작성 참고 자료이며, 실제 보유 역량의 근거로 사용하지 않았어요.</p>
      </details>}
      {completion && <p className="resume-draft-source">보완한 개인정보는 현재 화면에서만 사용하며, 새로고침하거나 이 화면을 나가면 사라져요.</p>}
      {onComplement && <div className="post-comparison-actions"><button type="button" className="post-comparison-resume-button" disabled={complementDisabled} onClick={onComplement}>보완하기</button>{onImport && <button type="button" className="post-comparison-resume-button" disabled={complementDisabled} onClick={onImport}>제출한 정보 가져오기</button>}</div>}
      {completion && onReconstruct && <div className="post-comparison-actions resume-draft-reconstruct-actions"><button type="button" className="post-comparison-resume-button" disabled={complementDisabled} onClick={onReconstruct}>이력서 형식에 맞게 재구성하기</button></div>}
    </div>
  </article>;
}

function FactList({ values, placeholder }: { values: string[]; placeholder: string }) {
  return values.length ? <ul>{values.map((value, index) => <li key={index}>{value}</li>)}</ul> : <p>{placeholder}</p>;
}
