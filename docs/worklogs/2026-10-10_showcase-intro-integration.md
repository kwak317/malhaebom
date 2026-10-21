# Worklog — 소개 페이지와 로그인 후 연습 진입

- 일시: 2026-10-10 KST
- 작업자: Codex
- 사용자 요청: 팀원 소개 페이지 이관, 도메인 첫 화면 소개, 연습 시작→필요한 로그인→채팅, 기존 서비스 홈 유지
- 관련 Spec: [소개/서비스 동선](../specs/showcase-intro-integration.md)

## 1. 목적
처음 방문한 사용자가 설명을 보고 바로 연습하도록 연결하고 기존 서비스 홈/기록을 유지한다.

## 2. 작업 전 상태
- 새 clone 브랜치 `codex/integrate-showcase-intro`, main `dfd79bb7c66cc2f3c68093efc046e3832b9be75f`. 기존 checkout 변경은 보존했다.
- showcase source `bae729360eaefdafbac5341c360b3c14f18559a2`.
- 앞선 읽기 전용 Vercel alias 조회: domain malhaebom.xyz → deployment dpl_JAwKCE3zfgof5TDxe2A6GevT3AxQ / project prj_YO6yJC9PgFnxNpXuLnLTwpAhxf1j. 이는 운영 주소 대상만 증명하며 최신 main과 운영 전체 소스 동일성을 증명하지 않는다.
- Google OAuth redirectTo는 origin이었고 App 첫 진입은 항상 home이었다.

## 3. 수행 내용
- 팀원 HTML 2개와 assets 14개를 이관했다. 12개 assets는 원본과 동일하며 HTML·site.js·site-config.js만 통합 경로/연습 연결을 수정했다. [원본 및 통합 SHA-256](../showcase/import-manifest.json).
- 소개의 canonical source는 frontend/index.html. 기존 React HTML은 frontend/app/index.html로 이동해 Vite multi-page로 빌드한다.
- `/` 소개, `/app/` 서비스 홈, `/app/practice` 연습, `/app/history` 기록, `/app/auth` 일반 로그인. `/intro/`, `/intro/project/`, 기존 `/practice` 호환.
- 소개에 연습 시작과 서비스 홈 링크를 제공하고 기존 홈은 소개 링크로 복귀한다. 시작 링크는 같은 탭으로 연습에 들어간다.
- 세션 확인 중 상태, 미로그인 로그인 안내, SIGNED_IN 후 연습 복귀, 세션 조회 실패/인증 취소를 처리한다.
- 기존 OAuth origin 허용 주소를 유지한다. root callback script가 code/fragment를 같은 origin의 고정 앱 경로로 전달한다. sessionStorage는 home/practice 의도만 저장하며 token은 저장/기록하지 않는다.
- App 이동 URL 및 popstate를 연결하고 기록 왕복 중 연습 인스턴스 보존을 유지한다. 로그아웃 초기화와 인터뷰 종료 복귀 링크를 서비스 경로에 맞췄다.
- Vercel SPA fallback, nginx fallback, Vite dev/preview를 앱 HTML로 정합화했다. API proxy는 유지한다.
- CURRENT_STATE·체크포인트·Spec과 원본 콘텐츠 체크리스트를 갱신/보존했다. 기획 목업·과거 데모 화면 고지는 유지했다.

## 주요 판단과 이유
별도 라우터 의존성을 추가하지 않고 기존 상태 기반 앱에 세 가지 진입 경로와 browser history 처리를 붙였다. 원격 Auth 허용 URL을 임의 변경하지 않고 기존 origin callback을 유지한다. SDK가 OAuth를 처리하며 서버 JWT 검증은 기존 구조를 유지한다.

## 4. 변경 파일
- frontend/index.html, frontend/app/index.html, frontend/public/intro/**
- frontend/vercel.json, frontend/nginx.conf, frontend/vite.config.ts
- frontend/src/App.tsx, App.test.tsx, api/supabaseAuth.ts 및 test, authCallback.test.ts
- frontend/src/pages/AuthPage.tsx, HomePage.tsx, styles/home-page.css
- frontend/src/components/InterviewFollowUpChat.tsx 및 test
- scripts/check_intro_site.py
- docs/specs/showcase-intro-integration.md, docs/showcase/**, CURRENT_STATE.md, project2-checkpoint-work-cards.md, 이 Worklog

## 5. 검증
- Supabase changelog index와 OAuth redirect/onAuthStateChange 공식 문서 확인. 사용 API에 관련된 신규 breaking change는 확인되지 않았다. 원격 DB/Auth 설정 변경 없음.
- `python3 scripts/check_intro_site.py`: PASS. root 18 IDs/33 links, project 7 IDs/31 links, 이미지 signature·CSS assets·앵커·중복 IDs.
- frontend `npm run test -- --reporter=dot`: 40 files/234 tests PASS.
- 추가 수정(성공 세션에서 이전 오류 제거) 후 App 11 tests 재실행 PASS.
- frontend `npm run build`: TypeScript + Vite PASS, dist/index.html 및 dist/app/index.html 생성.
- callback VM tests: implicit fragment·code 유지, home 복귀, 취소 오류, storage 실패·변조 값, 일반 앵커 비인증 처리.
- auth tests: 미로그인→로그인→SIGNED_IN→연습, 로그인 사용자 직접 진입, 확인 중 상태, 조회 실패, 취소 오류 비노출, 늦은 세션 조회 경쟁, 기존 기록 왕복/로그아웃.
- dev(18282)/preview(18281)의 root/app/practice/intro/project/legacy practice 경로 모두 200, 소개 HTML과 앱 HTML 구분 확인. public assets와 dist 바이트 일치.
- 공식 nginx:1.27-alpine image에서 nginx -t PASS; 임시 localhost18283 컨테이너의 `/`, `/app/`, `/app/practice`, `/intro/`, `/intro/project/`, `/practice`, callback JS 모두 200/올바른 HTML 확인 후 컨테이너 종료.
- 실제 브라우저: root 소개 → 연습 시작 → 로그인 안내, 소개 → 서비스 홈 → 소개 복귀. Google로 계속하기는 local 환경설정 없음으로 비활성임을 확인했다.
- 첫 이관의 375px 모바일 가로 넘침 없음·메뉴 및 theme 유지 검증에 더해 최종 root 화면의 연습/서비스 홈 버튼을 브라우저에서 확인했다.
- React 검토: hook 순서 유지, auth 구독 cleanup, 화면 인스턴스 보존, 상태 표시 role=status와 오류 role=alert, 링크 접근성 확인.
- 읽기 전용 독립 인증/경로 검토: 외부 redirect 위험/동선 차단 결함 없음. 같은 SPA에서 과거 authError가 남는 경미한 상태 문제를 제안받아 초기화와 회귀검사를 추가했다.
- 최종 diff whitespace 검사 PASS.

로컬 스크린샷(workspace output): showcase-entry-root-20261010.png, showcase-entry-login-20261010.png, showcase-entry-service-home-20261010.png. Git 외 로컬 자료이며 민감값 없음.

## 6. 발견한 문제 / 남은 리스크
- 팀원 [콘텐츠 체크리스트](../showcase/CONTENT_REVIEW.md)의 화면 최신성/자료 보관 세부 정책 등 미확정 사항은 임의 확정하지 않았다.
- 이관 코드 전체는 400줄을 넘으므로 PR 준비 때 review-size 정책과 이관 목적/크기 설명을 별도 확인한다.

## 미확인 사항
- 실제 Google OAuth 완료와 실제 Supabase 세션을 사용한 로그인 후 채팅은 미검증 (local Supabase 설정 없음). mock 이벤트/SDK 호출 계약 및 콜백 로직 검증을 실제 계정 E2E로 표현하지 않는다.
- 운영 Vercel routing/도메인 및 로그인 E2E, main과 운영 원본 전체 동일성은 미검증. 운영 배포 전 원본 비교 필요.
- 실녹음/STT/코칭 API/DB 전체 E2E를 재실행하지 않았다.
- commit/push/PR/merge/운영 배포, 원격 Auth/DB 변경은 미수행.

## 7. 다음 작업
변경 검토 및 명시적 승인 후 commit/push/PR을 진행한다. 운영 원본 비교와 팀원 승인 이후 merge/배포를 각각 승인받고 실제 도메인 root·서비스 홈·로그인 후 연습을 검증한다. 10/10 후속 변경이며 마감 전 제출 증거로 소급하지 않는다.

## PR 및 운영 적용 승인 (2026-10-10)

- 사용자가 PR 생성, 바로 머지, 운영 배포를 명시적으로 승인했다. 이번 작업에 한해 팀원 approve 대기를 생략하며 저장소 지침 자체는 변경하지 않는다.
- PR 크기 제한에 맞춰 자산 이관(379 core LOC)과 동선 적용을 별도 PR로 분리한다. 첫 PR은 자산만 추가하며 두 번째 PR에서 root와 인증 진입이 연결된다.

- #240 자산 이관 PR merged. 후속 동선 PR review core 573 LOC; 연결된 HTML/인증/라우팅을 하나의 책임 단위로 유지한다.
- GitHub Actions는 계정 billing/spending 문제로 job이 시작되지 않았다. 로컬 234 tests/build, PR policy unit tests 11건, 자산 PR gitleaks(no leaks) 대체 검증을 수행했다.
