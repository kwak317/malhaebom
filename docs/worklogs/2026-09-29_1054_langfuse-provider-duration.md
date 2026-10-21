# Worklog — Langfuse provider 지연시간 기록 수정

- 일시: 2026-09-29 10:54 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: `fix/langfuse-provider-duration` (PR 생성 예정)
- 관련 요구사항/결정: D6 Langfuse trace에서 실제 provider 호출의 입력·출력·지연시간을 남긴다.

## 1. 목적

Langfuse `coaching.provider` generation이 실제 LLM 호출을 마친 뒤 생성되어 화면 Duration이 `0.00s`로 보이던 문제를 수정한다. provider HTTP 요청 전 generation을 시작하고, 처리 결과로 같은 observation을 갱신·종료해 provider 호출을 둘러싼 실제 처리 시간을 표시한다.

## 2. 작업 전 상태

`OpenAICompatibleJsonProvider.generate()`는 provider HTTP 요청 완료 후 `_record_generation()`을 호출했다. `LangfuseCoachingObservationSink.record_generation()`은 그 시점에 generation을 생성하고 즉시 `end()`하므로 SDK 기록 구간만 duration으로 계산됐다. metadata의 `latency_ms`는 실제 시간이었지만 Langfuse UI Duration은 `0.00s`였다.

## 3. 수행 내용

1. HTTP 요청 직전에 attempt별 `generation_id`와 `outcome=pending` generation을 안전하게 시작했다.
2. 성공·timeout·network/HTTP·출력 계약 오류의 최종 기록은 동일 ID generation을 update하고 end하도록 했다.
3. Langfuse update 실패와 예상 밖 SDK 오류에서도 시작한 generation의 종료를 보장했다.
4. Langfuse 기록이 시작되지 않은 기존/외부 sink는 기존처럼 start/end하는 fallback을 유지했다.
5. unit test로 generation lifecycle, update 실패 종료, HTTP 요청 전 시작, 예상 밖 SDK 오류 종료 순서를 추가했다.
5. Japan Cloud project에서 고정 fixture 3건을 실제 provider로 호출하고 Observations API v2에서 저장된 start/end를 확인했다.

## 주요 판단과 이유

Langfuse SDK의 public `start_observation()`에는 과거 start time을 덮어쓰는 인자가 없으므로, 완료 후 observation을 새로 만드는 방식으로는 UI Duration을 고칠 수 없다. 실제 호출 직전 시작하고 완료 후 end하는 lifecycle로 변경했다. 검증은 사용자 원문·DB·MCP를 쓰지 않는 고정 service-integration fixture만 사용했고, 호출별 비용 상한은 `$0.05`로 설정했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/app/services/coaching_runtime.py` | provider HTTP 요청 직전 generation 시작 및 attempt ID 전달 |
| `backend/app/services/coaching_observability.py` | active generation update/end lifecycle과 안전한 시작 helper |
| `backend/tests/test_coaching_observability.py` | 같은 generation을 update/end하는 회귀 테스트 |
| `backend/tests/test_coaching_runtime.py` | HTTP 요청보다 observation 시작이 앞서는 회귀 테스트 |
| `docs/CURRENT_STATE.md` | 실제 3회 Cloud 검증과 범위 기록 |
| `docs/project2-checkpoint-work-cards.md` | D6 증거 상태 갱신 |

## 5. 검증

```text
docker compose build api
docker compose run --rm --no-deps api python -m unittest backend/tests/test_coaching_observability.py backend/tests/test_coaching_runtime.py
Ran 31 tests in 1.808s
OK
```

실제 OpenRouter + Japan Langfuse Cloud 검증(고정 fixture, transport 1회·contract 1회, call budget `$0.05`) 결과:

| case | trace ID | HTTP / contract | provider Duration | tokens (input/output) | cost |
| --- | --- | --- | ---: | ---: | ---: |
| `coach-normal-01` | `47fb3cf310584c90b92e8935ba74ecfc` | 200 / valid | 3.892s | 12,939 / 742 | $0.005737 |
| `coach-boundary-13` | `d1af1a7d0c7c4b359bd941e4181bd979` | 200 / valid | 3.206s | 12,895 / 735 | $0.005706 |
| `coach-failure-30` | `422fb1a1cfd04a06b0ec3b4e1d64c056` | 200 / valid | 2.666s | 12,906 / 635 | $0.005459 |

Langfuse Observations API v2에서 각 trace가 `coaching.analyze` span, `coaching.provider` generation, `coaching.output_validation` span의 세 observation을 포함하고, provider generation의 Cloud start/end 시각이 위 duration과 일치함을 읽기 전용으로 확인했다.

전체 backend discovery도 실행했으나 이번 변경과 무관한 기존 환경 의존 실패가 있었다.

```text
docker compose run --rm --no-deps api python -m unittest discover -s backend/tests -f
FAIL test_coaching_api.CoachingApiTest.test_hides_unknown_context_as_not_found
expected HTTP 404, actual HTTP 503
Ran 46 tests in 3.116s
```

## 6. 발견한 문제 / 남은 리스크

- 실제 provider로 성공·무재시도 경로만 확인했다. timeout·429·5xx 등 재시도 generation의 Cloud duration은 unit test로 회귀를 막지만 Cloud 실호출로 별도 검증하지 않았다.
- 실제 사용자 DB/MCP 문맥과 production Prompt 승격/rollback은 이 fixture 검증 범위에 포함되지 않는다.
- 전체 backend discovery의 `test_hides_unknown_context_as_not_found`가 503으로 실패했다. 이 작업의 Langfuse 변경과 직접 관련되는지 확인하지 않았으므로 별도 환경/회귀 조사 대상이다.

## 미확인 사항

- 배포 환경의 운영 사용자 요청으로 동일 duration이 표시되는지 미확인.
- Langfuse trace 목록 화면의 수동 스크린샷은 생성하지 않았다. trace ID로 Cloud에서 조회 가능하다.

## 7. 다음 작업

- PR 리뷰 후 merge한다.
- 운영 배포 후 사용자 요청의 redacted trace와 MCP 접근 제어 증거를 별도로 확인한다.
