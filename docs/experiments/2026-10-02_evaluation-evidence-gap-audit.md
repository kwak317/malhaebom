# 2026-10-02 평가·운영 증거 교차검증 및 누락 목록

> 기준: 2026-10-02 조회한 `origin/main` (PR #161 병합 이후). 측정 재실행·운영 설정 변경 없이 저장소 실험 기록, 평가 보고서, 체크리스트, 별도 Notion 단계별 기록을 교차 검토했다. 원본 응답·인증값·사용자 자료는 이 문서로 복사하지 않는다.
>
> 판정: **기존 근거 있음**은 출처 기록의 존재를 뜻하며, 해당 실행을 이번 작업에서 재현했거나 운영 접근을 독립 검증했다는 뜻이 아니다. **미확인**은 임의로 0점·실패·완료 중 어느 쪽으로도 분류하지 않는다.

## 1. 평가 실행별 원본과 경계

| 구분 | 고정 조건 / 원본 | 확인된 기록 | 사용 가능한 주장 / 주의 |
| --- | --- | --- | --- |
| D4 예전 90회 offline 재채점 | 과거 Flash-Lite·Dataset v2 30건×3회 저장 응답, 9/30 사람 정답 수정. [EVAL_REPORT 3-2](../../EVAL_REPORT.md), [사람 정답 검토](../../evals/reviewer-assignment.md) | `coach-boundary-17` V 정답 `partial → undetermined`; 기존 출력 재채점 label 313/360(86.9%), 계약 90/90 | **정답표 검토**이며 현재 v5 생성 결과의 사람 품질 검토가 아니다. Provider를 다시 호출하지 않았다. |
| 이전 v4 팀 품질 취합 | 별도 영문 v4 출력 30건; [취합](2026-10-01_coaching-v4-team-quality-review.md), [PR #154](https://github.com/aihuman-7th/proj2-3/pull/154) | 팀원 1 전체 227/240, 팀원 2 기존 기준 15건 101/120 및 추가 의견, 사용자 평가용 AI 초안 별도 | 30건 전원·동일 기준·독립적인 3명 평가가 아니다. 공통 루브릭·17번 중대 오류 분류와 최종 점수 미합의. |
| **동일 Skill v4/v5 비교** | 10/2, 현재 Skill v6.1 + 합성 v2 30건, 영문 v4/v5 각각 1회, max 2,048·timeout 45초. [비교 실험](2026-10-02_latest-english-v5-comparison.md), [PR #155](https://github.com/aihuman-7th/proj2-3/pull/155) | v4/v5 모두 계약 30/30; 종합 자동 통과 22/30→20/30, 판정 116/120→107/120, 총 비용 $0.19638110→$0.17027067, p95 4.621→4.622초 | [EVAL_REPORT 4·6·7](../../EVAL_REPORT.md)의 **전후 비교 기준**. 동일 현재 Skill의 Prompt 비교일 뿐 과거 v4+Skill v6 완전 재현은 아니다. 단일 실행·사람 평가 없음. |
| **v5 단독 2,048-token** | 10/2, v5 + 현재 Skill, max 2,048·timeout 60초. [실험](2026-10-02_gemini-v5-30case-evaluation.md), 분류 보완 [PR #158](https://github.com/aihuman-7th/proj2-3/pull/158) | 계약 29/30; `coach-failure-26` 2,032 completion tokens에서 JSON 절단, 당시 provider 오류 분류 보정 필요 | 앞의 **2,048·45초 페어 비교와 다른 실행**이다. 두 실행의 30/30과 29/30을 한 결과로 취급하지 않는다. |
| **v5 단독 4,096-token** | 10/2, v5 + 현재 Skill, max 4,096·timeout 60초. [실험](2026-10-02_gemini-v5-4096-30case-evaluation.md), [사람 검토 준비 PR #161](https://github.com/aihuman-7th/proj2-3/pull/161) | 계약 30/30, `finish_reason=stop` 30/30, 규칙 정확도 92.6%, 비용 $0.171308, p50/p95 4.393/6.167초; 자동 label/evidence 불일치 7건 | **출력 절단 후속 확인**. 토큰 상한이 달라 위 v4/v5 비용·지연·의미 품질 비교표를 대체하지 않는다. |
| 이전 v4+Skill v6 정형 출력 재평가 | 별도 조건의 [10/2 재평가](2026-10-02_gemini-structured-output-reevaluation.md) | 계약 30/30, 다른 불일치 7건 기록 | 실행 Prompt/Skill 및 불일치 case 집합이 다르므로 v5 4,096-token의 검토 목록으로 사용하지 않는다. |

`local-results/`의 비교 JSON, 결합 Prompt, 원시 출력, 사람 검토 양식은 Git 제외 대상이다. 장기 보고서는 각 실험 문서의 조건·집계·해시 설명으로 연결하되, **현재 작업에서 raw artifact를 재조회하거나 독립 재계산하지는 않았다.**

## 2. EVAL_REPORT 4·6·7장 교차검증

| 구간 | 기존에 확인되는 내용 | 누락된 증거 또는 해석 경계 |
| --- | --- | --- |
| **4장** 동일 조건 개선 전후 | [비교 실험](2026-10-02_latest-english-v5-comparison.md)의 계약 30/30, 자동 통과 22→20, 판정 116→107, 비용·p95·실패 case를 반영했다. 4-2에 단독 4,096-token 후속 실행도 분리 기록했다. | 4,096 재실행은 추가 계약 근거일 뿐 같은 조건의 비교 결과가 아니다. 전후 반복 측정·최신 v5 자유서술 사람 품질 검토는 없다. |
| **6장** 측정 지표 | 2,048·45초 **provider 평가 runner**의 완료 지연·비용·자동 통과를 기록했다. | 인증·공고 검색·MCP·STT·저장까지 포함한 운영 E2E latency/성공률과 **TTFT는 미측정**. 로컬 Langfuse 기록이나 과거 실험 수치를 이번 표에 합산하지 않는다. |
| **7장** 출시 게이트 | 동일 조건 v5의 계약 30/30·p95 4.622초·정상 10/12를 기록했고, 경계 4/10·실패 유도 6/8은 미달로 표기했다. 4,096-token 계약 30/30은 후속 근거로 남겼다. | 새 v5 사람 semantic/critical 검토 0/30, 비용 상한 미합의, 같은 조건 반복 검증과 실제 운영 E2E 미확인. 최종 출시 게이트 통과로 표시할 수 없다. |

**집계 분모 주의:** 2,048·45초 비교의 정책 포함 자동 경계 통과는 4/10이지만, runner `promotion_gate`(질문/행동 정책 제외)는 5/10이다. 지표를 섞지 않는다.

## 3. 현재 v5 사람 검토: 이미 준비됨 / 실제 미수행

[4,096-token 실험](2026-10-02_gemini-v5-4096-30case-evaluation.md)에서 선택한 유효 자동 불일치 **정확히 7건**:

| 정상 | 경계 | 실패 유도 |
| --- | --- | --- |
| `coach-normal-09` | `coach-boundary-13`, `coach-boundary-16`, `coach-boundary-17`, `coach-boundary-19`, `coach-boundary-20` | `coach-failure-27` |

- [PR #161](https://github.com/aihuman-7th/proj2-3/pull/161)은 병합됐다. `evals/build_gemini_v5_human_review.py`로 `local-results/gemini-v5-4096-live-30/comparison.json`을 읽고, `local-results/gemini-v5-4096-human-review/`에 `REVIEW.md`와 `semantic-reviews.template.json`을 생성했다는 [Worklog](../worklogs/2026-10-02_1140_gemini-v5-human-review-prep.md)가 있다.
- **미수행:** 원본 답변과 현재 출력에 대한 사람의 이유·행동·질문·사실 충실성 평가, case별 critical 판정과 이유, 검토자 서명/합의. 템플릿의 `null`은 미검토이지 오류 0건이 아니다.
- **범위 구분:** 이 7건은 우선 검토할 자동 불일치이며, [EVAL_REPORT 7장](../../EVAL_REPORT.md)의 전체 새 출력 사람 검토 상태 `0/30`을 자동으로 충족시키지 않는다. 나머지 23건 검토 범위와 최종 통과 기준은 팀이 정한다.
- [예전 v4+Skill v6 재평가](2026-10-02_gemini-structured-output-reevaluation.md)의 다른 7건, D4 Dataset v2 **정답표** 30건의 단일 사람 검토, 예전 영문 v4 팀원 의견은 이 v5 사람 평가에 대체 사용할 수 없다.
- 기존 runner에 작성된 `--semantic-reviews`를 전달하면 **새 유료 모델 호출**이 발생한다. 저장 출력에 대한 offline 사람 점수 취합 경로는 아직 기록되지 않았으므로 실행 비용 승인 전 임의 호출하지 않는다.

## 4. 배포·PlayMCP·Langfuse 증거: 별도 축

**2026-10-02 현재 read-only 공개 재검증:** 운영 Frontend `https://www.malhaebom.xyz/` GET 200, 운영 Cloud Run `https://malhaebom-mk2-909028462046.asia-northeast3.run.app/health` GET 200(`Access-Control-Allow-Origin: https://www.malhaebom.xyz`), 공고 추천 엔드포인트의 Frontend Origin/CORS OPTIONS 200(`GET, POST, DELETE` 허용)을 확인했다. 배포 Frontend JS의 Cloud Run 호스트 연결도 확인했다. 이는 URL·서버 health·CORS만 입증하며, 사용자 브라우저의 로그인 성공은 사용자 수동 보고이고 **인증 후 공고 검색·PlayMCP 정상 응답을 입증하지 않는다**.

운영 권한 확인: C2C 실행 환경에 `gcloud` 실행 파일은 있으나 현재 **활성 로그인 및 대상 GCP 프로젝트(프로젝트 번호 909028462046)의 조회 권한은 확인되지 않았다**. 따라서 과거 Cloud Logging의 인증 실패 예외 유형, 요청 당시 리비전·Secret 마운트/refresh 상태, production Langfuse trace를 열람하거나 원인을 확정하지 못했다. 공개 상태 확인 시도는 비인증 GET/OPTIONS뿐이며 운영 쓰기·배포·설정 변경은 없었다.

**후속 사용자 보고:** 사용자로부터 PlayMCP가 이제 작동한다는 복구 소식을 전달받았다. 기존 브라우저의 인증 오류는 당시 증상으로 보존하며, 현재까지 동일 운영 요청의 PlayMCP 도구 호출→공고 추천→선택 공고 원문 분석에 대한 연속 HTTP/도구 로그와 실행 시각은 별도로 받지 못했다. 현재 장애 지속으로 표현하거나, 복구 원인·전체 운영 E2E·운영 trace 확보로 확대하지 않는다.

**후속 사용자 수동 E2E:** 동일 사용자가 실제 운영 브라우저에서 공고 검색·선택 공고 원문 분석·연습 및 1/2차 코칭 비교까지 성공했다고 추가로 확인했다. 따라서 **외부 배포 URL 및 사용자 기능 동작**은 직접 수동 검증이 보고된 것으로 분류한다. 이 대화에서 실행 시각·캡처·요청 ID·실제 PlayMCP 도구 결과·production Langfuse trace는 전달받지 않았으며, 운영 로그 기반 검증이나 모델 품질 판정까지 완료됐다는 뜻은 아니다.

**후속 Langfuse Cloud 화면 증거:** 사용자가 10/2 14:28 경 실행의 동일 코칭 trace 상세 화면 세 장을 제공했다. `coaching.provider`는 `google/gemini-3.5-flash-lite`, 15.84초이며, `coaching.output_validation` 출력은 `valid=true`, `error_count=0`, `coaching.analyze` 최종 출력은 정상 코칭 상태 `needs_more_info`였다. Trace 헤더에는 총 16.00초·17,428 tokens·$0.008467이 표시됐다. 서로 다른 실행의 수치를 합산하지 않는다. 화면에 표시된 사용자·세션 식별자와 개인 원문은 저장소에 복사하지 않았다. **관측된 사실:** Langfuse Cloud에 해당 모델 호출→검증→결과 처리 트리가 존재한다. **추가 확인:** trace의 `environment`, Prompt·Skill 버전, 운영 Cloud Run 리비전과 보고된 1/2차 비교 세션의 동일성. Langfuse Cloud의 해당 기록만으로 운영 리비전·PlayMCP 검색 연결이나 전체 사용자 E2E 자동 계측을 독립 확정하지 않는다.

**추가 Metadata·Environment 화면 확인:** 동일 `coaching.provider` 상세 Attributes에서 `outcome=success`, `status_code=200`, `will_retry=false`, `transport_attempt=1`, `contract_attempt=1`을 확인했다. **기록된** `skill_version`은 `interview-coach-v6`이었다. 한편 현재 저장소 기본 Skill 카탈로그는 `interview-coach-v6.1-domain-rules`이고, [PR #162](https://github.com/aihuman-7th/proj2-3/pull/162)의 기본 버전 메타데이터·실행 버전 기록 수정은 `main`에 병합 완료됐다. 과거 trace의 표시된 `v6`은 **관측 메타데이터 불일치 가능성의 실사례**로 기록하고, 당시 운영에서 실제 v6을 로드했다는 결론으로 사용하지 않는다. 운영 재배포·적용 리비전·새 trace 검증은 별도다. Tracing 목록의 Environment는 `default`이고 Prompt Name은 표시되지 않았다. 이 값만으로 `production` 환경 또는 관리형 Prompt 부착을 입증할 수 없다. 식별자·공개 키가 나타나는 원본 캡처는 Git에 저장하지 않는다.

| 범위 | 확보된 기록과 출처 | D10 / 강사 피드백에서 아직 필요한 것 |
| --- | --- | --- |
| 인증 사용자 로컬 공고 분석 | [10/1 redacted E2E](../evidence/job-source-analysis-e2e-2026-10-01.md): 인증 사용자 → 추천 3건 → 사람인 원문 분석 5개 요구사항 → quote 검증 → 저장·조회 → 세션 생성. 당시 PlayMCP 인증 503으로 **web provider로 전환**했다. | 성공한 로컬 전체 경로를 **PlayMCP 직접 E2E**로 표시할 수 없다. |
| PlayMCP 검색/운영 요청 | [단계별 실행 Notion 기록](https://app.notion.com/p/3ed25eea3aeb80aa95d6d605354251c9): 10/1 로컬 직접 도구와 별도 Cloud Run 진단 Job 각 20건, 10/1 운영 추천 200→분석 201, 10/2 08:41 운영 추천 200 및 운영 리비전 구성 기록. 해당 Notion 페이지는 직접 열람했으나 Notion의 검증 상태는 unverified다. | **같은 운영 요청**의 PlayMCP 도구 결과 → 추천 응답 → 선택 원문 분석 결과를 이어주는 redacted correlation/로그·실행 시각·revision. 별도 성공 실행들을 하나로 결합하지 않는다. 코칭 직전 `CallToolRequest` 로그는 별도 stdio 코칭 MCP이며 사람인 PlayMCP 직접 검색 입증이 아니다. |
| 당시 운영 인증 오류 및 후속 수동 성공 | 10/2 사용자가 로그인 이후 공고 검색 시 PlayMCP 인증 안내를 확인했고, 이후 운영 브라우저에서 공고 검색→원문 분석→1/2차 비교까지 성공했다고 보고했다(이번 성공 실행 캡처·로그는 아직 미제공). | 사용자 수동 기능 성공으로 분류하되 복구 원인과 실제 동일 요청의 PlayMCP 도구 사용은 미확인. 운영 로그/trace와 요청별 correlation을 별도 검증한다. |
| Langfuse Cloud 화면 및 과거 로컬 trace | 사용자 캡처의 10/2 14:28 경 단일 코칭 trace에 provider 성공 HTTP 200·검증(`valid=true`, 오류 0)·분석(`needs_more_info`)이 연결된다. Skill **기록값**은 `interview-coach-v6`, 목록 Environment는 `default`, Prompt Name은 미표시다. 별도 [9/29 로컬 Worklog](../worklogs/2026-09-29_1430_langfuse-authenticated-e2e.md)는 당시 `coaching-output-v3`/`interview-coach-v5` 기록이다. | PR #162 적용 전 기본값 오표기 가능성과 실제 Skill 로딩을 구분한다. 현재 trace가 운영 리비전·1/2차 세션에 해당하는지 및 관리형 Prompt/실제 버전을 확인한다. 과거 로컬 trace를 최신 운영 설정의 증거로 대체하지 않는다. 원본 화면은 Git에 넣지 않는다. |
| 새 Prompt·Skill 정적 구현 | [분리 Spec](../specs/coaching-domain-rules-in-skill.md), 병합된 [PR #153](https://github.com/aihuman-7th/proj2-3/pull/153). [PR #162](https://github.com/aihuman-7th/proj2-3/pull/162)는 승인·CI 4/4 후 병합 완료됐다. | 운영 컨테이너의 실제 Prompt·Skill 조립 본문, Langfuse `production` 원격 Prompt 버전·규칙 중복 및 rollback 실제 동작 검증. PR 병합과 운영 적용은 다르다. |

**D10 당시 실패 observation 기반 한 줄 가설(미검증·현재 복구 보고):** 이전 PlayMCP 인증 오류는 당시 리비전의 인증 파일 제공·권한 또는 token refresh 실패였을 수 있다. 현재 동작 복구가 보고됐으므로 과거 원인 규명은 후순위로 두되 재발하면 운영 로그로 분리 확인한다. 이 가설은 원인 판정·전체 D10 달성이 아니다.

## 5. 남은 작업과 검증 주체

| 순서 | 주체 / 의존성 | 다음 증거 | 항목 |
| --- | --- | --- | --- |
| 1 | 로컬 평가 결과 접근 가능 검토자 | 4,096-token 실행의 **위 7건** `REVIEW.md`를 원문 대조해 검토자·semantic 점수·critical 여부/이유 작성. 나머지 23건 범위/합격 기준 합의 | v5 품질·D12 |
| 2 | 팀 합의 | 예전 영문 v4 평가의 공통 루브릭 및 17번 중대 오류 분류·최종 점수 확정. 새 v5와 별도 기록 | 과거 팀 평가 |
| 3 | 팀/평가 담당 | 비용 상한, 현재 v5 최종 반복 실행 조건, D11 운영 release 기준 baseline 및 동일 조건 단일 변경·3개 injection 전후 계획 확정. 재호출 전에 비용 승인 | EVAL_REPORT 7·D11/12 |
| 4 | GCP/Langfuse 운영 권한 보유 담당 | 요청별 PlayMCP 검색·원문 분석 correlation, 운영 성공/실패 trace의 모델·Prompt·Skill 버전, sanitize된 캡처, release manifest/rollback 실제 결과 | D10·강사 피드백 |

이 문서는 **증거 인덱스와 누락 점검**이다. 누락된 사람 평가 점수, 정상 운영 trace, 단일 PlayMCP 운영 요청 연결 증거, D11/D12 최종 동일 조건 전후를 만들어내거나 완료 처리하지 않는다.
