# Worklog — 모델 자유 질의 Probe 지표 표시

- 일시: 2026-09-21 17:04
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: Final Four 모델의 고정 30건 계약 평가와 자유 질문 응답 확인을 분리한다.

## 1. 목적

프런트엔드 없이 OpenRouter 후보 모델에 자유 질문을 보내고, 응답 옆에서 기존 30건 계약 평가 성적과 이번 호출의 사용량을 함께 확인한다.

## 2. 작업 전 상태

사용자가 만든 `evals/model_chat_probe.py`는 OpenRouter 호출과 응답 출력만 수행했으며, 모듈 import 시 즉시 API 키를 요구하고 호출 준비를 수행했다.

## 3. 수행 내용

- Final Four 네 모델의 고정 30건 평가 지표를 `BENCHMARK_SCORES`로 추가했다.
- 모델별 계약 통과, p50/p95, 30건 비용을 한 줄로 만드는 `benchmark_summary()`를 추가했다.
- 실행 시 고정 평가 지표와 실시간 지연·provider usage를 모두 출력하도록 변경했다.
- API 키 확인과 네트워크 호출을 `main()`/`run_probe()`로 옮겨 import 시 부작용이 없게 했다.
- Flash Lite의 고정 평가 지표 형식을 검증하는 단위 테스트를 추가했다.

## 주요 판단과 이유

자유 질문에는 독립 정답이 없으므로 그 응답의 품질을 임의 점수로 산출하지 않았다. 대신 이미 고정된 30건 계약 평가 성적과 이번 요청의 관측값을 함께 제공한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `evals/model_chat_probe.py` | Final Four benchmark 표시와 안전한 실행 진입점 추가 |
| `evals/test_model_chat_probe.py` | Flash Lite benchmark 표시 형식 테스트 추가 |

## 5. 검증

```text
.venv\Scripts\python.exe -m unittest evals.test_model_chat_probe
Ran 1 test — OK

.venv\Scripts\python.exe -m unittest discover -s backend/tests -p "test_coaching_eval.py"
Ran 9 tests — OK

C:\Users\home\AppData\Local\Programs\Python\Python312\python.exe -m py_compile evals/model_chat_probe.py
성공

C:\Users\home\AppData\Local\Programs\Python\Python312\python.exe evals/model_chat_probe.py
API 키 미설정 안내 후 종료 확인
```

## 6. 발견한 문제 / 남은 리스크

- 시스템 Python에는 `pydantic`이 없어 backend 코칭 평가 테스트를 실행할 수 없었다. 프로젝트 `.venv`에서는 통과했다.

## 미확인 사항

- 실제 OpenRouter API 호출은 비용이 발생하므로 이 작업에서는 실행하지 않았다.

## 7. 다음 작업

- 사용자가 `OPENROUTER_API_KEY`를 설정한 뒤 원하는 질문으로 live 응답·지연·usage를 확인한다.
