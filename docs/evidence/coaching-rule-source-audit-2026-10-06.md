# 코칭 판정 기준 단일 기준원 점검 — 2026-10-06

## 결론

코칭 판정의 canonical source는 **`load_skill_bundle()`이 조립하는 versioned Skill bundle 하나**로 고정한다.

이 bundle은 다음 세 계층으로 구성된다.

1. `criteria.json`: criterion ID·이름·버전·검토 상태와 기계 판독 계약
2. 질문 유형 문서: problem-solving/preset-interview의 의미·경계 판정·도메인 예시
3. `SKILL.md`: 공통 판정 절차·입력 신뢰 경계·근거/사실 보존 규칙

현재 운영용 Prompt 템플릿은 역할·입력/실행 경계·출력 계약만 소유하고, 새 도메인 판정표나 제품 숫자 임계값의 출처가 되지 않는다.

## 숫자 기준 점검

현재 canonical Skill bundle에는 “p95 700ms 이하면 met”처럼 제품 판정을 결정하는 고정 숫자 임계값이 없다.

- `problem-solving.md`는 **수치 없이도 동일 조건과 실제 관찰 결과가 있으면 V를 인정할 수 있다**고 정의한다.
- “~인지 확인했다”처럼 목표/임계값 확인 행위만 있고 실제 관찰값이 없으면 partial로 유지한다.
- 평가셋 안의 `700ms`, `350 CPM`, `300 CPM` 등은 답변 데이터 또는 회귀 사례이지 제품의 판정 임계값이 아니다.

따라서 숫자 자체가 여러 파일에 등장하는 것과 “숫자 기준이 여러 군데서 관리되는 것”은 구분한다.

## 중복 판정표 inventory

| 자산 | 판정 규칙 포함 | canonical 여부 | 처리 |
| --- | --- | --- | --- |
| `skills/interview-coach/SKILL.md` | 공통 판정 절차·안전 경계 | canonical | 유지 |
| `skills/interview-coach/problem-solving.md` | C/O/I/A/D/V 경계 판정 | canonical | 유지 |
| `skills/interview-coach/preset-interview.md` | preset 질문별 판정 규칙 | canonical | 유지 |
| `skills/interview-coach/criteria.json` | ID·버전·검토 상태·기계 판독 계약 | canonical | 유지 |
| `prompts/coaching.md` | 출력/입력 계약 중심 | canonical operating template | 도메인 판정 중복 금지 |
| `prompts/coaching-v5-skill-owned.md` | 출력/입력 계약 중심 | canonical candidate 구조 | 도메인 판정 중복 금지 |
| v3/v4/v4.1 builder | 과거 판정 문구 포함 | 비canonical 재현 snapshot | hash 보존 |
| `coaching-user-supplied-v4-verification.md` | Boundary table·예시 포함 | 비canonical 실험 snapshot | 재현용 보존 |
| `coaching-v5-reinforced-verification.md` | Boundary table·예시 포함 | 비canonical 실험 candidate | 그대로 production 승격 금지, skill-owned 구조로 이관 후 재평가 |
| `evals/results/.../system_prompt.txt` | 당시 전체 Prompt snapshot | 비canonical 결과 artifact | 변경 금지 |
| `evals/dataset*.jsonl` | 숫자·문장·expected label | 회귀 데이터 | 제품 기준원으로 사용 금지 |

## 실제 충돌 가능성

현재 기본 v4와 등록된 reinforced v5 candidate는 재현/실험 목적으로 Prompt 본문에 도메인 판정 규칙을 포함한다.
따라서 이 두 자산의 문구와 현재 Skill이 다르면 **새 기준을 어느 쪽에서 읽어야 하는지 혼동될 수 있다.**

이번 작업에서는 다음 원칙으로 해소한다.

- 새 규칙 수정은 Skill bundle에서만 한다.
- 현재 기본 v4는 배포 재현을 위해 동결하고, 그 문구를 새 기준으로 수정하지 않는다.
- reinforced v5 candidate는 canonical candidate로 간주하지 않고 production 승격 금지 대상으로 문서화한다.
- 다음 승격 후보는 `coaching-v5-skill-owned` 구조에서 현재 Skill bundle을 합성한 뒤 다시 측정한다.

## 회귀 방지

`backend/tests/test_prompt_skill_separation.py`에 현재 운영 템플릿(`coaching.md`, `coaching-v5-skill-owned`)이 다음 도메인 규칙 marker를 직접 소유하지 않는지 검사한다.

- `[Boundary decision table]`
- `threshold_assertion_without_value`
- `reproducible_test_result`
- `p95가 700ms`
- `Only reproducible_test_result or measured_outcome`

동시에 canonical Skill bundle 안에는 현재 V 규칙, `result_verification` criterion, `team_draft` 검토 상태가 실제로 포함되는지 확인한다.

## 체크리스트 판정

**“숫자 기준·판정표를 한곳에서 관리한다”는 설계/소유권 기준은 완료 처리할 수 있다.**

다만 이것은 현재 배포 v4 본문에서 과거 중복 규칙이 물리적으로 삭제됐다는 뜻이 아니다.
배포 v4와 과거 실험 Prompt는 재현 snapshot 예외이고, 다음 production 승격 후보가 실제로 `coaching-v5-skill-owned` 구조를 사용했는지는 별도 release 검증에서 확인한다.
