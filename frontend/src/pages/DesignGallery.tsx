import logo from "../assets/malhaebom-detail-logo.png";
import start from "../assets/demo-start.png";
import ready from "../assets/demo-record-ready.png";
import recording from "../assets/demo-recording.png";
import analysis from "../assets/demo-analysis.png";
import "../styles/design-gallery.css";

const screens = [
  ["시작 화면", start, "질문을 고르고 연습을 시작하는 첫 화면"],
  ["녹음 준비", ready, "마이크 확인 후 녹음을 준비하는 화면"],
  ["녹음 중", recording, "답변을 실제로 녹음하는 화면"],
  ["분석 결과", analysis, "말속도·긴 침묵·반복 표현을 확인하는 화면"],
] as const;

const demos = [
  ["기본 소개", "/demo/intro"], ["Feature", "/demo/intro-feature"], ["Flow", "/demo/intro-flow"],
  ["Problem / Solution", "/demo/intro-problem-solution"], ["Preview", "/demo/intro-preview"],
  ["Editorial", "/demo/intro-editorial"], ["Interactive", "/demo/intro-interactive"],
] as const;

const files = [
  ["페이지", "frontend/src/pages/PracticePage.tsx · RecordingPage.tsx · AnalysisPage.tsx · ResultPage.tsx"],
  ["스타일", "frontend/src/styles/practice-page.css · recording-page.css · flow-pages.css · detail-design.css"],
  ["이미지", "frontend/src/assets/demo-*.png · malhaebom-detail-logo.png · docs/images/*.png"],
  ["기획 문서", "docs/wireframe_완성본.md · docs/wireframe_PRD수정본.md · docs/prd.md"],
] as const;

export default function DesignGallery() {
  return <div className="design-gallery">
    <header className="design-header">
      <a className="design-brand" href="/"><img src={logo} alt="말해봄" /></a>
      <div className="design-header-meta"><span>DESIGN LIBRARY</span><a href="/">서비스 열기 ↗</a></div>
    </header>
    <main>
      <section className="design-hero">
        <div><p className="design-kicker">MALHAEBOM · LOCAL PREVIEW</p><h1>말해봄의 디자인을<br /><em>한 곳에서 확인하세요.</em></h1><p className="design-lead">현재 저장소에 있는 주요 화면 이미지, UI 데모, 디자인 파일을 빠르게 훑어볼 수 있는 로컬 쇼케이스입니다.</p><a className="design-button" href="#screens">주요 화면 보기 ↓</a></div>
        <div className="hero-note"><span>01</span><strong>말하기를 바꾸는<br />면접 연습</strong><small>Record · Analyze · Improve</small></div>
      </section>
      <section className="design-section" id="screens"><div className="section-heading"><div><p className="design-kicker">SCREEN ARCHIVE</p><h2>주요 화면</h2></div><span>PNG assets · 4 screens</span></div><div className="screen-grid">{screens.map(([title, image, description]) => <figure key={title}><div className="screen-image"><img src={image} alt={title} /></div><figcaption><strong>{title}</strong><span>{description}</span></figcaption></figure>)}</div></section>
      <section className="design-section tinted"><div className="section-heading"><div><p className="design-kicker">INTERACTIVE DEMOS</p><h2>소개 페이지 변형안</h2></div><span>새 탭에서 열기</span></div><div className="demo-grid">{demos.map(([title, href], index) => <a href={href} key={href}><span>0{index + 1}</span><strong>{title}</strong><b>↗</b></a>)}</div></section>
      <section className="design-section"><div className="section-heading"><div><p className="design-kicker">DESIGN SYSTEM</p><h2>시각 언어</h2></div><span>현재 CSS 기준</span></div><div className="tokens"><div><span className="token-swatch ink" /><strong>Ink</strong><small>#2F3445 · 본문/제목</small></div><div><span className="token-swatch blue" /><strong>Coach Blue</strong><small>#5B6FAE · 액션/강조</small></div><div><span className="token-swatch cream" /><strong>Warm White</strong><small>#F7F8FC · 배경</small></div><div><span className="token-swatch line" /><strong>Soft Line</strong><small>#D9DDEA · 경계선</small></div></div></section>
      <section className="design-section files-section"><div className="section-heading"><div><p className="design-kicker">FILE INDEX</p><h2>확인한 디자인 관련 파일</h2></div><span>repository map</span></div><div className="file-list">{files.map(([label, value]) => <div key={label}><strong>{label}</strong><span>{value}</span></div>)}</div></section>
    </main>
    <footer className="design-footer"><span>말해봄 디자인 라이브러리</span><span>로컬 확인용 · /design</span></footer>
  </div>;
}
