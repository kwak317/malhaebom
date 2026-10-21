import { AppHeader } from "../navigation";

type HomePageProps = {
  onStartPractice: () => void;
  onViewHistory: () => void;
};

const benefits = [
  ["▤", "실제와 같은 연습", "백엔드 직무에 맞춘 실전형 질문으로 연습해요."],
  ["☻", "AI 코칭 피드백", "답변을 분석해 강점과 개선점을 알려드려요."],
  ["▥", "더 나은 나의 답변", "반복 연습으로 자신 있는 답변을 만들어요."],
];

export default function HomePage({ onStartPractice, onViewHistory }: HomePageProps) {
  return <div className="home-page">
    <AppHeader />
    <main className="home-main">
      <section className="home-hero" aria-labelledby="home-title">
        <div className="home-copy">
          <p className="home-kicker">AI 면접 말하기 코치</p>
          <h1 id="home-title">면접을 말로<br />연습하는 습관,<br /><strong>말해봄</strong></h1>
          <p>실제 면접처럼 말해보고,<br />AI 코치의 피드백으로 더 나은 답변을 만들어보세요.</p>
          <div className="home-actions">
            <button className="home-primary" type="button" onClick={onStartPractice}>연습하기 <span aria-hidden="true">→</span></button>
            <button className="home-secondary" type="button" onClick={onViewHistory}>기록 확인하기</button>
          </div>
          <p className="home-intro-link"><a href="/">말해봄 소개 <span aria-hidden="true">↗</span></a></p>
        </div>
        <div className="home-question-art" aria-label="면접 질문 예시">
          <i className="art-sheet art-sheet-back" aria-hidden="true" /><i className="art-sheet art-sheet-front" aria-hidden="true" />
          <article className="home-question-card">
            <span className="home-question-badge">백엔드</span>
            <div className="home-question-copy">
              <strong>지금까지 진행한 프로젝트 중<br />기술적으로 가장 도전적이었던<br />경험에 대해 설명해 주세요.</strong>
              <p className="home-question-hint">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <rect x="9" y="2" width="6" height="12" rx="3" />
                  <path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M9 22h6" />
                </svg>
                이런 질문에 답해요
              </p>
            </div>
          </article>
        </div>
      </section>
      <section className="home-benefits" aria-label="말해봄의 연습 방식">
        {benefits.map(([icon, title, description]) => <article key={title}>
          <i aria-hidden="true">{icon}</i><h2>{title}</h2><p>{description}</p>
        </article>)}
      </section>
    </main>
  </div>;
}
