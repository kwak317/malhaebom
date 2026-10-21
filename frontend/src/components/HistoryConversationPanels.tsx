import { ComparisonAnswerSources } from "./ComparisonAnswerSources";
import { AttemptContentComparison } from "./AttemptContentComparison";
import { ComparisonFeedbackSummary } from "./ComparisonFeedbackSummary";
import type { PracticeHistoryItem } from "../services/practiceHistoryMapper";

export function HistoryConversationPanels({ item }: { item: PracticeHistoryItem }) {
  const second = item.attempt2Metrics;
  if (item.resultType !== "comparison" || !second || !item.attempt2Transcript) return null;

  return <div className="history-conversation-panels">
    <details className="history-fold">
      <summary>1·2차 답변 비교</summary>
      <div className="history-fold-content">
        <ComparisonAnswerSources firstTranscript={item.attempt1Transcript} secondTranscript={item.attempt2Transcript} feedback={item.feedback} />
        <section className="history-detail-section"><h2>기준별 내용 비교</h2><p className="comparison-section-description">각 답변에서 실제로 확인된 문장만 같은 기준으로 비교합니다.</p><AttemptContentComparison comparison={item.comparison ?? null} /></section>
        <section className="history-detail-section"><h2>1차 / 2차 분석 결과</h2><div className="history-metrics"><Metric label="말하기 속도" value={`${item.attempt1Metrics.speakingRate} → ${second.speakingRate} 음절/분`} /><Metric label="긴 침묵" value={`${item.attempt1Metrics.longSilence} → ${second.longSilence}회`} /><Metric label="반복 표현" value={`${item.attempt1Metrics.repeatedExpressions} → ${second.repeatedExpressions}회`} /></div></section>
        <section className="history-detail-section"><h2>달라진 점</h2><div className="history-change-list">{item.changes?.map((change) => <p key={change}>{change}</p>)}</div></section>
        <p className="comparison-caution">이 비교는 답변에 드러난 설명과 전달력 수치의 변화만 보여줍니다. 합격 가능성, 실제 역량 향상 또는 경험의 사실 여부를 판정하지 않습니다.</p>
        <ComparisonFeedbackSummary comparison={item.comparison ?? null} />
      </div>
    </details>
    <details className="history-fold">
      <summary>꼬리질문 대화</summary>
      <div className="history-fold-content">
        {item.interviewChat ? <div className="history-chat-messages">
          {item.interviewChat.messages.map((entry, index) => <article className={`history-chat-message ${entry.role}`} key={index}>
            <strong className="history-chat-speaker">{entry.role === "user" ? "나" : "말해봄 코치"}</strong>
            <p>{entry.message}</p>
            {entry.follow_up_question && <p className="history-chat-question">{entry.follow_up_question}</p>}
            {entry.summary && <div className="history-chat-summary">
              <h3>대화에서 정리한 내용</h3><ul>{entry.summary.clarified_points.map((point) => <li key={point}>{point}</li>)}</ul>
              <h3>다음 연습</h3><ul>{entry.summary.next_practice.map((point) => <li key={point}>{point}</li>)}</ul>
            </div>}
          </article>)}
        </div> : <p className="history-chat-empty">저장된 꼬리질문 대화가 없어요. 대화를 마친 기록에서 확인할 수 있어요.</p>}
      </div>
    </details>
  </div>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}
