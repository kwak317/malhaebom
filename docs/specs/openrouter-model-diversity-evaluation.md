# OpenRouter 모델 다양성 평가

## Why

기존 평가는 6개 고정 모델과 실패 복구 후보 비교에 초점이 있어, 수업용 OpenRouter 키로 실제 접근 가능한 서로 다른 개발사·모델 계열의 범위를 보여주지 못한다. 같은 코칭 계약에서 폭넓은 모델의 접근성, 구조화 출력 준수, 비용과 지연을 측정해야 모델 몇 개의 순위가 아닌 생태계 전반의 호환성을 설명할 수 있다.

측정 지표는 발견 후보 수, 실제 preflight 수, PASS 수, 30건 완료 수, 개발사별 분포, 계약 위반·접근 제한·timeout·API 오류 수, token·비용·p50·p95다.

## Goal

- OpenRouter의 현재 키 기준 모델 목록에서 text 입력과 text 출력을 지원하고 `response_format`을 광고하는 후보를 재현 가능한 규칙으로 추린다.
- OpenAI, Anthropic, Google, Meta, Qwen, DeepSeek, Mistral, Cohere, xAI, Microsoft, NVIDIA 및 기타 접근 가능한 계열을 가능한 한 다양하게 포함한다.
- 후보마다 대표 사례 1~3건의 preflight를 실행하고 정해진 실패 분류를 남긴다.
- 모든 preflight PASS 후보에 동일한 고정 30건 평가를 실행한다.
- 기존 `dataset.v2.jsonl`, Skill bundle, system prompt, strict JSON Schema, provider routing과 grader를 재사용한다.
- JSON, CSV, Markdown 결과와 중단 후 재개 가능한 호출별 원본 기록을 생성한다.

Out of Scope:

- 최고 모델 하나를 선정하거나 운영 모델 정책을 변경하지 않는다.
- dataset, Skill, schema, grader의 판정 정책을 바꾸지 않는다.
- embedding/image/audio 전용 모델을 평가하지 않는다.
- STT/TTS 코드·데이터·실험을 수정하지 않는다.
- 자동 사람 semantic 점수를 생성하지 않는다. 기존 사람 검토가 연결되지 않은 출력은 `null`로 둔다.

## What

Happy Path:

1. 인증된 모델 목록을 조회하고 원본 메타데이터의 안전한 부분만 저장한다.
2. modality, structured output 지원, alias 중복, 개발사 다양성과 가격을 기준으로 후보를 선택한다.
3. 소수 smoke 모델을 먼저 호출한다.
4. 전체 후보에 대표 3건을 순차/제한 병렬로 preflight한다.
5. 세 사례가 모두 계약을 통과한 모델만 30건을 평가한다.
6. 모델·개발사·실제 routed provider, token, 비용, 지연, 실패 분류를 집계한다.

Edge Cases:

- 목록에 있으나 현재 키·privacy/ZDR·provider 정책으로 호출할 수 없는 모델은 삭제하지 않고 `POLICY_RESTRICTED` 또는 `MODEL_UNAVAILABLE`로 남긴다.
- 401/402/403, 404, 408/timeout, 429, 5xx와 schema/validator 위반을 구분한다.
- 한 모델 또는 한 사례의 실패가 다음 모델 실행을 막지 않는다.
- 중단 후 이미 저장된 호출은 다시 결제하지 않고 재사용한다.
- 비용이 누락되면 0으로 추정하지 않고 `unknown`으로 집계한다.

## How

- `evals/run_openrouter_diversity.py`를 orchestration 진입점으로 추가한다.
- `.env`는 기존 `evals.environment`로만 읽고 key 값은 출력·직렬화하지 않는다.
- OpenRouter `GET /models/user`를 우선 사용하고 미지원일 때 인증된 `GET /models`로 fallback한다.
- 후보는 text→text, `response_format` 지원, 비 alias/router, 만료되지 않은 모델로 제한한다. 개발사는 model id 첫 segment를 canonical developer로 기록하고 실제 응답 provider를 별도 기록한다.
- 선택 규칙과 가격 상한은 CLI 인자로 기록하며, 기본적으로 개발사별 가격대·계열이 겹치지 않는 소수 후보를 선택한다. 명시적 `--model`로 추가할 수 있다.
- 기존 `OpenAICompatibleRunner`, `run_comparison`, validation/grader를 재사용한다.
- 요청 조건은 `evaluation_records.REQUEST_SETTINGS`와 동일하며 SDK retry는 0이다. orchestration은 429/408/5xx에만 제한적 exponential backoff를 적용한다.
- preflight는 normal/boundary/failure 대표 3건이며 모든 사례의 Pydantic·서버 validator 통과를 PASS 조건으로 한다.
- 본평가는 PASS 모델별 30건이고 호출별 JSON을 atomic write한다.
- 결과 위치는 `local-results/openrouter-diversity-<timestamp>/`이며 `manifest.json`, `discovery.json`, `preflight/`, `full/`, `summary.json`, `summary.csv`, `SUMMARY.md`를 생성한다.

## AC

- Given `.env`에 유효한 OpenRouter key가 있을 때, when discovery를 실행하면, then key를 포함하지 않은 후보 목록과 개발사·가격·지원 파라미터가 저장된다.
- Given text→text가 아니거나 `response_format`을 지원하지 않는 모델이 있을 때, when 후보를 필터링하면, then 제외 사유가 discovery 결과에 남고 preflight 대상이 되지 않는다.
- Given 후보 호출이 schema 또는 서버 validator를 위반할 때, when preflight를 집계하면, then `CONTRACT_VIOLATION`으로 분류되고 30건 평가를 실행하지 않는다.
- Given 403/404/timeout/429/5xx가 발생할 때, when 실행을 계속하면, then 정책 제한/모델 불가/timeout/API 오류로 분류되고 다른 모델은 계속 실행된다.
- Given preflight 3건이 모두 통과한 모델일 때, when full 단계를 실행하면, then 같은 dataset·prompt·Skill·schema 설정으로 30건 결과가 저장된다.
- Given 실행이 중단된 뒤 같은 output directory로 재실행할 때, when 이미 저장된 호출이 있으면, then 해당 호출을 재사용하고 중복 호출하지 않는다.
- Given 실행 결과가 완성됐을 때, when report를 생성하면, then 탈락 모델을 포함한 JSON/CSV/Markdown에 모델 id, developer, provider, preflight, 본평가 여부, 성공/전체, 계약 위반, semantic, p50/p95, token, 비용, 실패 이유가 포함된다.
