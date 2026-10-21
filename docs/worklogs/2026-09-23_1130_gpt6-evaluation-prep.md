# 2026-09-23 GPT-6 Luna / Sol 평가 실행 준비

## 목적

OpenRouter에 추가된 GPT-6 Luna/Sol을 현재 서비스 기준인 Flash-Lite와 동일 조건으로 비교할 수
있도록 기존 평가 하네스를 재사용하는 실행 진입점과 재현 문서를 준비한다.

## 작업 전 상태

- 원 작업트리 `proj2-3`는 `docs/stt-71592-results` 브랜치였고 dirty file은 없었다.
- `origin` fetch 후 최신 `origin/main`은 `0d0659d8...`였다.
- 기존 Final Four 전용 runner는 과거 v3 조건을 보존한다.
- 최신 main에는 `coaching-output-v4.1 + problem-solving-v4-draft.1 + contract repair`가 이미 병합돼 있다.
- generic `evals/run_model_comparison.py`는 arbitrary OpenAI-compatible candidate, Dataset v2,
  case 선택, contract repair, usage/cost, repeat를 지원한다.

## 수행한 작업

1. 최신 `origin/main`에서 linked worktree
   `/home/honorbear/proj2-3-gpt6-eval`을 만들고
   `experiment/gpt6-luna-sol-evaluation` 브랜치를 생성했다.
2. OpenRouter 공개 페이지에서 2026-09-23 기준 모델 ID를 재확인했다.
   - `openai/gpt-6-luna`
   - `openai/gpt-6-sol`
3. 새 평가 로직을 복제하지 않고 generic runner를 호출하는
   `evals/run_gpt6_luna_sol_comparison.py`를 추가했다.
4. wrapper가 다음 조건을 고정하도록 했다.
   - Flash-Lite / GPT-6 Luna / GPT-6 Sol
   - Dataset v2
   - `coaching-output-v4.1`
   - `interview-coach-v2`
   - max calls 2
   - timeout 90초
   - preflight 대표 3건 또는 full 30건
5. `--live` 없이는 network call 없이 계획만 출력하도록 했다.
6. 실행 계획과 후속 의사결정 순서를
   [실험 계획](../experiments/2026-09-23_gpt6-luna-sol-evaluation-plan.md)에 기록했다.

## 주요 판단과 이유

- 과거 Final Four runner를 수정하지 않는다. 해당 runner는 2026-09-21 v3 실험 재현 자산이다.
- 현재 generic runner가 v4.1과 repair를 이미 canonical하게 구현하므로 모델 목록만 고정하는 얇은
  wrapper가 중복 구현과 평가 조건 drift를 가장 적게 만든다.
- 이번 단계에서는 Prompt/Skill/Criteria를 수정하지 않는다. 모델이 유일한 독립 변수다.
- repeat 3회용 후보는 full 30 결과 뒤 선정하므로 지금 고정하지 않는다.
- 비용은 공개 list price를 수동 계산하지 않고 실제 응답의 `usage.cost`를 사용한다.

## 변경 파일

- `evals/run_gpt6_luna_sol_comparison.py`
- `evals/test_run_gpt6_luna_sol_comparison.py`
- `docs/experiments/2026-09-23_gpt6-luna-sol-evaluation-plan.md`
- `docs/worklogs/2026-09-23_1130_gpt6-evaluation-prep.md`
- 실험/Worklog index 문서

## 검증 내용

준비 검증 뒤 실제 OpenRouter Preflight까지 수행했다.

검증 결과:

- wrapper dry-run PASS: 3개 candidate, v4.1, 대표 3개 case, 9 executions / 최대 18 calls 확인
- 신규 wrapper 테스트 3/3 PASS
- 기존 coaching prompt 테스트 8/8 PASS
- 기존 coaching eval v2 테스트 PASS
- 위 offline 검증은 등록 Python runtime `proj2-3`을 재사용했다
- system Python 직접 실행에서는 새 worktree에 의존성이 없어 `pydantic` import가 실패했으나,
  이는 코드 회귀가 아니라 worktree 전용 venv 미생성 상태임을 확인했다

## 발견한 문제

Preflight 실호출 결과:
- Flash-Lite: 3/3 최종 계약 통과, provider error 0, 알려진 비용 $0.009425
- GPT-6 Sol: 3/3 최종 계약 통과, provider error 0, 알려진 비용 $0.036649
- GPT-6 Luna: 첫 pass 2/3 최종 계약 통과, provider error 3회
- Luna failure-30 targeted rerun: 100% 계약/정확도, 16.47s, $0.000874
- Luna failure-30이 재실행에서 정상 통과했으므로 입력별 고정 호환성 실패로 확정하지 않았다
- 이후 동일 평가 venv에서 재실행한 Preflight는 세 모델 모두 3/3 정상 통과했다.

Full 30 정상 호출 결과:
- Flash-Lite: final contract 30/30, accuracy 81.0%, $0.11464, p50/p95 3.34s/3.94s
- GPT-6 Luna: 29/30, 89.4%, $0.02006, 9.03s/36.37s
- GPT-6 Sol: 30/30, 97.6%, $0.35244, 10.10s/33.70s
- Sol은 provider/contract 오류와 repair 없이 30건을 완료했다.
- 대표 사람 검토에서도 Sol이 질문 적합성과 C/A/V를 가장 일관되게 분리했다.

PR 리뷰에서 canonical runner가 `openai/gpt-5*`에만 strict JSON Schema를 적용하고 GPT-6에는
`json_object`를 사용한 사실을 확인했다. 따라서 위 Full 30은 호출/validator 결과 참고값으로만
보존하고, 이번 실험의 strict-schema 비교 근거에서는 제외한다.

`build_response_format()`을 `openai/gpt-6*`까지 확장하고 GPT-6 strict schema 회귀 테스트를
추가했다.

strict Preflight 재실행은 provider 사용 한도에 걸려 Flash-Lite/Luna/Sol 모두 3 executions가
각 2회 provider error로 종료됐다(총 18 provider errors, 성공 응답 0). 이 실행은 품질 비교에서
제외하고, 추가 provider 테스트는 이번 작업에서 중단한다.

중간에 shell의 기존 `MODEL_API_BASE_URL`이 상속되어 세 모델 모두 즉시 provider error가 난
Full run 3회가 있었고 모두 무효 처리했다. GPT-6 비교 wrapper는 live 실행 시 OpenRouter
endpoint를 강제하도록 수정했다.

## 미확인 사항

- strict-schema GPT-6 Full 30 결과
- Luna provider error와 긴 tail latency의 strict 조건 재현성

## 다음 작업

1. 이번 작업에서는 추가 provider 호출을 하지 않는다.
2. 추후 한도/예산이 확보돼 strict-schema 비교가 필요하면 별도 실험으로 재실행한다.
3. 현재 결과만으로 모델 선택을 변경하지 않는다.
