# Supabase JWT 백엔드 인증 Spec

## Why

- **페르소나**: 혼자 면접 답변을 녹음·분석하려는 취업준비생
- **상황**: 향후 프론트엔드가 로컬 브라우저에서 연습 요청을 보낼 때, API가 요청자를 확인해야 한다.
- **문제**: 현재 로컬 분석 API는 요청자를 구분하지 못하므로, PRD의 로그인 사용자 기준 분석 요청 조건을 만족하지 못한다.
- **측정 지표**: 로그인 전 분석 요청 0건, Google 로그인 성공 뒤 사용자 정보 표시, 유효하지 않은 인증 토큰의 API 요청 차단.

## Goal

- FastAPI의 분석 Job 생성·조회 API는 Supabase에서 발급한 유효한 Bearer access token이 있을 때만 허용한다.
- 프론트엔드가 사용할 인증 헤더·실패 응답·개발 CORS 범위를 문서화한다.
- **Out of Scope**: React·Vite·프론트엔드 코드, 로그인·로그아웃 UI, Node.js 설치, 분석 결과·음성 파일의 Supabase DB/Storage 저장, 기록 화면, 회원 역할, 이메일·비밀번호 로그인, 배포, 런타임 TTS.

## What

### Happy Path

1. 향후 프론트엔드가 Supabase Google 로그인으로 access token을 얻는다.
2. 프론트엔드는 분석 요청 때 access token을 `Authorization: Bearer <token>`으로 FastAPI에 전송한다.
3. FastAPI는 Supabase JWT 검증을 통과한 요청만 기존 분석 작업을 생성·조회한다.

### Edge Case

| 상황 | 처리 방식 |
|---|---|
| 세션 만료 | 분석 API는 401을 반환하고 앱은 로그인 안내를 표시한다. |
| Authorization 헤더 누락·형식 오류 | API는 분석 Job을 만들지 않고 401을 반환한다. |
| 변조·검증 실패 토큰 | API는 분석 Job을 만들지 않고 401을 반환한다. |
| CORS 사전 요청 | Compose 기본 Origin `http://localhost:18080`과 Vite 단독 개발 Origin `http://localhost:5173`을 로컬 API 호출 출처로 허용한다. |

## How

- 백엔드는 `.env`로 `SUPABASE_URL`만 읽고, 공개 JWKS 엔드포인트를 조회한다. `.env.example`에는 값 없는 키 이름만 둔다. `sb_secret_...`, service role 키, Google client secret은 어떤 코드·환경 파일·커밋에도 넣지 않는다.
- FastAPI는 Supabase의 JWKS를 사용해 JWT 서명·issuer·audience·만료를 검증하고, 검증된 `sub`만 요청 사용자 ID로 사용한다. 프런트에서 보내는 사용자 ID나 user metadata는 권한 판단에 사용하지 않는다.
- 분석 Job은 이번 단계에서 메모리에만 보관한다. `sub`를 DB/Storage에 저장하거나 Supabase 테이블·RLS 정책을 만들지 않는다.
- 기본 CORS 허용 출처는 Compose 프런트 `http://localhost:18080`과 Vite 단독 개발 `http://localhost:5173`이며, 운영 URL은 `CORS_ALLOWED_ORIGINS`로 명시한다.

## AC

- **Given**: 프론트엔드가 로그인 사용자 access token을 갖고 있다. **When**: 분석 Job을 생성·조회한다. **Then**: `Authorization: Bearer` 헤더가 전송되고 기존 API의 성공 응답을 받을 수 있다.
- **Given**: Authorization 헤더가 없거나 잘못된 토큰이다. **When**: `POST /analysis-jobs` 또는 `GET /analysis-jobs/{job_id}`를 호출한다. **Then**: API는 401을 반환하고 분석 작업을 생성하거나 노출하지 않는다.
- **Given**: `http://localhost:18080`에서 Compose 앱을 실행한다. **When**: FastAPI에 인증 요청을 보낸다. **Then**: 브라우저 CORS 사전 요청과 실제 요청이 허용된다.
- **Given**: `SUPABASE_URL`이 없다. **When**: 백엔드를 실행한다. **Then**: 시크릿을 노출하지 않는 설정 오류가 발생하고 API는 인증 우회 상태로 시작하지 않는다.
