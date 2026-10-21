# Worklog — evaluator 정책 정렬 및252건 offline 재채점

- 일시: 2026-09-18
- 작업자/에이전트: Codex
- 관련요구사항: 사용자 승인 intent독립 / 확인행위Vpartial / not_observed근거허용 / 지원segment채점
- 관련실험: [6종평가](../experiments/2026-09-18_openrouter-six-evaluation.md)

## 1. 목적

Skill/dataset/schema/grader 정책을 정렬하고 기존252응답을 추가API없이 재채점한다.

## 2. 작업 전 상태

기존평가기반 uncommitted 변경을 보존했다. focused 기존평가12테스트 통과.
252원본은Basic90+Premium162이며54실패부모/24고유case. not_observed의 원문인용 금지,
v2정답과Skill V경계 차이, intent독립 정책 전달 부족, quote exact-match가 확인됐다.

## 3. 수행 내용

Spec을 먼저 확장하고 Skill·criteria 카탈로그와 system prompt를 정책에 맞춰 명시했다.
Pydantic not_observed evidence금지를 제거하고 필요한needed/원문/ID/한국어/행동 검사는 유지했다.
서버validator는 이미 상태와무관하게 원문/ID를 검사하므로 중복규칙을 추가하지 않았다.
v2 expected evidence에 support_segment_ids/required를 추가하고 부재근거는 선택적으로 허용했다.
기준별 모든반환인용의 지원segment/실제연속원문 충실성을 채점하며 의미적충분성은 사람검토다.
기존v1데이터/quote채점과 requirement없는job/status제외는 유지했다.

전체30expected label을 정책으로 재검증해 그대로 유지했다. 다수모델출력으로 정답을 바꾸지 않았다.
승인된정책상 case20 비백엔드경험 C/A/V독립,16 주체모호 undetermined,04/09/18 확인행위partial을 명시했다.
독립전문가 검토완료를 의미하지 않는다. expected quote는 기존원문을 복사한 선택근거/예시이며 새평가입력 생성 없음.

stdlib/Pydantic 전용 재채점CLI를 추가했다. raw문자열 우선으로 parse/Pydantic/server검증/채점을 수행한다.
원래source_record를 그대로 보존하고 regrade 필드를 별도저장한다. 실패이어도 usage/cost/provider/generation/latency는 보존된다.
인프라품질실패 제외, 제한적자동critical 범위, semantic/사람critical null을 유지했다.
source-snapshot과 버전/hash/환경/불변검증을 새로운결과디렉터리에 저장했다.

## 주요 판단과 이유

- 원래generation과 새Skill추론은 다르므로 policy/Skill/content 및 schema구현 hash를 따로 기록했다. customvalidator변경은 JSONSchema hash만으로 식별할 수 없다.
- prompt 기본버전 coaching-output-v2, grader v4, policy 별도기록. 기존skill/criteria 카탈로그 ID호환성을 유지하고 변경된본문은bundleSHA256으로 구분한다.
- not_observed 근거는 허용사항이라 누락을 실패로 강제하지 않았다. 반환한 근거는 모두 검사한다.
- 기존54부모 모집단과 현재47실패부모의 저장Premium복구율을 분리했다. 기존Premium실행을 삭제하거나 새로운실행으로 간주하지 않았다.

## 4. 변경 파일

- `skills/SKILL.md`, `skills/problem-solving.md`, `skills/criteria.json`: 판정정책 정렬.
- `backend/app/schemas/coaching.py`: 부재판정 근거 허용.
- `backend/app/services/coaching_observability.py`, `evals/run_model_comparison.py`: 새prompt 기본버전과policy/schema구현버전.
- `evals/coaching_dataset.py`, `evals/dataset.v2.jsonl`, `evals/evaluation_records.py`: support채점/선택근거/참조검사/버전.
- `evals/regrade_saved_results.py`: 네트워크 없는 재채점CLI.
- `backend/tests/test_evaluator_policy_alignment.py`: 회귀9테스트.
- `docs/specs/coaching-evaluation-ops.md`, `evals/README.md`, `docs/CURRENT_STATE.md`, `docs/DECISIONS.md`, 기존실험기록과본Worklog.
- 로컬 `local-results/openrouter-six-20260918T083814Z/regrade-policy-aligned/`: 공식이번재채점결과. 개발중 `regrade-policy-v2*`는 중간artifact이며 최종결과가 아님.

## 5. 검증

```text
PYTHONPATH=backend:. .venv-llm-eval/bin/python -B -m evals.regrade_saved_results --input local-results/openrouter-six-20260918T083814Z/all-attempts.json --output-dir local-results/openrouter-six-20260918T083814Z/regrade-policy-aligned
성공252건. 원본hash/raw/source_record불변. 30intent/C/A/V 및question/context불변. 사람semantic null.
.venv-llm-eval: schema/validator9 + 기존평가12 + 환경/기록9 + 새회귀9 =39테스트 통과.
CLI --help, regrade에서dotenv/openai 미import, v2 30mock모두계약/채점통과, git diff --check 통과.
timeout 90 /tmp/llm-eval-tests/bin/python -B -m unittest discover -s backend/tests
최종226테스트 통과(2.166초). 기존보유 전체테스트환경 Python3.14사용, 실제평가환경/재채점은전용Python3.12.
```

처음 sandbox 전체테스트는 로컬TestClient의 anyio/thread wait에서 멈췄다. faulthandler로 확인하고 해당baseline만종료했다.
sandbox밖에서 mock/로컬전체테스트 통과. 평가전용venv에서 전체코칭API테스트는jwt등 비평가의존성 부재로import오류여서 기존전체테스트환경을 재사용했다. 새dependency설치/외부API호출은없음.

## 6. 발견한 문제 / 남은 리스크

Basic실패 Qwen22→18,DeepSeek17→14,Gemini15→15(인프라1별도), 합54→47/21고유case.
계약통과 Qwen22→26,DS27→30,Gem29→29,DSPro42→52,Sonnet42→51,GPT54→54.
Premium원래54부모 재채점복구 DSPro8,Sonnet17,GPT9. 현재47부모대상 DSPro5,Sonnet13,GPT6.
6종모든관측실행공통실패12→9:01,04,06,14,16,18,20,21,22.

label분모 확대와 evidence정의변화는 모델개선이 아니다. 새Skill정책 준수율/새비용/새latency는 미측정.
원문충실성통과가 의미적정확성/hallucination안전성을 보증하지 않는다. job/status정확도제외와job출력의구조/원문contract검사는별개다.
독립label 검토·사람semantic검토 미완료. 자동critical는원래제한적범위. 발견정책불일치에대한Issue등록은 이번추가API없음범위에서 미수행.

## 7. 다음 작업

API없이 label독립검토/15case사람semantic 먼저가능. 정책파일럿은공통9case×Basic3=27호출,
실패case합집합만Premium3종 각1회(max27추가). 최종전체30건 비교는 새Skill로Basic90호출후
새실패case합집합만Premium평가. 이번단계재호출/PR/commit/push 없음.
