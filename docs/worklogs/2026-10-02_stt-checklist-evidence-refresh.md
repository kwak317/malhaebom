# Worklog — STT 실험 근거와 체크리스트 상태 재정렬

- 일시: 2026-10-02 (KST)
- 작업자/에이전트: ChatGPT
- 관련 PR: #146 (기존 계보 문서), 이번 체크리스트 수정은 로컬 미커밋
- 관련 결정: `docs/DECISIONS.md`의 B0/C2 면접 도메인 후보 선택·제품 기본 모델 별도 결정

## 1. 목적

기존 체크리스트가 STT 실사용 녹음·정규화 전후 측정·후보 비교를 미완료로 표시하는 문제를 바로잡고, **이미 끝난 개발/진단 실험**과 **아직 수행하지 않은 독립 acceptance/운영 E2E**를 분리한다. 공식 D2~D12 체크포인트와 독립인 STT 트랙만 갱신한다.

## 2. 작업 전 상태

- 체크리스트는 1인 녹음 확보·CER/WER·baseline 후보 비교·회귀·기본 모델 결정을 대체로 미완료로 기록했다.
- `docs/stt-finetuning-lineage.md`에는 50k retrain, B0 clean continuation, C1/C2 domain adaptation, sealed 71592 test, 1인 30건 비교 및 서비스 추론 실험의 구분이 기록돼 있다.
- `[REDACTED].md`는 30건의 raw/발화형 정규화 CER/WER를, `[REDACTED].md`는 9조합을 기록한다.
- `[REDACTED].md`, `[REDACTED].md`, `[REDACTED].md`에 추론 힌트·런타임·Cloud Run mock 실험 수치가 있다.
- 10/1 B0/C2 Drive 인계 Worklog는 현재 미커밋 로컬 파일이다. 본 작업과 무관한 해당 파일 변경은 보존한다.
- Hosted Supabase 실제 사용자 STT E2E는 별도 `experiment/hosted-analysis-e2e` worktree에 실행 계획/검증 스크립트가 준비된 상태였으며, 확인 당시 프로젝트 연결·실측 완료 증거는 없었다. 계획 파일은 main에 존재하지 않으므로 main 문서 링크로 만들지 않는다.

## 3. 수행 내용

1. `[REDACTED].md` 요약 표의 오래된 STT 미완료 설명을 진단 완료/최종 검증 대기로 바꿨다.
2. 완료 항목으로 1인 30건 devset 고정, raw·spoken-form normalized CER/WER, 50k/B0/C1/C2의 holdout·retention, 모델×beam 9조합, prompt/hotwords A/B, CPU/GPU parity, Cloud Run mock benchmark를 정리했다.
3. 로컬 Drive 인계·수신 검증은 일부 완료로 기록했고 수신자의 원격 다운로드 SHA256/모델 로드/추론은 미확인으로 남겼다.
4. 다중 화자 독립 acceptance 구축 및 최종 전사/환각/기술용어 회귀, 실제 Hosted Supabase STT E2E, 제품 기본 모델/런타임 결정을 후속 항목으로 남겼다.
5. STT 계보와 서비스 추론의 조건이 다르고, 1인 devset은 이미 튜닝에 사용됐음을 명시해 결과 오용을 막았다.

## 주요 판단과 이유

- 71592 sealed test(C2 CER 2.5876%, WER 9.7740%)는 신규 면접 도메인에 한정되며 기존 도메인 retention 및 서비스 모델 선정의 단독 근거로 확장하지 않는다.
- 1인 30건 raw/normalized CER·WER와 9조합 비교는 이미 수행됐으므로 해당 **실험 작업**은 완료로 표시한다. 다만 기존 녹음셋은 dev/diagnostic이므로 **신규 다중 화자 독립 acceptance**를 별도로 미완료로 기록한다.
- `large-v3-turbo`의 GPU devset 비교에서 유리한 지표가 관찰됐더라도 실제 서비스는 CPU/int8을 유지하며, 운영 장치 지연과 새로운 화자 데이터의 오류를 함께 확인해야 한다.
- Cloud Run 2/4/8 vCPU benchmark는 실제 Hosted Supabase DB/RLS/Storage latency를 포함하지 않으므로 운영 E2E 완료로 표시하지 않는다.
- 10/1 인계는 로컬 ZIP 체크섬·Drive 목록 확인까지 기록돼 있지만 원격 다운로드 후 바이트 검증과 수신자 추론까지 완료한 것으로 주장하지 않는다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `[REDACTED].md` | 요약 표 + 별도 STT 트랙 완료·미완료 세분화 |
| `[REDACTED].md` | 본 실험 근거 대조 Worklog |
| `docs/worklogs/README.md` | Worklog 목록 추가 |

## 5. 검증

- 위 원본 실험 문서의 수치·제약과 `docs/CURRENT_STATE.md`, `docs/DECISIONS.md`를 직접 대조했다.
- 별도 Hosted E2E worktree의 계획 상태를 읽고 main에 존재하지 않는 경로를 링크하지 않도록 확인했다.
- 체크리스트 갱신은 기록 정합성 작업이며, 새로 STT 학습·provider 호출·새 녹음 평가·Cloud Run 실행을 수행한 작업이 아니다. 실행 결과를 재측정했다고 기재하지 않는다.
- 반영 후 변경 파일/링크 및 기존 미커밋 작업 보존 여부를 재확인한다.

## 6. 발견한 문제 / 남은 리스크

- 기존 `docs/stt-current-status.md`는 9/17 이전 시점의 학습 기록도 함께 보존하므로, 최신 모델 실험 판단에는 `docs/stt-finetuning-lineage.md`와 시점별 실험 원본을 우선 사용해야 한다.
- 개인 30건 데이터의 사용자 다양성 부족, 원격 인계 검증 미완료, Hosted STT E2E 미완료로 최종 성능·제품 교체 판단을 확정할 수 없다.
- 신규 independent acceptance를 구성할 때 과거에 공개된 devset·sealed test를 재튜닝 또는 출시 판정 자료로 재사용하지 않는다.

## 미확인 사항

- 추가 화자 녹음 확보 여부, 표준어·자유발화·추임새 event 검증, 수신 환경 해시 확인/로드, 운영 RLS/Storage·실측 완료 및 모델 최종 교체는 확인되지 않았다.

## 7. 다음 작업

1. 신규 다중 화자 독립 acceptance의 음성/대본/provenance/분할 기준 확정.
2. 현재 production dynamic initial_prompt 및 후보 모델의 동일 조건 품질·기술용어·환각 회귀 평가.
3. 실제 Hosted STT E2E, 교차 사용자 RLS/Storage와 운영 지연 확인.
4. B0/C2 인계 수신 검증 후 서비스 모델/런타임 유지 또는 교체 최종 결정.

## 8. 사용자 확인 — 모델 인계 링크 전달

- 2026-10-02 사용자 확인에 따라 B0/C2 Drive 모델 인계 링크는 수신자에게 전달 완료로 기록했다. 공유 URL 자체는 제공받지 않았으므로 저장소에 임의 링크를 기재하지 않는다.
- 이는 로컬 ZIP/Drive 업로드 및 **링크 전달**의 완료를 뜻한다. 수신자가 해당 파일을 실제 다운로드한 후 원격 바이트 체크섬 대조, 모델 로드 및 음성 추론을 마쳤다는 뜻은 아니다. 후자의 증거는 계속 미완료로 관리한다.
