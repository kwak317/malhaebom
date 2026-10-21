# Worklog — LLM 평가 이력·재현 경로 정리

- 일시: 2026-09-21
- 작업자/에이전트: Codex
- 관련 문서: `EVAL_REPORT.md`, `docs/DECISIONS.md`

## 목적

새 API 실험 없이 초기 후보 비교, OpenRouter diversity/follow-up, Final Four의 목적·결과·판단 변화를
Git 추적 문서와 재현 코드로 연결한다. 같은 수치의 중복 문서를 만들지 않고 canonical을 명확히 한다.

## 작업 전 상태

- 초기 비교는 `EVAL_REPORT.md`, 2026-09-18~19 개별 실험 문서와 Decision에 충분히 기록돼 있었다.
- Diversity 1차는 open PR #36/#37의 기존 실험 문서·CLI에 기록돼 있었고 follow-up은 로컬 결과만 있었다.
- Final Four는 로컬 raw/summary와 blind CSV만 있고 Git 추적 실험 문서·재현 wrapper가 없었다.
- 현재 작업 전 worktree는 깨끗했고 STT/TTS 변경은 없었다.

## 수행 내용

- `EVAL_REPORT.md`를 세 단계 전체 흐름의 canonical entry point로 확장했다.
- 기존 diversity 문서에 preflight 탈락, follow-up, 누적 수치만 병합했다.
- Final Four 개별 실험 문서, 고정 4종 runner, blind pack builder, 1~5점 aggregator를 추가했다.
- 기존 2026-09-19 decision을 유지하고 2026-09-21 후속 decision을 추가했다.
- `evals/README.md`에는 실행법과 canonical 링크만 추가했다.

## 근거 대조

- 초기 수치: `EVAL_REPORT.md`, Basic/Premium experiment, Worklog, Decision 상호 대조.
- Diversity: `summary.json`, follow-up `summary.json`, `combined-summary.json`, manifest 대조.
- Final Four: `run-summary.json`, manifest, 120개 호출 record 대조. Terra20건은
  `raw_output=null`/`provider=null`/`ValueError`를 확인했다.
- API 재호출과 사람 semantic 평가는 수행하지 않았다.

## 변경 파일

- `EVAL_REPORT.md`, `docs/DECISIONS.md`, `docs/CURRENT_STATE.md`
- 기존 `docs/experiments/2026-09-21_openrouter-model-diversity.md`
- 신규 `docs/experiments/2026-09-21_openrouter-final-four.md`
- `evals/README.md`
- `evals/run_openrouter_final_four.py`
- `evals/build_final_four_semantic_review.py`
- `evals/aggregate_final_four_semantic.py`
- 본 Worklog

## 검증·미확인 사항

- 관련 Python 5개 `py_compile` 통과.
- Final Four dry-run은 4모델·120건 계획과 `network_calls=false`를 확인했다.
- 기존 로컬 결과로 blind CSV 120행·core15 60행을 재생성하고 빈 점수 집계가 빈 결과임을 확인했다.
- 신규 OpenRouter diversity4테스트와 기존 coaching eval5테스트, 총9테스트 통과.
- `git diff --check`, local Markdown link 32개(`broken_links=0`)를 확인했다.
- 변경 10파일에서 실제 OpenRouter key와 일반 secret pattern 일치가 모두 0건이며 STT/TTS 변경도 0건이다.
- 사람 semantic 결과와 production 모델 확정은 미완료다. `local-results/` raw는 계속 Git 제외한다.
