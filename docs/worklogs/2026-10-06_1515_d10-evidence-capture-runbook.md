# Worklog — D10 운영 증거 수집 runbook

- 일시: 2026-10-06 15:15 KST
- 작업자/에이전트: Codex
- 관련 요구사항/결정: 운영 trace·Prompt release/rollback·PlayMCP 동일 요청 E2E와 제출용 캡처는 동일 실행 연결과 비식별 원칙을 따른다.

## 1. 목적

D10의 미완료 운영 증거를 수집할 때 trace·revision·Prompt/Skill·PlayMCP 호출·제출 캡처를 서로 다른 실행으로 섞지 않도록 표준 절차를 남긴다.

## 2. 작업 전 상태

과거 운영 trace와 사용자 성공 보고는 있었으나, 현재 revision의 성공 요청·Prompt/Skill·DB·PlayMCP 경로를 동일 실행으로 연결한 증거와 managed Prompt release/rollback 실증은 없었다.

## 3. 수행 내용

- 운영 권한·비식별·승인 조건을 사전 조건으로 고정했다.
- 성공 trace, PlayMCP 동일 요청 E2E, Prompt production 승격/rollback, 제출 반영 절차를 한 runbook으로 정리했다.
- 실패 시 production을 더 변경하지 않고 기존 복구 절차로 전환하도록 명시했다.

## 주요 판단과 이유

문서화는 운영 실행 증거가 아니다. 따라서 체크포인트 상태를 변경하지 않았고, secret·실사용자 원문을 저장소에 남기지 않는 조건을 우선했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `docs/runbooks/d10-production-evidence-capture.md` | 운영 증거 수집 절차 |
| `docs/CURRENT_STATE.md` | runbook의 범위와 상태 기록 |
| `docs/worklogs/2026-10-06_1515_d10-evidence-capture-runbook.md` | 작업 기록 |
| `docs/worklogs/README.md` | Worklog 목록 연결 |

## 5. 검증

```text
python scripts/check_doc_references.py
Documentation references: OK
```

운영 배포·Prompt 승격/rollback·로그인 E2E·Langfuse 접근은 수행하지 않았다.

## 6. 발견한 문제 / 남은 리스크

- 운영 권한과 배포 창이 없으면 runbook을 실행할 수 없다.
- 실제 trace와 캡처는 비식별 검토 없이 commit하면 안 된다.

## 7. 다음 작업

- 운영 담당자와 D10 증거 수집 창 및 Prompt rollback 승인 조건을 확정한다.
