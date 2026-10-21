# Worklog — 범용 AI와 말해봄 비교 증거

- 일시: 2026-09-23 01:50
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: `docs/REQUIREMENTS.md`의 동일 입력 모델 비교 추가 계획 및 평가 입력/정답 오염 방지

## 1. 목적

동일 모델에서 범용 면접 피드백과 말해봄의 Skill·문맥·계약 검증 경로가 만드는 출력을 PowerShell로 재현 가능한 Markdown/JSON 증거로 제공한다.

## 2. 작업 전 상태

기존 `evals/run_model_comparison.py`는 strict JSON 계약을 전제로 후보 모델을 비교했으며, 질문·답변만 사용하는 자유 형식 범용 대조군 및 좌우 출력 리포트는 없었다.

## 3. 수행 내용

- `evals/generic_vs_malhaebom.py`에 mock/live 비교 실행기를 추가했다.
- 범용 조건은 질문·답변만 전달하고, 말해봄 조건은 기존 canonical prompt·Skill·server context·validator를 사용한다.
- 리포트에 범용 결과를 정확도 점수로 해석하지 않는 제한을 명시했다.
- PowerShell smoke/live 명령을 평가 README에 문서화했다.
- 공식 30건 v2 평가셋을 변경하지 않고, 원인 관찰 신호와 추론 연결을 별도 표시하는 발표용 단일 합성 사례를 추가했다.
- 초기 `cause_reasoning` 강화안은 후속 결정에서 `cause_observation`과 `cause_inference`로 분리해 대체했다. 현재 Skill/criteria 버전은 해당 분리 기준을 사용한다.
- 비교 runner가 운영 경로와 마찬가지로 structured output 계약 실패 뒤 1회 repair를 수행하고, 최종 실패 시 원본 JSON과 실패 필드 경로를 보존하게 했다.

## 주요 판단과 이유

외부 Gemini 웹 UI의 숨겨진 시스템 지침을 동일하게 재현한다고 주장하지 않는다. 대신 같은 provider model ID와 합성 사례를 고정해 말해봄이 추가한 입력·출력 계약의 차이를 보여준다. 기본 실행은 API 호출 없는 mock 모드로 두어 검증 및 발표 준비에 비용·민감 데이터 전송이 없게 했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `evals/generic_vs_malhaebom.py` | 범용/말해봄 비교 runner 및 Markdown/JSON 생성 |
| `evals/presentation_cause_reasoning.jsonl` | 원인 관찰 신호·추론 연결 기준을 포함한 발표용 합성 사례 |
| `backend/tests/test_generic_vs_malhaebom.py` | 범용 입력 경계와 Markdown 리포트 계약 테스트 |
| `backend/tests/test_presentation_cause_reasoning_dataset.py` | 발표용 사례의 관찰 신호·추론 연결 기준 및 레이블 검증 |
| `docs/specs/generic-vs-malhaebom-evidence.md` | Why·Goal·What·How·AC Spec |
| `evals/README.md` | PowerShell smoke/live 실행 방법 |
| `skills/criteria.json`, `skills/problem-solving.md` | 강화된 원인 판단 규칙과 Skill/criteria 버전 |
| `docs/DECISIONS.md`, `docs/CURRENT_STATE.md` | 판단 규칙 변경과 현재 기준 기록 |

## 5. 검증

```text
.\.venv\Scripts\python.exe -m unittest backend.tests.test_generic_vs_malhaebom
Ran 2 tests ... OK

.\.venv\Scripts\python.exe evals\generic_vs_malhaebom.py --mode mock --output-dir local-results\generic-vs-malhaebom-smoke
comparison.json 및 comparison.md 생성 확인
```

## 6. 발견한 문제 / 남은 리스크

- live provider 호출은 API 키·외부 네트워크·유료 사용이 필요해 이 작업에서는 실행하지 않았다.
- provider가 generic free-form 또는 strict JSON Schema 요청을 지원하지 않으면 해당 조건의 실패 유형이 리포트에 기록된다.

## 미확인 사항

- `google/gemini-3.5-flash-lite`의 실제 live 결과, 비용, 지연 시간.
- 사람 검토에 의한 범용/말해봄 출력의 질적 차이 판정.

## 7. 다음 작업

- 팀 승인 후 합성 사례 3건을 live 실행하고 생성된 `local-results` 리포트를 발표 증거로 검토한다.

## 리뷰 후속 수정 (2026-09-23)

- 첫 말해봄 provider 호출이 실패해도 `output: null`, 실패 유형, 계약 실패 상태를 기록하고 다음 사례를 계속 처리하도록 했다.
- 해당 provider 실패가 `UnboundLocalError`로 바뀌지 않는 회귀 테스트를 추가했다.
- 검증: `./.venv/Scripts/python.exe -m unittest backend.tests.test_generic_vs_malhaebom` — 8 tests OK.
