import logo from "../assets/malhaebom-detail-logo.png";
import start from "../assets/demo-start.png";
import ready from "../assets/demo-record-ready.png";
import recording from "../assets/demo-recording.png";
import analysis from "../assets/demo-analysis.png";
import "../styles/intro-preview-demo.css";

function Browser({ src, label }: { src: string; label: string }) { return <figure className="preview-browser"><div><i /><i /><i /><span>말해봄 · {label}</span></div><img src={src} alt={`${label} 실제 화면`} /><figcaption>{label}</figcaption></figure>; }

export default function IntroPreviewDemo() {
  return <div className="preview-demo"><header className="preview-header"><a href="/" aria-label="말해봄 연습 시작"><img src={logo} alt="말해봄" /></a><nav><a href="/">연습하기</a><a href="#screens">화면으로 살펴보기</a></nav></header><main>
    <section className="preview-hero"><div><p>✦ AI 면접 말하기 코치</p><h1>말해봄에서는<br /><em>이렇게 면접을 연습해요.</em></h1><span>면접 질문을 고른 뒤 직접 답변을 녹음하고, 말하기 습관과 다음 연습 방향을 확인해 보세요.</span><div><a href="#screens">화면으로 살펴보기 <b>↓</b></a><a href="/">바로 연습하기</a></div></div><section className="hero-screens"><Browser src={start} label="질문 선택" /><Browser src={analysis} label="분석 결과" /></section></section>
    <section className="screen-section" id="screens"><div className="screen-copy"><p>01 · 질문 선택</p><h2>연습할 질문을 선택해요</h2><span>준비된 면접 질문을 선택하거나, 직접 연습하고 싶은 질문을 입력할 수 있어요.</span></div><Browser src={start} label="시작 및 질문 선택 화면" /></section>
    <section className="screen-section reverse"><div className="screen-copy"><p>02 · 질문 의도 확인</p><h2>질문의 의도를 먼저 살펴볼 수 있어요</h2><span>면접관이 무엇을 확인하려는 질문인지, 답변에 어떤 내용을 포함하면 좋은지 확인해요.</span><small>정답이나 평가가 아니라 답변 방향을 잡는 도움으로 제공돼요.</small></div><div className="intent-large"><b>🔎 면접관이 확인하려는 점</b><p>의견 차이가 생겼을 때 어떤 방식으로 문제를 해결하는지 확인하려는 질문이에요.</p><b>✦ 답변에 포함하면 좋은 내용</b><div><span>• 상황</span><span>• 본인 역할</span><span>• 실제 행동</span><span>• 결과 또는 배운 점</span></div></div></section>
    <section className="screen-section"><div className="screen-copy"><p>03 · 답변 녹음</p><h2>실제 면접처럼 직접 말해봐요</h2><span>최대 60초 동안 직접 답변을 녹음해요.</span></div><div className="dual-browsers"><Browser src={ready} label="마이크 준비" /><Browser src={recording} label="답변 녹음" /></div></section>
    <section className="analysis-section"><div><p>04 · 분석 결과</p><h2>말한 뒤에는 내 답변을 눈으로 확인해요</h2><span>실제 결과 화면에서 답변의 전달 방식을 살펴볼 수 있어요.</span><ul><li><b>말하기 속도</b> 답변의 말하기 속도를 확인해요.</li><li><b>긴 침묵</b> 1초 이상 길게 멈춘 구간을 확인해요.</li><li><b>반복 표현</b> ‘어’, ‘음’, ‘약간’처럼 반복되는 표현을 확인해요.</li></ul></div><Browser src={analysis} label="1차 결과 분석 화면" /></section>
    <section className="feedback-section"><div><p>05 · 다음 연습 방향</p><h2>숫자만 보여주고 끝나지 않아요</h2><span>결과 화면에서는 다음 답변에서 직접 바꿔볼 수 있는 내용을 함께 확인해요.</span></div><article><small>소개용 예시</small><div><b>측정 결과</b><p>이번 답변에서는 긴 침묵이 <strong>3회</strong> 나타났어요.</p></div><div><b>다음 연습 목표</b><p>다음 답변에서는 긴 침묵을 한 번 줄여보세요.</p></div><div><b>답변에 더해볼 내용</b><p>본인이 맡은 역할과 실제 행동을 조금 더 구체적으로 설명해 보세요.</p></div></article></section>
    <section className="storyboard"><p>화면을 따라가면 이런 흐름이에요</p><h2>말해봄을 화면으로 먼저 만나보세요</h2><div>{[[start,"질문 선택"],[ready,"녹음 준비"],[recording,"답변 녹음"],[analysis,"분석 결과"],[ready,"다시 연습"]].map(([src,label],index)=><article key={`${label}-${index}`}><img src={src as string} alt={`${label} 화면`} /><b>{String(index+1).padStart(2,"0")}</b><span>{label}</span>{index<4&&<i>→</i>}</article>)}</div></section>
    <section className="compare-preview-section"><div><p>06 · 재연습과 비교</p><h2>첫 답변에서 끝나지 않아요</h2><span>결과에서 확인한 내용을 생각하면서 같은 질문에 다시 답하고, 1차와 2차 결과를 비교할 수 있어요.</span></div><article><small>소개용 예시 화면</small><header><b>항목</b><b>1차 답변</b><b>2차 답변</b></header>{[["말하기 속도","345 CPM","330 CPM"],["긴 침묵","3회","1회"],["반복 표현","4회","2회"]].map(row=><p key={row[0]}><b>{row[0]}</b><span>{row[1]}</span><span>{row[2]}</span></p>)}<em>수치 자체로 면접 결과를 판단하는 것이 아니라, 바꾸려고 했던 부분이 어떻게 달라졌는지 확인해요.</em></article></section>
    <section className="preview-functions"><p>기능 한눈에 보기</p><h2>말해봄으로 할 수 있는 것</h2><div>{["기본 면접 질문 연습","직접 질문 입력","면접관 의도 확인","질문 TTS","답변 녹음","STT 전사","말하기 속도 확인","긴 침묵 확인","반복 표현 확인","다음 연습 목표","답변에 더해볼 내용","말하기 예시","재녹음","1차·2차 비교"].map(item=><span key={item}>✦ {item}</span>)}</div></section>
    <section className="preview-final"><p>화면으로 살펴봤다면, 이번에는 직접 말해보세요.</p><h2>질문을 선택하고,<br />내 목소리로 답변을 연습해 보세요.</h2><a href="/">말해봄으로 연습 시작하기 <b>→</b></a></section>
  </main></div>;
}
