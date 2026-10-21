# Worklog — 평가 증거·누락 항목 교차검증

- 일시: 2026-10-02
- 작업자/에이전트: ChatGPT / C2C
- 관련 PR: [#154](https://github.com/aihuman-7th/proj2-3/pull/154) · [#155](https://github.com/aihuman-7th/proj2-3/pull/155) · [#158](https://github.com/aihuman-7th/proj2-3/pull/158) · [#161](https://github.com/aihuman-7th/proj2-3/pull/161) (7건 검토 양식); [#162](https://github.com/aihuman-7th/proj2-3/pull/162)는 별도의 실행 버전 기록 수정이며 사람 검토나 본 문서 PR의 코드 변경이 아님
- 요구사항: 강사 피드백의 LLM 제어력·관찰 평가 누락 증거, D10~D12 체크리스트

## 1. 목적

새로운 모델 호출이나 운영 재배포 없이 기존 평가 원본, `EVAL_REPORT.md` 4·6·7장과 체크리스트를 대조해 제출 가능한 출처 및 실제 미확인 증거를 명확히 한다.

## 2. 작업 전 상태

- 이전 영문 v4와 최신 v5를 **같은 현 Skill**로 각각 30건 호출한 비교는 보고서 4·6·7장에 이미 반영됐다. 총 60호출이며 각 후보 계약 30/30, 자동 전체 통과 v4 22/30→v5 20/30.
- 별도 v5 2,048-token·60초 실행은 29/30(`coach-failure-26` 절단), 별도 4,096-token·60초 실행은 계약 30/30 및 자동 불일치 7건이다. 보고서 주변 서술만 읽으면 페어 비교의 30/30과 혼동될 여지가 있었다.
- PR #161은 검토 양식과 테스트만 병합했고 최신 v5 사람 점수·critical 검토는 기록되지 않았다.
- 기존 D4 30건 검토는 Dataset expected 정답표 검토, 별도 v4 팀 품질 취합은 범위가 서로 다르다.
- 로컬 Langfuse와 공고 분석 web fallback 성공, Notion의 별도 PlayMCP 진단·운영 API 기록은 있으나 요청별 운영 PlayMCP 동일 실행 증거와 production trace는 확보되지 않았다.

## 3. 수행 내용

1. [실행·증거·누락 점검표](../experiments/2026-10-02_evaluation-evidence-gap-audit.md)에 실행 조건별 원본, 보고서 대응, 4,096-token v5의 검토 대상 7개 case, 운영·로컬 증거 경계를 정리했다.
2. `EVAL_REPORT.md`에 2,048·45초 페어 / 2,048·60초 단독 / 4,096·60초 단독 구분과 7건의 검토 준비·미검토 상태를 명시했다. 기존 숫자와 게이트 판정은 변경하지 않았다.
3. D11·D12 체크리스트에 증거 인덱스를 연결하고 기존 `[-]`/`[ ]` 상태를 보존했다. 정적 확인/기록만으로 운영 E2E·인젝션 3건 전후·production trace를 완료 처리하지 않는다.
4. `docs/CURRENT_STATE.md`, 실험/Worklog 색인을 동기화했다.

## 주요 판단과 이유

- 서로 다른 실행을 임의로 합쳐 새 개선율을 만들지 않는다. 서로 다른 일곱 case 집합도 현재 4,096-token 단독 실행 기준으로만 검토한다.
- 사람 검토되지 않은 `null`은 0건 발생/통과와 다르다. PR #161은 준비 근거일 뿐 사람 검토 완료 근거가 아니다.
- Notion 원본 페이지를 직접 열람했으나 Notion verification이 unverified였다. 기록된 분리 실험·운영 HTTP 결과를 같은 요청의 PlayMCP 도구→추천→원문 분석 증거로 결합하지 않는다.
- 최근 브라우저 공고 검색 인증 오류는 사용자 수동 관측이며 운영 로그로 원인을 확정하지 않았다. D10 운영 검증 작업은 보류한다.
- PR #162의 코드 검증·승인·CI는 이번 문서 PR에서 머지된 것으로 주장하지 않는다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `docs/experiments/2026-10-02_evaluation-evidence-gap-audit.md` | 측정 원본·수치·누락 증거의 통합 인덱스 |
| `EVAL_REPORT.md` | 실행 구분 및 사람 검토 준비·미수행 명시 |
| `docs/project2-checkpoint-work-cards.md` | D11·D12와 강사 피드백 증거 인덱스 연결 |
| `docs/CURRENT_STATE.md` | 문서 정리 상태와 남은 증거 요약 |
| `docs/experiments/README.md`, `docs/worklogs/README.md` | 문서 링크 |
| 본 Worklog | 판단 경계·검증 결과 |

## 5. 검증

- GitHub PR #154·#155·#158·#161 병합 상태, #162 승인·CI 4/4·미병합 상태를 10/2 조회 기준 확인했다.
- 문서에 수록된 수치·세 가지 최신 v5 관련 측정 조건·4,096-token 불일치 7개 case를 각각의 기존 실험 기록과 직접 대조했다.
- 문서 전용 점검 `local-results/evidence_gap_doc_check.py`에서 신규 증거 점검표 상대 링크 17개, Worklog 상대 링크 1개 존재를 확인했다. 4,096-token 실험의 불일치 7개 case와 EVAL_REPORT 주요 보고값도 소스 문서와 일치했다.
- `scripts/check_doc_references.py`: 유지관리 문서 7개 검사 PASS.
- `git diff --check`: PASS. 별도 PR 정책 diff 크기는 커밋 후 `origin/main...HEAD` 기준으로만 판정할 수 있으므로 아직 실행 결과를 완료로 표시하지 않는다.

## 6. 발견한 문제 / 남은 리스크

- 4,096-token v5 검토 양식의 로컬 원본을 사람이 실제로 판정해야 하며, 나머지 23건까지 최종 검토할지 팀 합의가 필요하다.
- `--semantic-reviews`는 저장 출력만 재채점하지 않고 새 provider 호출을 수행한다. 승인 없이 비용을 발생시키지 않는다.
- 운영 관리형 Prompt의 본문/Skill 중복, production trace, PlayMCP 한 요청의 도구→추천→분석 correlation, release rollback은 여전히 접근·실행 증거가 없다.

## 미확인 사항

- 로컬 Git 제외 raw 결과 파일과 새 검토 JSON의 현시점 존재·내용은 확인하지 않았으므로 별도 재채점/사람 검토 완료를 주장하지 않는다.
- 강사가 이 증거 인덱스를 공식적으로 인정했는지 확인하지 않았다.

## 7. 다음 작업

1. 담당 검토자가 v5 4,096-token 7건을 기존 `REVIEW.md`와 JSON 양식에 실제로 판정한다.
2. 팀이 최신 v5 사람 검토 범위, 비용 상한 및 v4 팀 리뷰 공통 기준을 합의한다.
3. GCP/Langfuse 담당자가 운영 요청의 redacted trace·PlayMCP correlation·Prompt/Skill 버전 증거를 확보한다.

### 후속 D10 공개 배포 재검증 (read-only)

- 외부 공개 Frontend GET 200, 배포 JS의 Cloud Run 호스트 연결, Cloud Run `/health` GET 200, 추천 API의 Frontend Origin CORS OPTIONS 200을 확인해 D8 선행 준비와 D10 배포 URL을 **부분 완료**로 갱신했다. 로그인 성공은 사용자의 브라우저 수동 보고이고, 공고 검색의 PlayMCP 인증 오류는 여전히 미해결이다.
- C2C 실행 환경에 `gcloud` 설치는 확인했으나 활성 로그인 및 대상 GCP 프로젝트 조회 권한이 확인되지 않아 운영 로그 재조회는 진행할 수 없었다. 운영 secret·token을 요청하거나 공개하지 않았고, 비인증 GET/OPTIONS 외의 생산 요청은 하지 않았다.
- D10 증거를 추가해도 production trace, 동일 운영 요청의 PlayMCP→추천→원문 분석, 현재 revision, 실제 rollback은 여전히 미확인이다.

### 후속 사용자 보고: PlayMCP 동작 복구

- 사용자가 PlayMCP가 이제 작동한다고 알렸다. 기존 인증 실패 관측은 과거 기록으로 보존하고 운영 장애 지속이라는 표현은 철회했다. 복구 방법·시각 및 성공 요청 로그는 확보하지 못했으므로 새 운영 E2E 성공 근거로 표시하지 않는다.
- 후속 우선순위는 과거 인증 오류 조사보다 복구 후 동일 로그인 세션의 추천→원문 분석→코칭 응답과 production trace 수집이다. Cloud Logging은 재발·정확한 복구 원인 확인이 필요한 경우에만 요청한다.

### 후속 사용자 보고: 운영 브라우저 기능 E2E 성공

- 사용자가 운영 브라우저에서 공고 검색·선택 공고 원문 분석·연습·1/2차 코칭 비교까지 완료했다고 추가로 확인했다. 이전의 단순 PlayMCP 복구 보고보다 검증된 사용자 기능 범위가 넓어, 공식 D10의 배포 URL 동작 및 D8의 공개 Frontend 접근 항목을 완료로 갱신했다.
- 이 증거 유형은 **사용자 수동 실행 보고**다. 성공 실행 캡처·실행 시각·request ID·운영 리비전·PlayMCP 실제 호출과 production Langfuse trace는 아직 확보하지 않았다. 강사 피드백의 동일 요청 PlayMCP 연결 입증과 관측/rollback 항목은 부분완료·미완료로 유지한다.

### 후속 Langfuse Cloud 코칭 trace 화면 검증

- 사용자가 10/2 14:28 경 Langfuse Cloud의 동일 코칭 trace에 대한 provider·output validation·analyze 상세 화면을 제출했다. `google/gemini-3.5-flash-lite` provider 관측 15.84초; 출력 검증 `valid=true` / `error_count=0`; 최종 코칭 `needs_more_info`. Trace 헤더 합계 16.00초·17,428 tokens·$0.008467.
- D10의 Langfuse 관측은 **부분완료**로 변경했다. Langfuse Cloud의 호출·검증·코칭 트리 자체는 직접 시각 확인했지만, 스크린샷에 `environment` 및 실제 Prompt·Skill 버전·Cloud Run 리비전이 보이지 않고 1/2차 비교와 같은 세션인지도 미확인이다. 해당 값과 운영 연계 확인 후 최종 상태를 판정한다.
- 원본 화면에는 사용자·세션 식별자가 있으므로 저장소에 이미지를 커밋하지 않고, 민감 정보가 제외된 확인 지표와 누락 항목만 문서에 기록했다.

### 후속 Metadata/Environment 확인 — 기록 Skill v6과 기본 Skill v6.1의 불일치

- 사용자가 같은 10/2 14:28 경 코칭 provider Attributes를 추가 캡처했다. `outcome=success`, `status_code=200`, `will_retry=false`, `transport_attempt=1`, `contract_attempt=1`, **표시된** `skill_version=interview-coach-v6`을 확인했다.
- Tracing 목록의 Environment는 `default`이며 Prompt Name은 표시되지 않았다. 기본 Skill 카탈로그 `interview-coach-v6.1-domain-rules`와 표시값이 일치하지 않아 [PR #162](https://github.com/aihuman-7th/proj2-3/pull/162)의 관측 기본값·실행 버전 기록 수정과 연관된 확인 사례로 남긴다. 하지만 해당 리비전이 실제로 어느 Skill을 로드했는지는 확인하지 않았으며 `default`는 `production` label의 증거가 아니다.
- 원본 캡처 속 사용자/세션 식별자 및 키를 복제하지 않았다. 실제 적용 버전·관리형 Prompt 부착 여부·운영 리비전의 연계 검증은 여전히 미완료다.
