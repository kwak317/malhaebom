import logo from "../assets/malhaebom-detail-logo.png";
import "../styles/intro-flow-demo.css";

type StepProps = { number: string; title: string; description: string; note?: string; reverse?: boolean; children: React.ReactNode };

function StoryStep({ number, title, description, note, reverse = false, children }: StepProps) {
  return <section className={`flow-story-step${reverse ? " is-reverse" : ""}`}>
    <div className="story-copy"><p className="story-number">STEP {number}</p><h2>{title}</h2><p>{description}</p>{note && <small>{note}</small>}</div>
    <div className="story-preview"><span className="preview-label">소개용 미리보기</span>{children}</div>
  </section>;
}

const summarySteps = [
  ["🗂️", "질문 선택"], ["🔎", "질문 이해"], ["🎙️", "답변 녹음"], ["📊", "전달 방식 확인"], ["💬", "피드백 확인"], ["🔁", "다시 녹음"], ["↔", "1·2차 비교"],
];

export default function IntroFlowDemo() {
  return <div className="flow-demo">
    <header className="flow-demo-header"><a href="/" aria-label="말해봄 연습 시작"><img src={logo} alt="말해봄" /></a><nav><a href="/">연습하기</a><a href="#story">연습 과정</a></nav></header>
    <main>
      <section className="flow-demo-hero">
        <div><p className="flow-badge">✦ AI 면접 말하기 연습</p><h1>면접 연습,<br />질문을 고르는 순간부터<br /><em>다시 말해보는 순간까지.</em></h1><p>말해봄에서는 면접 질문을 고른 뒤 직접 답변을 녹음하고, 내 말하기 방식을 확인한 뒤 같은 질문을 다시 연습할 수 있어요.</p><div className="flow-hero-actions"><a href="#story">연습 과정 살펴보기 <b>↓</b></a><a href="/">바로 연습하기</a></div></div>
        <div className="hero-progress" aria-label="말해봄 연습 진행 흐름"><div className="hero-progress-top"><img src={logo} alt="말해봄 캐릭터" /><p><b>오늘의 면접 연습</b><span>한 번 말하고, 확인하고, 다시 말해요</span></p></div><div className="hero-progress-line">{["질문 선택", "질문 이해", "녹음", "분석", "피드백", "재연습", "비교"].map((item, i) => <div key={item} className={i === 0 ? "is-active" : ""}><i>{i === 0 ? "●" : "○"}</i><span>{item}</span></div>)}</div></div>
      </section>

      <div className="story-wrap" id="story">
        <StoryStep number="01" title="연습하고 싶은 질문을 골라요" description="준비된 면접 질문을 선택하거나, 직접 연습하고 싶은 질문을 입력할 수 있어요." note="연습하고 싶은 질문이 있다면 내 질문으로 바로 시작할 수도 있어요.">
          <div className="question-preview"><div className="preview-heading"><span>오늘의 연습</span><b>어떤 질문으로 시작할까요?</b></div><div className="question-tabs"><b>기본 질문</b><span>내 질문</span></div><div className="question-item is-selected"><i>01</i><p>팀 프로젝트에서 갈등을 해결한 경험을 말해주세요.</p><em>✓</em></div><div className="question-item"><i>02</i><p>지원한 직무에 관심을 갖게 된 계기가 있나요?</p></div><div className="custom-question">직접 질문을 입력해도 돼요 <span>＋</span></div></div>
        </StoryStep>

        <StoryStep number="02" reverse title="말하기 전에 질문의 방향을 확인해요" description="면접관이 이 질문으로 무엇을 확인하려는지, 답변에 어떤 내용을 포함하면 좋은지 먼저 살펴볼 수 있어요.">
          <div className="intent-preview"><article><span>🔎 면접관이 확인하려는 점</span><p>갈등 자체보다 의견 차이를 어떤 방식으로 해결했는지 확인하려는 질문이에요.</p></article><article><span>✦ 답변에 포함하면 좋은 내용</span><ul><li>갈등 상황</li><li>본인의 역할</li><li>실제 행동</li><li>결과 또는 배운 점</li></ul></article><small>정답을 알려드리기보다, 답변 방향을 잡는 데 도움을 드려요.</small></div>
        </StoryStep>

        <StoryStep number="03" title="이제 실제 면접처럼 말해봐요" description="질문을 보고 최대 60초 동안 직접 답변을 녹음해요." note="텍스트로 답을 입력하는 대신, 실제로 말해보는 연습을 중심으로 합니다.">
          <div className="record-preview"><span className="record-question">팀 프로젝트에서 갈등을 해결한 경험을 말해주세요.</span><div className="record-timer">00:24 <i>/ 01:00</i></div><div className="record-wave">{[18, 36, 58, 33, 72, 45, 83, 50, 27, 66, 38, 55, 20].map((height, i) => <i key={i} style={{ height: `${height}%` }} />)}</div><div className="record-state"><b>●</b> 녹음 중이에요</div><button type="button">■ 녹음 완료</button></div>
        </StoryStep>

        <StoryStep number="04" reverse title="답변이 끝나면 말하는 방식을 확인해요" description="말하기 속도, 긴 침묵, 반복 표현을 통해 내 답변의 전달 방식을 살펴볼 수 있어요.">
          <div className="analysis-preview"><small>소개용 예시 화면</small><div className="analysis-metric"><span>말하기 속도</span><b>128 <em>단어/분</em></b><div className="mini-bars">{[24, 38, 62, 48, 80, 66, 43, 29].map((height, i) => <i key={i} style={{ height: `${height}%` }} />)}</div><p>말하는 속도를 확인해요.</p></div><div className="analysis-metric"><span>긴 침묵</span><b>3 <em>회</em></b><div className="mini-pause"><i /><i className="pause" /><i /><i className="pause" /><i /></div><p>1초 이상 길게 멈춘 구간을 확인해요.</p></div><div className="analysis-metric"><span>반복 표현</span><b>4 <em>회</em></b><div className="mini-tags"><i>어</i><i>음</i><i>약간</i></div><p>반복해서 사용한 표현을 확인해요.</p></div></div>
        </StoryStep>

        <StoryStep number="05" title="결과를 보고 다음 연습 목표를 정해요" description="분석 숫자만 보여주는 것이 아니라, 다음 답변에서 직접 바꿔볼 수 있는 내용을 함께 확인해요.">
          <div className="feedback-preview"><article><span>측정 결과</span><p>이번 답변에서는 긴 침묵이 <b>3회</b> 나타났어요.</p></article><article className="goal"><span>다음 연습 목표</span><p>다음 답변에서는 긴 침묵을 한 번 줄여보세요.</p></article><article className="add"><span>답변에 더해볼 내용</span><p>본인이 맡았던 역할과 실제 행동을 조금 더 구체적으로 설명해 보세요.</p></article></div>
        </StoryStep>

        <StoryStep number="06" reverse title="확인한 내용을 바탕으로 한 번 더 말해봐요" description="첫 번째 답변에서 확인한 내용을 생각하면서 같은 질문에 다시 답해볼 수 있어요." note="피드백을 읽고 끝나는 대신, 바로 같은 질문을 다시 말해보는 연습으로 이어져요.">
          <div className="retry-preview"><div><b>1차 답변</b><span>첫 번째로 말해보기</span></div><i>↓</i><div className="retry-note">확인한 내용<br /><strong>긴 침묵 한 번 줄이기</strong></div><i>↓</i><div><b>2차 답변</b><span>같은 질문 다시 말하기</span></div></div>
        </StoryStep>

        <StoryStep number="07" title="첫 번째와 두 번째 답변을 비교해요" description="같은 질문에 다시 답한 뒤 1차와 2차 결과를 나란히 확인할 수 있어요.">
          <div className="comparison-preview"><small>소개용 예시 화면</small><div className="compare-table"><div><span>항목</span><span>1차</span><span>2차</span></div><div><b>말하기 속도</b><span>345 CPM</span><span>330 CPM</span></div><div><b>긴 침묵</b><span>3회</span><span>1회</span></div><div><b>반복 표현</b><span>4회</span><span>2회</span></div></div><p>숫자로 합격 여부를 판단하지 않아요. 바꾸려고 했던 부분이 실제 답변에서 어떻게 달라졌는지 확인하는 데 활용해요.</p></div>
        </StoryStep>
      </div>

      <section className="flow-summary"><p>전체 흐름 다시 보기</p><h2>말해봄의 연습은 이렇게 이어져요</h2><div>{summarySteps.map(([icon, text], i) => <article key={text}><span>{icon}</span><b>{text}</b>{i < summarySteps.length - 1 && <i>→</i>}</article>)}</div></section>
      <section className="flow-functions"><p>한눈에 보는 기능</p><h2>말해봄으로 할 수 있는 것</h2><div>{[["기본 면접 질문 연습","준비된 질문으로 시작해요."],["직접 질문 연습","내 질문도 입력할 수 있어요."],["면접관 의도 확인","답변 방향을 살펴봐요."],["말하기 습관 분석","전달 방식을 확인해요."],["답변 내용 보완","다음 연습 목표를 정해요."],["재녹음 전후 비교","같은 질문을 다시 말해요."]].map(([title, text]) => <article key={title}><b>{title}</b><span>{text}</span></article>)}</div></section>
      <section className="flow-final"><p>이제 직접 한 번 말해볼까요?</p><h2>질문을 고르고, 직접 말하고,<br />확인하고, 한 번 더 연습해 보세요.</h2><a href="/">말해봄으로 연습 시작하기 <b>→</b></a></section>
    </main>
  </div>;
}
