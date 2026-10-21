# Worklog — 기본 질문 전체 코칭

- 일시: 2026-09-28 13:06
- 작업자: Codex
- 관련 요구: 기본 질문 4번 외에도 코칭 제공. GitHub PR 생성·merge 금지.

## 1. 목적

화면 기본 질문 1~10번에서 확인된 답변을 질문에 맞는 기준으로 코칭한다.

## 2. 작업 전 상태

McpLlmCoachingService와 SupabaseCoachingContextRepository가 `preset-04`만 허용했다. 화면에는 기본 질문 10개, 참고 루브릭 파일에는 60개가 있었다. 원본 checkout의 기존 변경 116개를 보존하며 깨끗한 작업 브랜치에서 먼저 구현·검증한 후 로컬 실행 소스에 필요한 변경만 적용했다.

## 3. 수행 내용

- 기존 기본 질문 루브릭을 서버 질문 카탈로그로 연결하고 4번 전용 차단을 등록 질문 검사로 교체했다.
- 기본 면접 질문 27개 기준과 유형별 기준 버전을 추가했다. 문제 해결 전용 규칙을 다른 질문에 적용하지 않도록 Skill 적용 경계를 명시했다.
- 코칭·비교 화면의 한국어 기준 이름, Skill v5 기본값과 로컬 환경 버전을 맞췄다.
- 새로운 모델이나 추가 MCP 도구를 도입하지 않았다. DB schema·migration·평가셋·이전 제출자료는 변경하지 않았다.

## 주요 판단과 이유

- 화면의 기본 질문 10개를 요청 범위로 해석했다. 직접 입력 질문과 11~60번 추가는 포함하지 않았다.
- 원본 실행 소스와 최신 main의 문제 해결 기준이 다르므로 각각의 기존 4번 기준과 버전을 보존했다. 이 checkout의 기준은 5개 / `problem-solving-v4-draft.1`이다.
- 새 기본 질문 규칙은 기존 고정 루브릭을 연결한 팀 구현 초안이다. 외부 전문가 검토나 신규 질문별 품질 측정을 완료로 기록하지 않는다.
- 소유자·만료·질문/세션 일치, 정확한 인용, 허용 기준, 다음 행동 개수 검증을 유지했다.

## 4. 변경 파일

- `backend/app/services/coaching_questions.py`
- `backend/app/services/coaching_runtime.py`
- `backend/app/services/coaching_skill.py`
- `backend/app/services/supabase_coaching_context.py`
- `backend/app/services/coaching_observability.py`
- `backend/app/services/practice_history.py`
- `skills/SKILL.md`
- `skills/preset-interview.md`
- `skills/criteria.json`
- `frontend/src/components/CoachingResultPanel.tsx`
- `backend/tests/test_preset_coaching.py`
- `backend/tests/test_coaching_skill.py`
- `backend/tests/test_coaching_runtime.py`
- `frontend/src/components/CoachingResultPanel.test.tsx`
- `.env.example`
- `docs/specs/all-preset-question-coaching.md`, PROJECT_OVERVIEW/CURRENT_STATE/TARGET_STATE/REQUIREMENTS/CONSTRAINTS 및 이 Worklog

## 5. 검증

- backend 302개 / frontend 80개 전체 테스트 통과, frontend build 통과.
- 신규 통합 테스트: 10개 질문 모두 HTTP 200·needs_more_info 응답, 실제 stdio MCP 및 개발용 REST 조회, 질문별 criterion ID 검증, 질문 불일치에서 LLM 추가 호출 없음.
- Docker API·frontend 재빌드/재시작, health 및 18000/18080 HTTP 200 확인.
- 실제 OpenRouter 모델: 자기소개·협업 갈등의 서로 다른 기준으로 HTTP 200와 응답 계약 검증 통과. 테스트 인증·개발 문맥만 사용했고 사용자 DB 저장·Langfuse 전송은 하지 않았다.
- 요청 범위 밖 기존 변경은 원본 116개 파일의 SHA-256 비교로 보존 확인.
- `git diff --check` 변경 대상 및 깨끗한 작업 브랜치에서 통과.

테스트 기록: `/tmp/malhaebom-all-preset-backend-tests.log`, `/tmp/malhaebom-all-preset-local-backend-tests.log`, `/tmp/malhaebom-all-preset-local-frontend-tests.log`, `/tmp/malhaebom-all-preset-local-frontend-build.log`. 소스·환경 백업은 접근 제한된 임시 폴더에 보관했으며 기존 Docker 이미지는 `malhaebom-api-before-preset-coaching:20260928`, `malhaebom-frontend-before-preset-coaching:20260928` 태그로 보존했다.

## 6. 발견한 문제 / 미확인 사항

- 초기 테스트 기대값에 이전 Skill v4가 남아 새 버전에 맞게 수정했다. 로컬 구버전 적용 시 import 및 Skill 참조 경로 차이를 해결하고 전체 테스트를 다시 통과시켰다.
- 모델 호출 두 건은 운영 인증·실제 사용자 DB·MCP 전체를 거친 E2E가 아니다. MCP 연결은 별도 개발용 통합 테스트로 검증했다.
- 브라우저 로그인·녹음 전체 E2E 및 console 오류 조회는 미확인이다.
- v5 변경 전후의 코칭 결과는 기존 버전 비교 규칙에 따라 같은 기준으로 재분석하기 전 혼합 비교하지 않는다.

## 7. 다음 작업

로그인한 사용자의 질문별 녹음·전사 확인·코칭·재답변을 확인하고 추가 질문 규칙의 실제 품질을 독립 검토한다. 이번 작업에서는 commit/push/PR 생성/merge를 하지 않았다.
