# Worklog — Gemini v5 4,096-token 출력 계약 재검증

- 일시: 2026-10-02 10:45 KST
- 작업자/에이전트: Codex 및 사용자 실 API 실행
- 관련 PR: 후속 문서 PR 예정
- 관련 요구사항: D3 실제 모델 출력 계약, D4 평가 재현 기록

## 1. 목적

2,048-token 실행에서 잘린 Gemini JSON이 출력 한도 문제인지, 4,096-token 상한에서 30건 전체 계약이 유지되는지 실제 호출로 확인한다.

## 2. 작업 전 상태

`gemini-v5-live-30`은 29/30 계약 통과였고 `coach-failure-26`이 2,032 completion tokens에서 JSON을 닫지 못했다. PR #158은 해당 failure를 `schema_violation`으로 분류하고 finish reason을 남기도록 병합됐다.

## 3. 수행 내용

- 최신 main에서 `experiment/gemini-v5-4096-validation` 브랜치를 생성했다.
- 사용자가 Gemini 3.5 Flash Lite 30건을 4,096-token, 60초 조건으로 실행했다.
- 결과와 종료 사유·불일치 사례를 문서화했다. raw 응답은 Git 제외 `local-results/`에 보존한다.

## 주요 판단과 이유

출력 한도만 바꾼 단일 재측정이므로, 기존 v4/v5 비교표의 품질 우열을 수정하지 않는다. 이번 근거는 2,048-token 절단의 재현 여부와 v5 출력 계약 확인에 한정한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `docs/experiments/2026-10-02_gemini-v5-4096-30case-evaluation.md` | 실행 조건·수치·한계 기록 |
| `EVAL_REPORT.md` | 4,096-token 후속 계약 측정을 canonical 보고서에 추가 |
| `docs/CURRENT_STATE.md` | 최신 실제 모델 평가 상태 반영 |
| `docs/project2-checkpoint-work-cards.md` | D12 증거 링크 보강 |
| 본 파일 | 실행 기록 |

## 5. 검증

```text
Gemini 30건: 계약 30/30, 실패 {}, finish_reason=stop 30건
git diff --check: passed
```

## 6. 발견한 문제 / 남은 리스크

- 자동 label/evidence 불일치가 7개 사례에 남아 사람 semantic 검토가 필요하다.
- 실제 운영 사용자 E2E와 비용 상한은 이번 측정 범위 밖이다.

## 미확인 사항

- 동일 조건 반복 실행과 사람 safety/semantic 검토는 수행하지 않았다.

## 7. 다음 작업

- 문서 PR의 팀원 승인을 받은 뒤 병합한다.
- 필요 시 7개 불일치 사례를 독립 사람 검토한다.
