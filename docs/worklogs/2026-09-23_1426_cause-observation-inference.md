# Worklog — 원인 관찰·추론 기준 분리

- 일시: 2026-09-23 14:26
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: `docs/specs/cause-reasoning-split.md`, `docs/DECISIONS.md`

## 1. 목적

원인 판단 한 항목을 관찰 신호와 추론 연결로 나눠, 말해봄이 답변에서 빠진 근거의 종류를 분명히 표시하게 한다.

## 2. 작업 전 상태

`cause_reasoning`은 로그 사용, 관찰 신호, 원인 추론을 한 기준으로 판정했다. 실제 live 비교에서 “만료 토큰 재사용을 확인했다”는 진술이 구체적 신호와 추론 연결 없이 `met`으로 나와 부족한 지점을 구분하지 못했다.

## 3. 수행 내용

- Skill catalog와 problem-solving 지침에서 `cause_reasoning`을 `cause_observation`, `cause_inference`로 대체했다.
- Skill/criteria 버전을 `interview-coach-v4` / `problem-solving-v4-draft.3`으로 올리고 서버 문맥·환경 기본값·평가 runner·관측 값을 맞췄다.
- 서버 validator가 옛 ID와 누락된 새 ID를 거부하는 테스트를 추가했다.
- 1차/2차 비교는 기존 `skill_version` 일치 검사를 이용해 구 Skill과 새 Skill의 직접 비교를 거부하며, 이를 테스트했다.
- 범용 AI와 말해봄의 발표 비교 실행기·합성 사례·재현 문서는 PR 크기 정책을 지키기 위해 후속 의존 PR로 분리했다.

## 주요 판단과 이유

기존 공식 `evals/dataset.v2.jsonl`은 과거 평가 재현을 위해 수정하지 않았다. 발표용 합성 사례만 새 계약으로 올렸다. 이 기준은 실제 로그·기술 원인의 진실성이나 사용자 경험의 진위를 검증하지 않고, 현재 답변에 드러난 근거 구조만 판정한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `skills/criteria.json`, `skills/problem-solving.md`, `skills/SKILL.md` | 원인 관찰 신호·추론 연결 기준과 적용 규칙 |
| `backend/app/services/coaching_context.py`, `backend/app/services/supabase_coaching_context.py` | 새 활성 기준과 demo 출력 |
| `backend/app/services/practice_history.py`, `backend/app/services/attempt_comparison.py` | 사용자 표시명·새 Skill 버전 fixture |
| `backend/tests/test_coaching_*.py`, `backend/tests/test_attempt_comparison.py` | 새 ID 계약·버전 호환성 회귀 테스트 |
| `docs/CURRENT_STATE.md`, `docs/DECISIONS.md`, `docs/REQUIREMENTS.md` | 현재 기준과 결정 기록 |

## 5. 검증

```text
.\.venv\Scripts\python.exe -m unittest backend.tests.test_coaching_skill backend.tests.test_coaching_validation backend.tests.test_attempt_comparison backend.tests.test_coaching_runtime
관련 기준·서버 계약·비교 호환성 테스트 통과

.\.venv\Scripts\python.exe -m unittest discover -s backend\tests
304 tests 실행: 303 passed, 1 failed
```

전체 회귀 실패는 `test_evaluation_records.EvaluationRecordsTest.test_isolated_provider_failure_returns_without_cost` 하나다. Windows의 자식 프로세스 기동 시간이 1초 제한을 넘어 예상 `provider_error` 대신 `timeout`이 반환됐다. 원인 관찰·추론 기준 및 JSON 문자열 해제 변경과는 관계가 없어 이 작업에서 동작을 바꾸지 않았다.

## 6. 발견한 문제 / 남은 리스크

- 실제 live provider 결과는 호출마다 달라질 수 있다. 같은 답변을 실제 평가 라벨처럼 보지 말고, 계약 통과·인용·부족 항목이 새 기준으로 분리되는지 확인해야 한다.
- 전체 회귀의 Windows 자식 프로세스 타이밍 실패 1건이 남아 있다.

## 미확인 사항

- API 키와 외부 네트워크가 필요한 범용 AI/말해봄 live 비교 결과(후속 의존 PR에서 수행).

## 7. 다음 작업

- PowerShell live 명령을 실행해 Markdown 리포트를 공유하고, 사람이 두 기준의 판정·확인 질문이 적절한지 검토한다.
- provider가 JSON 객체를 문자열로 한 번 더 감싸는 경우와 1,024 토큰 절단을 재현·수정한 뒤 live 리포트를 다시 생성한다.
- live 리포트에 provider 종료 이유를 남겨 `length` 종료와 structured-output 형식 실패를 구분한다.
