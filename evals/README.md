# 코칭 평가셋과 결과 안내

## 현재 운영 기준과 보존 자료

| 구분 | 위치·기준 |
| --- | --- |
| 현재 소스 기본 Prompt | coaching-user-supplied-v4-verification — [builder](../backend/app/services/coaching_prompt.py) |
| 현재 코칭 Skill | interview-coach-v6 — [활성 Skill](../skills/interview-coach/SKILL.md) |
| 동기화 전 main 후보 | [후보 보관](candidates/README.md): v6.2 원본과 전문가 검토 이력. 활성 v6 검토 완료로 전용하지 않음 |
| 고정 합성 평가셋 | dataset.jsonl / dataset.v2.jsonl — 재현 기준과 해시는 각 실험 확인 |
| 제출·종합 해석 | [EVAL_REPORT](../EVAL_REPORT.md) · [제출 증거](../docs/SUBMISSION_EVIDENCE.md) |
| 날짜별 원본 결과 | [results 안내](results/README.md) |

아래 runner와 날짜별 실험은 당시 조건의 재현 자료입니다. 원본 JSONL·점수·기대값·Prompt/Skill 후보 파일을 정리 목적으로 수정하거나 삭제하지 않습니다. 자동 계약 통과, AI 점수, 사람 판단, 운영 사용자 E2E는 구분합니다. 원격 Langfuse 라벨·버전은 별도 확인 대상입니다.

## 기존 실험과 재현 절차

2026-10-01 당시 로컬 기본값은 v5/Skill v6.1이었다. 이 문단은 당시 실험의 재현 기록이며 현재 소스 기본값은 위 표를 따른다. 당시 Skill과 Prompt를 함께 사용해야 과거 실행을 재현할 수 있다.

아래 2026-10-02 실험에서는 `coaching-v5-skill-owned` 후보와 v4를 비교했다. 현재 소스 기본값은 위 운영 기준 표를 따른다. `coaching-output-v4.2` 등 이전 템플릿도 당시 실행 재현용으로 보존한다. `prompts/`의 출력 계약과 `skills/`의 도메인 규칙을 운영·평가의 동일 builder로 결합한다. 과거 전체 입력을 재현하려면 당시 Skill 파일·버전도 함께 복원해야 한다.

2026-10-02 동일 현재 Skill에서 영문 v4/v5를 각각 합성 30건 실호출했다. 최신 v5 계약 30/30, 종합 자동 통과 20/30(v4 22/30), 비용 $0.17027067, 응답 완료 p95 4.622초다. [실험](../docs/experiments/2026-10-02_latest-english-v5-comparison.md)과 `EVAL_REPORT.md` 4·6·7장에 회귀 및 미검증 출시 게이트를 기록했다. 재현 entrypoint는 `python evals/run_prompt_version_comparison.py --output-dir local-results/NEW-RUN`이며 실제 유료 provider를 호출한다.

`sync_langfuse_assets.py`는 현재 Skill 본문이 포함된 완성 Prompt 대신 `{{skill_text}}` 슬롯이 있는 템플릿을 동기화 대상으로 만든다. 런타임이 현재 Skill을 결합하며, 슬롯 없는 과거 원격 완성 Prompt는 로컬 템플릿으로 fallback한다. 실제 Cloud 게시·label 변경은 이 문서 변경만으로 실행되지 않는다.

`dataset.jsonl`은 모델 선정 전에 고정한 합성 코칭 평가셋 **30건**입니다. 실제 사용자 답변·채용공고·개인정보는 포함하지 않습니다. 정상 12건, 경계 10건, 실패 유도 8건을 같은 조건으로 모든 후보 모델에 실행합니다.

## 구성

| 종류 | 왜 필요한가 |
|---|---|
| 정상 12건 | 문제·본인 행동·결과 확인의 기본 판정 |
| 경계 10건 | 짧은 답변, 팀/본인 역할 혼동, 기준 없는 수치, 직무 관련성 부족 |
| 실패 유도 8건 | prompt injection, 허위 인용·성과, 개인정보, 타인 기록 조회 요구 |

**잘 되는 것만 모으면 평가가 아니라 자랑입니다.** 실패 사례를 반드시 넣으세요.

각 행은 다음을 기록합니다.

- 서버가 허용한 `requirement_id`, `criterion_id`, `segment_id`
- 기대 `status`, 의도 판정, 공고 관련성, 기준별 판정
- 답변 원문에 실제 존재해야 하는 기대 근거
- 사람이 그 판정을 기대한 이유
- 실패 유도 사례의 실패 이유

`backend/tests/test_coaching_eval.py`가 건수·분포·ID 일치와 기대 출력의 Pydantic/서버 참조 검증을 확인합니다.

## 모델 비교 runner

실제 모델을 정하기 전에는 외부 호출 없이 runner 자체를 재현할 수 있습니다.

### 동일 모델의 범용 AI vs 말해봄 비교

`generic_vs_malhaebom.py`는 같은 모델 ID와 동일한 질문·답변으로 범용 피드백과
말해봄 경로를 나란히 기록한다. 범용 조건은 질문·답변만 사용하며, 말해봄 조건은
고정 Skill·구조화 server context·strict JSON schema·서버 validator를 사용한다.
이는 Gemini 웹 UI의 숨겨진 지침까지 동일하게 재현하는 도구가 아니라, **말해봄이
추가한 설계가 출력에 미치는 차이**를 재현하는 발표 증거다.
말해봄 조건의 첫 structured output이 Pydantic 또는 서버 계약에 실패하면 운영 경로와
동일하게 같은 모델에 1회 repair 요청을 보낸다. 재시도 뒤에도 실패하면 원본 JSON과
실패 필드 경로를 리포트에 남긴다.

API 키 없이 먼저 리포트 형식을 확인한다.

```powershell
cd C:\Users\home\Desktop\proj2-3
.\.venv\Scripts\python.exe -m unittest backend.tests.test_generic_vs_malhaebom
.\.venv\Scripts\python.exe evals\generic_vs_malhaebom.py --mode mock --output-dir local-results\generic-vs-malhaebom-smoke
Get-Content local-results\generic-vs-malhaebom-smoke\comparison.md
```

실제 Flash-Lite 실행은 합성 평가 입력만 외부 provider에 전송한다. API 키를 리포트나
Git에 저장하지 않는다.

```powershell
$env:MODEL_API_KEY = "<provider-api-key>"
$env:MODEL_API_BASE_URL = "https://openrouter.ai/api/v1"
.\.venv\Scripts\python.exe evals\generic_vs_malhaebom.py `
  --mode live `
  --model google/gemini-3.5-flash-lite `
  --case-id coach-normal-01 `
  --case-id coach-boundary-14 `
  --case-id coach-failure-29 `
  --output-dir local-results\generic-vs-malhaebom-live
Get-Content local-results\generic-vs-malhaebom-live\comparison.md
```

범용 출력은 자유 형식이므로 기존 정답·계약 정확도로 점수화하지 않는다. 말해봄 출력의
계약 통과 여부만 기록하며, 자연스러움·설득력 판단은 사람 검토로 분리한다.

원인 관찰 신호와 추론 연결 기준까지 포함한 단일 발표 사례는 `presentation_cause_reasoning.jsonl`을
사용한다. 이것은 공식 30건 평가셋을 변경하지 않는 발표용 합성 사례다.

```powershell
.\.venv\Scripts\python.exe evals\generic_vs_malhaebom.py `
  --mode mock `
  --dataset evals\presentation_cause_reasoning.jsonl `
  --case-id presentation-cause-01 `
  --output-dir local-results\cause-split-smoke
```

실제 같은 모델의 두 조건을 비교할 때는 다음 명령을 사용한다. 말해봄 출력의
`cause_observation`, `cause_inference`가 각각 반환됐는지와 계약 검증 상태를 확인한다.

```powershell
.\.venv\Scripts\python.exe evals\generic_vs_malhaebom.py `
  --mode live `
  --model google/gemini-3.5-flash-lite `
  --max-completion-tokens 2048 `
  --dataset evals\presentation_cause_reasoning.jsonl `
  --case-id presentation-cause-01 `
  --output-dir local-results\cause-split-live
Get-Content local-results\cause-split-live\comparison.md
```

리포트의 `provider 종료 이유`가 `length`면 해당 호출이 출력 한도에서 끝난 것이다. `stop`인데도 말해봄 JSON이 잘렸다면 provider가 structured output을 올바르게 반환하지 않은 것이므로, `comparison.json`도 함께 공유해 원본 응답 형태를 확인한다.

2026-09-22부터 기본 생성 prompt는 `coaching-output-v4`이며 운영의 local fallback과
`run_model_comparison.py`가 `app.services.coaching_prompt`의 같은 canonical builder를
사용합니다. v4는 최종 JSON 출력 전에 ID 완전성, exact evidence, intent/C/A/V 분리,
미확인 결과, 팀/개인 역할, 신규 사실·숫자, 확인 질문·next action 개수, JSON-only를
내부 점검하도록 합니다. 평가 결과의 configuration에는 prompt 본문 대신
`prompt_sha256`을 남겨 같은 prompt 실행인지 확인합니다. 기존 v3 실험 결과와
전용 재현 스크립트의 버전 표기는 과거 측정 재현을 위해 그대로 유지합니다.

```bash
python evals/run_model_comparison.py \
  --candidate expected=mock:expected \
  --candidate degraded=mock:degraded \
  --output-dir local-results/model-comparison-smoke
```

실제 OpenAI-compatible 후보는 같은 평가셋·Skill 묶음과 모델 기본 temperature/reasoning으로 실행합니다.
기본 묶음은 `skills/interview-coach/SKILL.md`, 같은 폴더의 `criteria.json`, 그 JSON이 참조하는 질문 유형 문서입니다. `--skill-file`로 다른 Skill을 지정할 때도 같은 구조가 필요합니다. `--skill-version`이 카탈로그 버전과 다르거나 평가셋이 없는 기준 ID를 사용하면 외부 호출 전에 중단합니다.

Runner는 `response_format.type=json_schema`와 `CoachingLLMOutput` JSON Schema를 요청합니다. 따라서 로컬 서버를 포함한 후보 provider는 OpenAI-compatible Chat Completions의 strict JSON Schema 출력을 지원해야 합니다. `json_object`만 받는 provider는 이 runner와 호환되지 않습니다.

### OpenRouter 모델 다양성 평가

`run_openrouter_diversity.py`는 인증된 `/models/user` 목록에서 text→text 및 strict structured output 후보를 찾고, 개발사 다양성을 우선해 preflight한 뒤 PASS 모델만 같은 30건으로 평가한다. 호출별 atomic JSON을 저장하므로 같은 output directory로 재개하면 완료된 사례를 다시 호출하지 않는다. API key와 provider 원문 오류 메시지는 결과에 저장하지 않는다.

```bash
.venv-llm-eval/bin/python -B evals/run_openrouter_diversity.py \
  --stage discover --output-dir local-results/openrouter-diversity-run
.venv-llm-eval/bin/python -B evals/run_openrouter_diversity.py \
  --stage preflight --output-dir local-results/openrouter-diversity-run
.venv-llm-eval/bin/python -B evals/run_openrouter_diversity.py \
  --stage full --output-dir local-results/openrouter-diversity-run
```

`summary.json`, `summary.csv`, `SUMMARY.md`는 preflight 탈락 모델도 유지한다. `semantic_result`는 사람 검토가 연결되지 않으면 null이다. 2026-09-21 실행 결과와 한계는 [모델 계열 다양성 평가](../docs/experiments/2026-09-21_openrouter-model-diversity.md)를 따른다.

### Final Four와 semantic blind 평가

Final Four runner는 네 고정 모델×30건만 허용하며 `--live` 없이는 API를 호출하지 않는다.

```bash
.venv-llm-eval/bin/python -B evals/run_openrouter_final_four.py \
  --catalog local-results/openrouter-diversity-run/discovery.json \
  --output-dir local-results/openrouter-final-four-run

.venv-llm-eval/bin/python -B evals/run_openrouter_final_four.py --live \
  --catalog local-results/openrouter-diversity-run/discovery.json \
  --output-dir local-results/openrouter-final-four-run
```

완료 결과에서 30case×4응답 blind CSV와 별도 mapping을 만들고, 사람이 1~5점을 입력한 뒤 집계한다.

```bash
.venv-llm-eval/bin/python -B evals/build_final_four_semantic_review.py \
  --results-dir local-results/openrouter-final-four-run
.venv-llm-eval/bin/python -B evals/aggregate_final_four_semantic.py \
  --review-csv local-results/openrouter-final-four-run/semantic-blind-review.csv \
  --mapping local-results/openrouter-final-four-run/semantic-blind-mapping.json \
  --output local-results/openrouter-final-four-run/semantic-summary.json
```

전체 흐름과 현재 판단은 [평가 리포트](../EVAL_REPORT.md), 상세 Final Four 조건은
[실험 기록](../docs/experiments/2026-09-21_openrouter-final-four.md), 판단 변경은
[Decision log](../docs/DECISIONS.md)를 따른다.

### 최종 두 후보의 실제 서비스 경로 통합 확인

Final Four runner와 별개로 아래 명령은 FastAPI `/api/agent` →
`McpLlmCoachingService` → OpenRouter → Pydantic/서버 참조 validator 경로를 실행한다.
기본 실행은 네트워크를 사용하지 않고 두 모델×대표 3건의 호출 계획만 출력한다.

```bash
.venv-llm-eval/bin/pip install -r backend/requirements-service-integration.txt
.venv-llm-eval/bin/python -B evals/run_service_candidate_integration.py

# 합성 평가 입력의 외부 전송과 유료 호출을 승인한 경우에만 실행
.venv-llm-eval/bin/python -B evals/run_service_candidate_integration.py --live \
  --output-dir local-results/service-candidate-integration-20260921
```

대표 입력은 정상 `coach-normal-01`, 경계 `coach-boundary-13`, 실패 유도
`coach-failure-30`이다. 모델별 3개 사용자 요청이며 서비스 기본값과 같은 계약 보정 2회,
전송 시도 2회, 요청당 비용 상한 `$0.10`을 적용한다. 결과에는 검증된 API 응답과
token/cost/latency/retry metadata만 저장하며 API key와 provider 원문 응답은 저장하지 않는다.
timeout·429·5xx·잘못된 JSON은 과금 호출로 만들지 않고 `test_coaching_runtime.py`의
결정론적 mock 테스트로 검증한다.

```bash
export MODEL_API_KEY=...
export MODEL_API_BASE_URL=https://openrouter.ai/api/v1
python evals/run_model_comparison.py \
  --candidate candidate-a=openai:provider/model-a \
  --candidate candidate-b=openai:provider/model-b \
  --price candidate-a=INPUT_USD_PER_MILLION,OUTPUT_USD_PER_MILLION \
  --price candidate-b=INPUT_USD_PER_MILLION,OUTPUT_USD_PER_MILLION \
  --repeats 4
```

### 로컬 Ollama 사전 점검

전체 30건 실행 전에는 `--case-id`로 한 건의 endpoint·모델 ID·JSON Schema·서버 계약을 확인한다. 사전 점검이 계약을 통과한 후보만 전체 평가를 실행한다.

```powershell
ollama list
ollama pull bnksys/eeve:2.8b-korean-instruct-q4_k_m-v1

$env:MODEL_API_KEY = "ollama-local"
$env:MODEL_API_BASE_URL = "http://127.0.0.1:11434/v1"
python evals/run_model_comparison.py `
  --candidate qwen3-4b=ollama:qwen3:4b `
  --candidate baseline=mock:expected `
  --case-id coach-normal-01 `
  --max-completion-tokens 768 `
  --timeout-seconds 45 `
  --output-dir local-results/qwen3-4b-preflight
```

EEVE는 후보만 `eeve=ollama:bnksys/eeve:2.8b-korean-instruct-q4_k_m-v1`로 바꾼다. `ollama` 후보는 OpenAI-compatible endpoint에 `json_schema`를 요청하며, 원시 JSON 문법 통과만으로 성공 처리하지 않고 기존 Pydantic·ID·인용 검증까지 통과해야 한다.

사전 점검을 통과하면 `--case-id`를 제거한 동일한 명령으로 30건을 실행한다. `--max-completion-tokens`·timeout·Skill·prompt·반복 횟수는 후보 간 고정하고, 실패 요청 지연은 성공 요청의 p50/p95와 분리해 해석한다.

실제 provider 호출은 요청별 자식 프로세스에서 격리된다. `--timeout-seconds`는 SDK transport timeout과 부모 프로세스의 hard timeout에 함께 적용되며, 제한 시간을 넘긴 자식은 종료하고 해당 attempt를 `timeout`으로 기록한 뒤 다음 사례를 계속한다. 강제 종료 시 provider usage를 받지 못했다면 비용은 0이 아니라 `null`/unknown으로 남긴다. 반대로 응답을 받은 뒤 JSON·Pydantic·서버 validator 검증에 실패한 경우에는 이미 보고된 token과 cost를 보존한다. 이 hard timeout은 평가 프로세스의 진행을 보장하지만 Ollama 서버 내부에서 이미 시작된 GPU 계산의 취소까지 보장하지는 않는다.

가격은 실행 시점 provider 가격표 값을 직접 넣습니다. 결과는 Git에서 제외된 `local-results/`에 JSON과 Markdown으로 생성되며 다음 값을 비교합니다.

- 출력 계약 준수율
- 기대 status·의도·공고·기준 판정과 필수 근거의 규칙 기반 정확도
- 입력·출력 token 가격으로 계산한 총비용
- 요청 지연 p50·p95
- `schema_violation`, `timeout`, `rate_limited`, provider 실패 건수
- prompt·Skill·criteria 버전과 실행에 사용한 Skill 묶음 SHA-256

규칙 기반 정확도는 표현의 자연스러움이나 코칭 문장의 설득력을 판단하지 못합니다. 최종 모델 선정 전에는 같은 결과에서 사람 검토를 병행하고, 평가 기준이나 Skill을 바꾼 경우 새 버전으로 다시 측정합니다.

### 예시 답변 평가 경계

기존 30건은 `example_answer` 도입 전 사람이 판정한 평가셋이다. Mock runner는 계약 검증용으로 기존 입력 문장을 재사용하며 자연스러움·코칭 반영·대필 여부를 점수화하지 않는다. 품질 평가에는 별도의 사람이 작성·검토한 사례가 필요하다.

## 고정 시점

**프로젝트 초반(9/23까지)에 만듭니다.** 나중에 만들면 이미 튜닝된 결과에 맞춰집니다.
추석 연휴(9/24~27) 전에 문제 정의와 이 평가셋이 확정돼 있어야 연휴 동안 각자 진행할 수 있습니다.

## 판정 방식

정확 일치 · 스키마 통과 여부 · 규칙 기반 채점 · LLM-as-judge 모두 가능합니다.
다만 **어떤 방식이고 그 방식의 한계가 무엇인지** 리포트에 적어야 합니다.

현재 runner는 재현 가능한 규칙 기반 채점을 사용합니다. LLM-as-judge를 추가한다면 생성 모델과 다른 판정 모델을 사용하고 사람 판정과의 불일치 사례를 별도로 기록합니다.

> 기존 저장소 평가 규칙에 따라 생성 모델과 판정 모델을 분리합니다. 제공 공식 요약은 이를 권장으로 표현하며, 팀은 더 엄격한 기존 규칙을 유지합니다. 모델 판정은 독립 정답 근거를 대체하지 않습니다.

## 말해봄 평가 계획

> 아래는 향후 평가 계획이다. 현재 `dataset.jsonl`은 합성 30건(정상 12 / 경계 10 / 실패 유도 8)의 계약·runner 검증용 입력이다. 아래 9/12/9 구성과 독립 판정 출처 확보는 별도 계획이며, 현재 파일 존재가 공식 현장 경험·정답 출처 요건 충족이나 실제 모델 품질 평가 완료를 의미하지 않는다. 실측 결과는 [평가 리포트](../EVAL_REPORT.md)에 기록한다.


### 목표

평가는 “피드백이 그럴듯한가” 하나로 합치지 않고 다음을 분리한다.

- 답변 근거와 판단의 일치
- 질문 의도 판정
- 다음 행동의 구체성
- 공고 요구사항 연결
- 미언급/미경험 구분
- 재답변 변화와 사람 판단의 일치
- 출력 계약 준수
- 실패 유도 대응
- 지연/비용/실패율

### 데이터 구성

| 구분 | 계획 | 용도 |
| --- | --- | --- |
| 개발 예제 | 별도 10건 | Skill/Prompt 작성·오류 수정 |
| 고정 품질 평가셋 | 30건 = 정상 9 + 경계 12 + 실패 유도 9 | 도메인 품질 비교 |
| 계약 평가셋 | 팀 계획: 고유 입력 100건 | 공식 100건 이상 실행 준수율 측정; 입력 수와 실행/재시도 수 분리 |
| 도메인 기준 구축 | 실제 개발 사례 3건 + 변형 | 외부 검토로 기준/예외 구축 |
| 실제 파일럿 | 별도 동의 3~5명 | 실제 역할/누락/재답변/사람 판단 수집 가능성 확인 |

### 대표 10개 평가 후보

- PS-01~03: 정상 응답 예상
- PS-04~07: 공식 분류 **경계** (기획 내부명: 구현 후 확인 필요)
- PS-08~10: 실패 유도

대표 후보는 **정상 3 / 경계 4 / 실패 유도 3**이다. 경계 4개 중 최소 3개는 실제 현장 경험이 있어야 정답을 낼 수 있어야 한다. PS 후보는 아직 이 조건과 독립 판정 출처를 검증하지 않았다. 사람의 실제 사례·독립 판정 근거로 같은 구분의 추가 입력을 확보하여 팀 계획인 총 30건을 구성한다. LLM으로 입력/정답을 생성해 채우지 않는다.

### 공식 조건의 실행 절차

공식 조건과 출처는 [REQUIREMENTS](../docs/REQUIREMENTS.md)가 canonical이다. 다음은 이를 실행하기 위한 기록 계획이다.

- 각 case: 유형, 실제 입력 원문, 기대 출력/정답/판정, 판정 방식(코드/LLM/사람), 이유·현장 기준, 범용 도구와의 차이(예상/실측 구분), 판정 조원, 불일치 의견과 담당자를 기록한다.
- 평가 입력과 정답을 LLM으로 만들지 않는다. 둘을 동시에 생성한 ground truth도 금지다. 형식 정리 보조를 문항/정답 생성 허용으로 확대하지 않으며, 사람 경험·검토 또는 명시적 규칙을 독립 근거로 남긴다. 허용 보조 범위는 확인 전이다.
- 팀 내 면접관 경험자 부재를 기록하고 착수 시 범위를 조정한다. 외부 자문을 팀원 경험으로 대체하지 않는다. 경계 최소 3건의 현장 경험 조건을 검수한다.
- 고정 평가셋 30건 이상을 **Langfuse Dataset**으로 등록하고 각 case의 판정 기준·이유를 보존한다. 실제 사용자 원문은 동의 없이 등록하지 않는다.
- 같은 Dataset/version으로 baseline과 변경 후를 **두 번 이상** 측정하며 2개 이상 품질축, 회귀 문항, 실패 원인을 보고한다. score와 judge trace를 연결한다.
- 모델 최소 2개를 아래 동일 조건으로 비교한다. Prompt release 비교에는 model/dataset/grader 및 반복 횟수도 고정한다.
- **100건 이상 실행**한 structured output 계약 준수율의 분모·분자를 보고한다. 팀은 고유 입력 100건을 사용하되 최초 응답/재시도 후 최종 응답, schema/인용·업무 검증, 고유 입력 수/호출 수/실패 수를 분리해 기록한다. 공식 세부 집계 기준은 후속 확인한다.
- 모든 LLM 호출 trace에 input/output·model·token·latency·cost·retry·가명화한 user_id/session_id·Prompt version을 연결한다. Langfuse Prompt를 배포 없이 교체·rollback한 증거와 스크린샷 3장 이상(trace 상세 포함)을 남긴다.

### Skill 규칙 1개 A/B 라운드

`run_single_skill_rule_comparison.py`는 Skill 개선 시 **한 번에 규칙 한 줄만** 바꾸는 라운드를 위한 전용 runner다. 후보 규칙은 `evals/skill_rule_candidates/*.json`에 이전/변경 문장을 모두 고정하고, runner는 assembled Skill bundle에서 해당 문장이 정확히 한 번만 바뀌는지 먼저 검증한다.

현재 1차 후보 `off-topic-cav-independence-v1`은 반복평가에서 3/3 실패한 `coach-boundary-19`를 대상으로 한다. 모델, Dataset v2, grader, generation 설정, `coaching-v5-skill-owned` Prompt와 모델에 노출되는 Skill version metadata를 고정하고 **off_topic이라는 이유만으로 C/A/V를 낮추지 말라는 한 규칙**만 강화한다.

저비용 smoke는 대상 case만 baseline/candidate 각 1회 실행한다.

```bash
python evals/run_single_skill_rule_comparison.py \
  --output-dir evals/results/<date>-single-rule-smoke \
  --case-id coach-boundary-19
```

smoke에서 target 방향이 개선되면 공식 비교는 전체 30건을 baseline/candidate 각각 2회 실행한다.

```bash
python evals/run_single_skill_rule_comparison.py \
  --output-dir evals/results/<date>-single-rule-full \
  --repeats 2
```

runner는 `plan.json`에 baseline/candidate Prompt·Skill hash와 단일 변경 문장을 기록하고, 실행 후 `decision-summary.md`에 target criterion별 hit 변화·전체 label accuracy·contract rate 기반의 자동 KEEP/DISCARD 후보를 만든다. 최소 한 target criterion은 개선되어야 하고 **어떤 target criterion도 baseline보다 나빠지면 안 된다.** 최종 KEEP/DISCARD는 target과 새 회귀 case의 사람 검토 후 확정한다.

### Langfuse 자산 동기화

`sync_langfuse_assets.py`는 실제 사용자 데이터가 아닌 `dataset.v2.jsonl`의 합성 30건만 등록한다. 기본 Prompt label은 `candidate`이며 평가 전에는 `production` label을 이동하지 않는다.

```bash
python -m evals.sync_langfuse_assets
python -m evals.sync_langfuse_assets --apply --smoke-trace
```

두 번째 명령은 외부 Langfuse 프로젝트를 변경한다. 등록 뒤 Observations API v2에서 redacted smoke trace 세 observation과 Prompt version 연결을 다시 읽어 확인한다.

완료된 `run_model_comparison.py` 결과를 다시 모델 호출하지 않고 Langfuse Experiment/Dataset Run과 Score로 연결하려면 아래 adapter를 사용한다. 기본 실행은 dry-run이며 `--apply`에서만 Langfuse를 변경한다.

```bash
python -m evals.export_langfuse_experiments \
  --report local-results/<run>/comparison.json

python -m evals.export_langfuse_experiments \
  --report local-results/<run>/comparison.json \
  --apply
```

- candidate × repeat를 별도 Experiment run으로 만든다. Langfuse가 한 Experiment에서 Dataset item 반복을 하나로 취급하는 제약 때문에 반복 측정치를 한 run에 합치지 않는다.
- 각 item에는 최종 contract attempt의 `contract_valid`, rule/label/evidence/ID 정확도, 사람 semantic 점수(존재할 때), critical failure, 자동 policy check, 기존 실행의 latency/cost를 Score로 기록한다.
- `recorded_latency_ms`, `recorded_cost_usd`는 **기존 평가 실행의 측정값**이며 import task 자체의 시간·비용이 아니다. Experiment metadata에도 `provider_recalled=false`를 남긴다.
- Langfuse Dataset item의 `metadata.synthetic=true`를 강제한다. 실제 사용자 자료가 섞인 Dataset은 export를 거부한다.
- run 이름은 원본 report 생성 시각·candidate·repeat로 결정되며 같은 run이 이미 있으면 다시 생성하지 않는다.
- Experiment Runner가 있는 Langfuse Python SDK v4가 필요하다. 저장소 기준 의존성은 `langfuse>=4.7,<5`다.

### 핵심 품질 지표

#### 답변 근거 일치율

검토 기준으로 뒷받침되는 사실 주장 수 / 전체 검증 대상 사실 주장 수.

목표 초안: 90% 이상.

#### 질문 의도 판정 적절성

의도 상태와 이유가 검토 기준에 맞는 문항 수 / 판정 대상 문항 수.

목표 초안: 85% 이상.

#### 개선 행동의 구체성

행동을 다음으로 평가한다.
- 0점: 추상적
- 1점: 대상만 구체적
- 2점: 무엇을 어떻게 할지 실행 가능

2점 행동 비율 목표 초안: 85% 이상.

목표치는 기획 초안이며 달성 결과나 과제 합격선이 아니다.

### 자체 데이터·공고 연결 평가

#### 공고 연결의 적절성
- 사람이 검토한 요구사항 관련성/이유/인용과 일치한 건수
- 잘못된 출처/없는 조건 추가 건수 별도 기록

#### 미언급·미경험 구분
- 확인 응답이 있는 사례에서 사용자 진술과 후속 안내가 일치하는지 평가
- 사용자 진술을 실제 경험의 진실성 인증으로 해석하지 않음

#### 변화와 사람 판단의 일치
- 자동 criterion 변화와 사람의 설명 보완 판단 비교
- 확인 응답과 모순/과장도 별도 기록
- 실제 역량 향상이나 코칭 인과 효과와 구분

#### 데이터·규칙 검토 범위
- 실제/변형/가상 사례 수
- 핵심 네 데이터가 모두 있는 사례 수
- 외부 검토 완료/미검토 수
- 규칙 카드 출처/버전

### 모델 비교

#### 후보 모델 A/B
고정:
- 평가셋
- Skill
- Prompt
- MCP 입력
- 가능한 생성 파라미터
- 실행 환경

변수:
- 모델만 변경

측정:
- 품질
- 비용
- p50 / p95 지연
- 안정성: 계약 준수율 / 실패율

#### 같은 모델 일반 피드백 vs 말해봄 방식

고정:
- 모델
- 공고
- 직무 정의
- 질문
- 답변
- 판정 기준
- 가능한 생성 설정

변수:
- 피드백 생성/검증 방식

일부러 약한 baseline을 만들지 않는다.

### 외부 도구 비교

ChatGPT(GPT), Gemini, Claude Code는 동일 입력/요청 조건으로 실제 실행 결과를 남긴다. 기획 문서의 예상 문구를 실측 결과로 사용하지 않는다.

### 계약/운영 지표

- 최초 출력 계약 준수율
- 재시도 후 최종 준수율
- 원시 스키마 통과율
- 인용/기준 검증 통과율
- 최종 유효 피드백 제공률
- 실패 유도에 넘어간 비율
- 잘못된 결과 차단율
- 재시도 횟수/호출 수
- p50/p95 지연
- 요청당 비용

잠정 운영 목표:
- 정상 처리 대상 최종 유효 피드백 제공률 95% 이상
- 내용 피드백 구간 p95 10초 이내

기준 측정 후 바꾸면 변경 이유를 기록한다.

### 평가 오염 방지

- 개발 예제와 고정 평가셋 분리
- 평가 정답/라벨은 모델 입력에서 제외
- 실제 사용자 사례는 별도 동의 없이 평가 Dataset에 복사하지 않음
- Prompt 변경 시 동일 평가 버전으로 전후 재실행
- 평가셋 자체 수정 시 새 버전에서 비교를 다시 수행

### 결과 보고

`EVAL_REPORT.md`에는 최소 다음을 남긴다.
- 평가 버전
- 모델/Prompt/Skill 버전
- 기준 결과
- 변경 변수
- 재측정 결과
- 회귀 사례
- 실패 사례
- KEEP/DISCARD 결정
- 한계

## 6종 평가 기반 (2026-09-18)

`--six-models`는 `evaluation_records.MODELS`의 basic 3종/premium 3종을 선택한다.
실제 API 실행은 별도이며, offline 검증은 기존 `mock:expected`/`mock:degraded` 명령을 사용한다.
요청은 strict `CoachingLLMOutput` JSON Schema 및 `provider.require_parameters: true`이며
provider 자동 routing을 유지한다. temperature/reasoning을 전송하지 않아 모델 기본값을 사용하고
`request_settings`에 이 정책을 기록한다. 실제 provider 미제공은 null로 남긴다.

JSON은 case/run/execution/call ID, raw/parsed/validated output, parse/schema/validator 단계,
generation/model/provider와 전체 usage(reasoning/cache/cost 포함)를 저장한다.
`usage.cost`가 없으면 unknown이며 합계는 알려진 비용만 합산한다. `--price`는 기존 CLI 호환용이고
실제 호출 비용을 대체하지 않는다. SDK 자동 재시도는 0이며 `--max-calls`(기본 1)로 계약 실패 후
명시적으로 재요청할 수 있다. OpenAI-compatible runner의 두 번째 호출부터는 이전 raw output과
Pydantic/server validator 오류를 포함한 공통 contract repair prompt를 사용하고, 기존 의미·사실은
유지하면서 오류만 수정하도록 요구한다. 모든 호출 기록·비용은 그대로 보존한다.

세부 label/evidence 점수는 계약 통과 결과 대상이며 evidence는 기대 인용 정확 일치율이다.
ID 점수는 ID 집합·참조 유효성으로 의미 타당성이 아니다. 기존 accuracy도 호환용으로 유지한다.
consistency는 case별 최종 실행의 유효 label pair 일치율과 전체 pair 계약 성공 여부 일치율이다.
실패끼리 같은 결과인 것을 label consistency로 계산하지 않는다.
`parent_links`는 premium execution ID → basic execution ID 참조를 준비하며 자동 fallback은 실행하지 않는다.
버전/해시는 dataset, grader, schema, model ID, config 및 기존 Prompt/Skill에 남긴다.
현재 입력의 공고 텍스트·R/D 기준 부족은 유지된다. 의미 품질 채점은 아래 v2 정책을 따른다.

## Dataset v2와 의미 품질 채점

비교 runner 기본 dataset은 `dataset.v2.jsonl`이다. 기존 `dataset.jsonl`(v1)은 수정하지
않았으며 `--dataset evals/dataset.jsonl`로 과거 평가를 재현한다. v2는 동일한 입력
30건과 승인된 expected label, 핵심 15건(01/02/04/07/10/14/15/16/17/18/20/21/22/23/30)의
reason/action/clarifying_question/hallucination annotation을 포함한다.

intent는 질문 적합성만 판정하고 완성도는 C/A/V에서 독립 판정한다.
not_observed는 정보 없음, partial은 관련 정보는 있으나 기준 부족,
undetermined는 상충·모호함으로 판정 어려움이다. V는 확인 행위만 있으면 partial,
관찰 결과가 있어야 met이다. 사람 검토에서는 V의 같은 상위 label 안의 차이를
`verified / verification_only / result_only / omitted / explicitly_unverified / ambiguous_target / conflicting_results`
보조지표로 기록한다. 이 detail은 현재 구조화 출력 계약이나 label accuracy 분모에는 포함하지 않는다.
requirement text가 없는 v2에서 job alignment/status 및
job 관련 expected evidence는 accuracy/label accuracy/label consistency에서 제외한다.
계약·ID 검증과 원본 출력 보존은 유지한다. `label_accuracy_by_dimension`은 intent와 각 C/A/V를 분리한다.

semantic은 자연어 키워드로 자동 정답 처리하지 않는다. annotation의 required_points,
forbidden_conclusions, support_segment_ids, 허용/우선 행동 대상, 질문 정책,
supported_facts/explicit_negations/forbidden_claims를 원문과 대조하여 사람이 검토한다.
`semantic_grader.SEMANTIC_RUBRIC`의 항목별 0/1/2 기준을 결과에도 보존한다.
질문 존재 여부와 action target ID만 자동 정책 검사하며 이 검사는 semantic 점수가 아니다.
0은 핵심 오류, 1은 타당하지만 누락·구체성 부족, 2는 핵심 조건 충족이다.

`run_comparison(..., semantic_reviews=...)` 또는 `--semantic-reviews reviews.json`으로
attempt ID별 검토 결과를 연결한다. 예시(실제 case/run/후보와 일치해야 한다):

```json
{"baseline:coach-normal-01:1:1": {"reviewer": "검토자", "rationale": "원문 대조 근거",
 "scores": {"reason": 2, "action": 1, "clarifying_question": 2, "hallucination": 2},
 "critical_failure": false, "critical_failure_reasons": []}}
```

### Gemini v5 자동 불일치 검토 양식

이미 생성한 `comparison.json`에서 Gemini의 계약 유효 응답 중 자동 label 또는 evidence가
불일치한 사례만 사람이 검토할 때는 아래 도구를 사용한다. 이 명령은 모델·네트워크를 호출하지
않으며 결과를 `local-results/`에만 쓴다.

```powershell
.\.venv\Scripts\python.exe -B evals\build_gemini_v5_human_review.py `
  --input local-results\gemini-v5-4096-live-30\comparison.json `
  --candidate gemini `
  --output-dir local-results\gemini-v5-4096-human-review
```

생성된 `REVIEW.md`에서 원문과 rubric을 확인하고,
`semantic-reviews.template.json`의 각 attempt ID에 reviewer, rationale, 0/1/2 scores,
critical_failure와 그 이유를 채운다. 빈 template은 의도적으로 유효한 `SemanticReview`가
아니므로 검토 전에는 runner에 전달할 수 없다. 원본 모델 출력·검토 원문은 Git에 커밋하지
않는다. 완료 JSON은 같은 실행 설정의 `--semantic-reviews` 입력으로만 연결하며, 이 runner
실행은 모델 호출을 다시 수행하므로 비용·latency를 재측정한다.

critical failure는 30건의 별도 조건으로 검토하며 semantic 점수를 덮어쓰지 않는다.
true 판정에는 이유가 필수다. 미검토 점수/critical failure는 null이며 0이나 통과로
계산하지 않는다. 후보별 `semantic_quality`는 최종 case/run별 항목 평균과 검토 수,
critical failure 검토 수/발생 수/발생률을 독립 집계한다. 재시도 검토도 개별 기록에 남는다. `critical_failure_by_call`은 모든 호출의 검토 결과를 집계해 재시도 성공으로 앞선 critical failure가 사라지지 않게 한다.
2026-09-30 Dataset v2 30건 expected 판정은 김재훈 단일 검토자로 사람 검토를 완료했다.
dataset provenance에는 검토 완료일과 single reviewer 한계를 명시한다.
expected/annotation/검토 결과는 실제 모델 입력에 넣지 않는다. R/D와 실제 API 평가는 제외한다.

## Python 3.12 전용 평가 환경

README의 `python -m venv`/`python -m pip install -r` 방식을 사용한다.
운영과 평가의 네 경량 의존성은 `backend/requirements-eval.txt`에서 공유하며
backend 전체 requirements도 이를 포함한다. 평가 환경에는 ML/API 서비스 패키지를 설치하지 않는다.

```bash
bash evals/setup_env.sh
source .venv-llm-eval/bin/activate
python -B evals/run_model_comparison.py --help
```

다른 위치의 Python 3.12는 `EVAL_PYTHON=/path/to/python3.12 bash evals/setup_env.sh`로 지정한다.
기존 환경을 지우지 않고 재사용하되 Python 3.12/venv 여부를 검사한다.
ensurepip 없는 Ubuntu는 기존 uv로 pip를 보완한다(둘 다 없으면 python3.12-venv 또는 uv 필요).
requirements 범위는 고정이며 설치되는 정확한 패치 버전은 시점에 따라 달라질 수 있다.
`pip check`, import, dataset/Skill/schema/config, help 및 30건×2후보 mock 평가가 실행된다.
mock 산출물은 `local-results/eval-env-smoke`에 저장된다. setup 자체는 실제 LLM 호출을 하지 않는다.

runner CLI는 프로젝트 루트 `.env`를 python-dotenv `override=False`로 읽는다.
이미 export한 변수는 유지된다. OpenRouter endpoint에서는 `OPENROUTER_API_KEY`만 사용하며
`MODEL_API_KEY`/`OPENAI_API_KEY`로 fallback하지 않는다. 키 존재 여부만 점검한다.
사용자 지정 다른 endpoint에서는 기존 MODEL → OPENROUTER → OPENAI 키 우선순위를 유지한다.
`--six-models`는 OpenRouter endpoint만 허용한다. OpenRouter는 HTTPS만 허용한다.
실제 평가 전에 키/endpoint shell override가 의도한 것인지 확인한다. 키 인증 유효성은 smoke로 검증되지 않는다.

### 자동 평가 정책 정렬과 저장 결과 재채점

현재 정책은 `independent-intent/observed-result`다. intent는 질문 적합성만 판정하고
C/A/V 완성도와 독립이다. 비백엔드 경험의 C/A/V도 경험 진술의 내용 구조로 판정하며
범위 밖 요청/injection을 경험으로 인정하지 않는다. 확인·테스트 행위만 있고 실제 관찰
결과가 없으면 V partial이다. not_observed의 evidence는 선택 사항으로 미확인·부재·팀only
원문 인용을 허용하며 실제 원문/허용 ID/needed 검사는 유지한다.

v2 `expected.evidence`는 `support_segment_ids`와 `required`를 명시한다.
`quote`는 정답 예시이며 채점에서 전체 문자열 동일성을 요구하지 않는다.
기준별 필요한 인용이 존재하고 반환한 모든 인용이 해당 기준의 허용 지원 문장에 실제
연속 부분 문자열로 존재하면 evidence 통과다. 선택 근거가 비어 있으면 점수 분모에서
제외하되 반환한 선택 근거는 검사한다. 다른 기준 문장·가짜 인용·잘못된 추가 인용은 실패한다.
이 지표는 문장 연결과 원문 충실성이며 의미적 충분성 또는 자유서술 hallucination 점수가 아니다.
v1 dataset과 exact-match 채점은 보존한다. requirement text없는 v2는
job alignment/status/job evidence를 정확도에서 계속 제외한다.

```bash
PYTHONPATH=backend:. .venv-llm-eval/bin/python -B -m evals.regrade_saved_results \
  --input local-results/openrouter-six-20260918T083814Z/all-attempts.json \
  --dataset evals/dataset.v2.jsonl \
  --output-dir local-results/openrouter-six-20260918T083814Z/regrade-new
```

재채점 CLI는 credential/env/SDK/network를 로드하지 않고 raw 문자열을 우선 parse한다.
기존 output 디렉터리는 덮어쓰지 않는다. 각 `source_record`는 원래raw/provider/generation/
usage/cost/latency/실행 설정을 보존하고 `regrade`는 새로운 검증/점수/실패 유형을 별도로 저장한다.
버전에는 grader/policy 및 dataset/Skill/schema/validator 구현 hash를 기록한다.
새 Skill hash는 재채점 정책 식별자이며 기존 응답이 그 Skill로 생성되었다는 뜻이 아니다.
기존54 Basic실패 부모 모집단과 현재실패 부모 모집단의 Premium복구율은 별도다.
사람 semantic0~2/critical은 null, 자동critical의 원래 제한된 검사 범위도 유지한다.

2026-09-18 재채점 결과는 로컬 `regrade-policy-aligned/REPORT.md`와
`six-model-common-failures.json`에 기록했다. Basic실패54→47, 공통실패12→9.
label 분모변화와 evidence정의변화를 모델개선으로 해석하지 않는다.
새prompt 정책 준수/새비용/새latency 및 prospective recovery는 실제 새생성이 필요하다.
공통실패9건×Basic3종으로 먼저27호출, 해당실패 case합집합에만 Premium3종을
중복제거하여 최대27호출 추가하는 정책 파일럿을 제안한다. 최종 전체30건 모델선정은
동일새Skill로 Basic90호출과 새실패case만 Premium평가가 필요하다. 이번단계 실제호출 없음.

### C 최소 기준 확정 (2026-09-19)

C=`met`은 문제 대상과 문제로 인식한 상태가 식별되고, 증상·발생 조건·영향·비교 상태 중 하나 이상이 연결되어 어떤 문제였는지 이해할 수 있는 경우다. 오류·느림·문제 자체만 언급되고 대상이나 발생 상황이 충분히 드러나지 않으면 `partial`, 문제 상황 자체를 확인할 수 없으면 `not_observed`다. 원인 규명·개인 행동·검증 결과·질문의 직무 적합성은 C에 섞지 않는다.

## Premium recovery 실행 (2026-09-19)

최신 Basic 중 DeepSeek/Gemini 품질 실패 합집합 8case를 중복 제거하고 Premium3종을 총24회 평가했다.
prompt label은 `coaching-output-v3`, case20은 known ambiguous로 포함/제외 집계한다. 전체 복구는
DeepSeek Pro2/8, Claude2/8, GPT Terra4/8이며 사람 semantic은 null이다. 정식24건의 raw/provider/
usage.cost/latency/token을 별도 결과에 보존했다. 초기 persistence 오류 3회는 출력과 비용을 잃은
instrumentation failure로 품질·복구 지표에서 제외하고 별도 기록했다. 상세 결과는
`local-results/openrouter-premium-recovery-c-policy-20260919/REPORT.md`를 따른다.

## 사람 semantic 검토와 모델 결론 (2026-09-19)

핵심15case에서 Basic45개와 실제 recovery Premium18개, 총63개를 동일 rubric으로 사람이 검토했다.
Batch1만 strict blind였고 이후 batch는 mapping 노출 후 채점되어 전체 blind 결과로 표현하지 않는다.
아래 semantic 집계는 동일 rubric으로 수행한 사용자 제공 사람 검토 결과이며 개별 검토표는 로컬에만 보존한다.
Basic semantic/critical은 DeepSeek91.3%/0, Gemini90.0%/0, Qwen68.0%/3이다.
Premium failure subset은 GPT Terra83.3%/0, Claude78.3%/0, DeepSeek Pro73.3%/0이다.
Premium은 어려운 subset만 평가했으므로 Basic과 절대 점수를 직접 비교하지 않는다.

Gemini는 자동 품질·latency, DeepSeek는 비용·semantic 품질의 Basic 후보로 유지한다.
GPT Terra는 4/8 recovery와 비용·지연을 함께 보고 Premium fallback 1순위로 둔다.
Qwen은 자동 품질·지연·semantic 안전성 때문에 제외한다. case20은 known ambiguous이며
R/D, requirement context, 반복 consistency와 검토자 간 일치도는 미완료다.
공식 수치와 해석 범위는 `EVAL_REPORT.md`가 canonical이다.

이 기준으로 dataset v2의 case14/18/21/22 C를 met에서 partial로 변경하고 case20 met을 유지한다. intent 및 A/V와 나머지26case label은 유지한다. 정책은 `independent-intent-observed-result-context-v3`, 새 생성 prompt 기본값은 `coaching-output-v3`로 식별한다. 기존 결과는 소급 수정하지 않으며 새 실행은 별도 결과 디렉터리에 저장한다.

## 2026-10-06 배포 구성 반복 평가 원본

[30건 × 3회 raw 결과](results/2026-10-06-deployed-repeat3/README.md)와 [해석·한계](../docs/evidence/coaching-repeat3-2026-10-06.md). 현재 운영 배포 이미지에서 새로 실행한 provider·계약 평가이며 GitHub 최신 코드의 E2E가 아니다.
