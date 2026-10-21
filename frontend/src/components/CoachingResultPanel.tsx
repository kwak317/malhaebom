import type { AnswerRevision } from "../api/answerRevisions";
import { coachingMessageId, quoteEvidenceId, workspaceId } from "./PracticeWorkspace";
import type { CoachingResponse } from "../api/coaching";
import { AnswerEvidenceMap } from "./AnswerEvidenceMap";

const LABELS: Record<string, string> = {
  aligned: "질문 의도에 맞음",
  partial: "일부 보완 필요",
  off_topic: "질문에서 벗어남",
  undetermined: "판단 근거 부족",
  related: "공고 요구와 관련 있음",
  insufficient_evidence: "공고 관련 근거 부족",
  unclear: "관련성 판단 어려움",
  met: "충족",
  not_observed: "확인되지 않음",
};

const CRITERION_LABELS: Record<string, string> = {
  problem_context: "문제 상황",
  cause_observation: "원인 관찰 신호",
  cause_inference: "원인 추론 연결",
  professional_identity: "직무 정체성",
  core_strength: "핵심 강점",
  supporting_experience: "근거 경험",
  company_understanding: "회사 이해",
  role_motivation: "직무 선택 동기",
  future_contribution: "기여 계획",
  specific_strength: "구체적 강점",
  evidence_example: "입증 사례",
  job_relevance: "직무 연결",
  conflict_context: "갈등 상황과 원인",
  communication_action: "소통·조율 행동",
  collaborative_result: "협업 결과",
  failure_context: "실패 상황과 책임",
  reflection_action: "성찰·개선 행동",
  applied_learning: "배운 점의 적용",
  project_goal: "프로젝트 목적",
  personal_role: "본인 역할·기여",
  project_outcome: "프로젝트 결과",
  role_scope: "책임 범위",
  execution_detail: "직접 수행한 일",
  collaboration_impact: "팀·결과에 미친 영향",
  career_direction: "성장 방향",
  growth_plan: "성장 계획",
  organization_contribution: "조직·사용자 기여",
  motivation_summary: "지원 의지·강점 요약",
  role_fit: "직무 적합성 설명",
  positive_closing: "간결한 마무리",
  cause_reasoning: "원인 판단",
  own_action: "본인이 한 행동",
  action_rationale: "행동 선택 이유",
  result_verification: "결과 확인",
};

const DELIVERY_LABELS: Record<string, string> = {
  cpm: "말하기 속도",
  long_silence_count: "긴 침묵",
  repetition_count: "반복 표현",
};

const PLACEHOLDER_ACTIONS = new Set(["-", "n/a", "na", "none", "null", "없음", "해당 없음"]);

export function CoachingResultPanel({ result, revision, onEvidenceSelect }: { result: CoachingResponse; revision?: AnswerRevision; onEvidenceSelect?: (taskId: string, messageId: string, evidenceId?: string) => void }) {
  const evidence = revision ? result.evidence : uniqueEvidence(result.evidence);
  const actions = result.next_actions.filter((item) => isUsefulKoreanText(item.action));
  return <section className="coaching-panel" aria-labelledby="coaching-heading">
    <div className="coaching-panel__heading">
      <div>
        <p className="flow-eyebrow">답변 코칭</p>
        <h2 id="coaching-heading">답변의 강점과 보완점을 정리했어요.</h2>
      </div>
      <span className={`coaching-status coaching-status--${statusTone(result.status)}`}>{result.status === "ok" ? "답변 근거 충족" : "추가 정보 필요"}</span>
    </div>

    <p className="workspace-coaching-summary">{koreanOr(result.intent_assessment.reason, intentFallback(result.intent_assessment.label))}</p>
    <div className="workspace-summary-grid">
      <article><span>질문 의도</span><strong>{label(result.intent_assessment.label)}</strong></article>
      <article><span>공고 연결</span><strong>{result.job_alignment.filter((item) => item.label === "related").length} / {result.job_alignment.length}개 관련 근거</strong></article>
      <article><span>보완 사항</span><strong>{result.gaps.length ? `${result.gaps.length}개 설명 확인 필요` : "현재 활성 기준에 추가 보완 없음"}</strong></article>
    </div>
    {revision && <AnswerEvidenceMap key={revision.answer_revision_id} revision={revision} result={result} criterionLabels={CRITERION_LABELS} />}
    <div className="workspace-coaching-details">
    <details className="coaching-block coaching-block--summary coaching-fold">
      <summary>질문 의도와 공고 연결 <span>{result.job_alignment.length}개 요구사항</span></summary>
      <article className={`coaching-intent-card coaching-assessment--${assessmentTone(result.intent_assessment.label)}`}>
        <span>질문 의도</span>
        <strong>{label(result.intent_assessment.label)}</strong>
        <p>{koreanOr(result.intent_assessment.reason, intentFallback(result.intent_assessment.label))}</p>
      </article>
      <div className="coaching-list coaching-list--requirements">{result.job_alignment.map((item, index) => <article className={`coaching-assessment coaching-assessment--${assessmentTone(item.label)}`} key={item.requirement_id}>
        <span>선택한 공고 요구사항 {index + 1}</span><strong>{label(item.label)}</strong><p>{koreanOr(item.reason, jobFallback(item.label))}</p>
      </article>)}</div>
    </details>

    <details className="coaching-block coaching-fold">
      <summary>판정과 근거 <span>{result.criterion_assessments.length}개 기준</span></summary>
      <p className="coaching-section-intro">답변에 실제로 드러난 내용만 기준으로 확인했어요.</p>
      <div className="coaching-list coaching-list--criteria">{result.criterion_assessments.map((item) => <article className={`coaching-assessment coaching-assessment--${assessmentTone(item.assessment)}`} key={item.criterion_id}>
        <span>{criterionLabel(item.criterion_id)}</span><strong>{label(item.assessment)}</strong><p>{koreanOr(item.reason, criterionFallback(item.criterion_id, item.assessment))}</p>
      </article>)}</div>
      {evidence.length > 0 && <ul className="coaching-evidence" aria-label="답변 근거">{evidence.map((item, index) => <li id={revision ? quoteEvidenceId(revision, item) : undefined} data-segment-id={revision ? item.segment_id : undefined} data-revision-id={revision?.answer_revision_id} key={`${item.source_type}-${item.source_id}-${item.segment_id}-${item.quote}`}>
        <span>답변 근거 {index + 1}</span><q>{item.quote}</q>{revision && onEvidenceSelect && <button className="workspace-quote-link" type="button" onClick={() => onEvidenceSelect(workspaceId("task", revision.analysis_job_id, revision.answer_revision_id, "coaching"), coachingMessageId(revision), quoteEvidenceId(revision, item))}>근거 자료실과 연결 →</button>}
      </li>)}</ul>}
    </details>

    </div>
    {result.gaps.length > 0 && <details className="coaching-block coaching-block--gap coaching-fold"><summary>보완하면 좋은 항목 <span>{result.gaps.length}개</span></summary>
      <ul>{result.gaps.map((gap) => <li id={revision ? workspaceId("check", revision.answer_revision_id, gap.criterion_id) : undefined} className={`coaching-gap-item coaching-assessment--${assessmentTone(gap.assessment)}`} key={gap.criterion_id}><strong>{criterionLabel(gap.criterion_id)}</strong><p>{koreanOr(gap.needed, `${criterionLabel(gap.criterion_id)} 설명을 보완해 보세요.`)}</p>{revision && onEvidenceSelect && <button className="workspace-quote-link" type="button" onClick={() => onEvidenceSelect(workspaceId("task", revision.analysis_job_id, revision.answer_revision_id, "coaching"), coachingMessageId(revision), workspaceId("check", revision.answer_revision_id, gap.criterion_id))}>추가 확인 사항과 연결 →</button>}</li>)}</ul>
    </details>}

    {result.clarifying_question && <section className="coaching-question"><span>확인 질문</span><strong>{koreanOr(result.clarifying_question, "현재 답변에서 빠뜨린 사실이 있는지 확인해 주세요.")}</strong></section>}

    <section className="coaching-block">
      <h2>다음 행동</h2>
      {actions.length > 0 ? <ol className="coaching-actions">{actions.map((item) => <li key={`${item.target_type}-${item.target_id}`}><span>{targetLabel(item.target_type, item.target_id)}</span>{item.action}</li>)}</ol> : <p>현재 답변의 근거 구조를 유지하면서 같은 질문에 다시 답해 보세요.</p>}
    </section>

    {result.example_answer && <section className="coaching-example" aria-labelledby="coaching-example-heading">
      <span>코칭 적용 예시</span>
      <h2 id="coaching-example-heading">이런 흐름으로 다시 답해 보세요.</h2>
      <p>{result.example_answer}</p>
      <small>정답이나 대필 답변이 아닙니다. 대괄호 부분은 본인이 실제로 경험한 내용으로만 바꾸고, 전체 문장이 사실과 일치하는지 확인해 주세요.</small>
    </section>}
    <section className="coaching-feedback-summary" aria-label="전체 코칭 피드백 요약">
      <h2>전체 코칭 피드백 요약</h2>
      <p>{shortFeedback(koreanOr(result.intent_assessment.reason, intentFallback(result.intent_assessment.label)))}</p>
      <dl>
        <div><dt>유지할 점</dt><dd>{result.criterion_assessments.some((item) => item.assessment === "met")
          ? `${criterionNames(result.criterion_assessments.filter((item) => item.assessment === "met"))} 설명이 확인됐어요. 재답변에서도 유지해 주세요.`
          : "현재 답변에서 충족으로 확인된 기준은 없어요. 아래 보완점을 중심으로 다시 답해 보세요."}</dd></div>
        <div><dt>보완할 점</dt><dd>{result.gaps.length > 0
          ? `${criterionNames(result.gaps)} 설명을 더 구체적으로 보완해 주세요.`
          : result.criterion_assessments.length > 0 && result.criterion_assessments.every((item) => item.assessment === "met")
            ? "모든 활성 기준의 설명이 확인됐어요."
            : "추가 보완 항목은 없어요. 상세 판정에서 확인되지 않은 기준이 있는지 살펴보세요."}</dd></div>
        <div><dt>다음 답변에서는</dt><dd>{actions.length > 0
          ? actions.slice(0, 2).map((item) => shortFeedback(item.action, 100)).join(" ")
          : "현재 답변의 근거 구조를 유지하면서 같은 질문에 다시 답해 보세요."}</dd></div>
      </dl>
    </section>
  </section>;
}

function shortFeedback(text: string, maxLength = 140) {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= maxLength) return normalized;
  const prefix = normalized.slice(0, maxLength);
  const sentenceEnd = prefix.lastIndexOf(". ");
  return sentenceEnd >= maxLength / 2 ? prefix.slice(0, sentenceEnd + 1) : `${prefix.trimEnd()}…`;
}

function criterionNames(items: Array<{ criterion_id: string }>) {
  const names = [...new Set(items.map((item) => criterionLabel(item.criterion_id)))];
  return names.slice(0, 3).join(" · ") + (names.length > 3 ? ` 외 ${names.length - 3}개 항목` : "");
}

function label(value: string) {
  return LABELS[value] || value;
}

function statusTone(value: CoachingResponse["status"]) {
  return value === "ok" ? "positive" : "partial";
}

function assessmentTone(value: string) {
  if (["aligned", "related", "met"].includes(value)) return "positive";
  if (["not_observed", "off_topic"].includes(value)) return "missing";
  return "partial";
}

function criterionLabel(value: string) {
  return CRITERION_LABELS[value] || "답변 구성";
}

function targetLabel(type: string, id: string) {
  return type === "delivery_metric" ? DELIVERY_LABELS[id] || "전달 방식" : criterionLabel(id);
}

function koreanOr(value: string, fallback: string) {
  return /[가-힣]/.test(value) ? value : fallback;
}

function isUsefulKoreanText(value: string) {
  return /[가-힣]/.test(value) && !PLACEHOLDER_ACTIONS.has(value.trim().toLocaleLowerCase());
}

function uniqueEvidence(evidence: CoachingResponse["evidence"]) {
  const seen = new Set<string>();
  return evidence.filter((item) => {
    const key = `${item.segment_id}\u0000${item.quote}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function intentFallback(value: string) {
  if (value === "aligned") return "질문이 요구한 문제 해결 과정이 현재 답변에서 확인됩니다.";
  if (value === "partial") return "질문 의도와 관련되지만 일부 설명을 보완할 필요가 있습니다.";
  if (value === "off_topic") return "현재 답변은 질문 의도와 직접 연결되지 않습니다.";
  return "현재 답변만으로 질문 의도와의 연결을 판단하기 어렵습니다.";
}

function jobFallback(value: string) {
  if (value === "related") return "현재 답변의 근거가 선택한 공고 요구사항과 관련됩니다.";
  if (value === "insufficient_evidence") return "공고 요구사항과 연결할 답변 근거가 부족합니다.";
  return "현재 답변만으로 공고 요구사항과의 관련성을 판단하기 어렵습니다.";
}

function criterionFallback(id: string, assessment: string) {
  const name = criterionLabel(id);
  if (assessment === "met") return `${name}에 필요한 설명이 현재 답변에서 확인됩니다.`;
  if (assessment === "partial") return `${name} 설명은 있으나 일부 연결을 보완할 필요가 있습니다.`;
  if (assessment === "not_observed") return `${name} 설명을 현재 답변에서 확인하지 못했습니다.`;
  return `${name} 설명을 현재 답변만으로 판단하기 어렵습니다.`;
}
