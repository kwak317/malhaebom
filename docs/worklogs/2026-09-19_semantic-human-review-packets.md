# Worklog — Semantic 사람 검토 자료 생성

- 일시: 2026-09-19
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: C policy v3, semantic annotation 15건

## 1. 목적

추가 API 호출 없이 최신 Basic 전체 결과와 정식 Premium recovery 결과로 사람이 직접 semantic 품질을
채점할 수 있는 모델 표시판·blind판을 5case씩 세 batch로 만든다.

## 2. 작업 전 상태

최신 Basic 결과에는 3종×30건이 있고, 정식 Premium recovery 결과에는 고유 실패 8case×3종이 있다.
핵심 15case와 교차하면 Basic 출력 45개, Premium 실제 호출 출력 18개가 검토 대상이다.

## 3. 수행 내용

- 각 case에 사용자 원문과 전체 expected semantic annotation을 표시했다.
- required points, forbidden conclusions/claims, explicit negations, action/question 기준과 critical 조건을 분리했다.
- 각 실제 structured output과 자동 계약·label·evidence·ID 결과를 함께 배치했다.
- 다섯 semantic/안전성 항목의 0/1/2와 critical yes/no 입력을 모두 빈 상태로 만들었다.
- 모델 표시판과 결정론적으로 순서를 섞은 blind판을 생성하고 `mapping.json`으로 연결했다.
- 브라우저에서 입력한 값을 로컬 JSON으로 내려받는 기능을 추가했으며 외부 전송은 없다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `local-results/semantic-human-review-c-policy-20260919/` | generator, labeled/blind HTML 6개, mapping, score template, 검증 |
| `docs/worklogs/2026-09-19_semantic-human-review-packets.md` | 수행·검증 기록 |

## 5. 검증

```text
15 cases / 3 batches / 5 cases each
Basic outputs 45, Premium outputs 18, total 63
labeled HTML 3, blind HTML 3, mapping items 63
source semantic scores null, blank score items 63
Basic/Premium source result SHA-256 match
blind HTML model/provider/generation-name scan: no matches
```

## 6. 발견한 문제 / 남은 리스크

- HTML 입력은 파일을 새로 열면 복원되지 않으므로 batch별 JSON 다운로드 버튼으로 저장해야 한다.
- 사람 검토 전이므로 의미 품질 점수와 critical failure 판정은 없다.

## 미확인 사항

- 서로 다른 검토자 간 일치도와 판정 calibration은 수행하지 않았다.

## 7. 다음 작업

- blind 검토 결과를 mapping으로 해제한 뒤 semantic grader 입력 형식으로 변환한다.
