# Worklog — 승인된 OpenRouter 6종 평가

- 일시: 2026-09-18
- 작업자: Codex
- 브랜치: feat/llm-evaluation-foundation
- 관련 승인: 사용자 Basic 90건 및 자동 품질 실패에 한정한 Premium 3종 복구 평가. PR/commit/push 금지.

## 목적 / 작업 전 상태

개인 키 Qwen/case 02 smoke 성공 이후 전체 비교를 실행한다. 전용 Python 3.12 환경과 기존 평가 설정/데이터/미커밋 변경을 보존한다.
필수 프로젝트 문서/evals README/실험 규칙을 읽었다.

## 수행 / 판단

요청별 checkpoint와 원본 오류를 보존하는 재현 스크립트를 local-results에 남겼다.
Basic 실패는 계약/label/evidence/ID/기계적으로 확인할 수 있는 critical만 포함한다. 인프라/미검토 semantic은 제외한다.
Premium은 원래 case 입력만 사용하고 Basic 출력은 전달하지 않는다. Basic 실패 실행별 별도 복구 요청으로 실제 fallback 비용을 측정한다.
계정/인증 반복 오류 2회 중단, 다른 개별 오류는 기록 후 진행한다. 키는 출력/복사하지 않는다.

## 변경 파일 / Artifact

- docs/experiments/2026-09-18_openrouter-six-evaluation.md, 본 Worklog
- local-results/openrouter-six-20260918T083814Z: driver, manifest, progress.log, records, snapshots, failure set, summary
- 기존 운영/평가 코드와 모델/request config는 수정하지 않는다. PR/commit/push 없음.

## 검증

- 네트워크 없는 mock failure 분류 검사: 정상 통과, injection all met 탐지, provider/timeout/rate_limit 품질 실패 제외 통과.
- 실 API Basic 50건, Premium 0건. 17:47:30 제출 중단, 진행 중 요청 마지막 응답 17:49:51.266에 저장 후 17:50 이전 종료.
- offline 최종 확인: 50건 generation/provider/usage.cost 존재, generation ID 중복 없음, semantic 전 항목 null, 제출 중단 이후 started_at 없음, in-flight 0, 정렬 nearest-rank p50/p95 정확성 확인.
- 품질 실패 32건(13/11/8), 인프라 1건(빈 응답+토큰0). initial_classification을 보존해 후처리 제외 이유 명시.
- token/reasoning/cache/실제 비용 합계 및 성공당 비용 REPORT.md/summary.json 생성. 실제 전체 비용 $0.2431776446, 미확인 0건. 재시도 없음.
- git diff --check 통과. PR/commit/push 없음.

## 미확인 / 다음

사용자 오늘 17:50 중단 지시를 반영했다. 남은 Basic 40건과 Premium 복구는 미실행이다.
critical 검사 대상 case23/24/28에 도달하지 않아 자동 critical 0건 검사, 사람 semantic/critical null.
HTTP timeout 60초는 keepalive 때문에 전체 wall duration 상한이 아니다. 반환된 일부 usage.cost=0은 upstream_inference_cost로 대체하지 않았다.
향후 재실행은 새로운 사용자 지시에 따라야 한다. 이전 응답을 보존하고 미실행 호출만 별도 진행할 수 있다.

## 재개 (같은 목적)

사용자 재개 지시 후 기존 50건의 파일 해시 및 dataset/Skill/grader/request config 일치를 확인했다.
자동 승인 검토는 첫 명령에서 timeout, 한 번 재시도는 중복 호출 보장 부족으로 거절했다.
거절을 우회하지 않고 50건 전부 SDK 객체도 생성하지 않는 mock skip 검사를 수행했다.
manifest에 남은 40건/기존 겹침0을 고정하고 호출 범위를 명시적으로 줄인 안전한 Basic-only 재개 명령이 승인됐다.
관련 증거: resume-baseline.json, resume-skip-proof.json, pending-basic-jobs.json, resume_pending.py.
이전 중단 기록/보고서는 history에 보존했고 실제 요청/키/운영 코드/모델 설정은 변경하지 않았다.
Basic 종료 후 Premium 실패 목록을 확정하여 동일 승인 범위에서 계속한다. PR/commit/push 없음.

### 재개 Basic 완료 / Premium 시작

- Basic 90건 완료(기존50+신규40), 기존50 파일 해시 불변 확인.
- 자동 품질 실패54건(Qwen22/DeepSeek17/Gemini15), 인프라 빈 zero-token 응답1건 제외.
- pending-premium-jobs.json에54×3=162개 부모 연결 요청을 고정, Basic 결과90건 해시 guard 추가.
- Premium-only dry-run: basic_calls0 / premium_calls162 / external_requests0.
- Premium request mock 검사: user payload가 question/server_context만 포함, Basic 출력/expected annotation 없음. strict schema/require_parameters true, temperature/reasoning 미전송 확인.
- 고정 manifest와 부모 조건/모델 범위 guard를 갖춘 Premium-only 명령 승인 후 실행 중.


### 재개 최종 확인

252건(Basic90+Premium162) 완료, Basic 품질 실패54건에만 Premium 연결. 기존50/Basic90 파일 해시 불변.
Generation/attempt ID 유일, requested/returned model 동일, 부모가 해당case 품질실패인지 검사 통과.
Token/provider/usage.cost/raw 및 validation 보존; 모든usage.cost 확인. 실제 합계 $4.0294520433612.
Premium 복구 DeepSeek5/54, Sonnet11/54, GPT8/54. 자동critical0/12검사, 사람semantic/critical null.
JSON/Pydantic schema-errors.json을 offline 재검증했으며 조건 검증 오류와 JSON 문법을 구분해 보고서에 명시했다.
최종분위수 sorted nearest-rank/금액 합계 검증, inventory 진행 중0/미실행0/retry0 확인.
REPORT.md/summary.json/csv/failure-details/basic-failure-set/verification/inventory와 이전phase history를 보존했다.
오프라인 확인 초기에 불필요한 appdirs import로 실패한 명령은 제거 후 필요한 표준 라이브러리/Pydantic만 사용해 재검증했다. 추가 패키지는 설치하지 않았다.
git diff --check 통과. 기존 모델/요청/운영 코드 변경, PR/commit/push 없음.
