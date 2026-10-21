# Worklog — Langfuse 실제 provider 3회 검증

- 일시: 2026-09-29 10:40 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 본 Worklog를 포함하는 PR 예정
- 관련 요구사항/결정: D6 Langfuse 실행 경로 검증, 실제 사용자 데이터와 평가 fixture 분리

## 1. 목적

OpenRouter 실제 provider 호출이 Langfuse Japan Cloud에 trace, generation, validation span, Prompt 연결, token·cost·재시도 메타데이터로 남는지 확인한다. 요청당 비용 상한 `COACHING_LLM_MAX_COST_USD=0.05`를 적용한 뒤 추가 2회를 실행해, 총 3건의 안전한 fixture 검증 결과를 남긴다.

## 2. 작업 전 상태

- Langfuse smoke trace는 수집됐지만 실제 provider 호출 trace의 운영 근거는 체크포인트에서 미확인 상태였다.
- `coaching.provider`는 provider 응답 뒤 Langfuse observation을 만들어 UI Duration이 `0.00s`로 표시될 수 있고, 실제 provider 소요시간은 Metadata의 `latency_ms`에 기록되는 상태였다.
- 실제 사용자·공고·답변 원문은 Langfuse 검증에 사용하지 않았다.

## 3. 수행 내용

1. 실행 중인 API 컨테이너가 `COACHING_LLM_MAX_COST_USD=0.05`를 읽는 것을 확인했다.
2. 합성 Dataset v2 fixture를 FastAPI `/api/agent`와 실제 OpenRouter provider로 호출했다. 전송 재시도와 계약 재시도는 각각 최대 1회로 제한했다.
3. Langfuse Observations API v2로 각 trace의 세 observation 및 Prompt 연결을 다시 조회했다.
4. API 컨테이너에서 Langfuse 관측 단위 테스트를 실행했다.

## 주요 판단과 이유

- `.env`와 API 키는 로컬 비밀값이므로 커밋하지 않는다.
- 세 요청은 실제 provider를 사용하지만 고정된 합성 fixture와 `TestClient` 기반 context gateway를 사용한다. 따라서 실제 사용자·MCP·운영 배포 흐름 검증으로 표현하지 않는다.
- Langfuse UI의 `0.00s`는 이 작업에서 수정하지 않았다. Metadata의 provider `latency_ms`가 실제 네트워크 호출 시간을 나타내며, UI Duration 보정은 별도 범위로 남긴다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `docs/CURRENT_STATE.md` | 실제 provider 기반 합성 fixture 검증의 범위와 한계를 기록 |
| `docs/project2-checkpoint-work-cards.md` | D6 Langfuse 항목에 근거와 남은 운영 검증 조건을 기록 |
| `docs/worklogs/2026-09-29_1040_langfuse-live-provider-verification.md` | 실행 결과와 검증 명령을 기록 |

## 5. 검증

```text
docker compose exec -T api python -c "import os; print(os.getenv('COACHING_LLM_MAX_COST_USD'))"
0.05

docker compose exec -T api python -m unittest backend/tests/test_coaching_observability.py
Ran 5 tests in 0.299s
OK
```

| 순서 | Fixture | Trace ID | HTTP | Provider latency | Input / Output tokens | Cost | Validator | 재시도 |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | `coach-normal-01` | `5fdb1e0e71454eab978023844403141e` | 200 | 3029.800 ms | 7,532 / 702 | $0.0040146 | `valid=true`, errors 0 | 없음 |
| 2 | `coach-boundary-13` | `6de2e0edc208475aaedd9e6b0025222d` | 200 | 3072.356 ms | 7,488 / 713 | $0.0040289 | `valid=true`, errors 0 | 없음 |
| 3 | `coach-failure-30` | `6188c8b7e49f43808d59bd96bcfdb04d` | 200 | 2868.410 ms | 7,499 / 687 | $0.0039672 | `valid=true`, errors 0 | 없음 |

각 trace는 Langfuse Observations API v2에서 다음 3개 observation과 generation Prompt `malhaebom-coaching` v3 연결을 확인했다.

```text
coaching.analyze (SPAN)
coaching.provider (GENERATION)
coaching.output_validation (SPAN)
```

## 6. 발견한 문제 / 남은 리스크

- 현재 `coaching.provider`는 HTTP 호출을 마친 뒤 Langfuse observation을 생성·종료한다. 따라서 Langfuse UI Duration은 `0.00s`가 될 수 있으며 실제 시간은 metadata `latency_ms`로 확인해야 한다.
- 호스트 Python에서 동일 단위 테스트를 실행하면 `jwt` 의존성이 없어 import가 실패했다. API Docker 이미지에는 의존성이 있어 컨테이너 실행으로 `5/5` 통과를 확인했다.
- 실패 provider request, 인증 사용자/MCP 문맥, 운영 배포 환경의 trace는 이번 범위에서 검증하지 않았다.

## 미확인 사항

- `production` label 승격·rollback 및 production Prompt 운영 절차
- 실제 프론트 로그인 사용자에서의 end-to-end trace
- Langfuse UI Duration을 실제 provider 요청 구간으로 표현하는 별도 코드 개선

## 7. 다음 작업

- 인증 사용자와 MCP 문맥을 포함한 실제 요청 trace를 별도 안전한 시나리오로 검증한다.
- 실패/재시도 trace와 Prompt production 승격·rollback을 별도 범위에서 검증한다.
