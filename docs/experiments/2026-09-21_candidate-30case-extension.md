# 후보 모델 30건 확장 평가

- 일시: 2026-09-21 KST
- 목적: 사전 점검만 수행한 Qwen3 4B, EEVE Korean 2.8B Q4, GPT-5 nano, Gemini 3.5 Flash를 고정 합성 30건에서 추가 측정한다.
- 코드 기준: `experiment/model-eval-harness`의 `516fe02` 이후 작업 트리. 결과 원본은 Git 제외 `local-results/`에 둔다.

## 데이터·공통 평가

- 데이터: `evals/dataset.jsonl`, 합성 30건(정상 12 / 경계 10 / 실패 유도 8).
- 평가: `evals/run_model_comparison.py`의 Pydantic·허용 ID·인용 원문 검증과 규칙 기반 정확도.
- 고정 Skill: `interview-coach-v1`, criteria `problem-solving-v4-draft.1`, prompt `coaching-output-v1`, temperature 0, 반복 1회.
- 한계: 합성 입력·1회 실행·규칙 기반 채점이므로 운영 품질 또는 사람 코칭 품질을 확정하지 않는다. 계약 위반 응답 비용이 0으로 집계되는 알려진 문제는 Issue #22를 따른다.

## 후보별 실행 조건

| 후보 | provider / model | 출력 상한 | timeout | 이유 |
|---|---|---:|---:|---|
| Qwen3 4B | Ollama / `qwen3:4b` | 768 | 45초 | 로컬 사전 점검 조건과 동일 |
| EEVE Korean 2.8B Q4 | Ollama / `bnksys/eeve:2.8b-korean-instruct-q4_k_m-v1` | 768 | 45초 | 로컬 사전 점검 조건과 동일 |
| GPT-5 nano | OpenRouter / `openai/gpt-5-nano` | 4096 | 60초 | API 후보 조건과 동일 |
| Gemini 3.5 Flash | OpenRouter / `google/gemini-3.5-flash` | 4096 | 60초 | API 후보 조건과 동일 |

로컬 모델은 2K 문맥 제약 때문에 API 모델과 출력 상한·timeout이 다르다. 따라서 속도·비용은 절대 비교하지 않고, 각 모델이 같은 서버 계약을 지키는지에 집중한다.

## 재현 명령

```powershell
# 로컬 후보
$env:MODEL_API_KEY = "ollama-local"
$env:MODEL_API_BASE_URL = "http://127.0.0.1:11434/v1"
python evals/run_model_comparison.py `
  --candidate qwen3-4b=ollama:qwen3:4b `
  --candidate eeve-korean-2-8b-q4=ollama:bnksys/eeve:2.8b-korean-instruct-q4_k_m-v1 `
  --candidate baseline=mock:expected `
  --repeats 1 --max-completion-tokens 768 --timeout-seconds 45 `
  --output-dir local-results/local-candidate-30cases-20260921

# API 후보
python -m dotenv -f .env run -- python evals/run_model_comparison.py `
  --candidate gpt-5-nano=openai:openai/gpt-5-nano `
  --candidate gemini-3-5-flash=openai:google/gemini-3.5-flash `
  --candidate baseline=mock:expected `
  --repeats 1 --max-completion-tokens 4096 --timeout-seconds 60 `
  --price gpt-5-nano=0.05,0.40 --price gemini-3-5-flash=1.50,9 `
  --output-dir local-results/api-candidate-30cases-20260921
```

## 결과

### API 후보

`local-results/api-candidate-30cases-20260921/`에서 확인한 결과다.

| 후보 | 계약 준수율 | 규칙 기반 정확도 | 기록 비용(USD) | p50 / p95 | 실패 |
|---|---:|---:|---:|---:|---|
| Gemini 3.5 Flash | 96.7% | 63.9% | $0.824244 | 12.48초 / 19.16초 | schema violation 1건 |
| GPT-5 nano | 16.7% | 13.7% | $0.002743 | 4.81초 / 6.99초 | schema violation 25건 |

Gemini 3.5 Flash는 Terra와 같은 계약 준수율을 기록했지만 p95 10초 운영 목표를 넘고 기록 비용도 높았다. GPT-5 nano는 계약 게이트에 미달했다. Issue #22에 따라 schema violation 요청의 비용이 0으로 기록되므로 비용은 하한값이다.

### 로컬 후보

Qwen3·EEVE 30건 명령은 45초 timeout을 줬지만 Ollama 요청이 timeout 이후에도 GPU에서 계속 실행돼 결과 파일을 만들지 못했다. 관련 Python 프로세스만 종료해 GPU 점유를 해제했고, 이 재현 문제는 Issue #32에 기록했다. 따라서 이 두 모델의 30건 수치는 없으며, 기존 1건 사전 점검 계약 위반 결과만 유효하다.
