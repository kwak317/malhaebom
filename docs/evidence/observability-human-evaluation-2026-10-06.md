# 운영 Langfuse trace와 실제 코칭 응답 사람 평가 증거

- 정리일: 2026-10-06
- 목적: 3조 관측·평가 피드백에서 찾기 어려웠던 기존 trace와 사람 평가 기록을 하나의 증거 문서로 연결한다.
- 기록의 존재와 최신 운영 품질 확정은 구분한다. 서로 다른 날짜·버전의 기록을 동일 실행으로 합치지 않는다.

## 1. 확인 결과

| 항목 | 존재하는 증거 | 확인 범위 |
| --- | --- | --- |
| 배포 서비스 요청과 직접 연결된 Langfuse trace | 10/5 운영 `/api/agent` 401의 `X-Trace-Id`와 Langfuse trace ID 일치 | 인증 실패 관측. 모델 호출·코칭 성공 증거 아님 |
| 코칭 호출·검증·분석 trace | 10/4 동일 trace의 provider → output validation → analyze | 트리 존재 확인. Cloud Run 요청과는 시간 대조이며 1:1 연결 미확정 |
| 실제 코칭 응답 사람 평가 | 과거 핵심 15case 출력 63개 및 10/1 v4 팀 품질 검토 | 과거 응답 평가. 현재 운영 버전의 신규 품질 승인 아님 |
| 평가셋 정답 사람 검토 | 9/30 김재훈의 30건 expected label·근거 검토 | 평가셋 정답 검토이며 코칭 출력 품질 점수와 별개 |

따라서 “운영 연결 trace와 사람 평가 기록이 전혀 없다”는 전체 이력 설명은 부정확하다. 현재 운영 버전의 성공 요청·trace 직접 연결 및 해당 출력의 사람 평가 완료는 별도의 미확인 항목이다.

## 2. 운영 요청과 직접 연결된 인증 실패 trace

- 과거 실행: 2026-10-05 20:34:18 KST.
- 운영 URL: `https://malhaebom-mk2-fmf5h3xp4q-du.a.run.app/api/agent`.
- 당시 기록된 트래픽: `malhaebom-mk2-resume-1004-1438` 100%.
- HTTP 401 응답의 `X-Trace-Id`: `69c407acae31476a9c4ecdbd0c9cba9c`.
- [Langfuse trace](https://jp.cloud.langfuse.com/project/cmuajvd4n00c9ad0c18ctq838/traces/69c407acae31476a9c4ecdbd0c9cba9c) — 프로젝트 접근 권한 필요.
- `coaching.analyze`, `level=ERROR`, `failure_stage=request`, `failure_state=auth_error`, `error_code=COACHING_REQUEST_FAILED`, `model=not_started`, `attempt_count=0`, `retry_count=0`.

[과거 요청의 공개용 증거](observability-human-evaluation-2026-10-06/production-request-2026-10-05.redacted.json)는 보존 기록에서 필요한 필드만 추출했다. 새 요청이나 모델 호출을 만들지 않았다. 이 trace는 관측 연결의 증거이며 Prompt·Skill 실패 또는 LLM 코칭 성공으로 해석하지 않는다.

## 3. 코칭 provider·검증·분석 trace

[대표 trace](https://jp.cloud.langfuse.com/project/cmuajvd4n00c9ad0c18ctq838/traces/97861049b9a44d6fb76f678f4c90eb8c)의 10/4 기록:

| 관측 | 시작 시각 KST | 기록 |
| --- | --- | --- |
| `coaching.provider` | 13:58:13.644 | `google/gemini-3.5-flash-lite`, 5.965초 |
| `coaching.output_validation` | 13:58:19.610 | 동일 trace ID |
| `coaching.analyze` | 13:58:19.748 | 동일 trace ID |

기록된 Prompt version은 `coaching-user-supplied-v4-verification`, environment는 `default`다. `default`만으로 운영 환경을 입증하지 않는다. 같은 시간 Cloud Run `malhaebom-mk2-targeted-1004-1340`의 `/api/agent` 200 기록이 있었으나 공통 trace ID가 없어 1:1 연결은 미확정이다.

이번 정리에서 운영 배포 revision에 연결된 자격증명을 사용해 Langfuse Observations API v2를 읽기 전용 재조회했다. 위 두 trace의 관측 총 4개가 현재 서버에도 존재함을 확인했다. [재조회 JSON](observability-human-evaluation-2026-10-06/langfuse-live-recheck.redacted.json)에 확인 시각과 공개용 필드만 보존했다. 자격증명·사용자/세션 ID·원문 input/output은 포함하지 않는다.

## 4. 실제 코칭 응답을 사람이 평가한 기록

### 4.1 과거 핵심 15case 의미 품질 평가

[평가 보고서의 과거 사람 semantic 검토](../../EVAL_REPORT.md)에 핵심 15case의 Basic 출력 45개와 실제 Premium recovery 출력 18개, 총 63개를 같은 rubric으로 검토한 기록이 있다. reason, 개선 행동, 확인 질문, 사실 보존 및 critical failure를 평가했다. 사용자 제공 사람 검토 결과이며 자동 grader 점수와 구분된다.

단일 검토자다. Batch 1만 strict blind이고 이후 batch는 mapping 노출 후 채점했다. Premium은 어려운 subset이므로 Basic과 절대 점수를 직접 비교하지 않는다.

### 4.2 2026-10-01 v4 코칭 응답 팀 품질 평가

[팀 품질 평가 취합](../experiments/2026-10-01_coaching-v4-team-quality-review.md)에 실제 Gemini 3.5 Flash Lite v4 응답 30건의 팀원 평가가 기록돼 있다.

| 평가 출처 | 범위 | 보고 점수 | 한계 |
| --- | --- | --- | --- |
| 팀원 1 | 응답 30건 | 227/240, 94.6% | 사례별 원점수와 신규 15건 기준 본문 미제공 |
| 팀원 2 | 15건 채점 + 나머지 15건 검토 의견 | 101/120, 평균 6.73/8 | 나머지 15건 정량 점수 없음 |
| 사용자 평가용 AI 초안 | 30건 초안 | 사람 점수 집계에서 제외 | AI 작성·사용자 확인 전, 독립 사람 평가 아님 |

사람이 실제 출력의 판정 일관성·개선 제안·확인 질문·사실 보존을 검토한 기록이다. 서로 다른 기준·범위의 점수를 합산해 최종 팀 점수로 만들지 않았다. 과거 v4 평가이며 현재 Prompt·Skill 품질 확정이나 외부 면접관 검토 완료를 주장하지 않는다.

### 4.3 평가셋 정답 검토는 별도

[30건 판정자·근거 표](../../evals/reviewer-assignment.md)에 김재훈의 9/30 사람 검토가 있다. 29건 확정, `coach-boundary-17`의 V를 `partial → undetermined`로 수정했다. 이는 입력과 expected 판정의 검토이며 위 출력 품질 점수와 합치지 않는다.

## 5. 남은 확인과 해석

- 현재 운영 버전의 로그인 성공 요청 → provider → 검증 → 분석을 동일 trace ID로 직접 연결한 증거.
- 현재 버전의 실제 출력에 대한 사례별 독립 사람 점수·근거 및 공통 기준 합의.
- 동일 버전·평가셋 반복 실행의 안정성과 원본 결과 공개는 별도 평가 기록으로 확인해야 한다.
- 이 문서화는 과거 기록의 공개용 정리와 조회다. 새 사용자 E2E·LLM 재평가·배포·Prompt 승격을 수행하지 않았다.
