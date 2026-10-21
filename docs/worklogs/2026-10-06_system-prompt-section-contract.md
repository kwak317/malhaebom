# Worklog — System Prompt 역할 단위 섹션 정리

- 일시: 2026-10-06
- 범위: E2E/provider 호출 없이 Prompt 구조와 정적 테스트만 변경.
- base: PR #176 `docs/prompt-input-security-audit` 위 stacked 작업.

## 목적

프롬프트 설계 체크리스트의 “실제 서비스 각 LLM 호출마다 역할·입력 필드·출력 형식·안전 경계가 한 Prompt 안에서 명확히 분리되는지”를 정리한다.

## 변경

- mutable Markdown Prompt 4개를 `[역할] → [입력 경계] → [출력 계약] → [안전 경계]` 순서로 통일.
- `JobSearchIntentService` inline system Prompt를 같은 구조로 변경.
- question rubric 생성/평가/예시의 inline system Prompt 3개도 같은 구조로 변경.
- 구조 회귀 테스트 `backend/tests/test_system_prompt_sections.py` 추가.
- 설계 문서 `docs/specs/system-prompt-section-contract.md` 추가.

## 의도적 예외

현재 배포 v4 기준인 `prompts/coaching.md`는 Prompt hash와 기존 반복평가 재현성을 보존하기 위해 수정하지 않는다. 다음 production 승격 후보는 이미 4섹션 구조를 가진 `coaching-v5-skill-owned.md`에서 재평가해야 한다.

따라서 체크리스트는 **부분완료 유지**가 맞다. mutable 호출 구조는 정리했지만 현재 배포 v4 자체를 새 구조로 바꾸지는 않았다.

## 검증

- system Prompt section contract test
- 관련 기존 prompt/security tests
- `git diff --check`
