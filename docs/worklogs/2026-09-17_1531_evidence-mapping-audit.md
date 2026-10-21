# Worklog — 코칭 평가셋 evidence 매핑 전수 점검

- 일시: 2026-09-17 15:31 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: PR #8 후속 수정
- 관련 요구사항/결정: `docs/REQUIREMENTS.md`의 근거 일치 평가, `skills/problem-solving.md`의 기준별 판정 규칙

## 1. 목적

`evals/dataset.jsonl` 30건의 기대 evidence가 지정한 문장에 존재하는지만 검사하던 한계를 보완하고, 각 `target_type`과 `target_id`가 의미상 맞는 문장을 가리키도록 수정한다.

완료 조건은 전체 expected evidence의 수동 대조, 확인된 오매핑 수정, 회귀 테스트와 기존 평가 테스트 통과다.

## 2. 작업 전 상태

- `coach-boundary-15`의 `own_action`이 행동 문장 대신 결과 문장을 가리켰다.
- `coach-boundary-21`의 `own_action`이 행동 문장 대신 결과 미확인 문장을 가리켰다.
- 30건 전체를 대조한 결과 같은 유형의 오매핑이 공고 관련성과 다른 경계 사례에도 있었다.
- 기존 테스트는 quote의 부분 문자열 일치와 fixture 자체의 일치만 검사해 의미상 잘못된 정답표도 `mock:expected` 100%로 통과할 수 있었다.

변경 전 `python backend/tests/test_coaching_eval.py`는 3개 테스트를 통과했다. 기본 Python 환경에는 `pytest`가 설치되어 있지 않아 unittest 진입점을 사용했다.

## 3. 수행 내용

1. 30건의 모든 expected evidence를 답변 segment 및 C/R/A/D/V 판정 규칙과 대조했다.
2. `coach-boundary-14`, `15`, `20`, `21`의 잘못된 segment와 quote 6개를 의미상 맞는 문장으로 교체했다.
3. 수정한 공고 관련성·본인 행동 매핑을 명시적으로 고정하는 회귀 테스트를 추가했다.

## 주요 판단과 이유

- 판정 label과 답변 문장은 이번 evidence 매핑 수정 범위에서 유지했다.
- 하나의 문장이 여러 기준을 실제로 함께 뒷받침하는 경우는 잘못된 중복으로 보지 않았다.
- `not_observed`와 `undetermined` 판정은 현재 계약에 따라 evidence가 없어도 되므로 새 근거를 만들지 않았다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `evals/dataset.jsonl` | 경계 사례 4건의 evidence 6개를 올바른 segment와 quote로 수정 |
| `backend/tests/test_coaching_eval.py` | 수정 대상의 의미 매핑을 고정하는 회귀 테스트 추가 |
| `docs/worklogs/2026-09-17_1531_evidence-mapping-audit.md` | 점검 범위, 변경 이유와 검증 결과 기록 |

## 5. 검증

```text
python backend/tests/test_coaching_eval.py
변경 전: Ran 3 tests, OK
변경 후: Ran 4 tests, OK

python evals/run_model_comparison.py \
  --candidate expected=mock:expected \
  --candidate degraded=mock:degraded \
  --output-dir local-results/evidence-mapping-audit
결과: 30건, 정상 12/경계 10/실패 8 유지
mock:expected contract_rate 1.0, accuracy 1.0
mock:degraded contract_rate 0.766667, accuracy 0.735926

python -m unittest discover -s backend/tests -p 'test_*.py'
결과: 164개 실행, 평가 관련 테스트 포함 163개 통과 후 test_mcp_tools import 오류 1개
원인: 현재 Python 환경에 선택 의존성 mcp가 설치되어 있지 않음
```

수동 점검에서는 정상 12건, 경계 10건, 실패 유도 8건의 모든 expected evidence를 확인했다.

## 6. 발견한 문제 / 남은 리스크

- 일반적인 의미 일치는 단순 문자열·Pydantic 검증으로 자동 판정할 수 없다. 이번 테스트는 확인된 회귀 지점을 명시적으로 고정한다.
- 합성 fixture의 전문가 검토 상태는 여전히 `team_draft`이며, 이번 수정은 외부 면접관 검토 완료를 의미하지 않는다.
- 전체 backend unittest는 현재 환경의 `mcp` 패키지 부재로 `test_mcp_tools`를 import하지 못했다. 이번 변경과 직접 관련된 평가 테스트는 모두 통과했다.

## 미확인 사항

- 실제 후보 모델과 Langfuse Dataset을 사용한 비교는 수행하지 않았다.
- 외부 검토자의 사례별 판정과 이유는 아직 확인하지 않았다.

## 7. 다음 작업

- 평가셋 버전이 바뀔 때 기준별 evidence를 사람 검토 항목으로 유지한다.
- 실제 모델 비교 전 독립 검토 근거와 이견 기록을 연결한다.
