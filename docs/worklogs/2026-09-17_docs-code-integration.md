# Worklog — 코드 이관 후 문서 브랜치 통합·정적 audit

- 일시: 2026-09-17 (Asia/Seoul)
- 작업자/에이전트: Codex
- 관련 이슈/PR: 이관 PR #1; 이번 문서 PR은 이 브랜치로 생성
- 관련 요구사항/결정: 사용자 지시의 rebase → 정적 조사 → 문서 검증 → push → PR, merge 금지

## 1. 목적

기존 문서 커밋을 최신 main 위에 보존하고 실제 코드와 현재/목표 문서를 대조한다. 코드·dependency·CI 변경, 설치·모델/데이터 다운로드·heavy test 없이 문서 PR을 준비한다.

## 2. 작업 전 상태

- branch: `docs/project-bootstrap`, working tree clean.
- 보존 commit: `b31ce98412f56eae5142af57383bd656eb0be3a1`.
- 공통 base: `a6adb2002c794637234d6c1cc2a5a67902c1405e`.
- fetch 후 origin/main: `73525a159e3faa61114d968e6dbdd14d0fb85a82`.
- 코드 이관: `bab4317`의 앱 이관을 PR #1이 병합. GitHub mergedAt `2026-09-16T23:45:05Z`. frontend·backend/app·tts_worker·supabase/migrations 및 배포 파일을 확인했다.
- rebase 전 비교: main 측 235파일, 문서 측 25파일. 공통 수정 파일은 AGENTS.md와 README.md뿐. 소개·스택·실행 안내가 겹쳐 충돌을 예상했고 rebase 전에 기록했다.

## 3. 수행 내용

1. 원래 commit을 로컬 `docs/project-bootstrap-before-integration`에도 보존했다.
2. `git rebase origin/main`: AGENTS.md, README.md에서 실제 conflict 발생.
3. AGENTS: 이관된 프로젝트 소개·스택과 최신 운영 규칙을 병합. 목표 에이전트와 현재 구현을 구분하고 이관 대기 문구를 정정했다.
4. README: 이관된 Compose/uvicorn/npm/Vercel 안내를 유지하고 문서 목차·운영 규칙을 연결했다. 옛 scaffold 폴더 설명·중복 협업 설명은 현재 구조와 canonical 규칙으로 병합했다. 수업 협업 원칙을 보존했다.
5. 파일 전체 ours/theirs 적용 없이 내용별로 해결. rebase 후 bootstrap commit: `a2f9d7feea14e66f8c26eb272def337998791193`.
6. 이관 코드의 호출 경로·환경·음성 자산·인증/저장·배포 설정을 읽고 문서를 갱신했다. [CURRENT_STATE](../CURRENT_STATE.md), [음성 인수 기록](../experiments/2026-09-17_voice-asset-intake.md)에 근거를 연결했다.

## 주요 판단과 이유

- 코드 존재·정적 연결은 STATIC_CONFIRMED로 표기하고 실행 완료로 표현하지 않았다.
- 이관된 PRD/Spec·실험 기록은 과거 문맥을 보존하고 현재 기준 문서와 연결했다. 신규 도메인 정책을 기존 코드 동작에 맞춰 완화하지 않았다.
- 사용자가 승인한 초기 documentation bootstrap 1회성 400줄 예외를 DECISIONS와 PR 본문에 명시한다. 이후 일반 PR은 400줄 규칙을 적용한다.
- 기존 원문 파일은 변경하지 않았다. 두 기획서 파일은 636행 공백만 다르며 기존 경로를 보존한다. 실제 요구사항 편집은 canonical 운영 문서에서 한다.
- `.gitignore`의 `experiments/`가 새 음성 인수 Markdown까지 무시한다. ignore 설정은 수정하지 않고 해당 문서 한 파일만 명시적으로 force-add한다.

## 4. 변경 파일

- README, CURRENT_STATE, ARCHITECTURE, IMPLEMENTATION_PLAN: 실제 구현·실행 설정·재사용 순서.
- PROJECT_OVERVIEW, TARGET_STATE, REQUIREMENTS, CONSTRAINTS, DECISIONS, proposal/README: 이관 상태·현재/목표 및 원본 관계.
- docs/README, stt-current-status, tts-current-status, configs/stt/README, configs/tts/README: 과거 안내와 현재 코드 차이 표시.
- experiments/README 및 음성 인수 기록: 환경·모델·데이터·benchmark 위치와 미확인 사항.
- research/JOB_POSTING_RESEARCH 및 DECISIONS: 원본 보관 파일 밖의 후행 공백 정리.
- 이 Worklog. AGENTS/README 충돌 해결은 rebased bootstrap commit에 포함되며 audit 수정은 별도 commit이다.

## 5. 검증

- `git diff --check`: audit 수정 통과.
- 전체 branch의 `git diff --check origin/main`: 보존 원본 636행 Markdown 줄바꿈 공백 1건만 남는다. 원문 바이트 보존을 위해 제외하며, 원본 제외 검사는 통과.
- Python 표준 라이브러리 검사 통과 (저장소 상대 링크 206개, 보관 원문 절대 참조 16개 제외): Markdown 상대 링크 목적지 존재, 현재 문서의 코드 링크 존재, 변경 파일 확장자/크기, conflict marker 검사. 작성자 로컬 절대 경로는 아래 별도 기록.
- 원본 보관 파일은 최초 bootstrap의 Git blob과 동일한 바이트임을 비교하여 확인했다.
- `git diff --name-only origin/main -- backend frontend .github Dockerfile docker-compose.yml .env.example mcp_server supabase`: 출력 없음. 모든 추가·수정 파일은 Markdown, 가장 큰 파일 154,250 bytes. 새 모델/dataset/checkpoint 없음.
- origin/main의 비 Markdown 파일 191개가 working tree와 바이트 동일함을 확인했다. 최초 검사에서 Git의 한글 경로 quoting 처리 오류가 있었으며 NUL 구분 목록으로 수정해 통과했다.
- dependency 설치·앱 import/서버 실행·모델 호출·build·unit/E2E/heavy test는 수행하지 않았다. 이번 검증은 문서·Git 범위에 한정한다.

## 6. 발견한 문제 / 남은 리스크

- 2026-09-17 `gh issue list --state all --limit 100`: 기존 Issue 0건. 비교 화면 증가/동일에도 감소 문구, 단건 분석/재답변 만료 검사 누락, Compose에서 .env 예시의 localhost TTS 주소 덮어쓰기를 Issue 후보로 기록했다. 코드 수정·Issue 등록은 하지 않았다.
- 처음 카탈로그 경로 오류를 의심했으나 Path.parents 계산·파일 존재 대조로 올바른 경로임을 확인해 제외했다.
- 기획서 원본 두 파일에 작성자 `/Users/...` 절대 경로가 각각 8개 있다. 제공되지 않은 자료이므로 추정 생성·원문 수정하지 않는다. 저장소 상대 링크 오류와 구분한다.
- 과거 문서의 STT/VAD 미결합·TTS 실시간 미구현·전체 catalog draft 설명이 현 코드와 달라 현재 상태 정정 안내를 추가했다.

## 미확인 사항

실제 OAuth/JWKS/RLS·DB migration 적용·음성/Storage 접근·GPU/CUDA·체크포인트 hash·데이터 권한/split·환경 재구축·benchmark/성능 재현·삭제/만료·브라우저 마이크·Cloud Run/Vercel 배포·LLM/관측 연결은 실행 검증하지 않았다. 기존 실험 문서의 수치를 이번 측정으로 보고하지 않는다.

## 7. 다음 작업

동료 리뷰 후 작성자가 별도 작업으로 merge한다. 코드 Issue 후보를 승인된 별도 작업에서 검증/수정하고, 음성 환경 인수 → 기존 checkpoint benchmark 재현 → baseline 확정 순서로 진행한다. 신규 STT/TTS 학습 제외는 유지한다.
