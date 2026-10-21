# Worklog — n8n 로컬 코칭 Mock 워크플로

- 일시: 2026-09-21
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: `docs/specs/n8n-local-coaching-mock-workflow.md`

## 1. 목적

n8n에서 Docker Compose E2E의 FastAPI 코칭 Mock API를 반복 가능하게 호출할 import용 JSON을 제공한다.

## 2. 작업 전 상태

프로젝트에는 `POST /api/agent`와 Compose E2E 전용 `compose-e2e-token` fixture가 있었지만 n8n import JSON과 n8n 로컬 Compose override는 없었다.

## 3. 수행 내용

1. 워크플로 JSON의 API URL·인증·Body 계약을 검사하는 unittest를 먼저 추가했다.
2. 파일 부재로 테스트가 실패하는 것을 확인했다.
3. Webhook과 HTTP Request 노드를 연결한 개발 전용 n8n JSON과 Spec을 추가했다.
4. n8n에서 Health Check, 정상/오류 출력, If 분기, 결과 요약을 수동 실행해 정상·연결 실패·복구 흐름을 확인했다.
5. 확인한 구성을 import JSON에 반영하고 구조 회귀 테스트를 확장했다.
6. Webhook Header Auth의 정상 호출과 잘못된 키의 403 차단을 수동 확인하고, import JSON에는 credential 참조·비밀값 없이 인증 요구만 반영했다.
7. PR #44 리뷰 피드백에 따라 n8n Compose 이미지를 `n8nio/n8n:1.113.3`으로 고정해 `latest` 변경으로 인한 workflow import 재현성 변동을 막았다.

## 주요 판단과 이유

- n8n은 FastAPI `/api/agent`만 호출한다. 현재 MCP는 외부 HTTP endpoint가 아닌 내부 stdio 도구이므로 n8n에 MCP secret을 넣지 않는다.
- `api:8000`은 n8n과 API가 같은 Compose 네트워크에 있을 때만 해석되는 서비스 이름이다.
- 실제 Supabase JWT 대신 E2E override에 한정된 고정 토큰만 사용한다.
- 이미지 태그는 로컬 workflow import 재현 기준으로 고정 버전(`1.113.3`)을 지정한다. digest 고정은 플랫폼별 manifest 선택을 제한할 수 있어 이번 로컬 Compose 범위에서는 적용하지 않았다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `n8n/workflows/malhaebom-coaching-mock.json` | n8n import용 개발 Mock 워크플로 |
| `docker-compose.n8n.local.yml` | n8n 컨테이너와 로컬 전용 환경값을 추가하는 Compose override |
| `backend/tests/test_n8n_coaching_workflow_export.py` | 요청·Health Check·오류 분기 구조 회귀 테스트 |
| `docs/specs/n8n-local-coaching-mock-workflow.md` | 범위·계약·AC |
| `docs/worklogs/2026-09-21_n8n-local-coaching-mock-workflow.md` | PR #44 재현성 보완과 검증 결과 |

## 5. 검증

```text
python -m unittest backend.tests.test_n8n_coaching_workflow_export
파일 생성 전 FileNotFoundError를 확인했고, 확장 후 3 tests OK를 확인했다.

python -m json.tool n8n/workflows/malhaebom-coaching-mock.json
JSON 문법 확인 성공.

docker compose -f docker-compose.yml -f docker-compose.e2e.yml -f docker-compose.n8n.local.yml config --quiet
세 Compose 파일의 병합 검증 성공.

docker manifest inspect n8nio/n8n:1.113.3
고정 태그의 multi-platform manifest 조회 성공.

python scripts/check_pr_policy.py --base origin/main --head feat/n8n-coaching-mock-workflow --pr-body <updated PR body>
Review Core 408 lines, Worklog exception 76 lines이며 rationale 인식으로 정책 검사 통과.

n8n workflow execution
`api:8000` 정상 경로에서 `needs_more_info` 요약을 수신했고, `api:9999` 연결 실패에서 `unavailable`과 `ECONNREFUSED`를 수신한 뒤 `api:8000`으로 복구해 정상 결과를 다시 수신했다.
```

## 6. 발견한 문제 / 남은 리스크

- 로컬 환경에 `pytest`는 설치되어 있지 않아 표준 라이브러리 `unittest`로 JSON 계약을 검사했다.
- `python -m unittest discover -s backend/tests -p 'test_*.py'`는 새 테스트를 포함해 57개를 발견했으나, 호스트 Python에 `fastapi`, `pydantic`, `httpx`, `jwt`, `numpy`가 없어 기존 모듈 30개가 import 단계에서 실패했다. 이 작업에서 의존성을 설치하거나 실패를 수정하지 않았다.

## 미확인 사항

- n8n UI에서 고정된 `1.113.3` 이미지로 새로 export한 JSON을 다시 import하는 round-trip 검증은 수행하지 않았다.

## 7. 다음 작업

- 현재 workflow JSON을 팀원 환경에서 import한 뒤 정상·오류 경로를 재현한다.
