# Worklog — 코칭 Prompt·Skill 실행 버전 정합성

- 일시: 2026-10-02
- 작업: 강사 피드백의 Prompt·Skill 조립/관측 추적 보완
- 범위: 로컬 소스와 테스트만; 원격 Langfuse 게시·운영 배포는 제외

## 1. 목적

실제 조립한 코칭 Prompt·Skill 버전과 관측/DB에 기록되는 버전이 달라질 수 있는 경로를 수정한다. 판정 규칙과 평가셋, Prompt 문구는 변경하지 않는다.

## 2. 작업 전 상태

- 기본 로컬 조립은 `coaching-v5-skill-owned` + 카탈로그 `interview-coach-v6.1-domain-rules`을 사용한다.
- 공통 관측 상수 `DEFAULT_SKILL_VERSION`은 `interview-coach-v6`으로 오래됐으며 일부 런타임 기본값·Langfuse 자산 계획·API 관측·DB 저장에서 참조한다.
- 관리형 Langfuse Prompt를 선택해도 Supabase `coaching_runs.prompt_version`은 로컬 환경변수를 독립적으로 다시 읽었다.
- 이전 분리 검증은 통과했지만 실제 운영 컨테이너/관리형 Prompt 적용 여부는 알 수 없다.

## 3. 수행 내용

1. 기본 Skill 버전을 실제 Skill 카탈로그에서 가져오게 변경했다.
2. 유효한 코칭 결과를 저장할 때 코칭 서비스가 실제 선택한 Prompt·Skill 버전을 저장소에 전달한다. DB 저장 함수는 실행 버전을 명시적으로 요구하며 환경변수로 덮어쓰지 않는다.
3. API 요청의 코칭 관측값은 실제 서비스 버전을 우선한다. 코칭 서비스가 시작되지 않은 경로는 기존 환경변수/기본값을 사용한다.
4. stale 환경변수, 관리형 Prompt, DB·관측 버전을 검증하는 회귀 테스트를 추가했다.

## 주요 판단과 이유

- managed Prompt의 실제 선택값(예: `malhaebom-coaching@7`)을 로컬 Prompt 버전 대신 보존한다.
- 버전 메타데이터 정합성만 변경한다. Skill 판정 의미, 요청·응답 계약, 모델 호출, production label 및 기존 DB 행은 변경하지 않는다.
- 과거 DB 기록은 실행 당시 상태를 확인하지 못하므로 자동 보정하지 않는다.

## 4. 변경 파일

- `backend/app/services/coaching_observability.py`: 현재 카탈로그 기본 Skill 버전.
- `backend/app/services/coaching_runtime.py`: 실제 실행 버전 저장소 전달.
- `backend/app/services/supabase_coaching_runs.py`: 전달받은 실제 버전 저장.
- `backend/app/main.py`: 실제 서비스 Skill 버전 관측.
- `backend/tests/test_*.py` 일부: 기본 버전, managed Prompt, 환경변수 불일치 회귀 검증.
- `docs/CURRENT_STATE.md`, `docs/project2-checkpoint-work-cards.md`, 본 Worklog와 색인: 검증 범위 기록.

## 5. 검증

- 별도 `agent_env` (Langfuse SDK 4.15.1)에서 관련 테스트 7개 파일 합계 70건 전부 통과: Prompt·Skill 분리 14, Prompt 10, 런타임 25, 진단 9, Supabase 코칭 저장 2, 관측 8, Langfuse 자산 2.
- 기존 `proj2-3` 프로필은 Langfuse SDK 2.60.10이므로 `propagate_attributes`를 요구하는 관측·진단 테스트가 실패했다. 저장소 요구사항은 `langfuse>=4.7,<5`이며 준수 프로필의 테스트 통과와 구분한다.
- PR 작성 전 문서 링크 검사·PR 정책·`git diff --check` 검증을 수행한다.

## 6. 발견한 문제 / 남은 리스크

- 운영 이미지에 어떤 Prompt·Skill·Langfuse 관리형 버전이 올라가 있는지 확인하지 않았다.
- 임의의 명시적 `COACHING_SKILL_VERSION`은 현재와 다른 버전을 표시할 수 있으므로 운영 환경값과 실제 카탈로그 일치 여부는 별도로 확인해야 한다.
- 이번 검증은 새로운 LLM 품질 측정이나 D10 production trace 검증이 아니다.

## 미확인 사항

- 실제 운영 Langfuse 원격 Prompt 본문에 옛 Skill 규칙이 중복 포함되어 있는지, rollback 경로가 정상인지 미확인.

## 7. 다음 작업

- 배포 접근 권한 확보 후 현재 운영 리비전의 Prompt·Skill 버전과 요청별 trace를 확인한다.
- 팀 합의 후 최신 v5 사람 검토와 최종 출시 게이트를 별도 진행한다.
