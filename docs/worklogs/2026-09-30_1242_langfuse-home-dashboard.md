# Worklog — Langfuse Home 화면을 구현 현황 문서에 추가

- 일시: 2026-09-30 12:42 KST 캡처 기준
- 관련 이슈/PR: 없음
- 목적: 사용자가 제공한 Langfuse Home 화면을 기존 구현 현황 문서에 보존하고 수치의 범위를 명시

## 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `../말해봄_개발기반_구현현황_NCS포함_20260929.md` | Langfuse 관측 현황과 캡처 추가 |
| `docs/evidence/langfuse/2026-09-30/home-dashboard.png` | 제공된 Home 캡처 보존 |
| 이 Worklog | 수치와 검증 경계 기록 |

## 확인 결과

- Home 캡처: Traces 136, Observations 229, Model costs $0.22, `google/gemini-3.5-flash-lite` 415.7K tokens, Scores 0.
- 동일 프로젝트 Observations API v2를 2020-01-01부터 2026-09-30 12:36 KST까지 조회해 observation 229건과 고유 trace ID 136개를 확인했다.
- 캡처에는 날짜 선택기가 없으므로 비용·score 값의 기간은 캡처만으로 확정하지 않는다.
- 합성·테스트 trace가 포함된다. 전체 trace 수는 실제 사용자 요청 수가 아니다.

## 검증

- PNG 파일 형식·크기를 확인한다.
- 문서 이미지 링크 대상과 표의 값이 캡처와 일치하는지 확인한다.
- 문서 변경 범위가 새 6절에 한정됐는지 백업과 비교한다.

## 실패·미확인 사항

- 캡처의 비용과 token 수치를 provider 청구서와 대조하지 않았다.

## 다음 작업

- 실제 사용자 trace만의 집계가 필요하면 로그인 사용자 요청을 식별할 수 있는 가명화 필터와 기간을 정한 뒤 별도 집계한다.
