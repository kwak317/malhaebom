# 최종 두 후보 서비스 경로 통합 테스트

## 목적

Final Four에서 좁힌 Gemini 3.5 Flash-Lite와 GPT-5.6 Luna를 기존 평가 runner가 아니라
현재 FastAPI 코칭 서비스 경로에 연결해 계약, validator, 지연, 비용, retry/repair 동작을 비교한다.

## 기준점과 범위

- 브랜치 기준: `origin/main` `f37a4b9` (PR #39 서비스 hardening과 PR #40~41 평가 근거 포함)
- 작업 브랜치: `test/final-candidate-service-integration`
- 모델: `google/gemini-3.5-flash-lite`, `openai/gpt-5.6-luna`
- 경로: `/api/agent` → `McpLlmCoachingService` → `OpenAICompatibleJsonProvider` →
  `CoachingLLMOutput`/서버 참조 validator
- 입력: `dataset.v2.jsonl`의 정상·경계·실패 유도 각 1건
- 제외: 운영 Supabase 저장, 실제 사용자 데이터, 음성/STT/TTS, 배포 환경

## 실행 설정과 호출 상한

| 항목 | 값 |
|---|---|
| 사용자 요청 | 모델 2 × 사례 3 = 6 |
| temperature | model default (요청에서 생략) |
| strict schema | 사용 |
| OpenRouter routing | `provider.require_parameters=true` |
| timeout | 요청당 25초 |
| 전송 시도 | 최대 2회 |
| 계약 보정 | 최대 2회 |
| 요청 비용 상한 | `$0.10` |
| 결과 위치 | `local-results/service-candidate-integration-20260921/` (Git 제외) |

최초 통합 실행에서 서비스 provider가 `temperature=0`을 강제한 차이가 두 후보의 OpenRouter
`supported_parameters`와 충돌함을 확인했다. 서비스도 Final Four와 같이 model-default가 되도록
temperature를 생략한다.

## 재현

```bash
.venv-llm-eval/bin/pip install -r backend/requirements-service-integration.txt
.venv-llm-eval/bin/python -B -m unittest backend.tests.test_service_candidate_integration
.venv-llm-eval/bin/python -B evals/run_service_candidate_integration.py

# 합성 평가 입력의 OpenRouter 전송과 유료 호출을 명시적으로 승인한 뒤에만 실행
.venv-llm-eval/bin/python -B evals/run_service_candidate_integration.py --live \
  --output-dir local-results/service-candidate-integration-20260921
```

## 통합 검증 결과

### 1. 1차 독립 하네스 smoke (2026-09-21 16:18, Run 1)
- **환경**: `.venv-llm-eval` 환경에서 `evals/run_service_candidate_integration.py` 실행 (FastAPI 서비스 하네스 + OpenRouter 직접 호출).
- 최초 6건은 `temperature=0`과 `require_parameters=true` 설정 불일치로 HTTP 404 실패 (비용 $0).
- 서비스가 temperature를 생략(model-default)하고 GPT-5 strict schema를 보강한 후 재실행 결과:

| 모델 | HTTP / 계약 / validator | p50 / p95 | Input / Output token | 알려진 비용 | 판정 / evidence |
|---|---:|---:|---:|---:|---:|
| Gemini 3.5 Flash-Lite | 3/3 · 3/3 · 3/3 | 3.37s / 3.40s | 20,764 / 2,058 | $0.01137420 | 11/12 · 4/5 |
| GPT-5.6 Luna | 3/3 · 3/3 · 3/3 | 13.41s / 14.14s | 19,188 / 3,290 | $0.00602871 | 10/12 · 7/7 |

### 2. 2차 Docker + 로컬 Supabase E2E 실측 (2026-09-21 23:15, Run 2)
- **환경**: PR #42 반영 후 Docker 전체 스택(Frontend :18080, Backend :8000) + 로컬 Supabase(127.0.0.1:54321) + stdio MCP context + live DB(`coaching_runs`) 저장 경로.
- **실행 결과**:
  - `google/gemini-3.5-flash-lite`: 3/3 통과 (HTTP 200, Validator 통과, p50 3.44s, p95 3.58s [표본 3건 기준], 비용 $0.01132, retry 0회). 날조 유도 케이스도 안전하게 방어.
  - `openai/gpt-5.6-luna`: 초기 실행 시 markdown code fence 및 스키마 위반으로 1/3 (502 2건) → 보수적 code fence unwrap(`_normalize_json_envelope`) 적용 후 선별 재검증에서 `coach-boundary-13`은 200 OK 복구(지연 10.51s, $0.00275), `coach-failure-30`(날조 유도)은 스키마 필드 누락으로 502 유지되어 최종 2/3.

## 결론 및 기본 모델 선정

- **기본 프로덕션 후보 모델**: `google/gemini-3.5-flash-lite` (`COACHING_LLM_MODEL=google/gemini-3.5-flash-lite`)
- **선정 근거**:
  1. 독립 하네스(Run 1) 및 Docker 전체 E2E(Run 2) 모두 3/3 100% 무재시도 통과.
  2. 지연시간 p50 ~3.4초로 Luna(~10.5~13.4초) 대비 3~4배 빠름.
  3. 날조 유도 프롬프트에서도 스키마 붕괴 없이 안전하게 거부.
- **Luna 평가**: 비용 효율은 우수하나 adversarial/failure 프롬프트에서 스키마 이탈(502) 위험이 확인되어 단독 기본 모델로는 부적합하며, 추가 파서 보정 검토 전까지 보조/fallback 후보로만 관리한다.

## 알려진 한계

- 고정 평가셋에는 공고 요구사항 원문이 없어 통합 하네스는 모든 requirement ID에 동일한 검토 완료 백엔드 문제 해결 역할 문구를 사용한다.
- 3건은 대표 smoke이며 Final Four 30건의 품질 순위나 사람 semantic 평가를 대체하지 않는다.
- p95는 모델별 표본 3건의 최댓값이라 분포 추정력이 낮다.

