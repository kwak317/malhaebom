import logo from "../assets/malhaebom-detail-logo.png";
import "../styles/intro-feature-demo.css";

const features = [
  { icon: "🗂️", title: "면접 질문 선택", text: "기본 면접 질문을 선택하거나, 연습하고 싶은 질문을 직접 입력할 수 있어요." },
  { icon: "🔎", title: "면접관 의도 확인", text: "이 질문에서 무엇을 확인하려는지와 답변에 담으면 좋은 내용을 먼저 살펴봐요." },
  { icon: "🎙️", title: "답변 녹음", text: "실제 면접처럼 직접 답변을 말하며 내 목소리로 연습해요." },
  { icon: "📊", title: "전달 방식 분석", text: "말하기 속도, 긴 침묵, 반복 표현을 가볍게 확인할 수 있어요." },
  { icon: "💬", title: "답변 피드백", text: "측정 결과와 함께 다음 연습 목표, 답변에 더해볼 내용을 확인해요." },
  { icon: "🔁", title: "다시 연습", text: "같은 질문을 다시 말하고 첫 답변과 두 번째 답변을 비교해요." },
];

const audience = [
  "혼자 면접 연습을 하고 있는 취업 준비생",
  "답변 내용은 준비했지만 말하기 연습이 필요한 분",
  "녹음은 해봤지만 무엇을 고쳐야 할지 막막했던 분",
  "같은 질문을 반복하며 말하기 흐름을 다듬고 싶은 분",
];

export default function IntroFeatureDemo() {
  return <div className="feature-demo">
    <header className="feature-header">
      <a href="/" aria-label="말해봄 연습하기"><img src={logo} alt="말해봄" /></a>
      <nav aria-label="빠른 이동"><a href="/">연습하기</a><a href="#features">기능 알아보기</a></nav>
    </header>
    <main>
      <section className="feature-hero">
        <div className="feature-hero-copy">
          <p className="feature-badge">✦ AI 면접 말하기 코치</p>
          <h1>면접 답변,<br /><em>직접 말해보면</em> 준비돼요</h1>
          <p className="feature-lead">말해봄은 면접 질문에 직접 답변해보고, 말하기 흐름을 확인한 뒤 다시 연습할 수 있도록 도와주는 AI 면접 연습 서비스예요.</p>
          <div className="feature-actions"><a className="feature-primary" href="/">말해봄으로 연습 시작하기 <span>→</span></a><a className="feature-secondary" href="#features">기능 알아보기</a></div>
        </div>
        <div className="feature-hero-visual" aria-label="말해봄 소개 미리보기">
          <div className="hero-orbit orbit-one" /><div className="hero-orbit orbit-two" />
          <img src={logo} alt="말해봄 캐릭터" />
          <div className="hero-speech">답변을 대신 만들어드리기보다<br /><strong>직접 말해보고 바꿔볼 점을<br />함께 찾아볼게요.</strong></div>
          <div className="hero-mini-card"><span>오늘의 연습</span><b>말하기 흐름 확인하기</b><i>● ● ● ● ●</i></div>
        </div>
      </section>

      <section className="feature-section feature-quick" aria-labelledby="feature-summary-title">
        <p className="feature-kicker">말해봄으로 할 수 있는 일</p><h2 id="feature-summary-title">답변을 준비하고, 말해보고,<br />다음 답변을 다시 다듬어요.</h2>
        <div className="quick-strip"><span>질문 선택</span><i>→</i><span>답변 녹음</span><i>→</i><span>전달 방식 확인</span><i>→</i><span>다시 연습</span></div>
      </section>

      <section className="feature-section feature-functions" id="features" aria-labelledby="features-title">
        <p className="feature-kicker">주요 기능</p><h2 id="features-title">말해봄에서는 이런 연습을 할 수 있어요</h2>
        <p className="feature-description">긴 설명보다 필요한 기능을 먼저 보고, 내게 맞는 방식으로 연습을 시작해보세요.</p>
        <div className="feature-grid">{features.map((feature, index) => <article key={feature.title} className="feature-card"><span className="feature-card-number">0{index + 1}</span><span className="feature-card-icon">{feature.icon}</span><h3>{feature.title}</h3><p>{feature.text}</p><span className="feature-card-arrow">→</span></article>)}</div>
      </section>

      <section className="feature-section feature-metrics" aria-labelledby="metrics-title">
        <p className="feature-kicker">전달 방식 미리보기</p><h2 id="metrics-title">내가 어떻게 말하고 있는지 확인해요</h2>
        <p className="feature-description">아래 수치는 실제 분석 결과가 아닌 소개용 예시입니다.</p>
        <div className="metric-grid">
          <article className="metric-card"><div className="metric-icon">〽</div><h3>말하기 속도</h3><p>답변이 너무 빠르거나 느리게 전달되고 있지는 않은지 확인해요.</p><div className="metric-bars" aria-hidden="true">{[30, 48, 62, 40, 76, 90, 66, 51, 35].map((height, i) => <i key={i} style={{ height: `${height}%` }} />)}</div><small>느림 <b>적정 구간</b> 빠름</small></article>
          <article className="metric-card"><div className="metric-icon">⏱</div><h3>긴 침묵</h3><p>답변 중 1초 이상 길게 멈춘 구간을 확인해요.</p><div className="metric-timeline" aria-hidden="true"><i /><i className="pause" /><i /><i /><i className="pause" /><i /></div><small>말하기 구간 <b>긴 침묵 구간</b></small></article>
          <article className="metric-card"><div className="metric-icon">Aa</div><h3>반복 표현</h3><p>‘어’, ‘음’, ‘약간’처럼 답변에서 반복되는 표현을 확인해요.</p><div className="metric-tags" aria-hidden="true"><span>어</span><span>음</span><span>약간</span></div><small>소개용 미리보기</small></article>
        </div>
      </section>

      <section className="feature-section feature-guidance" aria-labelledby="guidance-title">
        <p className="feature-kicker">결과 다음의 연습</p><h2 id="guidance-title">결과를 보고 다음 답변을 준비해요</h2>
        <p className="feature-description">말해봄은 숫자를 보여주는 데서 끝나지 않고, 이런 형태의 연습 방향을 함께 보여줘요.</p>
        <div className="guidance-grid">
          <article><span className="guidance-icon violet">✦</span><h3>다음 연습에서 바꿔볼 점</h3><p>“이번에는 긴 침묵을 한 번 줄여보세요.”</p></article>
          <article><span className="guidance-icon blue">＋</span><h3>답변에 더해볼 내용</h3><p>“본인의 역할과 실제 행동을 조금 더 구체적으로 설명해 보세요.”</p></article>
          <article><span className="guidance-icon lavender">?</span><h3>면접관이 확인하려는 점</h3><p>“해결책 자체보다 차이를 어떤 방식으로 해결했는지 확인하려는 질문이에요.”</p></article>
        </div>
      </section>

      <section className="feature-section feature-compare" aria-labelledby="compare-title">
        <div className="compare-copy"><p className="feature-kicker">반복 연습</p><h2 id="compare-title">같은 질문을 두 번 더 말해보세요</h2><p>첫 답변에서 확인한 내용을 바탕으로 같은 질문을 다시 연습하고, 변화한 부분을 직접 비교할 수 있어요.</p></div>
        <div className="compare-preview"><small>예시 화면</small><div className="compare-columns"><article><h3>1차 답변</h3><p>말하기 속도 <b>예시 A</b></p><p>긴 침묵 <b>예시 B</b></p><p>반복 표현 <b>예시 C</b></p></article><span className="compare-arrow">→<em>다시 연습</em></span><article className="compare-second"><h3>2차 답변</h3><p>말하기 속도 <b>예시 D</b></p><p>긴 침묵 <b>예시 E</b></p><p>반복 표현 <b>예시 F</b></p></article></div></div>
      </section>

      <section className="feature-section feature-flow" aria-labelledby="flow-title"><p className="feature-kicker">연습 흐름</p><h2 id="flow-title">하나의 답변을 이렇게 연습해요</h2><div className="flow-list">{["질문 선택", "질문 이해", "답변 녹음", "전달 방식 분석", "피드백 확인", "다시 연습"].map((step, index) => <div key={step}><b>0{index + 1}</b><span>{step}</span>{index < 5 && <i>→</i>}</div>)}</div></section>

      <section className="feature-section feature-audience" aria-labelledby="audience-title"><p className="feature-kicker">이런 분께 추천해요</p><h2 id="audience-title">혼자 말해보는 연습이 필요하다면</h2><div>{audience.map((text, index) => <article key={text}><span>0{index + 1}</span><p>{text}</p></article>)}</div></section>

      <section className="feature-final"><p>준비한 답변,</p><h2>이제 직접 말해보세요</h2><span>한 번 말하고, 확인하고, 다시 말해보는 연습을 시작해 보세요.</span><a href="/">연습 시작하기 <b>→</b></a></section>
    </main>
  </div>;
}
