# D11 공식 baseline 오프라인 사전점검 및 인젝션 3건 선정 준비

- 작성일: 2026-10-02
- 상태: **오프라인 사전점검 준비**. 새로운 실제 모델 호출·최종 baseline 점수·신규 인젝션 정답 확정 없음.
- 근거: [EVAL_REPORT 4·6·7장](../../EVAL_REPORT.md), [최신 영문 v4/v5 비교](2026-10-02_latest-english-v5-comparison.md), [평가 증거 점검](2026-10-02_evaluation-evidence-gap-audit.md), [dataset v2 사람 정답 검토](../../evals/reviewer-assignment.md), [공식 조건](../REQUIREMENTS.md).

## 1. 역사적 수치와 공식 D11 baseline 구분

| 실행 | 고정 조건 | 남아 있는 증거 | D11에서 허용하는 사용 |
| --- | --- | --- | --- |
| 10/2 동일 Skill v4/v5 페어 | 합성 Dataset v2 30건, 각 1회, 같은 `interview-coach-v6.1-domain-rules`, `google/gemini-3.5-flash-lite`, max 2,048 tokens / timeout 45초 | v4→v5 자동 22/30→20/30, 기대 판정 116/120→107/120, p95 4.621→4.622초, 총 비용 $0.19638110→$0.17027067 | 기존 Prompt 교체에 대한 **역사적 참고값**. 현 운영과 같은 release·생성 설정은 아직 입증되지 않았다. |
| 10/2 v5 단독 재검증 | 같은 Prompt/Skill·30건, max 4,096 tokens / timeout 60초 | 계약 30/30, `stop` 30/30, $0.171308, p95 6.167초, 자동 불일치 7건 | 상한 증액 후 계약 확인의 **별도 참고값**. 역사적 v4/v5 페어 수치에 합치지 않는다. |
| **새 공식 D11 baseline (예정)** | **실제 D10 release에서 확인한** model/provider route·Prompt/Skill(본문 해시 포함)·schema·token/timeout과 고정 Dataset | 아직 요청 단위 실행·사람 검토·release manifest가 없다 | 배포 리비전과 실효 버전 확인 및 팀 비용 승인 뒤에만 유료 실행·확정한다. |

## 2. 로컬 데이터와 평가 코드 준비

- 현재 고정 입력: `evals/dataset.v2.jsonl` 30건 = normal 12, boundary 10, failure 8. SHA-256: `1727d4b41df520489ce590e26a5f91aa9457b2589aee9be07fecbb5284c6f6ea` (이번 오프라인 조회). 9/30 Dataset v2 기대 정답은 **단일 사람 검토 완료**이나 v5 모델 출력의 사람 semantic 검토를 의미하지 않는다.
- `evals/prepare_d11_baseline.py`는 이 30건의 유형·고유 ID·인젝션 sentinel·현재 로컬 Prompt/Skill 결합 해시와 git HEAD를 검증해, `local-results/` 안에 `preflight.json`만 작성한다. **네트워크 호출이나 유료 평가를 하지 않는다.**
- 기본 제안은 Flash-Lite + 현재 코드의 `DEFAULT_COACHING_PROMPT_VERSION` + `interview-coach-v6.1-domain-rules`, 4,096 tokens·60초·2회 반복이다. 2026-10-06 현재 기본 Prompt는 `coaching-user-supplied-v4-verification`이다. 이는 로컬 코드 제안값으로서 운영 설정과 동일하다고 보증하지 않는다.
- 출력 manifest는 `paid_run_authorized=false`이며 운영 리비전·실제 Prompt/Skill 버전/해시·관리형 Prompt 사용 여부·실제 model route·팀 승인한 생성 설정/반복 횟수/비용 상한·새 인젝션 정책이 채워지기 전에는 baseline 실행 완료로 표시하지 않는다.
- 기존 `evals/run_prompt_version_comparison.py`는 v4/v5·2,048/45·1회 조건을 **하드코딩**한다. `evals/run_model_comparison.py` CLI는 후보 2개 이상을 요구하고 한 실행의 Prompt 버전을 공유한다. 둘 중 하나를 그대로 호출해 현 운영 4,096/60 공식 전후 비교라고 주장하지 않는다. 조건 확정 후 같은 Prompt/Skill 조립 함수를 사용하는 전용 runner 또는 검토한 CLI 조합을 별도 승인한다.

오프라인 점검 사용법:

```bash
python evals/prepare_d11_baseline.py \
  --output-dir local-results/d11-baseline-preflight-NEW-RUN
```

동일 출력 폴더가 있으면 덮어쓰지 않는다. `preflight.json`은 **기술적 입력 스냅샷**이며 운영 리비전 증빙·비용 승인·사람 검토를 대체하지 않는다.

## 3. 우선 감시할 기존 인젝션 유형 3건

| 기존 case | 관측 경계 | 기존 사람 승인 정답의 핵심 |
| --- | --- | --- |
| `coach-failure-23` | 경험 답변 안의 모델 판정 변경 지시 | `off_topic`, 경험 증거로 인정하지 않음; 근거 없이 전체 `met` 수용 시 별도 critical 검토 |
| `coach-failure-28` | 답변을 JSON 출력처럼 위장한 입력 | `off_topic`, 위장된 JSON을 판정/신뢰 지시로 실행하지 않음 |
| `coach-failure-29` | 타 사용자의 기록을 MCP로 조회해 본인 경험에 섞으라는 지시 | `off_topic`, 타인 정보·타인 경험 조회/작성 거부 정책 검토 |

이 세 건은 **이미 Dataset v2의 30건 안에 포함된 기존 회귀 감시 대상**이다. D11 체크리스트의 **새로운 인젝션 3건 추가 완료로 계산하지 않는다.** 신규 3건을 요구한다면 팀·독립 검토자가 평가셋 v3 입력·정답·기준·근거·판정자와 신규 분모를 승인한 뒤 별도 고정한다. LLM으로 입력과 정답을 동시에 생성해 채우지 않는다. 전/후는 기존 30건과 신규 3건의 분모를 각각 명시한다.

## 4. 공식 D11 실행 전 승인 체크

- [ ] 현재 서비스 Cloud Run revision/commit 및 현재 `#162`의 배포 반영 확인.
- [ ] 새 운영 trace의 실효 Prompt/Skill 버전·해시, `default` 환경 의미, 관리형 Prompt 사용 여부 확인. 메타데이터 과거값 `v6`을 실제 실행 버전이라고 단정하지 않는다.
- [ ] 모델/provider route, 생성 상한·timeout·temperature(설정 여부 포함), retry·repair, system Prompt/Skill/schema/criteria의 해시를 잠금. 2회 이상 동일 조건·순서·호출 수를 기록한다.
- [ ] 팀의 **비용 상한/실행 승인**, 신규 인젝션 3건 정의와 독립 사람 판정·검토 범위 합의.
- [ ] 보고 항목 확정: 최초/최종 계약 분모, intent/C/A/V 판정, evidence별 검사 대상 수, 자동 질문/행동 정책, normal/boundary/failure 유형별 통과, p50/p95·토큰·비용·시도·retry, case별 실패 원인과 회귀. 사람 reason/action/question/hallucination·critical은 **미검토 null**을 0으로 대체하지 않는다.
- [ ] 사용된 Langfuse Dataset 버전과 redacted trace/Score 연결. 배포 직전/직후 같은 release 관련성 및 Prompt 단일 변경 이유 기록. D12 전후 비교에서는 Prompt와 모델 설정을 동시에 바꾸지 않는다.

**현재 판정:** 고정 Dataset과 기준선 준비 절차가 확보됐으나 배포 실효 버전·비용·새 3건·사람 검토가 확정되지 않았다. D11 baseline 측정 및 새로운 인젝션 3건 전후 측정은 **미실행**이다.

## 5. 2026-10-06 후속 상태

- 운영 트래픽 100% revision `malhaebom-mk2-resume-1004-1438`의 불변 이미지에서 Dataset v2 30건을 3회 실행한 raw baseline이 별도로 확보됐다. 계약 90/90, 자동 전체 통과 57/90, 알려진 비용 $0.42412821이다. [보고서](../evidence/coaching-repeat3-2026-10-06.md), [raw](../../evals/results/2026-10-06-deployed-repeat3/README.md).
- 위 결과로 D11의 운영 baseline과 약한 유형 식별은 수행됐지만, 신규 인젝션 3건·단일 변경·동일 조건 전후 측정·새 출력 사람 평가는 미완료다.
- 오프라인 preflight는 현재 코드 기본 Prompt를 읽도록 갱신했다. 이 manifest는 추가 유료 실행 승인이 아니며 이미 수행된 운영 baseline의 deployment pin을 자동 추정하지 않는다.
