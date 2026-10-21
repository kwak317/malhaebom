# 최신 영문 v5 Prompt 동일 조건 비교 — 2026-10-02

## 목적과 조건

EVAL_REPORT 4·6·7장의 빈 비교표와 기본 Prompt 불일치를 해소한다. 최신 로컬 영문 `coaching-v5-skill-owned`와 이전 영문 `coaching-user-supplied-v4-verification`을 같은 현재 Skill·합성 데이터·모델에서 실호출했다. 사용자 요청에 따른 평가이며 운영 배포·Langfuse 게시·Git push는 제외했다.

- 모델: `google/gemini-3.5-flash-lite` / OpenRouter 자동 routing.
- Skill: `interview-coach-v6.1-domain-rules`, 기준 `problem-solving-v4-draft.3`.
- 평가셋: `evals/dataset.v2.jsonl` 합성 30건 (정상 12 / 경계 10 / 실패 유도 8). 기대 정답은 LLM 입력에 없음.
- 각각 1회, v4 전체 후 v5 전체 실행. Prompt만 변경; 당시 v4+Skill v6와의 역사 재현 비교는 아님.
- strict JSON Schema, max completion tokens 2048, timeout 45초, SDK retry 0, 계약 보정 최대 1회(총 2호출 제한). 실제 총 60호출·보정 0회.
- 환경: 기존 Docker 컨테이너의 `/tmp/latest-english-v5-20261002` 격리 소스; 운영 `/app` 변경 없음. Python 3.12.14 / openai 1.109.1 / pydantic 2.13.5.
- 기준 commit: `5d5dfc8714a58c7acb309f573a0578a0ee7de9c8` + 미커밋 Prompt/Skill/eval 소스. 원시 결과의 `source_manifest.json`으로 파일 해시 고정.

## 버전과 해시

- before_v4: `coaching-user-supplied-v4-verification`, 결합 시스템 Prompt SHA256 `c5bfcc401c0ac8346db7837a4ac9eb1e7ad2465ddfd822b62331a43dd49a3258`.
- latest_v5: `coaching-v5-skill-owned`, 결합 시스템 Prompt SHA256 `c4194d1a477bc38a667d27de806c49a04c78e5246c69eb8c4cd4e84505ca86a3`.
- Skill bundle SHA256: `6e12aeb78b1e1463022acedc22ae6498dfc035c867a8661277bfa5e2f90a67ae`.
- 정규화 Dataset SHA256: `fac706e33a98828bb980ad9d421e0e68836e7e657157011e91e3bf93dab5a7dc`.
- Schema SHA256: `ace4c2b20ea43e71d1e18fe6e964c07ffbb85dc5b417b8e8197739a4e2d704f0`.
- 생성 시각 UTC: `2026-10-02T00:19:14.005674+00:00`.

## 집계

| 지표 | 이전 v4 | 최신 v5 |
| --- | ---: | ---: |
| 최초/최종 계약 | 30/30 · 30/30 | 30/30 · 30/30 |
| 종합 자동 통과 | 22/30 | 20/30 |
| 판정 | 116/120 | 107/120 |
| 근거 | 63/63 | 58/61 |
| p50 / p95 | 3.847초 / 4.621초 | 3.939초 / 4.622초 |
| 비용 | $0.19638110 | $0.17027067 |

종합 자동 통과 = 계약 + 적용되는 모든 label + support evidence + 질문 존재/행동 대상 자동 정책 검사. null 정책은 검사 제외. 의미 품질·critical은 새 사람 검토가 없으므로 null이며 0건 발생으로 해석하지 않는다. 근거 분모는 출력마다 검사 대상이 달라 단순 개수 비교에 주의한다.

## 문항별 전후와 회귀

| Case | v4 | v5 | 최신 실패 검사 |
| --- | --- | --- | --- |
| `coach-normal-01` | 통과 | 통과 | — |
| `coach-normal-02` | 통과 | 통과 | — |
| `coach-normal-03` | 통과 | 통과 | — |
| `coach-normal-04` | 통과 | 통과 | — |
| `coach-normal-05` | 통과 | 통과 | — |
| `coach-normal-06` | 통과 | 통과 | — |
| `coach-normal-07` | 실패 | 통과 | — |
| `coach-normal-08` | 통과 | 통과 | — |
| `coach-normal-09` | 통과 | 실패 | criterion:result_verification |
| `coach-normal-10` | 통과 | 실패 | criterion:problem_context, action_targets |
| `coach-normal-11` | 통과 | 통과 | — |
| `coach-normal-12` | 통과 | 통과 | — |
| `coach-boundary-13` | 통과 | 실패 | criterion:own_action |
| `coach-boundary-14` | 통과 | 통과 | — |
| `coach-boundary-15` | 통과 | 통과 | — |
| `coach-boundary-16` | 실패 | 실패 | criterion:own_action |
| `coach-boundary-17` | 실패 | 실패 | criterion:own_action, criterion:result_verification |
| `coach-boundary-18` | 통과 | 통과 | — |
| `coach-boundary-19` | 실패 | 실패 | criterion:problem_context, criterion:own_action |
| `coach-boundary-20` | 통과 | 실패 | criterion:problem_context, criterion:own_action, criterion:result_verification |
| `coach-boundary-21` | 실패 | 실패 | question_presence |
| `coach-boundary-22` | 통과 | 통과 | — |
| `coach-failure-23` | 실패 | 통과 | — |
| `coach-failure-24` | 통과 | 통과 | — |
| `coach-failure-25` | 통과 | 통과 | — |
| `coach-failure-26` | 통과 | 통과 | — |
| `coach-failure-27` | 실패 | 실패 | intent |
| `coach-failure-28` | 통과 | 통과 | — |
| `coach-failure-29` | 통과 | 통과 | — |
| `coach-failure-30` | 실패 | 실패 | intent, action_targets |

v4 통과 → v5 실패: `coach-boundary-13`, `coach-boundary-20`, `coach-normal-09`, `coach-normal-10`.
v4 실패 → v5 통과: `coach-failure-23`, `coach-normal-07`.

## 판단과 한계

- 최신 v5는 비용 약 13.3% 감소, 종합 자동 통과 22→20, 판정 116→107. 개선 후보 승격은 DISCARD/보류이며 구조 분리와 측정 기록은 보존한다. 기본값 변경·운영 rollback은 하지 않는다.
- 기존 runner 승격 집계는 질문/행동 정책을 제외해 v5 정상10/경계5/실패유도6; 정책 포함 집계는 정상10/경계4/실패유도6. 둘 다 경계≥7 및 실패유도≥7 미달.
- 최초 계약 100%·p95≤10초는 이 합성 runner 범위의 통과다. 사람 안전성·비용 상한·로그인 운영 E2E는 미검증/미정. R/D와 원문 공고 관련성도 이 30건 평가에 포함하지 않는다.
- 각 case 1회, 순서·provider·캐시·시간대 미통제. 반복 consistency, 일반화, Prompt 변경의 인과효과는 확정하지 않는다. TTFT를 측정하지 않았으며 과거 TTFT 수치를 이번 결과로 쓰지 않는다.
- JSON 결과 저장 후 Markdown 생성에서 `configuration.prompt_sha256` 누락 KeyError가 발생했다. 후보별 해시 참조와 criteria version을 보고서 metadata에 추가하고 저장 결과로 Markdown을 복구했다. 추가 provider 호출은 없었다.

## 재현과 증빙

```bash
PYTHONPATH=backend:. python evals/run_prompt_version_comparison.py \
  --output-dir local-results/latest-english-v5-NEW-RUN
```

Python 3.12 평가 환경과 OpenRouter 키가 필요하며 키를 출력/커밋하지 않는다. 첫 명령은 실제 유료 API를 호출한다. 원본 `local-results/latest-english-v5-20261002/`의 `comparison.json`, `plan.json`, 결합 Prompt 두 파일, `source_manifest.json`, `summary.json`, `summarize.py`를 보존했다. 원시 응답은 Git 제외이며 보고서에는 집계·실패 검사만 기록한다. 재현 시 같은 snapshot 파일과 해시를 확인한다.

검증: 관련 평가/정책/Prompt 결합 unittest 30개 통과, harness CLI help 및 Python 구문 확인, report JSON으로 집계 재검산. 최초 테스트 복사에 의존 테스트가 빠져 import 3건 실패했고 전체 tests를 복사해 필요한 3개 모듈의 30개 테스트 통과를 확인했다.

PR 준비 검증: `origin/main` 9ee64fe 기반 격리 worktree에서 Gemini strict schema 회귀 테스트를 포함한 관련 unittest 42개가 통과했다. 위 명령은 새 실행 결과를 생성하며, 이전 실행의 로컬 집계 스크립트는 저장소에 포함하지 않는다.
