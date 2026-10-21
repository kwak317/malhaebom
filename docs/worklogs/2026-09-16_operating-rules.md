# Worklog — 프로젝트 운영 규칙 추가

- 일시: 2026-09-16 (Asia/Seoul)
- 작업자/에이전트: Codex
- 관련 이슈/PR: 생성하지 않음
- 관련 결정: [운영 규칙 결정](../DECISIONS.md)

## 1. 목적

개발·Git/PR·Issue·실험 재현·STT/TTS fine-tuning·CI 자원 보호 규칙을 문서화한다. AGENTS를 canonical entry point로 유지하고 앞선 미커밋 문서를 보존한다. 실제 코드·학습·설정·GitHub 작업은 수행하지 않는다.

## 2. 작업 전 상태

- 현재 브랜치는 `main`. 기존 미커밋 문서 작업을 유지한 채 요청된 문서만 편집했으며 브랜치 전환·생성·commit·push는 하지 않았다. 이번에는 기능 작업이 없다. 후속 작업은 새 prefix 규칙에 맞는 작업 브랜치에서 진행한다.
- `git status --short --untracked-files=all`: tracked 수정 4개(AGENTS/README/evals README/Skill), untracked 문서 18개. staging은 비어 있었다.
- tracked/untracked 파일 38개의 시작 SHA256을 임시 기록했다. 이전 bootstrap/요구사항 통합 변경을 리셋하거나 제거하지 않았다.
- 필수 읽기 문서 5개, README, AGENTS, CLAUDE, DECISIONS, IMPLEMENTATION_PLAN, Worklog 안내·템플릿, 기존 PR 템플릿을 조사했다.
- README에는 main 직접 push 금지·feat/fix 예·동료 승인 규칙이 있고 CLAUDE는 AGENTS를 참조한다. AGENTS에는 Spec/AC·범위·Worklog 규칙이 있다.
- 실험 전용 문서가 없었다. 신규 STT/TTS 학습은 기존 범위에서 제외되어 있다. CI workflow 파일이 존재하지만 실제 실행·원격 보호 설정은 확인하지 않았다.

## 3. 수행 내용

- AGENTS에 Git/branch/commit, PR/review/merge, Issues, 실험 필수 규칙 및 링크, CI 자원 보호, 기술적 강제 상태 구분을 추가했다.
- Git type 8개와 branch/commit 형식, 논리적 변경 단위, 선별 staging·dirty tree 보존을 명시했다.
- PR 단일 목적·400줄 원칙·예외 파일 설명, 다른 팀원 승인, 미해결 리뷰 차단, 작성자 merge 및 예외 이유 기록을 명시했다.
- 기능 문제의 Issue 대상·재현 정보·중복 확인·해결 PR 연결·무관한 버그 분리를 명시했다. 이번에는 Issues를 생성하지 않았다.
- `docs/experiments/README.md`에 환경·모델·데이터·설정·명령·평가·결과 재현 기록을 정리했다. 불필요한 빈 STT/TTS 디렉터리는 생성하지 않았다.
- STT/TTS는 자산 조사→환경 재구축→기존 checkpoint benchmark 재현→baseline→신규 데이터 fine-tuning→동일 benchmark 비교 순서로 정리했다. 기존 train 재사용 금지, test/benchmark 학습 금지, validation 모델 선택 및 test 최종 평가, 동일 평가 조건·회귀 기록을 명시했다.
- 일반 CI의 전체 ML 환경·대형 모델/데이터 자동 다운로드 금지, 가벼운 gate와 heavy validation 분리, cache hash·timeout·concurrency·변경 영향 검토·원인 조사 후 rerun을 명시했다.

## 주요 판단과 이유

- 상세 Git/PR·Issue·CI 정책은 AGENTS 한 곳에 둔다. README의 기존 겹치는 규칙은 참조로 병합하고 수업의 제출·협업·시크릿 안내는 보존했다. 커밋 계정·공동 작성자 규칙은 AGENTS로 옮겨 유지했다.
- README 예시의 `git add .`는 작업 파일을 선별하는 방식으로 바꿔 기존 변경 혼입을 방지했다. 충돌 해결 커밋 예시에도 type을 붙였다.
- 400줄은 base 대비 추가·삭제 합계로 정의했다. AI 보조 코드/문서도 사람의 리뷰 대상이므로 자동 생성 artifact 예외로 우회하지 않게 명시했다. 실제 PR 생성/분할은 수행하지 않았다. 앞선 미커밋 문서 묶음도 추후 PR에서 목적별 분리·크기 검토가 필요하다.
- STT/TTS 학습 제외를 해제하지 않았다. 신규 실험 규칙은 향후 별도 범위 결정과 승인 후 적용한다. CONSTRAINTS와 DECISIONS에 이 해석을 연결했다.
- CLAUDE 위임, 기존 구현 계획·제품 요구사항·도메인 Skill·평가 계획은 그대로 유지했다. 새 규칙을 다른 문서에 길게 복제하지 않았다.

## 4. 변경 파일

| 구분 | 파일 | 내용 |
| --- | --- | --- |
| 기존 수정 | `AGENTS.md` | 운영 규칙 canonical 및 상세 실험 링크 |
| 기존 수정 | `README.md` | 운영·실험 링크, 중복 규칙 통합, Git 예시 정합성 |
| 기존 수정 | `docs/CONSTRAINTS.md` | 현재 학습 제외와 향후 실험 규칙의 경계 |
| 기존 수정 | `docs/DECISIONS.md` | 단일 진입점·재현성·CI 자원 보호 결정 |
| 기존 수정 | `docs/worklogs/README.md` | 이번 기록 링크 |
| 신규 | `docs/experiments/README.md` | 실험 재현 및 STT/TTS 상세 규칙 |
| 신규 | `docs/worklogs/2026-09-16_operating-rules.md` | 이번 Worklog |

## 5. 검증

- 시작 파일 SHA256과 최종 파일을 대조해 기존 수정 5개·신규 Markdown 2개로 변경 범위를 제한했다. 기존 파일 삭제는 없다. 그 외 코드·CI·설정·의존성·기존 기획 원본·과거 Worklog 등은 시작 상태와 동일하다.
- 운영 문서 상대 Markdown 링크 77개를 검사하여 통과했다. 기획 원본의 기존 작성자 PC 경로 8개는 앞선 기록의 보존 예외로 유지했다.
- 브랜치/커밋 type, PR 크기·승인·merge·Issue, 실험 기록·데이터 분리·CI 보호 주요 조건을 검사하고 요청과 대조했다.
- `git diff --check` 통과. 신규 문서도 별도 공백 검사를 수행했다.
- `git diff --cached --name-only`는 비어 있다. Git status에는 이전 문서 변경도 포함되며 Skill/evals 수정은 이번 작업의 변경이 아니다.
- 문서 작업 AC만 검증했다. 코드 테스트, 모델/데이터 다운로드, benchmark, 학습, requirements 설치, CI 실행·수정, 원격 GitHub 설정/Issues 생성은 수행하지 않았다.

## 6. 발견한 문제 / 남은 리스크

기존 학습 제외와 fine-tuning 규칙이 승인 범위로 혼동될 수 있어 현재 범위를 명시했다. 기존 broad staging 예시를 선별 방식으로 수정했다. 사용자 요청에서 언급한 과거 dependency 다운로드 문제는 이번에 재현하거나 원격 로그를 확인한 사실이 아니다.

## 미확인 사항

다음은 문서 정책이며 이번 작업에서 기술적으로 설정·강제하지 않았다. 원격 기존 설정도 미확인이다.

- branch protection
- required approval
- 400-line PR limit
- workflow timeout
- concurrency / cancel-in-progress
- dependency split 및 cache 설정

현재 CI 성공 여부·실제 GPU/모델 성능·기존 benchmark 재현성은 검증하지 않았다.

## 7. 다음 작업

별도 승인된 후속 작업에서 원격 보호 설정·CI 구조를 확인하고 필요한 강제를 구현·검증한다. PR을 만들 때 기존 미커밋 작업을 목적별로 나누고 400줄 기준을 검토한다. 향후 STT/TTS 실험은 범위 결정과 이관 이후 문서화된 baseline 절차부터 시작한다. 이번 작업에서는 commit/push/merge하지 않았다.
