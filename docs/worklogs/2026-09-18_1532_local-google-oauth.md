# Worklog — 로컬 Google OAuth 재연결

- 일시: 2026-09-18 15:32
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: `docs/specs/supabase-google-auth.md`, 기존 1차 Google OAuth Client 재사용

## 1. 목적

Mailpit 이메일 링크 없이 로컬 말해봄에서 기존 Google OAuth Client를 재사용해 Google 로그인을 시작할 수 있게 한다. 기존 호스팅 로그인을 중단하지 않고 로컬 callback과 별도 secret을 연결하며, Google 계정 선택 화면까지 실제 실행으로 확인한다.

## 2. 작업 전 상태

- 프런트에는 `signInWithOAuth({ provider: "google" })`와 `Google로 계속하기` 버튼이 이미 구현되어 있었다.
- 로컬 Supabase `/auth/v1/settings`는 `external.google=false`, `external.email=true`였다.
- `supabase/config.toml`에는 Google Provider 설정이 없었다.
- Google Cloud `malhebom` 프로젝트에는 기존 OAuth Web Client가 남아 있었고, 호스팅 Supabase callback 한 개만 등록되어 있었다.
- 기존 호스팅 Supabase의 Google Provider와 Google authorize endpoint는 동작 중이었다.

## 3. 수행 내용

1. 기존 OAuth Client의 승인된 redirect URI에 `http://127.0.0.1:54321/auth/v1/callback`을 추가했다.
2. 기존 Client에 로컬용 client secret을 추가했다. 기존 호스팅용 secret은 유지했다.
3. 새 secret을 Git에서 제외된 루트 `.env`에 `SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_SECRET`으로 저장하고 파일 권한을 `0600`으로 설정했다. secret 값은 코드·문서·로그에 기록하지 않았다.
4. `supabase/config.toml`에 `[auth.external.google]`을 추가하고 기존 Client ID와 환경변수 기반 secret 참조를 설정했다.
5. 로컬 Supabase를 데이터 백업 유지 방식으로 재시작했다.
6. 말해봄의 `Google로 계속하기` 버튼에서 Google 계정 선택 및 동의 화면까지 이동하는 것을 확인했다.

## 주요 판단과 이유

- 새 OAuth Client를 중복 생성하지 않고 기존 Client를 재사용했다.
- 기존 호스팅 로그인 중단을 피하기 위해 기존 secret을 교체하지 않고 두 번째 secret을 로컬 전용으로 추가했다.
- client secret은 저장소에 넣지 않고 `config.toml`의 `env(...)` 참조만 커밋 가능한 설정으로 남겼다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `supabase/config.toml` | 로컬 Google Provider 활성화와 기존 Client ID 연결 |
| `.env` | 로컬용 Google client secret 저장, Git 제외 및 `0600` 적용 |
| `docs/CURRENT_STATE.md` | 로컬 OAuth 실행 확인 범위와 미완료 E2E 기록 |
| `docs/worklogs/2026-09-18_1532_local-google-oauth.md` | 작업·검증·남은 단계 기록 |

## 5. 검증

```text
GET http://127.0.0.1:54321/auth/v1/settings
google=true, email=true

GET /auth/v1/authorize?provider=google&redirect_to=http://localhost:3000/
HTTP 302, accounts.google.com redirect, redirect_uri=http://127.0.0.1:54321/auth/v1/callback

GET http://127.0.0.1:8003/health
{"status":"ok"}

GET http://localhost:3000/
HTTP 200

브라우저: Google로 계속하기
Google 계정 선택 화면 및 malhaebom 동의 화면 도달
```

## 6. 발견한 문제 / 남은 리스크

- Google은 redirect URI 변경 반영에 시간이 걸릴 수 있다고 안내한다.
- OAuth Client에 활성 secret이 두 개이므로 새 로컬 secret을 분실하지 않도록 관리해야 한다. 기존 secret은 호스팅 Supabase가 사용 중일 수 있어 이번 작업에서 중지하거나 삭제하지 않았다.

## 미확인 사항

- 사용자의 Google 동의 화면 최종 `계속` 선택 전이므로 callback 완료, 프런트 세션 생성, FastAPI Bearer token 인증은 아직 확인하지 않았다.

## 7. 다음 작업

- 사용자 확인 후 Google 동의 화면에서 `계속`을 선택하고 callback·세션·인증 API까지 E2E 검증한다.

## 8. 2026-09-21 실행 설정 동기화

### 발견

- 브라우저 callback이 `127.0.0.1:3000`으로 향했지만, 현재 소스의 `supabase/config.toml`은 Compose 프런트 주소인 `localhost:18080`과 `127.0.0.1:18080`을 선언하고 있었다.
- 실행 중인 GoTrue 컨테이너의 `GOTRUE_SITE_URL`과 허용 목록은 이전 `127.0.0.1:3000` 값을 유지하고 있어 소스와 런타임이 불일치했다.

### 조치 및 검증

1. 프로젝트 ID `proj1-b-supabase-google-auth`의 로컬 Supabase만 기본 백업 옵션으로 중지한 뒤 다시 시작했다. 데이터 삭제 옵션은 사용하지 않았다.
2. 재기동한 GoTrue의 `GOTRUE_SITE_URL=http://localhost:18080`, 허용 추가 주소 `http://127.0.0.1:18080`, Google Provider 활성화를 확인했다.
3. 공개 publishable key를 값 노출 없이 헤더로만 사용해 두 주소의 `/auth/v1/authorize?provider=google` 요청이 모두 `302`으로 `accounts.google.com`에 이동하는 것을 확인했다.
4. Compose 프런트 `http://localhost:18080/`도 HTTP 200으로 응답했다.

### 남은 검증

- 사용자가 새 Google 로그인을 완료한 뒤 callback, 프런트 세션 생성, FastAPI Bearer 인증까지 이어지는 전체 흐름은 아직 확인하지 않았다.
