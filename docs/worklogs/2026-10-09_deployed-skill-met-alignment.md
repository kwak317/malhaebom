# Worklog — 배포 기준 Skill·met 조건 정합화

- 일시: 2026-10-09 (Asia/Seoul)
- 작업자/에이전트: kwak317 / Codex
- 관련 이슈: #218
- 관련 Spec: [deployed-skill-met-alignment](../specs/deployed-skill-met-alignment.md)

## 1. 목적
운영 설정과 Skill의 met 조건을 실제 배포 기준으로 확인하고, 조건이 충돌하지 않는 최소 후보를 최신 main에 PR로 제출한다. 머지·배포·Langfuse 쓰기는 하지 않는다.

## 2. 작업 전 상태
- 운영 트래픽 100%는 `malhaebom-mk2-reference-finish-1009-verified`, image digest는 `d3cd9b7d941eac39fb04f96e211bf6882b8291454050f7b0d3bfcad67a3663d1`이었다. 이전 10/4 baseline 및 로컬 미커밋 소스는 사용하지 않았다.
- Langfuse production은 `malhaebom-coaching-v5-reinforced-verification@4`; 본문 hash는 `1f0187960cecad4b3b8bace33b237b04d05f9ddbe2d5604959ee1f11fddfbb49`였다. 이름은 v5지만 과거 도메인 판정표와 결과 met 제한이 남아 있다.
- 운영 Skill(v6)은 방법·조건과 실제 관찰 결과의 연결을 요구하며 정성적 결과도 인정한다. Prompt는 `Only reproducible_test_result or measured_outcome may support met`으로 인정 유형을 제한한다.
- JSON은 결과 met을 단순 구체성으로 축약하고 행동 선택 이유의 description은 대안 대비 이유를 요구하는 듯한 표현이었다. 유형 문서는 대안 비교를 필수로 요구하지 않는다.
- GitHub main의 Skill 본문/유형 문서는 운영 이미지와 같았다. criteria.json은 Skill 버전 문자열(v6.1)만 다르므로 이 차이만 보존하고 정합화 변경을 적용했다. GitHub 최신 코드를 운영 변경 전체로 덮어쓰지 않았다.

## 3. 수행 내용과 주요 판단
1. 운영 immutable image에서 소스·Skill을 추출하고 원격 Prompt를 읽기 전용 조회했다. 별도 백업을 보존하고 개인 데이터/키는 복사하지 않았다.
2. 기존 작업 폴더의 사용자 변경을 보존하기 위해 최신 main의 독립 checkout을 사용했다.
3. 원격 @4의 역할·입력/실행 경계·안전 문구에서 새 후보를 만들었다. 판정표·라벨 사례·도메인 tie-break는 후보에 넣지 않고 Skill에 위임한다. 기존 로컬 v5를 출발점으로 복사하지 않았다.
4. 먼저 운영 Skill 그대로 합성하여 Prompt만 바꾼 ownership 검사를 통과했다. 이후 Skill의 상태별 JSON을 유형 문서와 맞춰 별도로 검증했다.
5. 기존 Skill에 부족한 주체·미수행·사건 연결·인용된 지시문 경계를 운영 규칙에서 이관했다. 후보 Skill 버전과 provenance를 갱신했다. criteria_version 및 enum은 기존 기준과 호환된다.
6. 기존 archive/default selector와 모델·평가셋·서버 validator를 유지했다. 후보는 명시 선택만 가능하다. production 승격을 품질 검증 없이 수행하지 않는다.

## 4. 변경 파일
- `prompts/coaching-v5.4-skill-met-aligned.md`, `backend/app/services/coaching_prompt.py`: 운영 본문 기반 별도 후보와 selector.
- `skills/interview-coach/{SKILL.md,problem-solving.md,criteria.json,rule-provenance.json}`: 단일 기준과 출처/버전 정합화.
- `backend/tests/test_deployed_skill_met_alignment.py`: 6개 기준 × 4개 상태 동등성, 한쪽만 바뀐 fixture 검출, Skill 교체/후보 소유권/역사 템플릿 보존.
- `backend/tests/test_coaching_skill.py`, `test_coaching_runtime.py`, `test_prepare_d11_baseline.py`: 새 Skill 메타데이터 기대값.
- Spec, 증거 JSON, Current State, 작업 카드, Worklog/색인: 증거와 적용 범위 구분.

## 5. 검증
운영 image의 Python 런타임에서 해당 checkout을 read-only mount하고 아래 suite를 실행했다. provider/API 경로는 mock·fixture이며 운영 사용자 호출이 아니다.

```text
PYTHONPATH=backend:backend/tests:. python -m unittest \
  backend.tests.test_deployed_skill_met_alignment backend.tests.test_coaching_skill \
  backend.tests.test_coaching_prompt backend.tests.test_prompt_skill_separation \
  backend.tests.test_coaching_runtime backend.tests.test_coaching_validation \
  backend.tests.test_coaching_api backend.tests.test_preset_coaching \
  backend.tests.test_prepare_d11_baseline
100 tests: OK
```

최종 검증은 최신 main 94 tests와 PR staged tree 100 tests가 통과했다. 운영 image에 테스트용 Git CLI만 추가한 임시 로컬 컨테이너를 사용했다. 소스 일부만 추출한 초기 검증 사본에서 services/MCP/config 및 git 의존성이 없어 실패한 실행은 최종 결과에 포함하지 않았다. 전체 tracked source와 read-only Git metadata mount를 포함한 뒤 재검증했다. 운영 컨테이너와 외부 배포는 변경하지 않았다.

초기 실행은 변경된 Skill 버전의 fallback 기대값 1건이 과거 v6.1로 고정돼 실패했다. 본문/계약이 아니라 메타데이터 불일치였고, 기대값을 후보 버전으로 수정한 뒤 재실행했다. 전체 Prompt를 예외 출력에 복제하지 않았다.

Prompt-only 검사와 읽기 전용 운영 manifest: [증거 JSON](../evidence/deployed-skill-met-alignment-2026-10-09.json).

별도 작업이 전문가 검토 메타데이터를 작업 사본에 변경한 것을 최종 diff에서 발견했다. 해당 작업 변경은 보존하며 이 PR에는 버전·rationale 정합화만 stage했다. 검증은 실제 staged tree의 별도 사본으로 수행한다.

## 6. 발견한 문제 / 미확인 사항
- 원격 production label의 조회 시점 version은 @4이며 mutable label은 이후 달라질 수 있다. 해당 문서는 revision/본문 hash와 함께 읽는다.
- 실제 배포 응답에서 버전 연결을 새로 추적한 결과는 아니다. 설정·원격 본문·소스 검사와 실제 LLM 동작/품질은 구분한다.
- 실제 LLM paired 평가, 사람 품질 판정, 로그인 사용자 E2E, 운영 배포·rollback은 실행하지 않았다.
- 기존 local fallback v4는 재현 증거를 보존한다. 이번 후보 PR이 병합/배포되지 않으면 기존 운영 충돌은 남아 있다.

## 7. 다음 작업
PR review 후 동일 조건 실제 LLM before/after 및 사람 검토를 수행하고, 승인된 후보에 대해서만 Langfuse 등록·승격과 fallback 선택을 맞춘다.
