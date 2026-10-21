import logo from "../assets/malhaebom-detail-logo.png";
import "../styles/intro-problem-solution-demo.css";

const worries = ["내가 너무 빠르게 말하는지 잘 모르겠어요.", "생각하다가 얼마나 자주 멈추는지 알기 어려워요.", "‘어’, ‘음’, ‘약간’을 반복하는지 잘 모르겠어요.", "다시 연습했는데 무엇이 달라졌는지 확인하기 어려워요."];

export default function IntroProblemSolutionDemo() {
  return <div className="problem-demo">
    <header className="problem-header"><a href="/" aria-label="말해봄 연습 시작"><img src={logo} alt="말해봄" /></a><nav><a href="/">연습하기</a><a href="#empathy">말해봄 알아보기</a></nav></header>
    <main>
      <section className="problem-hero"><div className="problem-hero-copy"><p className="problem-badge">✦ AI 면접 말하기 연습</p><h1>답변은 준비했는데,<br />막상 말하려니 <em>생각처럼<br />안 나오나요?</em></h1><p>말해봄은 준비한 답변을 직접 말해보고, 내가 어떻게 말하고 있는지 확인한 뒤 다시 연습할 수 있도록 도와주는 AI 면접 말하기 서비스예요.</p><div className="problem-actions"><a href="#empathy">말해봄 알아보기 <b>↓</b></a><a href="/">바로 연습하기</a></div></div><div className="problem-conversation"><img src={logo} alt="말해봄 캐릭터" /><p className="user-bubble">“분명 준비했는데 왜 자꾸 중간에 멈추지?”</p><p className="coach-bubble">직접 말해보면 바꿔볼 부분을<br /><b>더 쉽게 찾을 수 있어요.</b></p></div></section>

      <section className="empathy-section" id="empathy"><p>혼자 연습하다 보면</p><h2>이런 순간이 생길 수 있어요.</h2><div className="worry-list">{worries.map((text, index) => <article key={text}><span>0{index + 1}</span><p>{text}</p></article>)}</div><b className="empathy-bridge">그래서 말해봄은 답변을 머릿속으로만 준비하는 데서 끝내지 않고,<br />직접 말해보는 연습으로 이어지도록 도와줘요.</b></section>

      <section className="solution-section speak-solution"><div className="solution-copy"><p>문제에서 연습으로</p><h2>준비한 답변을<br /><em>직접 말해보세요.</em></h2><span>기본 면접 질문을 선택하거나 직접 질문을 입력한 뒤, 실제 면접처럼 답변을 녹음할 수 있어요.</span><strong>글로 답을 작성하는 대신, 내 목소리로 답변을 연습합니다.</strong></div><div className="solution-preview question-record-preview"><small>소개용 미리보기</small><b>어떤 질문으로 시작할까요?</b><div className="mini-question active">01&nbsp;&nbsp; 팀 프로젝트에서 갈등을 해결한 경험을 말해주세요. <i>✓</i></div><div className="mini-question">02&nbsp;&nbsp; 지원 직무에 관심을 갖게 된 계기가 있나요?</div><div className="mini-input">내 질문을 직접 입력할 수 있어요 <i>＋</i></div><div className="mini-record"><span>00:18 <i>/ 01:00</i></span><div>{[20,45,70,42,86,52,25,60,38].map((height, index) => <i key={index} style={{height:`${height}%`}} />)}</div><b>● 녹음 중</b></div></div></section>

      <section className="solution-section intent-solution reverse"><div className="solution-copy"><p>막막한 질문 앞에서</p><h2>무엇을 말해야 할지 막막하다면,<br /><em>질문의 방향부터 살펴봐요.</em></h2><span>면접관이 이 질문으로 무엇을 확인하려는지, 답변에 어떤 내용을 포함하면 좋은지 확인할 수 있어요.</span><strong>정답을 제시하기보다, 답변 방향을 잡도록 도와드려요.</strong></div><div className="solution-preview intent-solution-preview"><article><b>🔎 면접관이 확인하려는 점</b><p>의견 차이가 생겼을 때 어떤 방식으로 문제를 해결하는지 확인하려는 질문이에요.</p></article><article><b>✦ 답변에 포함하면 좋은 내용</b><div><span>• 갈등 상황</span><span>• 본인의 역할</span><span>• 실제 행동</span><span>• 결과 또는 배운 점</span></div></article></div></section>

      <section className="habit-section"><p>말한 뒤에는</p><h2>내가 어떻게 말했는지,<br />감으로만 판단하지 않아도 돼요.</h2><div className="habit-list"><article><div className="habit-question">“내가 너무 빨랐나?”</div><i>→</i><div className="habit-answer"><span>말하기 속도</span><b>128 <em>단어/분</em></b><div className="habit-bars">{[28,43,62,80,56,74,39].map((height,index)=><i key={index} style={{height:`${height}%`}} />)}</div><p>답변의 말하기 속도를 확인해요.</p></div></article><article><div className="habit-question">“중간에 너무 오래 멈췄나?”</div><i>→</i><div className="habit-answer"><span>긴 침묵</span><b>3 <em>회</em></b><div className="habit-pauses"><i/><i className="is-pause"/><i/><i className="is-pause"/><i/></div><p>1초 이상 길게 멈춘 구간을 확인해요.</p></div></article><article><div className="habit-question">“‘어’, ‘음’을 많이 썼나?”</div><i>→</i><div className="habit-answer"><span>반복 표현</span><b>4 <em>회</em></b><div className="habit-words"><i>어</i><i>음</i><i>약간</i></div><p>답변에서 반복되는 표현을 확인해요.</p></div></article></div><small>모든 수치는 소개용 예시입니다.</small></section>

      <section className="result-solution"><div><p>확인했다면</p><h2>다음 답변에서<br />바꿔볼 점도 찾아봐요.</h2><span>측정 결과를 보는 데서 끝나지 않고, 다음 연습에서 직접 해볼 수 있는 내용을 함께 확인해요.</span></div><div className="result-card-preview"><article><b>측정 결과</b><p>이번 답변에서는 긴 침묵이 <strong>3회</strong> 나타났어요.</p></article><article><b>다음 연습 목표</b><p>다음 답변에서는 긴 침묵을 한 번 줄여보세요.</p></article><article><b>답변에 더해볼 내용</b><p>본인이 맡은 역할과 실제 행동을 조금 더 구체적으로 설명해 보세요.</p></article></div></section>

      <section className="retry-solution"><p>피드백을 읽는 것에서 끝나지 않아요</p><h2>확인한 내용을 바로 다시 말해볼 수 있어요</h2><span>첫 답변에서 확인한 내용을 생각하면서 같은 질문에 다시 답해보세요.</span><div className="retry-flow"><article><b>1차 답변</b><span>직접 말해보기</span></article><i>↓</i><article className="retry-center"><b>말하기 습관 확인</b><span>다음 연습 목표</span></article><i>↓</i><article><b>다시 녹음</b><span>같은 질문 다시 말하기</span></article><i>↓</i><article><b>2차 답변</b><span>변화 확인하기</span></article></div><strong>말해봄의 연습은 결과를 보는 것보다, 그 결과를 가지고 다시 말해보는 데 이어집니다.</strong></section>

      <section className="comparison-solution"><div><p>달라진 부분을 직접 확인해요</p><h2>다시 말한 뒤에는<br />두 답변을 나란히 확인해요.</h2><span>숫자로 면접 결과를 판단하지 않아요. 바꾸려고 했던 부분이 두 번째 답변에서 어떻게 달라졌는지 확인하는 데 활용해요.</span></div><div className="problem-compare"><small>소개용 예시 화면</small><div className="problem-table"><header><b>항목</b><b>1차 답변</b><b>2차 답변</b></header>{[["말하기 속도","345 CPM","330 CPM"],["긴 침묵","3회","1회"],["반복 표현","4회","2회"]].map(row=><p key={row[0]}><b>{row[0]}</b><span>{row[1]}</span><span>{row[2]}</span></p>)}</div></div></section>

      <section className="three-steps"><p>그래서 말해봄에서는</p><h2>말하고, 확인하고, 다시 말해요</h2><div>{[["01","말해보기","면접 질문에 직접 답변해요."],["02","확인하기","말하기 습관과 다음 연습 방향을 확인해요."],["03","다시 말하기","같은 질문을 한 번 더 연습하고 변화를 확인해요."]].map(([number,title,text])=><article key={number}><b>{number}</b><h3>{title}</h3><p>{text}</p></article>)}</div></section>

      <section className="problem-functions"><p>전체 기능 한눈에 보기</p><h2>말해봄에서 사용할 수 있는 기능</h2><div>{["기본 면접 질문 선택","직접 질문 입력","면접관 의도 확인","답변 녹음","말하기 속도 분석","긴 침묵 분석","반복 표현 분석","답변 내용 보완","말하기 예시","재녹음","1차·2차 비교"].map(feature=><span key={feature}>{feature}</span>)}</div></section>
      <section className="problem-audience"><p>이런 연습이 필요하다면</p><h2>말해봄을 활용해 보세요</h2><div>{["답변 내용은 준비했지만 직접 말하는 연습이 부족한 사람","혼자 녹음해봤지만 무엇을 확인해야 할지 막막했던 사람","말하기 습관을 구체적으로 확인하고 싶은 사람","같은 질문을 반복하면서 답변을 다듬고 싶은 사람"].map((text,index)=><article key={text}><b>0{index+1}</b><span>{text}</span></article>)}</div></section>
      <section className="problem-final"><p>준비한 답변, 이번에는 직접 말해보세요.</p><h2>한 번 말하고, 확인하고,<br />다시 말해보는 면접 연습을 시작해 보세요.</h2><a href="/">말해봄으로 연습 시작하기 <b>→</b></a></section>
    </main>
  </div>;
}
