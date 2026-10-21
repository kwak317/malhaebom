import { useEffect, useRef, useState } from "react";
import logo from "../assets/malhaebom-detail-logo.png";
import start from "../assets/demo-start.png";
import recording from "../assets/demo-recording.png";
import analysis from "../assets/demo-analysis.png";
import "../styles/intro-interactive-demo.css";

const steps = [
  ["01","연습할 질문을 골라요","준비된 면접 질문을 선택하거나 직접 연습하고 싶은 질문을 입력할 수 있어요.","질문 하나를 고르는 것부터 연습이 시작됩니다."],
  ["02","말하기 전에 질문의 방향을 확인해요","면접관이 무엇을 확인하려는 질문인지, 답변에 어떤 내용을 포함하면 좋은지 살펴볼 수 있어요.","정답을 알려주는 대신, 답변을 시작할 방향을 잡도록 도와줘요."],
  ["03","이제 직접 말해봐요","실제 면접처럼 최대 60초 동안 내 목소리로 답변을 녹음해요.","글로 답을 입력하는 대신, 직접 말하는 연습을 합니다."],
  ["04","말한 뒤에는 내 전달 방식을 확인해요","내가 어떻게 말했는지 세 가지 항목으로 살펴볼 수 있어요.","말하기 속도 · 긴 침묵 · 반복 표현"],
  ["05","결과를 보고 다음 답변을 준비해요","숫자만 확인하고 끝나는 것이 아니라, 다음 답변에서 바꿔볼 내용도 함께 확인해요.","측정 결과 · 다음 연습 목표 · 답변에 더해볼 내용"],
  ["06","확인한 내용을 가지고 한 번 더 말해봐요","첫 번째 답변에서 확인한 내용을 생각하면서 같은 질문에 다시 답할 수 있어요.","피드백을 읽는 것에서 끝나지 않고, 바로 다음 연습으로 이어집니다."],
  ["07","두 답변을 나란히 확인해요","같은 질문에 다시 답한 뒤 첫 번째와 두 번째 결과를 비교할 수 있어요.","좋고 나쁨을 판정하기보다, 바꾸려 했던 부분이 어떻게 달라졌는지 확인해요."],
];

function Preview({ step }: { step: number }) {
  if (step === 0) return <img className="interactive-image" src={start} alt="질문 선택 실제 화면" />;
  if (step === 1) return <div className="interactive-mock intent"><b>면접관이 확인하려는 점</b><p>의견 차이가 생겼을 때 어떤 방식으로 문제를 해결하는지 확인하려는 질문이에요.</p><b>답변에 포함하면 좋은 내용</b><span>• 상황　• 본인의 역할<br />• 실제 행동　• 결과 또는 배운 점</span></div>;
  if (step === 2) return <img className="interactive-image" src={recording} alt="답변 녹음 실제 화면" />;
  if (step === 3) return <img className="interactive-image" src={analysis} alt="전달 방식 분석 실제 화면" />;
  if (step === 4) return <div className="interactive-mock feedback"><small>소개용 예시</small><p><b>측정 결과</b>이번 답변에서는 긴 침묵이 3회 나타났어요.</p><p><b>다음 연습 목표</b>다음 답변에서는 긴 침묵을 한 번 줄여보세요.</p><p><b>답변에 더해볼 내용</b>본인이 맡은 역할과 실제 행동을 조금 더 구체적으로 설명해 보세요.</p></div>;
  if (step === 5) return <div className="interactive-mock retry"><b>1차 답변</b><i>↓</i><span>확인한 내용</span><i>↓</i><b>다시 녹음 · 2차 답변</b></div>;
  return <div className="interactive-mock compare"><small>소개용 예시</small><p><b>항목</b><b>1차 답변</b><b>2차 답변</b></p>{[["말하기 속도","345 CPM","330 CPM"],["긴 침묵","3회","1회"],["반복 표현","4회","2회"]].map(row=><p key={row[0]}><span>{row[0]}</span><span>{row[1]}</span><strong>{row[2]}</strong></p>)}</div>;
}

export default function IntroInteractiveDemo() {
  const [active, setActive] = useState(0); const refs = useRef<(HTMLElement | null)[]>([]);
  useEffect(() => { const observer = new IntersectionObserver(entries => entries.forEach(entry => { if (entry.isIntersecting) { const index = Number((entry.target as HTMLElement).dataset.step); setActive(index); } }), { rootMargin: "-35% 0px -45% 0px", threshold: 0 }); refs.current.forEach(node => node && observer.observe(node)); return () => observer.disconnect(); }, []);
  return <div className="interactive-demo"><header><a href="/" aria-label="말해봄 연습 시작"><img src={logo} alt="말해봄" /></a><a href="/">연습하기 ↗</a></header><main>
    <section className="interactive-hero"><div><p>✦ AI 면접 말하기 코치</p><h1>말해봄에서는<br />한 번 말하고 <em>끝내지 않아요.</em></h1><span>질문을 이해하고, 직접 답변하고, 내 말하기 방식을 확인한 뒤 같은 질문을 다시 연습해 보세요.</span><nav><a href="#interactive-story">연습 과정 따라보기 ↓</a><a href="/">바로 연습하기</a></nav></div><div className="hero-product"><img src={analysis} alt="말해봄 분석 화면 미리보기" /></div></section>
    <section className="interactive-intro" id="interactive-story"><p>INTERACTIVE STORY</p><h2>말해봄으로 이렇게 연습해요</h2><span>아래로 내려가며 실제 연습 과정을 하나씩 살펴보세요.</span></section>
    <section className="story-layout"><div className="story-steps">{steps.map(([number,title,description,note],index)=><article key={number} data-step={index} ref={node => { refs.current[index] = node; }} className={active===index?"is-active":""}><b>{number}</b><h3>{title}</h3><p>{description}</p><small>{note}</small><div className="mobile-preview"><Preview step={index} /></div></article>)}</div><aside className="sticky-preview" aria-live="polite"><span>STEP {steps[active][0]} · 화면 미리보기</span><div key={active} className="preview-transition"><Preview step={active} /></div></aside></section>
    <section className="interactive-summary"><h2>말하고,<br />확인하고,<br /><em>다시 말해요.</em></h2><div><p><b>01</b> SPEAK<br /><span>말해보기</span></p><p><b>02</b> CHECK<br /><span>확인하기</span></p><p><b>03</b> RETRY<br /><span>다시 말하기</span></p></div></section>
    <section className="interactive-metric-words"><h2>말하는 방식은 세 가지로 살펴봐요</h2><p><b>말하기 속도</b><span>답변의 말하기 속도를 확인해요.</span></p><p><b>긴 침묵</b><span>1초 이상 길게 멈춘 구간을 확인해요.</span></p><p><b>반복 표현</b><span>반복해서 사용한 표현을 확인해요.</span></p></section>
    <section className="interactive-help"><h2>결과를 보여주는 데서<br />연습을 멈추지 않도록.</h2><p>→ 질문의 방향 확인<br />→ 내 말하기 방식 확인<br />→ 다음 연습 목표 확인<br />→ 답변에 더해볼 내용 확인<br />→ 같은 질문 다시 연습<br />→ 1차·2차 변화 확인</p></section>
    <section className="interactive-final"><h2>이제 한 질문을 골라<br />직접 말해볼까요?</h2><p>한 번 말하고, 확인하고, 다시 말하는 면접 연습을 시작해 보세요.</p><a href="/">말해봄으로 연습 시작하기 →</a></section>
  </main></div>;
}
