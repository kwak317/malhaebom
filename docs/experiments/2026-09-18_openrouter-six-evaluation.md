# OpenRouter 6종 — Basic 전체 및 실패 실행별 Premium 복구

## 목적 / 실행 범위

사용자 승인: Basic 3종 × dataset v2 30건, 자동 품질 실패 실행에 대해서만 Premium 3종.
개인 키로 성공한 Qwen/case 02 smoke 이후 실행했다. 이전 smoke 비용/결과는 이번 평가 집계와 분리한다.

## 재현 / 환경

- artifact 및 실행 스크립트: `local-results/openrouter-six-20260918T083814Z/`
- 명령: `.venv-llm-eval/bin/python -B local-results/openrouter-six-20260918T083814Z/evaluate.py --live`
- `--live` 없는 실행은 기존 artifact 집계만 한다. 재실행은 이미 저장된 호출을 다시 보내지 않는다.
- Python 3.12.3 / OpenAI SDK 1.109.1, CPU API 클라이언트(GPU/CUDA N/A).
- 브랜치/commit/dataset hash/버전/config: manifest.json 및 호출별 comparison.json. 미커밋 변경은 working-tree.patch와 source-snapshot에 보존했다. 키/.env는 복사하지 않았다.
- 입력: dataset.v2.jsonl 30건, 동일 고정 Skill/운영 JSON Schema. expected/semantic annotation/Basic 출력은 모델 prompt에 넣지 않는다.

## 조건 / 정의

- 모델 ID는 기존 6종 그대로. Basic 3종 90건 후, 실패한 Basic 실행마다 각 Premium을 한 번씩 요청한다. 같은 case의 다른 Basic 실패도 별도 연결하므로 fallback 비용은 실제 요청 비용이다.
- strict JSON Schema, provider.require_parameters true, automatic provider routing. temperature/reasoning 미전송(모델 기본). timeout 60초 / SDK 자동 재시도 0 / 명시 max_calls 1. 기존 smoke 요청 조건 유지.
- client 동시 요청 최대 6. latency는 요청 시작부터 응답/실패까지이며 큐 대기는 제외. 동시 요청과 provider routing 영향을 받으므로 직렬 운영 latency로 해석하지 않는다.
- 원본/검증/usage/cost/provider/generation/latency와 parent_basic_execution_id를 호출마다 저장한다. 중간 실패에도 다른 케이스 계속 수행. 인증/계정 401/402/403 반복 2회 시 추가 제출 중단, 진행 중 요청은 저장한다.
- 품질 실패: 응답이 있는 schema/validator 오류, intent/C/A/V 오답, 기대 evidence 정확 불일치, ID 오류, 확정적인 자동 critical 탐지. API/provider/timeout는 별도 인프라 실패. 미검토 semantic null은 품질 실패 아님.
- critical 자동 범위: case23/28의 모든 활성 criterion met(injection 수용), case24의 어느 원문에도 없는 인용. 범위 밖 critical과 사람 semantic 점수는 null. 문자열만으로 자유서술의 날조를 인증하지 않는다.
- accuracy는 validator 통과 결과에 대한 각 dimension 정확도와 분모를 표시한다. evidence는 기존 grader의 기대 인용 정확 일치이고 의미 타당성 평가가 아니다. job alignment/status는 v2 고정 점수 제외.
- recovery는 원래 실패 일부가 아니라 전체 자동 품질 검사를 통과한 실행. Premium 인프라 실패는 복구 성공이 아니며 전체 Basic 품질 실패 분모는 유지한다.
- 비용은 usage.cost만 사용한다. 미확인 cost는 null이며 알려진 소계는 별도 표기한다. 성공당 비용은 해당 모델의 모든 호출 비용 / 자동 품질 통과 수. recovery당 비용/시간은 Premium 모든 시도 비용/시간 / 복구 수.
- 1회 실행이라 consistency는 미측정. 의미 품질 사람 검토/실제 인증 무효 여부는 별도 검토 대상.

## 진행 / 결과

사용자 추가 지시로 오늘 17:50(KST)에 중단하도록 제한했다.
17:47:30에 SIGINT로 신규 제출을 중단하고 진행 중 응답을 보존했으며 마지막 응답은 17:49:51.266 KST에 저장됐다. 강제 SIGTERM 없이 종료했다. 신규 제출 중단 후 새 호출 없음.

- 보존 응답: Basic 50건(Qwen 17, DeepSeek Flash 17, Gemini 16), Premium 0건. 남은 Basic 40건 미실행.
- contract 통과: Qwen 13/17, DeepSeek 16/17, Gemini 15/16.
- 전체 자동 품질 통과: 4/17, 6/17, 7/16. 품질 실패 13/11/8 = 32건.
- 인프라/판정불가 응답: Gemini case15는 raw null/input0/output0으로 모델 출력을 평가할 수 없어 품질 실패 제외. 원본 runner는 schema_violation로 기록했으므로 초기 분류를 initial_classification에 보존하고 후처리 분류 이유를 명시했다. finish_reason/full SDK completion은 기존 adapter가 저장하지 않아 추가 원인 단정은 하지 않았다.
- API 응답 latency p50/p95(초): Qwen 86.07/198.51, DeepSeek 72.51/235.39, Gemini 12.55/24.79. nearest-rank로 정렬 후 계산. partial case 집합 차이에 유의.
- 실제 usage.cost 합계: Qwen $0.039790776, DeepSeek $0.0460968686, Gemini $0.15729; 전체 $0.2431776446. 모든 보존 호출에서 usage.cost 확인. upstream 비용이 있어도 usage.cost=0인 응답은 0으로 사용했다.
- 재시도 0회. 각 요청 raw/usage/검증/provider/generation 모두 보존. 처리 중/미확인 비용 없음.
- critical 자동 범위(case23/24/28)에 도달하지 않아 검사 0건. critical/semantic 사람 점수는 null이며 0점이나 안전 통과로 간주하지 않는다.
- Basic failure set 32건 보존. Premium은 사용자 시간 제한으로 미실행이며 recovery rate/fallback 최종 비용 null. 복구 실패 0%로 해석하지 않는다.

전체 표/토큰/provider/실패 유형/소스 해시는 REPORT.md, summary.json, failure-details.json, inventory.json에 보존했다. 90건 완료 평가가 아니므로 최종 모델 선정 근거로 사용하지 않는다.
기존 운영 코드/모델/request 설정은 바꾸지 않았다. 집계 스크립트의 정렬 percentile/0-token 빈 응답 제외만 offline 후처리에서 확인했다.

## Worklog

[기록](../worklogs/2026-09-18_openrouter-six-evaluation.md)

## 21시대 재개

사용자가 “아까 중단한 거 마저”를 명시해 재개했다. 이전 17:50 제한은 종료된 첫 실행 기록이며 새 실행에는 적용하지 않는다.
이전 보고서/manifest/중단 기록은 history/before-resume-20260918T124200Z에 보존했다.
재개 전에 기존 원본 50건의 해시, dataset/Skill/grader/config 일치를 확인했다.
기존 50건 모두 호출 객체 생성 없이 재사용되는 mock 검증 50/50 통과 및 pending 목록과 겹침0 확인.
pending-basic-jobs.json의 40건만 whitelist로 제출하는 resume_pending.py --live --basic-only를 사용한다.
Basic 종료 후 실제 실패 수를 확정해 Premium 대기 목록을 별도로 고정한다. 기존 응답은 implicit retry하지 않는다.
재개 코드/대기 목록/skip 검사/manifest는 동일 artifact 디렉터리에 보존했다. 종료 후 기존 원본 해시 불변을 다시 검증했다.

## 재개 최종 결과

- 완료: Basic90건 + Premium162건 = 252건, 진행 중0, retry0. 이전50건 재호출 없음.
- Basic contract/품질통과/품질실패: Qwen22/8/22, DeepSeek Flash27/13/17, Gemini29/14/15(각30건). 빈 zero-token 응답1건 품질 제외.
- Premium contract/복구: DeepSeek Pro42/5, Sonnet5 42/11, GPT Terra54/8(각54건). 자동 recovery9.3%/20.4%/14.8%.
- 실제 usage.cost: Basic $0.4617437304812, Premium $3.56770831288, campaign $4.0294520433612. 미확인0건. smoke는 별도 비용.
- Premium recovery당 실제 추가비용: DeepSeek Pro $0.101351142576, Sonnet $0.2429681818181818, GPT $0.048537825. 모든 실패 시도 비용 포함.
- latency p50/p95(초): Basic Qwen102.755/183.376, DeepSeek46.090/217.213, Gemini11.317/19.077. Premium DeepSeek36.727/113.257, Sonnet30.798/51.569, GPT7.013/19.619.
- 자동 critical 탐지0/12검사. 제한된 case23/24/28 조건만 검사했으며 다른 critical 및 semantic 사람 점수 null.
- 최종확인: 모델별30/54건, 모든generation ID/attempt ID 유일, requested/returned 모델 동일, 부모는54품질실패만, 이전50 및 Basic90 원본 해시 불변, 비용/정렬 percentile 검증.
- 주요 Pydantic 오류: not_observed에 evidence 포함, 비충족 needed 누락. 기존 schema_valid는 Python 조건 검증도 포함하므로 JSON 문법 문제와 구분한다. 실제 상세는 schema-errors.json.
- 상세 label/evidence/ID/token/provider/failure-type recovery/9개 fallback 비용 조합은 REPORT.md 및 summary.json 참조.
- 한계: 자동 정답 일치/서버 계약 결과이며 의미품질을 인증하지 않는다. Premium은 실패 실행에 조건부로 평가되어 Basic 전체 정확도와 직접 비교하지 않는다.
운영 코드/모델/요청 설정 변경 및 PR/commit/push는 수행하지 않았다.

## 252건 offline 자동 평가 감사

추가 API 호출 없이 원본252건을 감사했다. [감사 Worklog](../worklogs/2026-09-18_openrouter-evaluation-audit.md)에 검증과 한계를 기록했다. 로컬 `local-results/openrouter-six-20260918T083814Z/analysis/AUDIT.md`와 `semantic-review.html`에 세부 수치 및 핵심15건6종 나란히 검토 자료가 있다. 재현은 동일 폴더 `analyze.py`, 이어서 `interpret.py`를 `.venv-llm-eval/bin/python -B`로 실행한다. stdlib만 사용하며 credential/network 모듈을 로드하지 않는다. 기존 원본 artifact의 전후SHA256 동일 검증을 통과했다.

Basic54실패는 고유24case, 3종 모두 실패14case. not_observed+evidence는27실행/34인용 모두 실제 해당segment의 부분인용이었다. evidence exact-match 불일치212항목 중147항목에 동일 정답segment의 합법부분인용이 존재하지만 의미적 충분성은 사람검토 대상이다. 입력 Skill과v2의 V/intent 정책 차이 및case20 criterion범위가 공통실패 원인 후보다. dataset/grader/schema/기존결과는 변경하지 않았고 semantic 및 사람critical점수도 null로 유지했다.

## 정책 정렬 후 offline 재채점

[정렬 Worklog](../worklogs/2026-09-18_evaluator-policy-alignment.md)에 변경·검증·재현을 기록했다.
최종로컬결과는 `local-results/openrouter-six-20260918T083814Z/regrade-policy-aligned/REPORT.md`.
원본252건 raw/usage/provider/generation/latency를 보존하고 별도 regrade 결과를 만들었다.
동일30입력/expected label은 유지하며 새정책의 support_segment_ids/선택근거정보를 명시했다.
Basic품질실패54→47,6종공통실패12→9. 원래54부모 모집단의Premium복구는DSPro8/Sonnet17/GPT9,
현재47실패부모로한정하면5/13/6이다. 새Skill로 생성된 응답이 아니며 label분모·evidence정의도달라
실제모델개선/prospective recovery로 해석하지 않는다. 추가API호출없음, semantic/사람critical null.
전체226테스트와전용Python3.12의CLI/30mock검증통과. 재채점소스snapshot/환경/hash를결과에보존했다.
