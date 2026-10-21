# 소개 페이지와 서비스 진입 동선

## Why
처음 방문한 사용자는 서비스 설명을 보고 바로 면접 연습을 시작한다. 기존 사용자는 서비스 홈과 기록으로 들어갈 수 있다.

## Goal
- `/`: 소개 페이지. `/app/`: 기존 서비스 홈. `/app/practice`: 연습 채팅.
- 연습 시작은 로그인 사용자를 채팅으로, 미로그인 사용자를 로그인으로 연결하며 인증 완료 후 채팅으로 복귀한다.
- 성공 기준: 세 진입 경로, OAuth 복귀, 기존 기록 왕복 동작 검증.
- 제외: commit/push/merge/운영 배포, 원격 인증 설정·DB·Prompt/Skill 변경.

## What
- 소개 → 연습 시작 → (필요한 경우 Google 로그인) → 연습 채팅.
- 소개 → 서비스 홈 → 기존 홈. 기존 홈의 소개 링크는 `/`로 복귀한다.
- 연습 진입에서 세션 확인 중에는 확인 중 상태를 표시한다. 세션 조회 실패/인증 취소는 재시도 가능한 로그인 화면으로 안내한다.
- 기록 왕복 시 기존 연습 인스턴스와 진행 상태를 보존한다. 로그아웃은 기존 상태 초기화 후 서비스 홈으로 복귀한다.
- 기존 `/intro/`와 `/practice` 링크는 호환한다.

## How
- 원본 showcase commit `bae729360eaefdafbac5341c360b3c14f18559a2`, 통합 main `dfd79bb7c66cc2f3c68093efc046e3832b9be75f`.
- Vite multi-page: root index는 소개, app/index는 기존 React 진입점. 정적 자산은 public/intro 유지.
- Vercel/nginx 및 로컬 dev/preview에서 앱 경로는 app/index.html로 연결한다.
- Supabase OAuth redirectTo는 기존 origin 그대로 유지한다. root 소개 JS가 인증 fragment/code를 같은 origin의 `/app/practice` 또는 `/app/`로 전달한다.
- 로그인 시작 시 sessionStorage에는 고정된 home/practice 값만 저장한다. 실패하면 연습을 기본 복귀 대상으로 사용한다. 임의 URL 또는 외부 returnTo를 사용하지 않는다.
- 인증 토큰은 기록/저장/출력하지 않는다. SDK가 처리하고 API는 기존 서버 JWT 검증을 유지한다.

## AC
- GIVEN `/` WHEN 접속 THEN 소개와 연습 시작/서비스 홈 링크를 제공한다.
- GIVEN 로그인 세션 WHEN 연습 시작 THEN 서비스 홈을 거치지 않고 채팅 표시.
- GIVEN 세션 없음 WHEN 연습 시작 THEN 로그인 표시; SIGNED_IN 후 채팅 표시.
- GIVEN root OAuth 복귀 WHEN code/token/error 전달 THEN 같은 origin 앱으로 전달하고 SDK/로그인 오류 처리.
- GIVEN 세션 조회 실패 WHEN 연습 진입 THEN 무한 로딩 없이 로그인 안내.
- GIVEN 서비스 홈 WHEN 연습·기록 이동 THEN 기존 동작 유지.
- GIVEN 뒤로가기 WHEN 서비스 홈/연습/기록 이동 THEN URL과 표시 화면 일치.
- GIVEN 모바일375px WHEN 소개 메뉴 THEN 연습 시작/서비스 홈 접근 가능.
