# 현재 v5 Prompt + Skill 중복·충돌 점검 — 2026-10-06

## 점검 범위

현재 개발·평가 기준으로 사용하는 `coaching-v5-skill-owned`와 현재 GitHub Skill을
`build_coaching_system_prompt()`으로 실제 조립해 도메인 규칙 중복·상충을 정적으로 점검했다.

- current working/evaluation Prompt: `coaching-v5-skill-owned`
- Skill: `load_skill_bundle()`이 조립하는 현재 `interview-coach` bundle
- 조립 경로: runtime과 eval이 공유하는 `build_coaching_system_prompt()`
- provider/E2E 호출: 없음

버전 이름이 섞이지 않도록 다음을 구분한다.

- `coaching-v5-skill-owned`: 현재 작업·평가 기준 v5. #185 단일 Skill 규칙 A/B도 이 Prompt를 고정했다.
- local fallback/default selector: 10/6 배포 재현 정렬 작업으로 v4 계열을 가리킬 수 있다. 이는 **v5 작업 기준과 별개**다.
- `coaching-v5-reinforced-...`: 별도로 등록된 v5 후보다. 등록 manifest상 Langfuse `candidate`이며 당시 production 승격·Cloud Run 변경은 없었다.
- 마지막 저장소 운영 증거는 v4 production을 기록한다. 이후 실제 운영이 v5로 바뀌었는지는 저장소 정적 점검만으로 확정하지 않는다.

## 현재 v5 조립 결과

| 규칙 | v5 Skill-owned Prompt | 현재 Skill | 판정 |
| --- | --- | --- | --- |
| intent와 C/A/V 독립 판정 | 도메인 판정 본문 없음 | off_topic이어도 C/A/V를 독립 평가 | **Skill 단일 소유** |
| `result_verification=met` 조건 | 도메인 판정표·threshold 없음 | method/condition + observed result 기준 및 예시 | **Skill 단일 소유** |
| evidence quote / ID / JSON output / 보안 경계 | Prompt가 서버 계약으로 소유 | Skill은 도메인 판정 절차 소유 | 정상 분리 |

현재 v5 조합에는 archived v4의
`Only reproducible_test_result or measured_outcome` 문구가 없고,
`Do not require a repeat count or numeric measurement` 같은 도메인 판정 규칙은 Skill에서만 들어간다.
따라서 **현재 v5 Prompt + Skill 자체에서는 앞서 우려한 도메인 규칙 중복·충돌이 확인되지 않았다.**

## archived v4와의 차이

배포 재현용 v4 snapshot에는 Boundary decision table과 결과 검증 제한이 Prompt 본문에 남아 있다.
현재 Skill과 합치면 일부 규칙은 중복되고 `result_verification=met` 조건은 의미가 충돌할 수 있다.

이것은 현재 v5 설계의 충돌이 아니라 **archived/deployment-v4 계열의 기술부채**로 분리한다.
v4 snapshot은 재현성을 위해 수정하지 않는다.

## 회귀 검사

`backend/tests/test_prompt_skill_separation.py`에서 다음을 고정한다.

- `coaching-v5-skill-owned` template에는 Boundary table·과거 V gate가 없음
- current Skill의 도메인 규칙이 assembled v5 Prompt에 정확히 한 번 들어감
- archived v4 template에는 과거 Boundary table과 V gate가 남아 있음을 별도 회귀 테스트로 보존

## 결론

**현재 v5 Prompt + Skill의 규칙 중복·충돌 검증은 완료로 판단한다.**

다만 실제 운영 production이 v5인지 여부는 별도 운영 사실이다.
저장소에 남은 마지막 명시적 검증은 v4 production이며,
Langfuse managed Prompt 또는 Cloud Run 설정이 이후 변경됐다면 D10 운영 증거에서 현재 버전·본문 hash를 다시 확인해야 한다.
