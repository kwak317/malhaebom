# Worklog — 2026-10-08 D12 평가·체크리스트·제출 증거 정합성

## 목적

D12 점검 전에 `EVAL_REPORT.md`, `docs/project2-checkpoint-work-cards.md`, `docs/SUBMISSION_EVIDENCE.md`에 흩어진 과거 '인젝션 미측정/운영 trace 미확인' 표현을 **10/8 관측 범위 내에서만** 정정한다. 이번 변경은 문서 정합성 전용이며 새 provider 호출, 사람 채점, 배포/Prompt 조작, 데모 촬영, 코드 동결을 수행하지 않는다.

## 작업 전 기준과 출처

- `origin/main` 기반 clean 별도 worktree. 원본 `main`의 D11/제출/STT 미커밋 변경은 다른 작업자의 파일과 섞이지 않도록 유지.
- [PR #215](https://github.com/aihuman-7th/proj2-3/pull/215) — D11 신규 인젝션 3건 v4/v5 비교 및 추가 1회씩 재시도, 두 개의 raw 추가 재시도 기록은 Git ignored `local-results/`에 보존. 실제 유효한 마지막 응답 기준 **v4 계약·판정 3/3, v5 계약 3/3·판정 2/3**. v5 최초 계약은 1/3, 일부 실패/timeout 과금 불확실. 단일 검토자만 입력·정답 검토, 독립 검토 미실시.
- [PR #216](https://github.com/aihuman-7th/proj2-3/pull/216) — 사용자 제공 Langfuse Cloud 화면의 managed Prompt `malhaebom-coaching-v5-reinforced-verification@4`에 `production` 라벨, 동일 trace ID의 실제 `coaching.provider` 및 `coaching.output_validation` PASS (`CoachingLLMOutput.valid=true`, `error_count=0`). Skill 표기 `interview-coach-v6`, 실제 Bundle SHA·Cloud Run revision/DB/release rollback은 미확인.
- 기존 `EVAL_REPORT.md` 10/2 30건 비교는 자동 통과 **22/30(v4), 20/30(v5)**, 10/6 운영 이미지 30건×3회는 종합 자동 통과 **57/90**. 모집단과 조건이 다른 실험을 합산하면 안 된다.
- 두 PR은 작성 당시 **OPEN/미병합**이므로 이번 D12 문서는 PR 링크를 참조하며, 아직 `main`에 결과 원본이 포함됐다고 주장하지 않는다.

## 작업과 판단

1. 평가 보고서 상단에 10/2 30건 A/B, 10/6 운영 이미지 재현, 10/8 신규 인젝션, 10/8 Langfuse 실사용 trace의 증거·해석 경계를 나누는 표를 추가했다. **v5 최초 시도 1/3과 사례별 마지막 시도 3/3**을 모두 표기한다.
2. D11 및 D12 체크리스트의 **'신규 3건 미측정' 과거 서술을 10/8 실제 실험 기록에 맞춰 갱신**했다. 독립 검토, 운영 연계, 사람 품질 평가 7건과 공식 release/rollback은 그대로 미완료다.
3. 제출 인덱스에 실측한 Langfuse Prompt/trace/validator를 링크했다. 단, 채팅에서 받은 원본 스크린샷에는 user/session ID와 SDK public key가 보여 **제출 가능한 비식별 스크린샷 3장 확보로 계산하지 않았다**. 현재 이미지·키·원문 데이터는 Git에 복사하지 않는다.
4. 영상 정상/실패 각 1개, 코드 동결, 최종 PDF는 기능 수정 예정이므로 **보류/미완료 유지**.
5. 상대경로 링크 및 민감값 금지 검사를 별도 오프라인 검증한다.

## 한계 / 다음 단계

- 이 문서는 PR #215·#216의 실험·관측 증거를 참조하는 **문서 정리**다. 자체적으로 provider/E2E/사람 채점·운영 전환 테스트를 새로 수행하지 않는다.
- PR #215, #216 및 현재 D12 변경분의 merge 시점에는 `EVAL_REPORT.md`, 체크포인트/인덱스 충돌과 동일 내용 중복을 재검토한다.
- 팀원 승인 전 병합 금지. 운영 담당자의 Cloud Run/Skill 확인은 별도 대기. 실패/성공 비식별 캡처와 영상은 기능 수정 종료 후 확보한다.
