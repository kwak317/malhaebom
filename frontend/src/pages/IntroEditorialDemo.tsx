import logo from "../assets/malhaebom-detail-logo.png";
import start from "../assets/demo-start.png";
import recording from "../assets/demo-recording.png";
import analysis from "../assets/demo-analysis.png";
import "../styles/intro-editorial-demo.css";

function Screen({ src, alt }: { src: string; alt: string }) { return <div className="editorial-screen"><span><i/><i/><i/> 말해봄</span><img src={src} alt={alt} /></div>; }

export default function IntroEditorialDemo() {
  return <div className="editorial-demo"><header className="editorial-header"><a href="/" aria-label="말해봄 연습 시작"><img src={logo} alt="말해봄" /></a><a href="/">연습하기 ↗</a></header><main>
    <section className="ed-hero"><div><p>AI INTERVIEW SPEAKING COACH</p><h1>준비한 답변을<br /><em>직접 말해보세요.</em></h1><span>말해봄은 면접 질문에 직접 답하고, 말하는 방식을 확인한 뒤 같은 질문을 다시 연습하는 AI 면접 말하기 코치입니다.</span><a href="/">연습 시작하기 <b>→</b></a></div><aside><img src={logo} alt="말해봄 캐릭터" /><div className="ed-wave">{[28,52,81,42,67,95,50,30,73,48,85].map((v,i)=><i key={i} style={{height:`${v}%`}} />)}</div></aside></section>
    <section className="ed-statement"><h2>말해봄은<br />답변을 만들어주는 AI가 아니라,<br /><em>직접 말해보는 연습을 돕습니다.</em></h2><p>질문을 이해하고, 말하고, 확인하고, 다시 말합니다.</p></section>
    <section className="ed-split"><div className="ed-copy"><b>01</b><h2>질문을 고릅니다.</h2><p>준비된 면접 질문을 선택하거나 직접 연습하고 싶은 질문을 입력할 수 있습니다.</p></div><Screen src={start} alt="질문 선택 실제 화면" /></section>
    <section className="ed-split reverse"><div className="intent-editorial"><span>면접관이 확인하려는 점</span><p>의견 차이가 생겼을 때 어떤 방식으로 문제를 해결하는지 확인하려는 질문이에요.</p><span>답변에 포함하면 좋은 내용</span><p>상황 · 본인 역할 · 실제 행동 · 결과 또는 배운 점</p></div><div className="ed-copy"><b>02</b><h2>말하기 전에<br />질문의 방향을 살펴봅니다.</h2><p>면접관이 무엇을 확인하려는지, 답변에 어떤 내용을 포함하면 좋은지 확인합니다.</p><small>정답을 제공하기보다 답변 방향을 잡도록 돕습니다.</small></div></section>
    <section className="ed-record"><div><b>03</b><h2>이제 말해봅니다.</h2><p>최대 60초 동안 실제 면접처럼 답변합니다.</p></div><Screen src={recording} alt="답변 녹음 실제 화면" /></section>
    <section className="ed-metrics"><div><b>04</b><h2>답변 뒤에는<br />말하는 방식을 확인합니다.</h2></div><article className="metric-one"><strong>말하기 속도</strong><span>답변 속도를 확인합니다.</span></article><article className="metric-two"><strong>긴 침묵</strong><span>1초 이상 멈춘 구간을 확인합니다.</span></article><article className="metric-three"><strong>반복 표현</strong><span>반복해서 사용한 표현을 확인합니다.</span></article></section>
    <section className="ed-result"><div><h2>결과는 숫자에서<br />끝나지 않습니다.</h2><p>→ 측정 결과<br />→ 다음 연습 목표<br />→ 답변에 더해볼 내용<br />→ 참고 기준</p></div><Screen src={analysis} alt="1차 결과 분석 실제 화면" /></section>
    <section className="ed-retry"><b>05</b><h2>읽고 끝내지 않고,<br />같은 질문을 다시 말합니다.</h2><div><span>1st answer</span><i>↓</i><span>practice</span><i>↓</i><span>2nd answer</span></div><p>첫 번째 답변에서 확인한 내용을 두 번째 답변에서 직접 적용해봅니다.</p></section>
    <section className="ed-compare"><article><p>1차 답변</p><b>1st</b><span>345 CPM<br />3 pauses<br />4 repetitions</span></article><article><p>2차 답변</p><b>2nd</b><span>330 CPM<br />1 pause<br />2 repetitions</span></article><small>소개용 예시 · Before / After Practice</small><em>좋고 나쁨을 판정하기보다, 내가 바꾸려 했던 부분이 어떻게 달라졌는지 확인합니다.</em></section>
    <section className="ed-ending"><h2>말하고.<br />확인하고.<br /><em>다시 말합니다.</em></h2><p>면접 답변을 머릿속으로만 준비하지 않도록.</p></section>
    <section className="ed-final"><p>이번에는</p><h2>직접 말해볼까요?</h2><span>질문 하나를 골라 첫 번째 답변을 시작해 보세요.</span><a href="/">말해봄 시작하기 <b>→</b></a></section>
  </main></div>;
}
