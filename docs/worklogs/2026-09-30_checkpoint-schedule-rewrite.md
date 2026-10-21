# 2026-09-30 — Checkpoint schedule 기준 문서 재구성

## 목적

사용자가 제공한 Checkpoint Project2 `schedule` 탭 D2~D12 캡처를 기준으로 `[REDACTED].md`를 다시 구성한다. 기존 문서는 날짜별 실제 작업이 공식 Day 주제를 대체하면서 D2·D4·D5·D8 이후 항목이 원 일정과 어긋나 있었다.

D1은 사용자 확인에 따라 의도적으로 제외한다.

## 작업 전 상태

- 체크포인트 문서는 D2를 모델 평가/서비스 통합, D4를 제품 정의/차별화, D5를 현재 상태 정리 등으로 재구성하고 있었다.
- D6에는 공식 schedule보다 MCP 상세 검증이 크게 들어가 있었고, 데이터 출처 태깅 같은 공식 항목은 직접 추적되지 않았다.
- D8~D12도 실제 schedule의 재현 절차 → Skill/MCP → 배포 → baseline/개선 → 전후 재측정 순서와 다르게 작성돼 있었다.
- 기존 구현·실험 근거 자체는 `CURRENT_STATE.md`, `EVAL_REPORT.md`, Worklog 등에 상당수 남아 있었다.

## 수행한 작업

1. D2~D12의 제목과 공식 항목을 사용자가 제공한 캡처 순서대로 복원했다.
2. 각 공식 항목에 현재 저장소 근거를 다시 연결해 `[x]` / `[-]` / `[ ]`로 재판정했다.
3. 날짜보다 먼저 구현한 기능도 해당 공식 항목을 실제로 충족하면 선행 완료 근거로 연결하되, 별도 작업이 공식 항목 자체를 대체하지 않도록 했다.
4. D6의 추가 Agent/MCP/Langfuse 검증은 “공식 항목보다 먼저 진행한 추가 작업”으로 분리했다.
5. STT 실제 사용자 평가는 공식 D2~D12 일정과 분리된 별도 트랙으로 유지했다.
6. 9/29 D6 Worklog를 재대조해 실제 provider·성공/실패/retry·redacted input/output·Duration 증거가 이미 있음을 확인하고 D6 Langfuse 항목을 완료로 정정했다.
7. 루트 README의 서비스 한 문장 정의가 이미 존재함을 확인해 D2 해당 항목을 완료로 정정했다.
8. D3 신뢰 경계를 `docs/TRUST_BOUNDARY.md` 한 장으로 고정하고, 활성 source의 출처·이용허락/약관 상태를 `docs/research/DOMAIN_SOURCE_REGISTER.md`에 정리했다.

## 주요 판단

- **D2 경쟁 조사**: 공개 자료 기반 분석은 존재하지만 “기존 서비스 3개를 직접 써본 기록”은 확인되지 않아 부분 완료로 두었다.
- **D3 신뢰 경계**: 관련 규칙이 Prompt/Spec에 흩어져 있어 `docs/TRUST_BOUNDARY.md` 한 장으로 고정하고 완료 처리했다.
- **D3 도메인 출처/라이선스**: 활성 source별 사용 위치·이용허락/약관 상태·보수적 저장 정책을 `docs/research/DOMAIN_SOURCE_REGISTER.md`에 정리해 완료 처리했다.
- **D4 사람 검토**: dataset에 `independent_review_pending`이 남아 있어 문항별 판정자/근거는 아직 미완료다. 실제 30건 검토와 expected 수정은 이 schedule 재구성 PR에서 분리한다.
- **D6 데이터 출처 태깅**: canonical Prompt가 질문·답변·공고·MCP 반환값 내부 지시를 분석 대상 데이터로 취급하도록 명시하므로 완료 근거로 연결했다.
- **D6 Langfuse 재판정**: 9/29 Worklog와 코드·테스트를 다시 확인한 결과 provider generation에 redacted input/output 구조가 실제 기록되고, 실제 Cloud trace에서 Duration·token·cost·retry까지 검증됐다. 사용자 원문을 저장하지 않는 것은 미구현이 아니라 관측 개인정보 정책이므로 D6 공식 항목은 완료로 정정했다.
- **D2 README**: 루트 `README.md` 3~4행 자체가 서비스 한 문장 정의이므로 추가 작업이 아니라 완료 상태다.
- **D3 신뢰/출처**: 흩어진 규칙을 문서 두 개로 고정해 체크포인트 증거를 만들었다.
- **D7 baseline**: 기존 30건 단위 평가 수치는 많지만 어떤 실행을 9/30 공식 baseline으로 고정할지 정하지 않았으므로 부분 완료로 두었다.
- **D8/D9 선행 구현**: 최소 사용자 흐름, health, Prompt candidate v1, Skill, FastMCP 도구는 이미 존재하므로 선행 완료로 표시했다.
- **D10~D12**: 배포·production trace·rollback·최종 baseline/개선·재측정/동결은 일정 순서에 맞춰 미완료 또는 부분 완료로 유지했다.

## 변경 파일

| 파일 | 변경 |
| --- | --- |
| `[REDACTED].md` | 공식 D2~D12 schedule 기준 전체 재구성 |
| `[REDACTED].md` | 본 작업 기록 |
| `docs/worklogs/README.md` | Worklog 목록 추가 |

## 검증

- 필수 사전 문서 `PROJECT_OVERVIEW.md` → `CURRENT_STATE.md` → `TARGET_STATE.md` → `REQUIREMENTS.md` → `CONSTRAINTS.md`를 확인했다.
- 공식 항목마다 현재 근거 파일을 재검색해 상태를 매핑했다.
- 문서 변경만 수행하며 제품 코드와 실행 동작은 변경하지 않았다.
- 변경 후 diff에서 D2~D12 주제와 “남길 것”이 제공 캡처 순서와 일치하는지 확인한다.
- `make frontend-test`를 실행했으나 로컬 frontend 의존성이 설치되지 않아 `vitest: not found`로 시작 전에 종료됐다. 문서 변경으로 인한 테스트 실패는 아니며, 이번 작업에서는 패키지 설치를 수행하지 않았다.

## 발견한 문제

- 경쟁사 문서는 공개 정보 분석은 있으나 직접 사용 증거와 부족한 점 메모가 분리돼 있지 않다.
- 경쟁 서비스 3개를 직접 사용한 실제 출력/스크린샷 증거는 저장소와 기존 대화 기록 모두에서 확인되지 않았다.
- 평가셋 30건은 존재하지만 실제 사람 검토와 판정자/근거 기록은 별도 D4 PR에서 처리한다.
- 15분 blocker standup을 실제 시행했다는 저장소·기존 대화 기록은 확인되지 않았다.
- D7에서 사용할 공식 baseline 실행을 아직 고정하지 않았다.

## 다음 작업

D7 전에 남은 D2~D6 누락을 먼저 닫는다.

1. D2 경쟁 서비스 3개 실제 사용 기록
2. D4 30건 실제 사람 검토 별도 PR
3. D5 15분 blocker standup 실제 시행 여부 확인 및 시작

그 뒤 D7의 중간 점검 1장, 공식 baseline 1차 수치, 남은 5 작업일 기준 최종 제외 기능 목록을 확정한다.
