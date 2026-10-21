# Worklog — 최종 LLM 후보 서비스 통합 테스트

- 일시: 2026-09-21 16:18 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음 (로컬 작업, commit/push/PR 미수행)
- 관련 요구사항/결정: P2-03, 모델 비교와 실패 경로, 2026-09-21 최종 후보 결정

## 1. 목적

Gemini 3.5 Flash-Lite와 GPT-5.6 Luna를 현재 머지된 실제 코칭 runtime과 FastAPI 경로로
통합 확인하고, 재현 가능한 최소 호출 하네스와 결과 기록을 남긴다.

## 2. 작업 전 상태

- 작업 트리는 깨끗했고 로컬 `main`과 `origin/main`은 `f37a4b9`로 일치했다.
- 기본 브랜치는 `main`, 마지막 서비스 기능 PR은 #39, 이후 평가/문서 PR #40~41도 main에 머지됐다.
- Final Four runner는 strict schema와 validator를 사용했지만 실제 서비스의 계약 보정, 비용 상한,
  FastAPI 오류 정규화 경로를 직접 통과하지 않았다.
- `.env`에는 `OPENROUTER_API_KEY` 변수만 설정되어 있음을 값 비공개로 확인했다.

## 3. 수행 내용

- 최신 `origin/main`에서 `test/final-candidate-service-integration` 브랜치를 만들었다.
- 실제 FastAPI 코칭 경로를 두 후보와 대표 3사례에 연결하는 dry-run 기본 CLI를 추가했다.
- 검증 API 응답과 usage/latency/retry/repair만 Git 제외 결과에 저장하고 secret/raw provider 응답은
  저장하지 않도록 했다.
- 대표 사례 문맥 변환과 집계 단위 테스트, 경량 서비스 통합 의존성 목록, 재현 문서를 추가했다.
- 실제 6건 호출을 시도했으나 외부 payload 전송 명시 승인 부재로 실행 환경에서 호출 전에 차단됐다.
- 사용자 승인 후 6건을 실행했으나 두 모델 모두 OpenRouter 404 → 서비스 503으로 종료됐다.
  두 모델이 지원하지 않는 `temperature=0`과 `require_parameters=true`의 조합이 원인이었다.
- 서비스가 model-default temperature를 사용하도록 필드를 생략하고 Luna용 strict schema를 정규화했다.
- 수정 후 정상 preflight 2건과 경계·실패 유도 4건을 실행해 두 모델 모두 3/3 계약·validator 통과를
  확인했다. retry·repair는 0회였다.

## 주요 판단과 이유

기존 30건 eval을 반복하지 않고 정상·경계·실패 유도 각 1건만 골라 총 6개 사용자 요청으로 제한했다.
timeout/429/5xx/invalid JSON은 유료 provider에 고의로 발생시키지 않고 결정론적 mock 테스트를 사용했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `evals/run_service_candidate_integration.py` | dry-run 기본 실제 서비스 경로 통합 하네스 |
| `backend/app/services/coaching_runtime.py` | 미지원 temperature 제거, GPT-5 strict schema 정규화 |
| `backend/tests/test_service_candidate_integration.py` | 대표 문맥 변환·집계 테스트 |
| `backend/requirements-service-integration.txt` | ML runtime 제외 통합 테스트 의존성 |
| `evals/README.md` | 재현 명령과 호출 경계 |
| `docs/experiments/2026-09-21_service-candidate-integration.md` | 실험 조건·현재 결과·한계 |
| `docs/worklogs/2026-09-21_1618_service-candidate-integration.md` | 작업 기록 |

## 5. 검증

```text
.venv-llm-eval/bin/python -B -m unittest backend.tests.test_service_candidate_integration
2 tests passed

.venv-llm-eval/bin/python -B evals/run_service_candidate_integration.py
planned_user_requests=6, network_calls=false

test_coaching_runtime.py 선택 7건
계약 보정/JSON/5xx/429/timeout/4xx/비용 상한 7건 passed

수정 후 관련 단위·회귀 테스트
평가 discovery 17건 + 서비스/validator/runtime 22건, 총 39건 passed

수정 후 OpenRouter 서비스 통합
Flash-Lite: HTTP/계약/validator 3/3, p50 3.37s, p95 3.40s, $0.01137420
Luna: HTTP/계약/validator 3/3, p50 13.41s, p95 14.14s, $0.00602871
```

승인 후 최초 OpenRouter 호출 6건은 모두 HTTP 404였고 usage가 없어 확인 비용은 `$0`이다.
수정 후 6건의 확인 비용 합계는 `$0.01740291`이다.

## 6. 발견한 문제 / 남은 리스크

- 기존 `test_coaching_api.py`의 선택 오류 정규화 테스트는 `TestClient` 종료가 지연돼 이번 환경에서
  완료 결과를 받지 못했다. 해당 테스트의 assertion 실패는 관찰하지 않았으나 통과로 기록하지 않는다.
- 모델별 3건뿐이라 p95와 품질 차이를 일반화할 수 없다.

## 미확인 사항

- 운영 Supabase 저장과 실제 MCP stdio를 포함한 외부 서비스 E2E.
- 대표 응답 및 Final Four 전체의 blind 사람 semantic 판정.

## 7. 다음 작업

- Final Four blind semantic 검토 후 Flash-Lite 기본 후보 판단을 재검토한다.
