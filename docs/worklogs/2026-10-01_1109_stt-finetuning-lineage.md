# Worklog — STT 파인튜닝 계보 문서화

- 일시: 2026-10-01 11:09
- 작업자/에이전트: ChatGPT
- 관련 이슈/PR: 이 작업에서 생성
- 관련 요구사항/결정: STT 신규 학습은 제품 기본 모델과 분리된 실험 범위로 관리하고, 평가 근거 없이 제품 기본 모델을 교체하지 않는다.

## 1. 목적

말해봄 저장소에 흩어져 있는 STT 파인튜닝 기록을 하나의 상위 문서로 정리한다.

완료 조건은 다음과 같다.

- 기존 6,000개 LoRA 이력과 adapter 누락으로 인한 계보 단절을 구분한다.
- 50k QLoRA retrain, clean continuation, AI Hub 71592 C1/C2 적응을 순서대로 연결한다.
- 각 단계의 고정 평가 수치를 기존 실험 문서와 일치하게 기록한다.
- 실제 녹음 30건의 범위와 일반화 한계를 명시한다.
- large-v3-turbo / beam / prompt / runtime 작업은 파인튜닝이 아닌 서비스 추론 최적화로 분리한다.

## 2. 작업 전 상태

- `docs/stt-finetuning-6000.md`에 legacy 6k LoRA 기록이 존재했다.
- `docs/specs/stt-finetuning-retrain.md`에 legacy adapter 누락과 새 50k QLoRA 계보의 실험 경계가 정의돼 있었다.
- 50k retrain, clean continuation, 71592 domain adaptation, 실제 녹음 평가는 각각 별도 실험 문서로 존재했다.
- 서비스 추론 최적화는 large-v3-turbo 기준의 model × beam, prompt/hotwords, runtime 실험으로 별도 진행된 상태였다.
- 위 흐름을 한 번에 설명하는 상위 파인튜닝 계보 문서는 없었다.

## 3. 수행 내용

1. legacy 6k LoRA부터 C2까지의 모델 계보를 하나의 문서에 연결했다.
2. 각 단계의 데이터 규모, 학습 설정, validation/holdout/test 결과를 기존 실험 기록에서 재확인해 요약했다.
3. C2의 71592 적응 성능과 historical 119 retention 회귀를 동시에 기록했다.
4. 1인 30건 실사용 평가를 별도 섹션으로 두고 일반화 제한을 명시했다.
5. large-v3-turbo 계열 작업을 파인튜닝과 분리해 서비스 추론 최적화로 설명했다.
6. `docs/README.md`에 새 문서를 추가하고 Worklog 목록을 갱신했다.

## 주요 판단과 이유

- 새 문서는 기존 실험 원본을 대체하지 않고 상위 요약/계보 문서로 둔다.
- 6k legacy 모델과 50k retrain 사이에는 adapter weight 누락으로 exact continuation이 없으므로 하나의 연속 학습처럼 서술하지 않는다.
- 71592는 면접/content domain 데이터이며 지역 출신 metadata가 검증되지 않았으므로 경상도 적응 근거로 사용하지 않는다.
- C2는 B0보다 historical retention이 나쁘므로 전역적으로 더 우수한 모델이라고 표현하지 않는다.
- 서비스 기본 STT 선택은 파인튜닝 결과와 별도의 model/beam/prompt/runtime 비교 근거로 판단한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `docs/stt-finetuning-lineage.md` | STT 파인튜닝 전체 계보와 평가 결과 요약 |
| `docs/README.md` | 새 STT 파인튜닝 계보 문서 링크 추가 |
| `docs/worklogs/2026-10-01_1109_stt-finetuning-lineage.md` | 이번 문서화 작업 기록 |
| `docs/worklogs/README.md` | Worklog 목록 추가 |

## 5. 검증

- 기존 실험 문서의 데이터 규모, 학습 설정, CER/WER 수치를 새 문서와 대조한다.
- Markdown 링크와 저장소 diff를 확인한다.
- 문서 전용 변경이므로 모델 학습이나 제품 E2E를 다시 실행하지 않는다.
- PR 생성 전 저장소의 review-size/policy check를 실행 가능한 범위에서 확인한다.

## 6. 발견한 문제 / 남은 리스크

- legacy 6k LoRA의 원 adapter weight는 기존 기록대로 누락 상태다.
- C2는 historical 119 retention에서 B0보다 회귀하므로 전역 기본 모델 채택 근거로 사용할 수 없다.
- 실제 녹음 평가는 동일 화자 30건으로 제한돼 multi-speaker 일반화 근거가 아니다.

## 미확인 사항

- 이 문서화 작업에서 STT 학습이나 실제 추론 benchmark를 재실행하지 않는다.
- 서비스 기본 runtime 변경 여부는 별도의 최신 STT runtime 평가와 통합 판단을 따른다.

## 7. 다음 작업

- 발표/보고서에서는 파인튜닝 계보와 서비스 추론 최적화를 별도 슬라이드/항목으로 구분한다.
- 신규 multi-speaker acceptance 평가가 수행되면 이 문서의 실사용 평가 한계를 후속 증거로 보완한다.
