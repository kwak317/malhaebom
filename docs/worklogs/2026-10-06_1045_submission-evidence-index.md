# Worklog — 최종 제출 증거 인덱스

- 일시: 2026-10-06 10:45 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: P2 최종 제출물, D12 증거

## 1. 목적

마감 제출물의 실제 파일·링크 존재 여부를 한 문서에서 확인하고, 없는 증거를 완료로 오인하지 않도록 남은 작업을 명시한다.

## 2. 작업 전 상태

- 제출 증거가 README, EVAL_REPORT, 체크포인트, evidence 폴더에 분산돼 있었다.
- Langfuse 스크린샷·데모 영상·발표 PDF의 실제 존재 수를 한눈에 확인할 canonical 인덱스가 없었다.

## 3. 수행 내용

- 저장소의 evidence 및 PNG/JPG/WEBP/MP4/MOV/PDF 파일을 재귀 조사했다.
- 제출 항목별 완료·일부·미완료를 실제 파일과 링크에 연결했다.
- Langfuse 캡처 3장과 정상·실패 영상이 갖춰야 할 내용·비식별 조건을 체크리스트로 작성했다.
- README와 체크포인트 작업표에서 새 인덱스로 연결했다.

## 주요 판단과 이유

- 추적된 Langfuse `home-dashboard.png` 1장은 trace 상세가 아니므로 3장 요구를 충족하지 않는다.
- 제품 화면 PNG와 프런트 demo asset은 정상·실패 데모 영상으로 계산하지 않는다.
- 외부 제출 링크가 저장소에 없다면 존재를 추정하지 않는다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `docs/SUBMISSION_EVIDENCE.md` | 제출 현황·핵심 링크·캡처/영상 체크리스트 |
| `README.md` | canonical 문서 표에 제출 증거 인덱스 연결 |
| `docs/CURRENT_STATE.md` | 확인된 증거와 미완료 제출물 기록 |
| `docs/project2-checkpoint-work-cards.md` | D12에서 제출 인덱스 연결 |
| `docs/worklogs/2026-10-06_1045_submission-evidence-index.md` | 조사 범위와 판단 기록 |
| `docs/worklogs/README.md` | Worklog 인덱스 |

## 5. 검증

```text
저장소 미디어 전수 확인:
- Langfuse 관련 PNG: 1개 (`home-dashboard.png`)
- MP4/MOV: 0개
- PDF: 0개

python scripts/check_doc_references.py
Documentation references: OK
```

## 6. 발견한 문제 / 남은 리스크

- Langfuse trace 상세 스크린샷 최소 3장이 없다.
- 정상·실패 데모 영상과 발표 PDF가 없다.
- 별도 소개 페이지 URL을 확인하지 못했다.

## 미확인 사항

- 저장소 밖 제출 채널에 이미 업로드된 영상·PDF·캡처의 존재
- 발표 자료의 최종 제출 방식과 링크 공개 범위

## 7. 다음 작업

- 팀원이 저장소 밖 자산의 위치를 확인해 인덱스에 실제 링크와 버전을 추가한다.
- 현재 운영 revision에서 비식별 trace 캡처와 정상·실패 영상을 제작한다.
