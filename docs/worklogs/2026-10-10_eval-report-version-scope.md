# Worklog — 평가 리포트 날짜·버전·운영 근거 정리

- 일시: 2026-10-10 (KST)
- 작업자/에이전트: Codex
- 관련 요구: 평가 리포트의 과거 평가·현재 운영 구분, PR 보완 및 병합 요청 (기존 PR #238 재사용)

## 1. 목적

10/2 v5 후보 평가를 현재 운영 품질 평가로 오해하지 않도록 날짜·버전·증거를 명확히 표시한다.

## 2. 작업 전 상태

- GitHub main `dfd79bb7c66cc2f3c68093efc046e3832b9be75f` 기준으로 별도 clone에서 작업했다.
- 보고서 상단은 최신 측정을 10/2로 표시했지만 하단에는 10/6 당시 배포 구성 반복 평가가 연결돼 있었다.
- 10/9 운영 HTTP 증거와 에이전트 리포트가 main에 존재했다.
- 기존 `proj2-3` checkout에는 무관한 미커밋 변경과 fetch 시 참조 오류가 있어 그대로 보존했다.

## 3. 수행 내용과 판단

- 10/2 Prompt 전후 비교, 10/6 당시 운영 구성 90건 반복 평가, 10/9 운영 HTTP 확인을 상단 표로 연결했다.
- v5·로컬 기본값·출시 게이트 등의 표현에 평가 당시 날짜와 후보 범위를 명시했다.
- 기존 평가 수치·판정·원본 결과는 보존했다. 새로운 실험이나 과제 충족 판정을 추가하지 않았다.

## 4. 변경 파일

- `EVAL_REPORT.md`: 기준 표·근거 링크·날짜 표현 정리
- `docs/worklogs/2026-10-10_eval-report-version-scope.md`: 작업 기록
- `docs/worklogs/README.md`: 기록 링크

## 5. 검증

- 보고서의 신규 로컬 Markdown 링크 대상 존재 확인: 통과.
- 기존 본문 표의 수치 셀 보존 확인: 통과.
- 10/6 반복 평가 원본 보고서 및 10/9 운영 HTTP 증거와 상단 요약 대조: 일치.
- `git diff --check`: 통과.
- `scripts/check_pr_policy.py`: 통과.

## 6. 15:05 KST 후속 운영 구분 및 검증

- 사용자 요청에 따라 기존 PR #238을 보완하고 병합까지 진행한다. 최신 `origin/main` `0d182a99`를 merge해 기준을 동기화했다.
- Cloud Run 서비스 `status.traffic`에서 `malhaebom-mk2-custom-question-1010` 100%를 확인했다.
- 해당 revision의 image digest는 `sha256:a8a5ab966d8742dede8e1400426f20035dc7d71dc2b965c12394070d1f6eca19`다. 서비스 최신 template과 트래픽 대상 revision은 다를 수 있어 revision을 직접 조회했다.
- 코칭 환경 설정은 Gemini 3.5 Flash Lite, managed Prompt `malhaebom-coaching-v5-reinforced-verification` / `production` 라벨이다.
- 보고서 상단에 운영 확인 표와 과거 점수 재사용 금지 범위를 추가했다. 과거 평가 표의 수치는 변경하지 않았다.
- 실제 로드된 Prompt/Skill 본문·원격 숫자 버전, 새 LLM 평가·사람 평가·마이크 전체 E2E는 미검증이다.
- 기존 GitHub Actions 실패는 작업 시작 전 account payments/spending limit 문제로 job 자체가 시작되지 않은 상태였다. 코드 테스트 실패로 해석하지 않으며 문서 링크·diff·PR 정책을 로컬 검증한다.
- 이 작업은 문서 변경이며 운영 설정·Prompt·Skill·DB·트래픽을 수정하지 않았다.

## 7. 다음 작업

사용자가 승인한 범위에서 PR #238을 병합하고 main 반영을 확인한다. GitHub 검사 결과와 실제 수행한 로컬 검증은 최종 답변에서 구분한다.
