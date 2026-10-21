# 코칭 평가·관측·Frontend·E2E Spec

## Why

- 모델 선정 전에 평가 기준과 실패 경계를 고정하지 않으면 후보마다 유리한 예제로 비교하게 된다.
- API Mock이 있어도 사용자가 보는 판정·근거·부족 항목·확인 질문·다음 행동까지 연결하지 않으면 출력 계약의 사용성을 확인할 수 없다.
- trace에 답변·채용공고·token을 그대로 남기면 디버깅 편의 때문에 개인정보 경계가 무너진다.
- 단위 테스트만으로는 Nginx proxy, 컨테이너 환경 변수, FastAPI 인증, Mock과 MCP 도구가 함께 동작하는지 확인할 수 없다.

## Goal

1. 합성 평가셋 30건에 정상·경계·실패 유도 사례와 기대 판정·근거·실패 이유를 기록한다.
2. `/demo/coaching`에서 API Mock의 판정, 근거, 부족 항목, 확인 질문과 다음 행동을 표시한다.
3. Langfuse trace 이름, 버전, 지연·비용·실패 필드와 개인정보 제외 규칙을 코드 계약으로 고정한다.
4. 스키마 위반·인증·timeout·rate limit을 공통 실패 상태로 변환한다.
5. Compose에서 frontend → Nginx proxy → FastAPI Mock → Pydantic 응답과 MCP 세 도구를 재현한다.
6. 같은 평가셋을 후보 모델에 실행해 계약 준수율·정확도·비용·p50·p95를 비교한다.

## What

### 평가셋

| 구분 | 건수 | 포함 사례 |
|---|---:|---|
| 정상 | 12 | 인증, 성능, 배포, CI, 모니터링 등 문제 해결 답변 |
| 경계 | 10 | 추상적 답변, 팀 행동, 기준 없는 수치, 역할·관련성 모호함 |
| 실패 유도 | 8 | 지시문 삽입, 허위 근거, 개인정보, 타인 기록, 합격 보장 |

모든 문장은 합성이며 실제 사용자·회사·채용공고를 사용하지 않는다. 기대 evidence의 `quote`는 지정한 `segment_id` 문장에 정확히 존재해야 한다.

### 공통 실패 계약

| 상태 | HTTP | 의미 | 재시도 |
|---|---:|---|---|
| `schema_violation` | 422/502 | 요청 또는 모델 출력 계약 위반 | 요청 422는 아니오, 출력 502는 예 |
| `auth_error` | 401 | 인증 없음·만료·검증 실패 | 아니오, 재로그인 |
| `timeout` | 504 | 모델·도구 제한 시간 초과 | 예 |
| `rate_limited` | 429 | provider 요청 제한 | 예, `Retry-After` 우선 |
| `context_error` | 404/409 | 문맥 없음·소유자/만료 은닉·세션 불일치 | 아니오 |

응답 형식은 `{"detail":{"state","code","message","retryable"}}`다. 프런트의 네트워크 실패는 같은 client 모델의 `provider_error`로 변환한다.

### Langfuse 관측 계약

- trace 이름: `coaching.analyze`
- 버전: `COACHING_PROMPT_VERSION`, `COACHING_SKILL_VERSION`
- 성능: `latency_ms`, `input_tokens`, `output_tokens`, `cost_usd`
- 결과: `status`, `failure_state`, `criterion_count`, `gap_count`, `model`
- 식별자: `COACHING_OBSERVATION_SALT`가 16자 이상일 때만 사용자·연습 ID의 HMAC 앞 24자를 기록
- 금지: Authorization/token, 답변·전사, evidence quote, 공고 원문·URL, raw model input/output
- 관측 전송 실패는 사용자 API 결과를 바꾸지 않는다.

### 모델 비교

- 모든 후보에 같은 30건, 같은 Skill, 같은 prompt version을 적용한다. 6종 평가 기반은 운영과 같은 strict JSON Schema 및 `provider.require_parameters: true`를 사용하며 temperature와 reasoning은 보내지 않는다.
- v1 규칙 기반 정확도는 status·의도·공고·기준 판정·필수 근거 일치율이며, v2는 requirement text 없는 공고 판정/status/job evidence를 제외한다.
- 출력 계약 위반은 해당 실행 정확도 0점이며 별도 실패 건수로 집계한다.
- 비용은 `usage.cost`를 우선하며 누락은 미확인으로 보존한다. parse/validator 실패와 명시적 재시도의 호출 기록도 보존한다. SDK 자동 재시도는 끈다.
- 실제 모델과 키가 없을 때 `mock:expected`, `mock:degraded`로 runner·채점·리포트 생성만 검증한다.
- 결과에는 prompt·Skill·criteria 버전과 실행에 사용한 Skill 묶음 SHA-256을 기록한다.
- basic 3종/premium 3종 config, raw output, 단계별 검증, generation/provider/usage, case/run/호출 ID와 basic 부모 실행 참조를 로컬 결과에 저장한다. Premium 자동 실행은 범위 밖이다.
- label/evidence/ID 지표와 label 반복 일치율을 분리한다. v2 의미 품질·환각은 annotation과 사람 검토로 채점한다. Premium 자동 복구 실행은 범위 밖이다.

### 전용 평가 환경

프로젝트 로컬 `.venv-llm-eval`은 Python 3.12로 생성하고 평가 전용 requirements만 설치한다.
`evals/setup_env.sh`는 반복 실행 시 버전을 검사하고 import/help/mock smoke를 수행한다.
runner는 프로젝트 루트 .env를 override=False로 읽고 OpenRouter에서는 OPENROUTER_API_KEY만 사용한다.
MODEL_API_KEY 우선순위는 사용자 지정 타 제공자 endpoint에서 유지한다. six-models는 OpenRouter endpoint만 허용한다.
설치 및 mock 점검은 실제 LLM 요청을 보내지 않는다. 키 값은 출력하지 않는다.

## How

### 화면

`/demo/coaching`은 로그인 session 또는 E2E 전용 token으로 `/api/agent`를 호출한다. 전용 token은 `docker-compose.e2e.yml`에서만 build/runtime에 주며 운영 기본값은 빈 값이다.

### Compose 검증

```bash
docker compose -f docker-compose.yml -f docker-compose.e2e.yml \
  up --build --abort-on-container-exit --exit-code-from coaching-e2e coaching-e2e
```

E2E 컨테이너는 화면 경로의 SPA root, frontend Nginx를 통한 API 응답, Pydantic `CoachingResponse`, 내부 token으로 제한한 MCP 세 도구를 차례로 검사한다.

### 후보 모델 비교

실행법과 가격 입력은 [`evals/README.md`](../../evals/README.md)를 따른다. 생성되는 원시 비교 결과는 사용자 데이터와 분리된 `local-results/`에 두며 Git에 커밋하지 않는다.

### 평가 v2 정책

v2는 정보 부재/not_observed, 관련 정보 부족/partial, 상충·모호함/undetermined를 구분한다.
V는 테스트·확인 행위만 있으면 partial, 방법·조건과 실제 관찰 결과가 있으면 met이다.
intent는 질문 적합성만 평가하며 C/A/V 완성도와 독립이다. requirement text가 없으므로
job alignment와 그 영향을 받는 status는 고정 정확도에서 제외한다. R/D는 추가하지 않는다.
15건 annotation은 사용자 승인 수정안이며 독립 검토 완료를 뜻하지 않는다.
semantic은 사람 검토 입력으로 채점하고 critical failure는 별도 지표로 집계한다.

C는 문제 대상과 문제로 인식한 상태가 식별되고 증상·발생 조건·영향·비교 상태 중 하나 이상이 연결되어 어떤 문제였는지 이해할 수 있을 때 met이다. 오류·느림·문제 자체만 언급되고 대상이나 발생 상황이 충분히 드러나지 않으면 partial, 문제 상황 자체를 확인할 수 없으면 not_observed다. 원인 규명·개인 행동·검증 결과·질문의 직무 적합성은 C 판정에서 제외한다.

### 252건 offline 재채점 정렬

- evidence는 assessment를 뒷받침하는 원문 근거이며 not_observed에서도 미확인·부재·팀only 원문을 허용한다. 없는 근거를 요구하지 않는다.
- v2 evidence는 기준별 support_segment_ids와 실제 연속 부분 인용 일치로 채점한다. required=false 근거는 선택적이다. 다른 기준의 문장을 인용하거나 원문 불일치인 경우 통과시키지 않는다. 이는 의미적 타당성 점수가 아니다.
- 기존30건 label은 승인된 독립 정책으로 다시 검증하고 모델 출력의 다수결로 변경하지 않는다. 비백엔드 경험의 C/A/V도 intent와 별도로 내용 구조를 판정하며 입력이 경험 아닌 지시문이면 경험 정보로 사용하지 않는다.
- 기존252건 raw 문자열을 다시 parse/schema/validator/grader 처리하고 원본은 보존한다. 인프라 실패 제외 정책·자동critical 검사 범위는 유지한다. 부모 Basic 재채점 성공 여부와 무관하게 이미 수행한 Premium 모집단은54실패 실행을 유지하고 현재도 실패하는 부모 모집단의 복구율을 별도로 제공한다.
- 새 grader/schema/dataset/Skill hash 및 원래 generation 설정을 함께 기록한다. 새 Skill을 사용한 추론으로 오인하지 않는다. semantic 및 사람critical은 null이다. 네트워크/credential 로딩을 수행하지 않는 offline CLI로 재현한다.

## AC

- **AC-16**: Given not_observed와 실제 미확인 인용, When 검증, Then evidence를 허용하고 원문/ID/needed 검사는 유지한다.
- **AC-17**: Given v2의 정답 지원segment 부분인용, When 채점, Then 정답 quote 전체일치 없이 통과하며 다른segment/가짜quote는 실패한다. v1 exact-match는 유지한다.
- **AC-18**: Given 저장된 raw 실패/정상/인프라 기록, When offline 재채점, Then 전부 보존하고 원본 hash 불변·현재 부모 연결·전후 비교·공통실패를 기록한다. 추가 API호출 없음.

- **AC-14**: Given Python 3.12, When setup 반복 실행, Then 로컬 전용 venv와 평가 의존성을 설치하고 import/CLI/mock 검사에 통과한다.
- **AC-15**: Given .env와 충돌하는 MODEL_API_KEY, When OpenRouter 키를 선택, Then OPENROUTER_API_KEY만 선택하고 값은 출력하지 않는다.


- **AC-11**: Given 기존 dataset v1, When v2를 로드, Then v1 원본을 보존하고 재검토 30건 및 semantic annotation 15건을 제공한다.
- **AC-12**: Given v2 응답, When 채점, Then intent는 질문 적합성만 평가하고 job alignment/status 및 job evidence는 고정 정확도에서 제외한다.
- **AC-13**: Given annotation과 사람 검토 점수, When 집계, Then 네 semantic 0~2 점수와 critical failure를 별도로 집계하고 미검토는 null로 보존한다.

- **AC-09**: Given fake OpenRouter 응답, When JSON parse 또는 validator 실패 후 재시도, Then 모든 호출의 usage/cost와 원문이 남고 요청에 strict schema/routing만 명시된다.
- **AC-10**: Given 반복 mock 실행, When 보고서 생성, Then 세부 점수·반복 일치율·dataset/grader/model/config 버전 및 부모 참조 필드가 보존된다.

- **AC-01**: 평가셋 loader가 30건과 12/10/8 분포, 고유 ID, 기대 ID 일치를 검증한다.
- **AC-02**: 기대 fixture 30건이 모두 현재 Pydantic·서버 evidence 검증을 통과한다.
- **AC-03**: 화면이 판정·근거·부족 항목·확인 질문·다음 행동을 표시한다.
- **AC-04**: schema/auth/timeout/rate limit이 공통 실패 body와 올바른 HTTP 상태가 된다.
- **AC-05**: 관측 metadata에 버전·지연·비용·실패가 있고 금지 필드는 없다.
- **AC-06**: Compose E2E가 frontend proxy, Mock 검증 응답과 MCP 세 도구를 통과한다.
- **AC-07**: offline runner가 기준 후보 100%와 계약을 깨는 후보의 회귀를 구분한다.
- **AC-08**: 실제 모델 runner가 후보별 계약 준수율·정확도·비용·p50·p95·실패 건수와 Skill 묶음 버전·해시를 JSON/Markdown으로 남긴다.
