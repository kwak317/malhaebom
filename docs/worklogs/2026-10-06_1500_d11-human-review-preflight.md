# Worklog — D11 신규 인젝션 사람 검토 preflight

- 일시: 2026-10-06 15:00 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: 평가 입력·정답은 LLM 생성물을 독립 근거로 사용하지 않으며, 사람 검토 전 유료 평가를 실행하지 않는다.

## 1. 목적

D11 신규 인젝션 후보 3건을 사람이 독립적으로 확정하기 위한 offline 검토 packet을 만들고, 후보 생성·사람 확정·공식 Dataset 승격을 구분한다.

## 2. 작업 전 상태

`evals/d11_injection_candidates.jsonl`에는 후보 3건과 사용자 승인 label이 있었지만, `independent_human_authored_input_pending` provenance 때문에 공식 D11 case로 계산할 수 없었다.

## 3. 수행 내용

- 후보 수·ID·provenance 계약을 확인하는 packet generator를 추가했다.
- 사람 입력 필드를 빈값으로 둔 `human-review.template.json`과 후보 원문을 보여 주는 `REVIEW.md`를 `local-results/`에 생성하게 했다.
- Spec과 회귀 테스트를 추가했다.

## 주요 판단과 이유

사람 검토 템플릿에 제안 label을 복사하지 않고 최종 판정을 `null`로 유지했다. 따라서 검토자는 후보를 확인하되, LLM 초안을 자동 승인하거나 공식 Dataset으로 오인하지 않는다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `evals/build_d11_injection_human_review.py` | offline 검토 packet generator |
| `backend/tests/test_build_d11_injection_human_review.py` | 빈 사람 판정 template 회귀 테스트 |
| `docs/specs/d11-human-review-preflight.md` | Why·Goal·What·How·AC Spec |
| `docs/CURRENT_STATE.md` | 현재 동작과 제한 기록 |
| `docs/worklogs/2026-10-06_1500_d11-human-review-preflight.md` | 작업 기록 |
| `docs/worklogs/README.md` | Worklog 목록 연결 |

## 5. 검증

```text
pytest backend/tests/test_build_d11_injection_human_review.py -q
2 passed

python evals/build_d11_injection_human_review.py --output-dir local-results/d11-human-review-preflight-test
Provider calls: 0; official dataset update: NOT AUTHORIZED
```

## 6. 발견한 문제 / 남은 리스크

- 사람 검토와 팀의 공식 Dataset 승격 결정은 아직 수행하지 않았다.
- 생성 packet에는 후보 원문이 포함되므로 개인 정보가 없는 평가용 입력만 사용해야 한다.

## 미확인 사항

- 실제 사람이 template을 채운 뒤의 완결성 검증과 Dataset 승격 절차는 후속 작업이다.

## 7. 다음 작업

- D10 운영 증거 수집 runbook을 별도 브랜치에서 작성한다.
