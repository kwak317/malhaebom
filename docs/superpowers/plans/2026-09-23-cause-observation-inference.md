# 원인 관찰·추론 분리 구현 계획

> **에이전트 작업자용:** 이 계획을 구현할 때 `superpowers:executing-plans` 또는 `superpowers:subagent-driven-development`를 사용한다.

**목표:** `cause_reasoning`을 관찰과 추론으로 나눠 말해봄이 원인 설명에서 빠진 지점을 구체적으로 표시한다.

**구조:** Skill catalog를 새 criterion ID의 단일 출처로 삼는다. 질문 문맥이 새 ID를 활성화하고, 기존 Pydantic/서버 validator가 각 ID의 정확한 반환을 강제한다. 평가·비교·발표도 동일한 ID와 버전을 사용한다.

**기술 스택:** Python 3.12, FastAPI/Pydantic, FastMCP 문맥 서비스, unittest, JSONL.

**Spec:** `docs/specs/cause-reasoning-split.md`

## 공통 제약

- 답변에 없는 로그 관찰·원인·도구·수치·역할·결과를 생성하지 않는다.
- `cause_observation`은 관찰 신호만, `cause_inference`는 신호에서 원인을 좁힌 연결만 판정한다.
- 확인 질문 1개·다음 행동 2개 제한 및 정확한 인용문 검증을 유지한다.
- 새 문맥에서 `cause_reasoning`을 사용하지 않으며, 이전 결과와 새 결과를 직접 비교하지 않는다.
- 사람 평가 라벨은 모델 프롬프트에 넣지 않는다.

## 리뷰 중점

- “로그를 봤다”만 있는 답변은 두 기준을 자동 `met`으로 처리하지 않는다.
- 구체적 오류 패턴만 있고 원인 연결이 없으면 관찰만 `met`일 수 있다.
- 원인만 단정하고 관찰 신호가 없으면 검증된 관찰로 처리하지 않는다.
- 모델이 폐기된 `cause_reasoning`을 반환하면 계약 검증에서 거부하고 최대 1회 repair한다.
- 옛/새 criteria version의 결과를 같은 기준처럼 비교하지 않는다.

---

### 작업 1: Skill 기준과 버전 분리

**파일:**

- 수정: `skills/criteria.json`, `skills/problem-solving.md`, `skills/SKILL.md`
- 테스트: `backend/tests/test_coaching_skill.py`

- [ ] 실패 테스트를 작성한다.

```python
def test_catalog_has_split_cause_criteria(self):
    self.assertIn("cause_observation", self.bundle.criterion_ids)
    self.assertIn("cause_inference", self.bundle.criterion_ids)
    self.assertNotIn("cause_reasoning", self.bundle.criterion_ids)
```

- [ ] 실행: `.\.venv\Scripts\python.exe -m unittest backend.tests.test_coaching_skill`

  기대: 새 ID가 없어 실패.

- [ ] `criteria.json`에서 `cause_reasoning`을 다음 두 항목으로 교체한다.

```json
{"id":"cause_observation","met":"로그·재현·비교·실험에서 관찰한 구체적 신호가 답변에 있다."}
{"id":"cause_inference","met":"관찰한 신호가 특정 원인 후보를 좁히거나 배제한 이유와 연결된다."}
```

- [ ] 새 Skill/criteria 버전을 설정하고 `problem-solving.md`에 “도구 사용·확인했다는 말만으로는 관찰 신호가 아니다”를 기록한다.
- [ ] 동일 테스트를 다시 실행해 통과를 확인한다.
- [ ] 커밋: `git commit -m "feat: split cause observation and inference criteria"`

### 작업 2: 서버 문맥과 출력 계약 변경

**파일:**

- 수정: `backend/app/services/coaching_context.py`, `backend/app/services/supabase_coaching_context.py`
- 수정: `backend/app/services/coaching_observability.py`, `.env.example`
- 수정: `evals/run_model_comparison.py`, `evals/generic_vs_malhaebom.py`
- 테스트: `backend/tests/test_coaching_validation.py`, `backend/tests/test_coaching_runtime.py`

- [ ] 폐기된 ID를 반환하면 거부되는 실패 테스트를 작성한다.

```python
def test_removed_cause_reasoning_id_is_rejected(self):
    output = valid_output_with_new_cause_ids()
    output["criterion_assessments"][1]["criterion_id"] = "cause_reasoning"
    with self.assertRaises(OutputContractError):
        validate_and_build_response(output, validation_context())
```

- [ ] 실행: `.\.venv\Scripts\python.exe -m unittest backend.tests.test_coaching_validation`

  기대: 기존 fixture가 옛 ID를 사용해 실패.

- [ ] 모든 문제 해결 질문 문맥을 아래처럼 변경한다.

```python
active_criterion_ids=[
    "problem_context", "cause_observation", "cause_inference",
    "own_action", "action_rationale", "result_verification",
]
```

- [ ] 환경·관측·평가 기본 버전도 새 Skill/criteria 버전으로 맞춘다.
- [ ] 계약과 런타임 테스트를 실행한다.

```powershell
.\.venv\Scripts\python.exe -m unittest backend.tests.test_coaching_validation backend.tests.test_coaching_runtime
```

- [ ] 커밋: `git commit -m "feat: activate split cause criteria in coaching context"`

### 작업 3: 발표 데이터·비교 안전성 갱신

**파일:**

- 수정: `evals/presentation_cause_reasoning.jsonl`, `backend/app/services/attempt_comparison.py`
- 수정: `backend/tests/test_presentation_cause_reasoning_dataset.py`, `backend/tests/test_attempt_comparison.py`, `backend/tests/test_generic_vs_malhaebom.py`

- [ ] 발표 사례가 두 새 기준을 `partial`로 기대하는 실패 테스트를 작성한다.

```python
def test_presentation_case_marks_both_cause_parts_partial(self):
    case = load_dataset(PRESENTATION_DATASET)[0]
    self.assertEqual(case.expected.criterion_assessments["cause_observation"].value, "partial")
    self.assertEqual(case.expected.criterion_assessments["cause_inference"].value, "partial")
```

- [ ] 옛·새 criteria version을 비교하려 할 때 거부되는 테스트를 작성한다.
- [ ] 실행: `.\.venv\Scripts\python.exe -m unittest backend.tests.test_presentation_cause_reasoning_dataset backend.tests.test_attempt_comparison`

  기대: 옛 데이터·fixture 때문에 실패.

- [ ] 발표용 JSONL만 새 ID와 독립 사람 라벨로 수정한다. 역사적 `evals/dataset.v2.jsonl`은 수정하지 않는다.
- [ ] 비교 로직은 옛 결과를 새 ID로 매핑하지 않고 호환되지 않는 criteria version을 거부하게 한다.
- [ ] mock 리포트를 실행한다.

```powershell
.\.venv\Scripts\python.exe evals\generic_vs_malhaebom.py --mode mock --dataset evals\presentation_cause_reasoning.jsonl --case-id presentation-cause-01 --output-dir local-results\cause-split-smoke
```

  기대: `cause_observation`, `cause_inference`가 표시되고 `cause_reasoning`은 없다.

- [ ] 커밋: `git commit -m "test: cover split cause criteria comparison"`

### 작업 4: 문서·live 검증

**파일:**

- 수정: `docs/CURRENT_STATE.md`, `docs/DECISIONS.md`, `evals/README.md`
- 수정: `docs/worklogs/2026-09-23_0150_generic-vs-malhaebom-evidence.md`

- [ ] 새 버전 경계와 다음 live 명령을 문서화한다.

```powershell
.\.venv\Scripts\python.exe evals\generic_vs_malhaebom.py `
  --mode live `
  --dataset evals\presentation_cause_reasoning.jsonl `
  --case-id presentation-cause-01 `
  --output-dir local-results\cause-split-live
```

- [ ] 전체 테스트를 실행한다.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests
```

- [ ] 실패가 있으면 Worklog에 테스트 이름과 실제 결과를 기록한다.
- [ ] 커밋: `git commit -m "docs: record split cause criteria validation"`

## 자체 검토

- Spec의 기준 분리·계약 강제·발표 출력·버전 호환성·문서화 요구를 작업 1~4가 모두 다룬다.
- 새 외부 ID는 `cause_observation`, `cause_inference` 두 개뿐이며 catalog → 질문 문맥 → validator → 평가/비교에 동일하게 전달된다.
- 다섯 리뷰 중점은 각 작업의 실패 테스트 또는 전체 검증으로 확인한다.
