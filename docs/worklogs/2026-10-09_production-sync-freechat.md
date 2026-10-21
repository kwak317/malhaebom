# Worklog — feat: 운영 자유채팅 요청 분기와 근거 검증 반영

- 일시: 2026-10-09 11:09 KST
- 작업자: Codex / kwak317
- 관련 PR: production-sync stack 3/11, base `codex/production-sync-selection-20261009`
- 관련 요구사항: 운영 원본 기준 GitHub 동기화, PR만 생성, merge·운영 변경 금지

## 1. 목적

요청 분기와 Prompt·Skill·근거 계약을 하나의 모듈 경계로 묶는다.

## 2. 작업 전 상태

main `fd9a6b9`와 운영 revision `malhaebom-mk2-request-trace-linkage-1009` 및 Vercel `dpl_CAho6AFsXoDTorgn3V8X9i47QVbE`를 고정했다. [비교 보고서](../evidence/production-source-sync-2026-10-09.md)와 [Spec](../specs/production-source-sync.md)을 따른다.

## 3. 수행 내용 및 주요 판단

운영 활성 기능을 반영하되 GitHub 전용 문서·migration·평가 자산과 인증/만료/단계 gate·버전 provenance 개선을 보존했다. 이전 checkout에서 운영 원본을 추정하지 않았다. 책임별 stack의 선행 PR을 base로 사용한다.

## 4. 변경 파일

- `backend/app/services/free_chat.py`
- `backend/app/services/free_chat_evidence.py`
- `prompts/free-chat-v4.md`
- `skills/free-chat-request-handling/SKILL.md`
- `backend/app/services/preparation_conversation_policy.py`

## 5. 검증

전체 통합 후보에서 frontend 220 tests와 TypeScript/Vite build 통과, backend 준비 68·런타임 92·회귀 122 tests 통과. 경험 확인 후 별도 저장 동의·단계 제한·강조 속 허위 완료 방지 추가 3 tests 통과. fake provider/repository이며 실제 모델 품질 검증은 아니다. 개별 중간 PR의 standalone E2E 통과를 뜻하지 않는다. diff 공백 검사·문서 참조·추적 artifact 검사·원본 및 Prompt SHA 검증도 통과했다.

각 PR은 base 대비 Review Core 800 LOC 이하로 제한하고 400 초과 사유를 PR 설명에 기록한다.

## 6. 발견한 문제 / 미확인 사항

전체 backend discover는 exit 137로 종료되어 전체 suite 통과를 주장하지 않는다. 운영 로그인·DB·마이크·실제 LLM E2E는 실행하지 않았다. Prompt snapshot은 원격 최신을 기록하는 자산이며 Langfuse 등록/라벨 변경을 수행하지 않았다. 준비 Prompt는 운영 로컬 v3.3이 원격 @1과 달라 현재 선택 동작을 보존한다.

## 7. 다음 작업

팀원이 순서대로 검토하고 통합 후보와 실제 운영 E2E의 차이를 확인한다. 이 작업에서는 merge·배포하지 않는다.
