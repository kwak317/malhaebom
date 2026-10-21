# Worklog — 최신 영문 Prompt 측정과 EVAL_REPORT 보완

## 목적과 범위

사용자 스크린샷에서 지적한 EVAL_REPORT 4·6·7장의 빈 비교표와 현재 기본값/측정 Prompt 불일치를 해소한다. [Spec](../specs/latest-english-prompt-eval-report.md)에 조건을 먼저 고정했다. 기존 파일은 `local-results/latest-english-v5-20261002/EVAL_REPORT.before.md`에 백업했다. 다른 로컬 변경은 보존했다.

## 수행

- 현재 로컬 기본 영문 `coaching-v5-skill-owned`, Skill `interview-coach-v6.1-domain-rules` 확인.
- 같은 Skill·모델·합성 30건에서 이전 영문 v4와 최신 v5를 각각 1회 실제 OpenRouter 호출. 이전 모델의 역사 기록은 보존하고 중복 장 제목은 과거 기록으로 표시.
- 계약 양쪽 30/30, 자동 전체 22/30→20/30, 기대 판정 116/120→107/120, 비용 $0.19638110→$0.17027067, p95 4.621초→4.622초. 총 60호출, 보정 0회. 최신 v5 개선 승격은 보류이며 운영 기본값 변경은 하지 않았다.
- 변경 파일: `EVAL_REPORT.md`, `evals/run_prompt_version_comparison.py`, `evals/README.md`, Spec·실험 문서·Worklog·각 index·CURRENT_STATE·체크포인트 D12 부분 상태.

## 검증과 실패 처리

- 기존 실행 컨테이너의 `/tmp/latest-english-v5-20261002`에 소스만 복사해 평가; 운영 `/app`은 변경하지 않았다. Python 3.12.14 / openai 1.109.1 / pydantic 2.13.5.
- `test_coaching_eval_v2`, `test_evaluator_policy_alignment`, `test_prompt_skill_separation`: 30개 통과. 최초 부분 테스트 복사에서 의존 모듈 누락으로 import 3건 실패, 전체 tests 복사 후 복구.
- JSON 저장 후 Markdown 작성에서 비교용 `prompt_sha256` metadata 누락 KeyError가 발생했다. 후보별 해시 참조·criteria version을 채우고 저장된 결과만 재렌더링했다. provider 재호출 없음.
- CLI help·Python 구문 검사 및 원시 결과 독립 집계 확인. 원시 결과/해시/결합 Prompt/요약은 Git 제외 `local-results/latest-english-v5-20261002/`에 보존한다.

## 한계와 다음 작업

각 30건 1회이며 순서/캐시/provider/시간대 미통제다. 현재 Skill에서 Prompt만 비교했으므로 과거 다른 Skill의 v4 전체 구성을 재현한 것은 아니다. 사람 semantic/critical·운영 E2E·R/D·실제 공고 관련성·TTFT는 미검증이다. 최신 v5 경계/실패 유도 게이트는 미달하며 반복·사람 검토와 비용 상한 합의가 남는다. 배포·Langfuse 게시·commit/push/PR/merge는 하지 않았다.

## PR 준비 검증

사용자의 PR 생성·비머지 요청에 따라 `origin/main`의 `9ee64fe`에서 별도 worktree를 만들었다. 최신 v5/Skill은 이미 main에 있으며, 측정된 dataset·grader·schema·validator·Skill·Prompt 파일은 main과 byte 일치를 확인했다. main의 평가 runner에 Gemini strict schema 분기만 반영하고 회귀 테스트를 추가했다. 로컬 두 단계 추출/승격 게이트 등 무관한 실험 코드는 PR에 포함하지 않는다. 원시 응답·환경변수·비밀값도 제외한다.

PR 기준 관련 unittest 42개 통과, 재현 harness CLI help 통과, diff 공백 검사 통과. 이번 PR 준비에서는 provider를 재호출하지 않았다.
