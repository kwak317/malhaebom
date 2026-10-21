# Worklog — 인증 사용자 Langfuse E2E 및 실패/retry 검증

- 일시: 2026-09-29 14:30 KST
- 관련 범위: D6 Langfuse
- 모델: `google/gemini-3.5-flash-lite`
- Prompt / Skill 표시: `coaching-output-v3` / `interview-coach-v5`

## 1. 목적

합성 fixture를 넘어 실제 로그인 사용자 흐름에서 코칭 요청이 Langfuse에 연결되는지 확인하고, 성공·실패·retry·출력 검증·비용/토큰 메타데이터를 함께 검증한다. Prompt 내용 품질 평가는 이 작업 범위에 포함하지 않는다.

## 2. 실행 경로

로컬 전체 스택에서 다음 흐름을 사용했다.

```text
Frontend :18080
-> 로그인 사용자 연습 조건/공고/질문 선택
-> WAV 업로드
-> STT 및 전사 확인
-> POST /api/agent
-> MCP-backed coaching service
-> OpenRouter provider
-> output validation
-> coaching_runs persistence
-> Langfuse trace
```

음성 입력은 기존 STT 실사용 평가 녹음 중 일반 면접 구간 파일을 WAV로 변환해 사용했다. 원본 음성·전사 원문은 Worklog와 Langfuse에 기록하지 않는다.

## 3. controlled provider failure / retry

코칭 provider만 연결 불가능한 로컬 endpoint로 덮어쓰고, 공고 요구사항 분석 provider는 정상 OpenRouter 설정으로 유지했다. 이 상태에서 사용자 흐름을 코칭 단계까지 진행했다.

Trace:

```text
edeb73e5d1424c9fa877c00509ef9473
```

관측 결과:

| observation | 결과 |
| --- | --- |
| `coaching.provider` attempt 1 | `ERROR`, `outcome=network_error`, `transport_attempt=1`, `will_retry=true`, `retry_reason=network_error` |
| `coaching.provider` attempt 2 | `ERROR`, `outcome=network_error`, `transport_attempt=2`, `will_retry=false` |
| `coaching.analyze` | `ERROR` |

따라서 실제 Langfuse Cloud에서 전송 실패 후 1회 retry와 최종 실패가 attempt 단위로 분리돼 기록되는 것을 확인했다.

## 4. validation 이후 persistence 실패 발견

실패 override를 제거한 뒤 실제 provider 호출은 성공했고 다음 메타데이터가 기록됐다.

```text
trace: e3a9b8c176584a0faae688aaf537dda6
input_tokens: 13197
output_tokens: 1261
cost_usd: 0.0071116
coaching.output_validation.valid: true
coaching.output_validation.error_count: 0
final failure_state: provider_error
```

출력 계약 검증이 성공했는데 최종 API가 503으로 끝나 저장 경로를 확인했다. 로컬 Supabase schema 조회 결과:

```text
status: 400
code: 42703
message: column coaching_runs.criteria_version does not exist
```

`supabase/migrations/20260928065116_coaching_run_criteria_version.sql`이 현재 코드가 요구하는 `criteria_version` 컬럼을 추가하므로, pending migration을 적용한 뒤 동일 사용자 흐름을 다시 실행했다.

이 과정에서 `CoachingRunPersistenceError`도 현재 API에서 `provider_error / COACHING_PROVIDER_UNAVAILABLE`로 정규화되어 실제 provider 장애처럼 보일 수 있음을 확인했다. 기능 완료를 막는 문제는 아니지만 운영 진단성을 위해 별도 failure code 분리를 검토할 수 있다.

## 5. 정상 성공 trace

migration 적용 후 같은 흐름이 정상 완료됐다.

```text
trace: 7f67f14ceb9040868bad4249903c79a8
model: google/gemini-3.5-flash-lite
total tokens: 14560
cost: about $0.007367
final status: needs_more_info
```

Langfuse Tree에서 같은 trace 아래 다음 observation을 확인했다.

```text
coaching.provider
coaching.output_validation
coaching.analyze
```

최종 `coaching.analyze`는 오류 없이 종료됐고, output validation도 유효한 결과로 완료됐다.

## 6. 이미지 증거 보관 원칙

UI 캡처는 확인에 유용하지만 trace ID와 구조화 metadata를 canonical 증거로 둔다. 저장소에 이미지를 추가할 경우 전체 브라우저 화면을 그대로 올리지 않고, trace tree와 필요한 metadata 영역만 crop한 뒤 사용자 ID·session ID·조직/프로젝트명 등 불필요한 식별 정보를 가린다.

권장 증거 3장은 다음과 같다.

1. retry attempt 1 — `network_error / will_retry=true / transport_attempt=1`
2. retry attempt 2 — `network_error / will_retry=false / transport_attempt=2`
3. 정상 성공 trace — provider / validation / analyze tree와 token·cost 표시

Raw Prompt, 사용자 답변, 전사 원문, access token, secret key는 이미지와 문서 모두에 남기지 않는다.

## 7. D6 판단

- 실제 provider 포함 인증 사용자 trace: 완료
- model / token / cost: 완료
- provider Duration: 기존 live provider fixture 검증 근거 유지
- retry metadata: 완료
- 실패 요청 trace: 완료
- output validation trace: 완료
- managed Prompt production 연결: 미완료, Prompt 담당 작업으로 유지

## 8. 다음 작업

- Prompt 담당자가 managed Prompt production 연결을 완료하면 canonical Prompt version 항목을 최종 확인한다.
- `CoachingRunPersistenceError`를 provider 장애와 구분할 별도 API failure code/state가 필요한지 후속 검토한다.
