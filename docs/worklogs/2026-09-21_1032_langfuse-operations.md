# Worklog — Langfuse Prompt·Dataset·Trace 운영 연결

- 일시: 2026-09-21 10:32 KST
- 작업자/에이전트: Codex
- 브랜치: `feat/llm-mcp-langfuse-hardening`
- 관련 Spec: `docs/specs/langfuse-operations.md`

## 1. 목적

Langfuse Japan Cloud 자격 증명을 검증하고, candidate Prompt와 합성 평가셋 30건을 등록하며, redacted trace가 Prompt version과 연결되는지 실제 Observations API v2에서 확인한다.

## 2. 작업 전 상태

- 키 인증은 가능했지만 SDK가 `langfuse 2.60.10`이었다.
- Prompt Management 게시와 Langfuse Dataset 등록은 없었다.
- 호출 단위 계측 코드는 있었지만 실제 Cloud 수신은 검증되지 않았다.
- 신규 조직에서 legacy `GET /api/public/traces/{id}`는 `410 LEGACY_API_UNAVAILABLE_FOR_NEW_ORGANIZATION`을 반환했다.

## 3. 수행 내용

1. `langfuse>=4.7,<5`로 전환하고 trace/span/generation 호출을 OpenTelemetry `start_observation()` 방식으로 변경했다.
2. generation에 Langfuse Prompt 객체를 전달해 Prompt 이름과 불변 version을 연결했다.
3. 앱 시작 시 설정된 Prompt label을 읽고 실패 시 로컬 고정 Prompt로 fallback하도록 했다.
4. `evals/sync_langfuse_assets.py`를 추가해 Prompt와 Dataset 30건을 재실행 가능하게 등록했다.
5. clean Docker build가 참조 requirements 파일을 복사하지 않던 문제를 최소 수정했다.

## 4. 실제 Langfuse 결과

- 인증: 성공
- Prompt: `malhaebom-coaching`, 원격 version `1`, labels `candidate`, `latest`
- Dataset: `malhaebom-coaching-eval-v2`, item `30`, 모두 `synthetic=true`
- 확인 trace: `0beed10a3cd84060abec9d0af2b92df6`
- observation: `coaching.analyze`, `coaching.provider`, `coaching.output_validation`
- generation Prompt 연결: `malhaebom-coaching@1`

Prompt는 평가 전이므로 `production`으로 승격하지 않았다.

## 5. 검증

```text
관련 테스트: 23 tests, OK
전체 backend 테스트: 248 tests, OK
Langfuse auth_check: OK
원격 Prompt 재조회: version 1, candidate/latest
원격 Dataset 재조회: 30 items, all synthetic
Observations API v2: 3 observations, prompt_linked=true
```

## 6. 남은 작업

- 동일 Dataset으로 baseline과 candidate 실제 모델 평가를 실행하고 품질축·회귀 문항을 비교한다.
- release gate 통과 후에만 `production` label을 candidate version으로 이동한다.
- 이전 검증 version으로 label을 되돌리는 rollback 시연과 화면 증적을 남긴다.
- 실제 provider 요청 trace의 token·cost·latency·retry를 확인한다.
