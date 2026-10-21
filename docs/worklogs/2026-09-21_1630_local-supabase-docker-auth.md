# Worklog — Docker에서 로컬 Supabase 인증 검증

- 일시: 2026-09-21 16:30 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 로컬 Supabase Docker 인증 및 Compose 포트 통일 PR
- 관련 요구사항/결정: P2-02 로컬 Docker 재현, 브라우저 비밀값 비노출, 검증 가능한 JWT issuer

## 1. 목적

팀원의 Windows Docker Compose 실행에서 Google 로그인 뒤 API가 access token을 검증하지 못해
`auth_error`를 반환하는 문제를 해결한다. Compose 웹 기본 주소를 `http://localhost:18080`으로
통일하고, 브라우저·API 컨테이너가 서로 다른 로컬 Supabase 주소를 사용할 때에도 JWT issuer를
정확히 검증하는 것을 완료 조건으로 둔다.

## 2. 작업 전 상태

- 브라우저는 `http://127.0.0.1:54321`의 로컬 Supabase에서 token을 발급한다.
- API 컨테이너에서 같은 주소의 `127.0.0.1`은 컨테이너 자신을 가리켜 JWKS를 조회할 수 없다.
- 컨테이너 접근 주소를 `host.docker.internal`로 바꾸면 token의 issuer
  (`http://127.0.0.1:54321/auth/v1`)와 달라져 기존 verifier가 token을 거부한다.
- Compose 기본 웹 포트와 Supabase Auth redirect URL은 기존 `8080`·`3000` 기준이라 팀원 실행 주소와 맞지 않았다.

## 3. 수행 내용

1. API 컨테이너의 JWKS 조회 URL(`SUPABASE_DOCKER_URL`)과 token issuer
   (`SUPABASE_JWT_ISSUER`)를 별도 환경변수로 처리했다.
2. `host.docker.internal`을 로컬 Supabase 허용 주소로 추가하고, 별도 issuer를 검증하는
   인증 회귀 테스트를 추가했다.
3. Compose 기본 웹 포트, CORS 기본 허용 Origin, 로컬 Supabase Auth redirect URL을 `18080`으로 맞췄다.
4. 실행 문서와 현재 상태 문서를 갱신했다.

## 주요 판단과 이유

- API는 Docker 내부에서 JWKS를 조회하므로 `host.docker.internal` 주소가 필요하지만, JWT의
  `iss` claim은 브라우저가 접속한 `127.0.0.1` 주소를 유지한다. 조회 URL과 issuer를 하나의
  변수로 강제하지 않고 분리해 두 주소를 각각 검증한다.
- `SUPABASE_SERVICE_ROLE_KEY`, Google OAuth client secret, LLM provider key는 예시·프런트
  번들·커밋에 추가하지 않았다.
- Hosted Supabase를 사용하는 환경은 기존 `https://...` URL만 사용하며
  `SUPABASE_DOCKER_URL`과 `SUPABASE_JWT_ISSUER`를 설정할 필요가 없다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `docker-compose.yml`, `.env.example` | 컨테이너용 Supabase URL·issuer와 `18080` 기본 Origin을 설정 |
| `backend/app/core/auth.py`, `backend/app/core/supabase_settings.py` | JWKS 조회 URL과 JWT issuer 분리, Docker loopback 주소 허용 |
| `backend/app/main.py` | Compose 웹 Origin을 CORS 기본 허용 목록에 추가 |
| `backend/tests/test_auth.py`, `backend/tests/test_local_analysis_api.py` | issuer 분리와 `18080` CORS 회귀 테스트 추가 |
| `supabase/config.toml` | 로컬 Google OAuth 복귀 주소를 `18080`으로 변경 |
| `README.md`, `docs/CURRENT_STATE.md`, `docs/SCAFFOLD.md`, `docs/specs/*.md` | Compose 주소·인증 동작 문서화 |

## 5. 검증

```text
docker compose config --quiet
PASS

docker compose build api && docker compose run --rm --no-deps api \
  python -m unittest backend.tests.test_auth backend.tests.test_local_analysis_api
PASS: 17 tests

python scripts/check_pr_policy.py --base origin/main
PASS: Review Core 111 lines, recommended 400 lines 이내

git diff origin/main...HEAD --check
PASS
```

## 6. 발견한 문제 / 남은 리스크

- GitHub에 PR이 merge되기 전 팀원 clone에는 이 변경이 없으므로, 기존 코드에서는 로그인 후 API가
  여전히 `auth_error`를 표시할 수 있다.
- `http://127.0.0.1:54321`은 각 팀원 자신의 로컬 Supabase를 뜻한다. 공유 Hosted Supabase가
  필요하면 `.env`의 `https://...supabase.co` URL과 Dashboard redirect allow list를 별도로 사용해야 한다.

## 미확인 사항

- 팀원 Windows 환경의 실제 Google OAuth callback → access token → API 요청 E2E는 아직 실행하지 않았다.
- 로컬 Supabase 시작에 필요한 Google OAuth secret은 Git에 포함하지 않았으며, 팀 내부의 비공개 전달과
  Google Console callback 등록 상태는 별도 확인이 필요하다.

## 7. 다음 작업

- PR 리뷰·승인 후 작성자가 merge한다.
- 팀원 PC에서 최신 main, 비공개 `.env`, Docker Desktop으로 `docker compose up -d --build`를 실행하고
  `http://localhost:18080` 로그인 후 인증 API 요청을 확인한다.
