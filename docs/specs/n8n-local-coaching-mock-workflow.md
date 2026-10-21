# n8n 로컬 코칭 Mock 워크플로 Spec

## Why

- **페르소나**: 말해봄 FastAPI 코칭 계약을 n8n에서 확인하려는 팀 개발자.
- **상황**: Docker Compose E2E 설정에는 Mock 코칭 API가 있지만, n8n에서 바로 import할 수 있는 워크플로가 없다.
- **문제**: API URL, 인증 헤더, 고정 fixture ID를 UI에서 매번 수동 입력하면 테스트 설정이 달라질 수 있다.
- **측정 지표**: n8n에 JSON 한 개를 import한 뒤 추가 노드 설정 없이 Mock 코칭 요청을 실행한다.

## Goal

- `Webhook → Health Check → 조건 분기 → POST /api/agent` 워크플로 JSON을 저장소에 제공한다.
- Docker Compose E2E 네트워크에서 `api:8000`과 고정 개발 fixture만 사용한다.
- **Out of Scope**: 실제 Supabase JWT·사용자 음성·운영 LLM·외부 HTTP MCP·자동 배포.

## What

**Happy Path**

1. 개발자가 n8n UI에서 JSON을 import한다.
2. 테스트 Webhook을 수신하고 Health Check가 `api:8000/health`를 호출한다.
3. 정상 응답이면 Mock 코칭 API를 호출하고 핵심 결과 네 필드만 반환한다.
4. 연결 오류면 코칭 API를 호출하지 않고 `unavailable` 오류 요약을 반환한다.

**Edge Cases**

| 상황 | 처리 방식 |
| --- | --- |
| API 컨테이너가 실행되지 않음 | Health Check 오류 출력이 `unavailable` 오류 요약으로 연결된다. |
| E2E override 없이 실행 | 고정 개발 토큰이 인증되지 않아 FastAPI가 401을 반환한다. |
| 운영 환경에 import | 개발 fixture 전용 구성임을 워크플로 노트에서 명시하고 운영 활성화를 범위에서 제외한다. |

## How

- 파일: `n8n/workflows/malhaebom-coaching-mock.json`
- Webhook: `POST /malhaebom-coaching-test`, 마지막 노드의 첫 JSON 응답
- Webhook 인증: `Header Auth`를 사용한다. Import 뒤 각 팀원이 `X-N8N-Test-Key`와 별도의 로컬 비밀값 credential을 연결한다.
- Health Check: `http://api:8000/health`, 오류 시 별도 출력으로 계속 실행
- API URL: `http://api:8000/api/agent`
- Header: `Authorization: Bearer compose-e2e-token`
- 요청 Body: `preset-04`와 프로젝트의 Compose E2E fixture UUID 두 개
- 성공 요약: `status`, `clarifying_question`, `next_actions`, `gaps`
- 오류 요약: `status=unavailable`, 사용자 안내, `technical_error`
- credential ID·비밀값은 export JSON, Git, API 요청 본문에 저장하지 않는다.
- 실행 전 Compose: `docker-compose.yml`, `docker-compose.e2e.yml`, `docker-compose.n8n.local.yml`을 함께 사용한다. `docker-compose.n8n.local.yml`은 workflow import 재현을 위해 `n8nio/n8n:1.113.3`을 사용한다.

## AC

- **AC-01 · 요청 계약 고정**
  - GIVEN: 워크플로 JSON 파일이 있다.
  - WHEN: 구조 회귀 테스트를 실행한다.
  - THEN: API URL, Bearer header, 네 개의 코칭 요청 필드가 E2E 계약과 일치한다.
- **AC-02 · n8n import**
  - GIVEN: 세 Compose 파일로 시작한 로컬 n8n이 있다.
  - WHEN: JSON을 import한다.
  - THEN: Webhook 노드와 HTTP Request 노드가 연결된 비활성 워크플로가 나타난다.
- **AC-03 · API 연결 실패 요약**
  - GIVEN: Health Check가 연결할 수 없는 주소를 호출한다.
  - WHEN: n8n 워크플로를 실행한다.
  - THEN: 코칭 API 대신 `Health Error Summary`가 `unavailable`과 오류 원인을 반환한다.
