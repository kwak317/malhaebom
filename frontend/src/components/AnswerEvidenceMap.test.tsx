import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import type { AnswerRevision } from "../api/answerRevisions";
import type { CoachingResponse } from "../api/coaching";
import { CoachingResultPanel } from "./CoachingResultPanel";
import { AnswerEvidenceMap } from "./AnswerEvidenceMap";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const revision: AnswerRevision = {
  answer_revision_id: "revision-1", analysis_job_id: "job-1", practice_session_id: "practice-1",
  question_id: "preset-04", job_snapshot_id: "snapshot-1", confirmed_at: "2026-10-04", expires_at: "2026-10-05",
  answer_segments: [
    { segment_id: "s1", text: "저는 로그를 확인하고 코드를 수정했습니다." },
    { segment_id: "s2", text: "팀 프로젝트에 참여했습니다." },
  ],
};
const result: CoachingResponse = {
  status: "needs_more_info", intent_assessment: { label: "aligned", reason: "질문과 관련된 답변입니다." },
  job_alignment: [],
  criterion_assessments: [
    { criterion_id: "cause_observation", assessment: "partial", reason: "로그 확인은 있지만 관찰한 신호가 부족합니다.", needed: "실제로 관찰한 오류를 설명해 주세요." },
    { criterion_id: "own_action", assessment: "met", reason: "본인의 수정 행동을 설명했습니다.", needed: null },
    { criterion_id: "result_verification", assessment: "not_observed", reason: "수정 후 관찰 결과가 없습니다.", needed: "같은 조건에서 확인한 결과를 설명해 주세요." },
  ],
  evidence: [
    { source_type: "criterion_assessment", source_id: "cause_observation", segment_id: "s1", quote: "로그를 확인", reason: "관찰 행동" },
    { source_type: "criterion_assessment", source_id: "own_action", segment_id: "s1", quote: "코드를 수정했습니다.", reason: "본인 행동" },
  ],
  gaps: [], clarifying_question: null, next_actions: [], example_answer: null,
};

describe("답변 근거 지도", () => {
  let container: HTMLDivElement;
  let root: Root;
  beforeEach(() => { container = document.createElement("div"); document.body.append(container); root = createRoot(container); });
  afterEach(async () => { await act(async () => root.unmount()); container.remove(); });
  const render = async (value = result, answer: AnswerRevision | undefined = revision) => {
    await act(async () => root.render(<CoachingResultPanel result={value} revision={answer} />));
  };
  const map = () => container.querySelector('[aria-label="답변 근거 지도"]')!;
  const detail = () => map().querySelector(".answer-evidence-map__detail")!;
  const click = async (selector: string) => { await act(async () => (map().querySelector(selector) as HTMLButtonElement).click()); };

  it("근거 지도는 처음 접혀 있고 펼침 후 선택 기능을 유지한다", async () => {
    await render();
    const fold = map() as HTMLDetailsElement;
    expect(fold.tagName).toBe("DETAILS");
    expect(fold.open).toBe(false);
    expect(fold.querySelector("summary")?.textContent).toContain("3개 기준");
    fold.open = true;
    await click(".answer-evidence-map__criteria button:nth-child(3)");
    expect(detail().textContent).toContain("같은 조건에서 확인한 결과");
    fold.open = false;
    fold.open = true;
    expect(map().querySelector('.answer-evidence-map__criteria button[aria-pressed="true"]')?.textContent).toContain("결과 확인");
  });
  it("문장 하나에 연결된 복수 기준과 부분 인용·부족 이유를 보여준다", async () => {
    await render();
    await click(".answer-evidence-map__sentence");
    expect(detail().textContent).toContain("원인 관찰 신호");
    expect(detail().textContent).toContain("본인이 한 행동");
    expect(detail().textContent).toContain("실제로 관찰한 오류를 설명해 주세요.");
    expect([...map().querySelectorAll("mark")].map((node) => node.textContent)).toEqual(["로그를 확인", "코드를 수정했습니다."]);
    expect(detail().textContent).not.toContain("수정 후 관찰 결과가 없습니다.");
    expect(map().querySelector("button")?.hasAttribute("aria-controls")).toBe(true);
  });
  it("근거 없는 기준을 선택하면 필요한 설명을 표시하며 문장을 연결하지 않는다", async () => {
    await render();
    await click(".answer-evidence-map__criteria button:nth-child(3)");
    expect(detail().textContent).toContain("결과 확인");
    expect(detail().textContent).toContain("같은 조건에서 확인한 결과");
    expect(detail().querySelector("blockquote")).toBeNull();
    expect(map().querySelector('.answer-evidence-map__sentence[aria-pressed="true"]')).toBeNull();
  });
  it("공고 인용·원문 불일치·없는 문장·비활성 기준을 내용 판정으로 연결하지 않는다", async () => {
    await render({ ...result, evidence: [
      { ...result.evidence[0], source_type: "job_alignment" },
      { ...result.evidence[0], quote: "가상의 오류" },
      { ...result.evidence[0], segment_id: "other-revision-s1" },
      { ...result.evidence[0], source_id: "inactive" },
    ] });
    await click(".answer-evidence-map__sentence");
    expect(detail().textContent).toContain("연결된 판정 근거가 없어요");
    expect(detail().textContent).toContain("경험이 없다는 뜻은 아니에요");
    expect(detail().querySelector("blockquote")).toBeNull();
  });
  it("연결 없는 문장을 선택해도 다른 문장 근거를 가져오지 않는다", async () => {
    await render();
    await click(".answer-evidence-map__sentence:nth-of-type(2)");
    expect(detail().textContent).toContain("연결된 판정 근거가 없어요");
    expect(detail().textContent).not.toContain("로그 확인은 있지만");
  });
  it("중복·겹친 인용은 한 번 강조하고 해당 기준의 문장만 선택한다", async () => {
    await act(async () => root.render(<AnswerEvidenceMap revision={revision}
      criterionLabels={{ cause_observation: "원인 관찰 신호", own_action: "본인이 한 행동", result_verification: "결과 확인" }}
      result={{ ...result, evidence: [...result.evidence, result.evidence[0], { ...result.evidence[0], quote: "로그를 확인하고" }] }} />));
    await click(".answer-evidence-map__criteria button");
    expect(map().querySelectorAll("mark")).toHaveLength(1);
    expect(map().querySelector("mark")?.textContent).toBe("로그를 확인하고");
    expect(detail().querySelectorAll("blockquote")).toHaveLength(2);
    expect(map().querySelectorAll('.answer-evidence-map__sentence[aria-pressed="true"]')).toHaveLength(1);
  });
  it("revision이 바뀌면 같은 문장 ID에도 선택 상태를 초기화한다", async () => {
    await render(); await click(".answer-evidence-map__sentence");
    await render(result, { ...revision, answer_revision_id: "revision-2" });
    expect(detail().textContent).toContain("문장이나 위의 기준을 선택");
    expect(map().querySelector('[aria-pressed="true"]')).toBeNull();
  });
  it("revision 없는 기존 결과에서는 지도를 노출하지 않는다", async () => {
    await act(async () => root.render(<CoachingResultPanel result={result} />));
    expect(container.querySelector('[aria-label="답변 근거 지도"]')).toBeNull();
    expect(container.textContent).toContain("판정과 근거");
  });
});
