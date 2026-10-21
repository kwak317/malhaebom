# Worklog — GPT-5 mini OpenRouter smoke 측정

- 일시: 2026-09-18 17:42
- 작업자/에이전트: Codex
- 관련 이슈/PR: PR 생성 전
- 관련 요구사항/결정: `docs/specs/coaching-evaluation-ops.md` AC-08, `docs/REQUIREMENTS.md` 모델 비교와 structured output 계약 준수율

## 1. 목적

OpenRouter의 `openai/gpt-5-mini`를 고정 30건 평가셋에 1회 실행해 API 연결, strict JSON Schema 계약, 지연과 비용을 smoke 수준에서 측정한다.

## 2. 작업 전 상태

- LM Studio EEVE Q4 실행은 JSON Schema grammar 엔진 오류로 provider 오류 30건이 발생했다.
- OpenAI 직접 API 실행은 OpenRouter 키와 OpenAI endpoint의 조합으로 401이 발생했고, 이후 OpenAI API 크레딧 부족으로 429가 발생했다.
- 따라서 OpenRouter key와 `https://openrouter.ai/api/v1` endpoint, `openai/gpt-5-mini` 모델 ID를 사용했다.

## 3. 수행 내용

- `evals/run_model_comparison.py`를 `expected=mock:expected`와 `gpt-5-mini=openai:openai/gpt-5-mini` 후보로 실행했다.
- 30건 × 1회, timeout 180초, 입력/출력 가격 $0.25/$2.00 per 1M tokens로 실행했다.
- 생성 결과는 Git 제외 경로 `local-results/gpt-5-mini-openrouter-check/`에 저장했고, 측정값과 실패 원인을 `EVAL_REPORT.md`에 기록했다.

## 주요 판단과 이유

실패는 provider 오류가 아니라 원시 JSON의 끝나지 않은 문자열에 따른 `schema_violation`이었다. 계약 준수율 10%와 p95 57.632초는 모델 선정 또는 반복 측정 단계로 진행하기에 부적합하므로 이 설정을 DISCARD로 기록한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `EVAL_REPORT.md` | GPT-5 mini OpenRouter 1회 실측 결과와 DISCARD 판단 기록 |
| `docs/worklogs/2026-09-18_1742_gpt5-mini-openrouter-smoke.md` | 실행 조건·결과·실패 원인 기록 |

## 5. 검증

```text
local-results/gpt-5-mini-openrouter-check/comparison.md
expected: 계약 100.0%, 정확도 100.0%
gpt-5-mini: 계약 10.0%, 정확도 8.7%, 비용 $0.014397,
p50 20.081초, p95 57.632초, schema_violation 27건
```

## 6. 발견한 문제 / 남은 리스크

- 모델 출력이 JSON Schema 요청에도 완결된 JSON으로 반환되지 않은 27건이 있었다.
- 이 30건은 합성 평가셋이므로 실제 사용자 음성 기반 품질을 뜻하지 않는다.

## 미확인 사항

- 100건 고유 입력 계약 평가와 4회 반복 비교는 수행하지 않았다.
- GPT-5 mini의 생성 상한, 프롬프트 길이, provider routing을 단일 변수로 조정한 재실험은 아직 수행하지 않았다.

## 7. 다음 작업

- OpenRouter 또는 로컬 모델 후보의 출력 상한·계약 안정화 방식을 한 번에 하나씩 바꿔 재측정한다.
- 프런트 음성 업로드 경로에서 GPT/Gemini를 비교하려면 기존 Ollama 전용 feedback provider를 OpenAI-compatible provider로 확장하는 별도 Spec과 구현이 필요하다.
