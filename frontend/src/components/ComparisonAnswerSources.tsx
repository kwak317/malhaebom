import "../styles/attempt-comparison.css";

type ComparisonAnswerSourcesProps = {
  firstTranscript: string;
  secondTranscript: string;
  feedback: string[];
};

export function ComparisonAnswerSources({ firstTranscript, secondTranscript, feedback }: ComparisonAnswerSourcesProps) {
  return <details className="comparison-answer-sources">
    <summary>답변 원문과 1차 피드백 보기</summary>
    <div className="comparison-source-content">
      <section><h3>1차 답변</h3><p>{firstTranscript || "전사문이 없습니다."}</p></section>
      <section><h3>1차 피드백</h3>{feedback.length
        ? feedback.map((item, index) => <p key={index}>{item}</p>)
        : <p>저장된 피드백이 없습니다.</p>}</section>
      <section><h3>2차 답변</h3><p>{secondTranscript || "전사문이 없습니다."}</p></section>
    </div>
  </details>;
}
