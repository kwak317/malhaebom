import { useId, useState } from "react";
import type { AnswerRevision } from "../api/answerRevisions";
import type { CoachingResponse } from "../api/coaching";
import "../styles/answer-evidence-map.css";

const STATUS_LABELS: Record<string, string> = {
  met: "확인됨", partial: "일부 보완 필요", not_observed: "확인되지 않음", undetermined: "판단 어려움",
};

export function AnswerEvidenceMap({ revision, result, criterionLabels }: {
  revision: AnswerRevision;
  result: CoachingResponse;
  criterionLabels: Record<string, string>;
}) {
  const detailId = useId();
  const [selection, setSelection] = useState<{ kind: "segment" | "criterion"; id: string } | null>(null);
  const criterionName = (id: string) => criterionLabels[id] || "답변 구성";
  const evidence = result.evidence.filter((item) => item.source_type === "criterion_assessment"
    && result.criterion_assessments.some((criterion) => criterion.criterion_id === item.source_id)
    && item.quote.trim().length > 0
    && revision.answer_segments.some((segment) => segment.segment_id === item.segment_id && segment.text.includes(item.quote)));
  const selectedEvidence = evidence.filter((item) => selection?.kind === "segment"
    ? item.segment_id === selection.id : selection?.kind === "criterion" && item.source_id === selection.id);
  const selectedCriteria = result.criterion_assessments.filter((item) => selection?.kind === "criterion"
    ? item.criterion_id === selection.id : selectedEvidence.some((quote) => quote.source_id === item.criterion_id));

  return <details className="answer-evidence-map coaching-block coaching-fold" aria-label="답변 근거 지도">
    <summary>답변 근거 지도 <span>{result.criterion_assessments.length}개 기준</span></summary>
    <p className="coaching-section-intro">문장을 누르면 연결된 판정을, 기준을 누르면 해당 인용을 확인할 수 있어요.</p>
    <div className="answer-evidence-map__criteria" aria-label="판정 기준 선택">
      {result.criterion_assessments.map((item) => <button type="button" key={item.criterion_id}
        aria-pressed={selection?.kind === "criterion" && selection.id === item.criterion_id}
        aria-controls={detailId} onClick={() => setSelection({ kind: "criterion", id: item.criterion_id })}>
        {criterionName(item.criterion_id)}<small>{STATUS_LABELS[item.assessment] || "판단 어려움"}</small>
      </button>)}
    </div>
    <div className="answer-evidence-map__layout">
      <div className="answer-evidence-map__sentences" aria-label="확정 답변 문장">
        <h3>내가 말한 답변</h3>
        {revision.answer_segments.map((segment, index) => {
          const linked = evidence.filter((item) => item.segment_id === segment.segment_id);
          const selected = selection?.kind === "segment" ? selection.id === segment.segment_id
            : selectedEvidence.some((item) => item.segment_id === segment.segment_id);
          return <button type="button" key={segment.segment_id} aria-pressed={selected} aria-controls={detailId}
            className="answer-evidence-map__sentence" onClick={() => setSelection({ kind: "segment", id: segment.segment_id })}>
            <span className="answer-evidence-map__number">문장 {index + 1}</span>
            <span className="answer-evidence-map__text">{highlightQuotes(segment.text, selected ? selectedEvidence.filter((item) => item.segment_id === segment.segment_id).map((item) => item.quote) : [])}</span>
            <span className="answer-evidence-map__tags">{linked.length
              ? [...new Set(linked.map((item) => item.source_id))].map((id) => <span key={id}>{criterionName(id)}</span>)
              : <span>연결된 판정 근거 없음</span>}</span>
          </button>;
        })}
      </div>
      <div id={detailId} className="answer-evidence-map__detail" aria-live="polite" aria-atomic="true">
        <h3>{selection?.kind === "segment" ? "이 문장에 연결된 판정" : selection?.kind === "criterion" ? "선택한 기준의 판정" : "판정과 인용 살펴보기"}</h3>
        {!selection && <p>왼쪽 문장이나 위의 기준을 선택해 보세요.</p>}
        {selection && !selectedCriteria.length && <p>이 문장에 연결된 판정 근거가 없어요. 경험이 없다는 뜻은 아니에요.</p>}
        {selectedCriteria.map((item) => {
          const quotes = selectedEvidence.filter((quote) => quote.source_id === item.criterion_id);
          return <article className="answer-evidence-map__assessment" key={item.criterion_id}>
            <h4>{criterionName(item.criterion_id)} <span>{STATUS_LABELS[item.assessment] || "판단 어려움"}</span></h4>
            <p>{koreanOr(item.reason, "현재 답변의 설명을 기준으로 판정했어요.")}</p>
            {[...new Set(quotes.map((quote) => quote.quote))].map((quote) => <blockquote key={quote}>{quote}</blockquote>)}
            {!quotes.length && <p className="answer-evidence-map__notice">이 기준에 연결된 인용이 없어요.</p>}
            {item.needed && <p><strong>필요한 설명</strong><br />{koreanOr(item.needed, "이 기준에 필요한 설명을 보완해 주세요.")}</p>}
          </article>;
        })}
      </div>
    </div>
  </details>;
}

function koreanOr(value: string, fallback: string) {
  return /[가-힣]/.test(value) ? value : fallback;
}

function highlightQuotes(text: string, quotes: string[]) {
  const ranges: Array<[number, number]> = [];
  for (const quote of new Set(quotes)) {
    let start = text.indexOf(quote);
    while (start !== -1) {
      ranges.push([start, start + quote.length]);
      start = text.indexOf(quote, start + quote.length);
    }
  }
  ranges.sort((a, b) => a[0] - b[0]);
  const merged: Array<[number, number]> = [];
  for (const range of ranges) {
    const previous = merged[merged.length - 1];
    if (previous && range[0] <= previous[1]) previous[1] = Math.max(previous[1], range[1]);
    else merged.push([...range]);
  }
  let cursor = 0;
  const parts = merged.flatMap(([start, end]) => {
    const nodes = [text.slice(cursor, start), <mark key={start}>{text.slice(start, end)}</mark>];
    cursor = end;
    return nodes;
  });
  return [...parts, text.slice(cursor)];
}
