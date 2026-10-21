# 2026-09-23 문서 정합성 정리

## 목적

현재 구현 상태와 역사적 문서가 섞여 서로 다른 결론을 주는 문제를 정리하고, 현재 상태·과거 snapshot·운영 정책의 우선순위를 명확히 한다.

## 작업 전 상태

- `docs/CURRENT_STATE.md` 구현 표에 1차/2차 비교, 신규 에이전트, 평가가 과거 상태와 최신 상태로 중복되어 있었다.
- 루트 `README.md`에는 `/api/agent`와 HTTP `/mcp`가 연결되지 않았다는 과거 상태가 남아 있었다.
- 두 와이어프레임 문서는 존재하지 않는 `malhaebom-wireframe.md`를 기준 문서로 지칭하고, 현재 구현과 다른 제외 범위를 “현재”로 표현했다.
- README의 PR 크기 요약은 “400줄 PR”로 축약되어 최신 Review Core 정책을 충분히 설명하지 못했다.

## 수행한 작업

- `CURRENT_STATE.md` 상단에 최신 섹션·구현 표 우선 원칙을 명시했다.
- 구현 표의 중복된 1차/2차 비교·신규 에이전트·평가 행을 최신 상태 하나로 정리했다.
- 2026-09-18 이하 과거 기록 앞에 Historical snapshots 경계를 추가했다.
- README의 PR 크기 표현을 Review Core 400 LOC 권장 / 800 LOC hard limit으로 맞췄다.
- README의 과거 endpoint 미연결 문구 앞에 2026-09-23 상태 정정을 추가해 CURRENT_STATE 최신 섹션을 우선하도록 했다.
- 두 와이어프레임을 historical snapshot으로 표시하고 현재 canonical 범위·Spec 링크를 연결했다.

## 주요 판단과 이유

- 과거 Worklog성 상태 기록은 삭제하지 않고 당시 snapshot으로 보존한다.
- 현재 상태를 설명하는 표에서는 같은 영역의 과거/현재 행을 동시에 두지 않는다.
- 구현이 진행된 뒤 오래된 와이어프레임을 억지로 최신화하기보다 역사적 설계 자료로 명확히 구분한다.
- 문서에 과거 상태가 남아 있어도 최신 canonical 상태가 무엇인지 즉시 알 수 있도록 우선순위를 표시한다.

## 변경 파일

- `docs/CURRENT_STATE.md`
- `README.md`
- `docs/wireframe_완성본.md`
- `frontend/src/wireframe_초안.md`
- `docs/worklogs/README.md`
- 이 Worklog

## 검증 내용

- 최신 `CURRENT_STATE.md`에서 1차/2차 비교·신규 에이전트·평가가 각각 한 행만 현재 상태로 남는지 확인한다.
- README의 Review Core 정책이 `AGENTS.md`의 400 LOC guideline / 800 LOC hard limit과 일치하는지 확인한다.
- 와이어프레임에서 현재 범위로 오인될 수 있는 문구 앞에 historical snapshot 경계가 있는지 확인한다.
- 코드 변경은 없으므로 런타임 테스트 대상은 없다.

## 발견한 문제

- README의 과거 endpoint 상태 문장은 음성 인수 기록 링크와 한 줄에 함께 있어 자동 패치 시 경로 redaction 영향을 받는다. 이번 정리에서는 바로 앞에 명시적 상태 정정을 두어 최신 상태의 우선순위를 보장했다.

## 미확인 사항

- 전체 저장소의 모든 역사적 Worklog와 실험 문서를 최신 상태로 다시 쓰지는 않았다. 날짜가 붙은 기록은 당시 사실로 보존한다.

## 다음 작업

- 제품 문제정의·차별화 문서 PR이 병합되면 `docs/README.md`의 제품 문서 링크와 함께 최종 문서 탐색 흐름을 다시 확인한다.
