import { AppHeader } from "../navigation";
import { HistoryConversationPanels } from "../components/HistoryConversationPanels";
import { HistoryExperienceChat } from "../components/HistoryExperienceChat";
import type { PracticeHistoryItem } from "../services/practiceHistoryMapper";
import "../styles/history-page.css";
import "../styles/history-result-page.css";

type Metrics = PracticeHistoryItem["attempt1Metrics"];

function HistoryResultPage({ item, onBack }: { item: PracticeHistoryItem; onDetail: () => void; onBack: () => void }) {
  const second = item.resultType === "comparison" ? item.attempt2Metrics : undefined;
  const speedScale = Math.max(item.attempt1Metrics.speakingRate, second?.speakingRate ?? 0, 1);
  return <div className="history-page history-result-page"><AppHeader /><main className="history-main">
    <section className="flow-card history-detail-card history-result-card">
      <header className="history-result-heading"><div><p className="flow-eyebrow">연습 기록 / 결과</p><h1>연습 결과</h1></div><span className="history-status">{item.status}</span></header>
      <div className="history-detail-question"><span>연습한 질문</span><strong>{item.question}</strong><small>{item.practicedAt}</small></div>
      <div className={`history-attempt-grid ${second ? "has-second" : ""}`}>
        <AttemptMetrics attempt={1} metrics={item.attempt1Metrics} speedScale={speedScale} />
        {second && <AttemptMetrics attempt={2} metrics={second} speedScale={speedScale} />}
      </div>
      {second && <div className="history-result-deltas" aria-label="1차 대비 2차 수치 변화">
        <span>말하기 속도 <strong>{delta(item.attempt1Metrics.speakingRate, second.speakingRate, "음절/분")}</strong></span>
        <span>긴 침묵 <strong>{delta(item.attempt1Metrics.longSilence, second.longSilence, "회")}</strong></span>
        <span>반복 표현 <strong>{delta(item.attempt1Metrics.repeatedExpressions, second.repeatedExpressions, "회")}</strong></span>
      </div>}
      {!second && <section className="history-detail-section"><h2>내 답변</h2><p className="history-transcript">{item.attempt1Transcript}</p><h2>다음 연습에서 바꿔볼 점</h2><div className="history-change-list">{item.feedback.slice(0, 2).map((feedback) => <p key={feedback}>{feedback}</p>)}</div></section>}
      <div className="history-result-folds">{second && <HistoryConversationPanels item={item} />}<HistoryExperienceChat key={item.id} sessionId={item.id} /></div>
      <footer className="history-result-actions"><button className="history-back-button" type="button" onClick={onBack}>연습 기록으로 돌아가기</button></footer>
    </section>
  </main></div>;
}

function AttemptMetrics({ attempt, metrics, speedScale }: { attempt: 1 | 2; metrics: Metrics; speedScale: number }) {
  return <section className={`history-attempt-card history-attempt-card--${attempt}`} aria-label={`${attempt}차 분석 결과`}>
    <div className="history-attempt-label"><span>ATTEMPT 0{attempt}</span><span>{attempt === 1 ? "첫 답변" : "다시 답변"}</span></div>
    <h2>{attempt}차 분석 결과</h2>
    <div className="history-attempt-metric"><span>말하기 속도</span><div><strong>{metrics.speakingRate}</strong> 음절/분</div></div>
    <div className="history-speed-track" aria-hidden="true"><i style={{ width: `${metrics.speakingRate / speedScale * 100}%` }} /></div>
    <div className="history-attempt-metric"><span>긴 침묵</span><div><strong>{metrics.longSilence}</strong> 회</div></div>
    <div className="history-attempt-metric"><span>반복 표현</span><div><strong>{metrics.repeatedExpressions}</strong> 회</div></div>
  </section>;
}

function delta(before: number, after: number, unit: string) {
  const change = after - before;
  return change === 0 ? "동일" : `${change < 0 ? "−" : "+"}${Math.abs(change)} ${unit}`;
}

export default HistoryResultPage;
