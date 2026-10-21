# D10 운영 증거 수집 runbook

## 목적과 경계

이 runbook은 현재 운영 revision에서 D10 trace·Prompt release/rollback·PlayMCP 동일 요청 E2E와 제출용 Langfuse 캡처를 **한 실행 단위**로 남기는 절차다. 운영 배포·Prompt 승격·rollback은 운영 권한 보유자가 명시적으로 승인한 경우에만 수행한다.

수집 전후에 API 키, JWT, 이메일, 사용자/세션 ID, 답변 전사, 공고 원문 URL·본문을 캡처·commit·공유하지 않는다.

## 사전 승인과 준비

1. 운영 담당자가 실행 창, Cloud Run service/revision 조회 권한, Langfuse read 권한, managed Prompt 승격/rollback 권한을 확인한다.
2. 비식별 테스트 계정과 합성 답변을 준비한다. 실제 사용자 기록을 재사용하지 않는다.
3. 실행 전 revision, 배포 commit, Prompt label/version/hash, Skill version/hash, 모델·provider route, 예산 상한을 기록한다. secret 원문은 기록하지 않는다.
4. 실패 데모는 재현 가능한 단일 실패 코드와 사용자 복구 안내를 사전에 합의한다. 인위적 장애 주입은 별도 승인 없이는 하지 않는다.

## A. 성공 요청의 동일 실행 증거

1. 운영 URL에서 로그인 → 공고 추천 → 선택 공고 원문 분석 → 연습 세션 → 코칭 → 재연습 비교를 수행한다.
2. 같은 요청에서 PlayMCP 도구 호출, 추천 응답, 원문 분석 응답에 공통으로 남는 redacted correlation ID를 보존한다. 각 단계에 provider/tool identity가 `PlayMCP`임을 함께 기록한다. 시각·revision만 일치하는 기록은 web fallback 또는 동시 요청과 구분할 수 없으므로 이 항목의 증거로 사용하지 않는다.
3. 같은 코칭 실행의 Cloud Run request ID/trace ID와 Langfuse trace를 연결한다.
4. Langfuse에서 다음 세 화면을 비식별 캡처한다.
   - trace tree: `coaching.provider` → `coaching.output_validation` → `coaching.analyze`
   - provider detail: model, token, cost, latency, retry/repair, Prompt·Skill version
   - 실패 trace: failure stage/code, retry 여부, 사용자 복구 안내
5. DB의 `coaching_runs` Prompt·Skill 값은 동일 실행 trace와 값 일치 여부만 남긴다.

## B. Prompt release와 rollback

1. 승격 조건(변경 변수 1개, Dataset/Skill/model 고정, 승인된 비용·품질 gate)을 기록한다.
2. candidate를 production label로 승격하고, A 절차의 합성 요청 1건을 실행해 trace의 Prompt version과 Skill version을 확인한다.
3. 이전 production version으로 rollback하고, 같은 조건의 합성 요청 1건을 실행해 이전 Prompt version으로 돌아왔음을 확인한다.
4. release/rollback 전후의 revision, 시각, Prompt version/hash, trace ID, 성공/실패를 release manifest에 기록한다.

## C. 판정과 제출 반영

- A와 B가 같은 운영 revision·동일 요청 연결을 증명하면 D10 trace 및 release/rollback 항목의 상태 갱신을 검토한다.
- 화면 존재나 HTTP 200만으로 Prompt production 적용·rollback·PlayMCP 동일 요청 E2E를 완료 처리하지 않는다.
- 비식별 캡처는 `docs/evidence/langfuse/`에, redacted 로그 요약은 `docs/evidence/`에 저장하고 [제출 증거 인덱스](../SUBMISSION_EVIDENCE.md)를 갱신한다.

## 실패 시 처리

- 권한·설정·trace 연결이 실패하면 production을 변경하지 않고, 시각·revision·고정 오류 코드·재시도 여부만 남긴다.
- rollback이 실패하거나 사용자 흐름이 훼손되면 즉시 운영 담당자의 기존 복구 절차로 전환하고, 증거 수집을 중단한다.
