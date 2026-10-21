# 말해봄 서비스·프로젝트 소개 사이트 (`site/`)

> **상태:** 말해봄 Mk.2 저장소의 독립 정적 소개 사이트. 실제 서비스 코드와 분리된 `site/` 경로에서 관리하며 GitHub Pages 공개는 별도 단계입니다.

## 구성

- **서비스 소개 `/`** — 히어로, 면접 고민 4가지, 이용 과정 4단계, 3단 코칭 UI 목업, 내용/전달 코칭, 답변 전후 예시, FAQ, 서비스 CTA.
- **프로젝트 소개 `/project/`** — 문제 정의, 가치 제안, 개념 아키텍처, 근거 중심 설계, 평가·검증 접근 방식, 개발 저장소 연결.
- **공통 UI** — PC/모바일 반응형, Light/Dark/System 테마 선택, 키보드 내비게이션, 움직임 감소 설정, 상단 고정 메뉴.

첨부된 11쪽짜리 `말해봄 랜딩페이지 개선 목업 제안서`에 담긴 문구와 구조를 웹용으로 재구성했습니다. **로고, 마스코트, 상태별 캐릭터, 데모 화면 4장, 배경 SVG는 이 저장소의 기존 프론트엔드 원본을 활용**했습니다. 프로젝트 소개의 기술 설명은 개념적 수준이며, 배포 중인 저장소와 대조되지 않은 정량 지표는 **기재하지 않았습니다**.

## 파일 구조

```text
site/
├── index.html                 # 서비스 소개
├── project/
│   └── index.html             # 프로젝트 소개
├── assets/
│   ├── malhaebom-logo.webp    # 기존 frontend/src/assets 브랜드 원본
│   ├── mascot-crop.webp       # 기존 frontend/public 파비콘 마스코트
│   ├── favicon.png            # 기존 프론트엔드 파비콘에서 생성
│   ├── malhaebom-background.svg # 기존 서비스 배경
│   ├── brand/                 # 녹음 중 / 음성 전사 중 코치 이미지
│   ├── screenshots/           # 기존 프론트엔드의 데모 화면 4장
│   ├── brand-assets.css       # 기존 리소스용 스타일
│   ├── site-config.js         # URL 및 공개 설정 (여기부터 수정)
│   ├── site.css               # 디자인 시스템 + 반응형 스타일
│   └── site.js                # 메뉴, 테마, 다이얼로그, 모션
├── docs/
│   └── CONTENT_REVIEW.md      # 공개 전 검증 필요 사항
├── .nojekyll                 # Pages Jekyll 변환 생략
├── .gitignore
└── README.md
```

## 로컬 미리보기 (저장소 루트 기준)

**Node.js / npm 설치가 필요하지 않습니다.** `site/` 폴더에서:

```bash
python -m http.server 8000
```

- 서비스 소개: `http://localhost:8000/`
- 프로젝트 소개: `http://localhost:8000/project/`

간단히 확인하는 경우 `index.html`을 직접 열 수도 있지만, 상대 링크와 브라우저 정책을 고려하면 로컬 서버를 권장합니다.

## 공개 전 필수 수정

1. `assets/site-config.js`의 `serviceUrl` 기본값은 저장소 문서의 실제 Frontend URL인 `https://malhaebom.xyz`입니다. 서비스 주소 변경 시 갱신합니다.
2. `projectRepoUrl`이 최종 프로젝트 코드 저장소를 가리키는지 확인합니다. 현재 값은 기존 프로젝트 저장소 `https://github.com/aihuman-7th/proj2-3`입니다.
3. `docs/CONTENT_REVIEW.md`를 보고 현재 구현된 기능, 팀 및 역할, 정량 실험 결과, 보관 기간 등 확인합니다.
4. 브랜드 이미지는 기존 저장소 원본에서 WebP로 생성했습니다. 서비스 운영 화면과 데모 이미지가 다른지 확인하고 필요한 화면은 최신 스크린샷으로 교체하세요.

## 기존 프론트엔드 리소스 대응표

| 원본 | 정적 소개 사이트 | 사용 목적 |
| --- | --- | --- |
| `frontend/src/assets/malhaebom-detail-logo.png` | `assets/malhaebom-logo.webp` | 두 페이지 헤더·푸터 공식 로고 |
| `frontend/public/malhaebom-favicon.png` | `assets/mascot-crop.webp`, `assets/favicon.png` | 히어로 캐릭터·파비콘 |
| `frontend/src/assets/coach-recording.png` / `coach-transcribing.png` | `assets/brand/*.webp` | 녹음·전사 상태 캐릭터 |
| `frontend/src/assets/demo-*.png` 4장 | `assets/screenshots/*.webp` | 기존 프론트엔드 데모 이미지 |
| `frontend/public/malhaebom-background.svg` | `assets/malhaebom-background.svg` | 이용 방법 섹션 장식 |

원본 이미지는 변경하지 않았으며, 소개 사이트에 필요한 사본만 리사이즈/WebP로 변환했습니다. **데모 이미지는 현재 실서비스 캡처를 보증하지 않습니다.** PDF 기반 3단 코칭 영역은 계속 '기획 목업'으로 표시됩니다.

## 기존 저장소에서 GitHub Pages에 게시하기

**현재 이 PR은 소스만 `site/` 경로에 추가하며, Pages 설정·배포·운영 서비스에는 영향을 주지 않습니다.** GitHub Pages의 브랜치 게시 옵션은 저장소 루트 또는 `/docs`만 지원합니다. 현재 저장소는 `/docs`에 프로젝트 문서가 있으므로 `site/`를 Pages에 직접 지정하지 않습니다.

팀원 리뷰와 병합 이후 다음 중 하나를 선택합니다.

1. 별도 소개 저장소를 만들고 `site/`의 **내용**을 새 저장소 루트에 배치해 `main`의 `/ (root)`에서 브랜치 게시.
2. 현재 저장소에 소개 사이트 전용 `gh-pages` 브랜치를 게시. `site/`만 추출하여 전용 브랜치 루트로 올린 다음 Pages에서 `gh-pages` `/ (root)`를 선택. 예: `git subtree split --prefix site -b pages-site-snapshot`으로 스냅샷을 만든 뒤 검토하여 별도 배포 브랜치에 게시. **이 PR에서는 배포 브랜치를 만들거나 푸시하지 않습니다.**

정적 HTML/CSS/JS로 동작하므로 Actions 빌드 워크플로는 필요 없고, 기존 서비스 프론트엔드를 변경하지 않습니다.

## 선택: React/Vite 전환

이 초안은 **GitHub Pages 배포와 CI 사용량 최소화**를 우선한 의존성 없는 정적 구현입니다. 앞선 기획안의 React/Vite/TypeScript를 사용하지는 않았습니다. 추후 상호작용이 커지면 같은 섹션과 CSS 토큰을 React 컴포넌트로 옮기고 Vite 멀티 페이지/라우팅 구조를 도입할 수 있습니다. 이 전환은 사이트 공개의 선행 조건이 아닙니다.

## 디자인 및 근거

- 콘텐츠: 사용자가 제공한 2026.10 말해봄 랜딩페이지 개선 PDF.
- 브랜드: 보라색 계열, 말해봄 로고·마스코트, 라이트/다크/시스템 테마.
- 서비스 기능: 경험 연결 → 답변 → 코칭 → 재답변; 말하기 방식과 답변 내용 분석.
- 예시 UI와 답변: **기획용 예시**로 명시해 실제 사용자 데이터/배포 화면으로 오인되지 않도록 함.
- 프로젝트 소개의 아키텍처: **사용자 흐름 수준의 개념도**로 표시함.

## 개인정보 및 비밀 관리

이 사이트에는 서버, 인증, API 키가 없습니다. `site-config.js`는 **공개 파일**이므로 인증 토큰, 비밀번호, Supabase secret key 등을 넣지 마세요.
