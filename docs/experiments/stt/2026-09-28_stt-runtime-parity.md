# 2026-09-28 STT service-runtime parity

## 상태

COMPLETED — frozen 30건 dev/diagnostic set에서 CPU/int8 ↔ CUDA/float16 비교 완료

## 목적

서비스 기본 STT 런타임과 기존 실험 런타임의 차이를 분리한다.

이전 model × beam, prompt/hotwords 실험은 large-v3-turbo + beam 1 + CUDA/float16에서 수행했다. 실제 서비스 기본값은 large-v3-turbo + beam 1 + CPU/int8이므로, 모델·revision·devset·prompt를 고정하고 device/compute type만 바꿔 정확도와 지연을 비교한다.

## 고정 조건

- model: mobiuslabsgmbh/faster-whisper-large-v3-turbo
- immutable model revision: 기존 matrix/prompt A/B와 동일
- beam size: 1
- language: ko
- task: transcribe
- temperature: 0.0
- word_timestamps=True
- vad_filter=False
- condition_on_previous_text=False
- frozen dev/diagnostic set: 30건, 기존 provenance 검증 재사용
- hint mode: initial_prompt
- hint content: 기존 prompt/hotwords A/B의 고정 15개 diagnostic term
- 변경 변수만:
  - cpu-int8: device=cpu, compute_type=int8
  - cuda-float16: device=cuda, compute_type=float16

고정 15개 prompt는 production dynamic hint 자체를 재현하려는 것이 아니라 runtime 차이만 분리하기 위한 통제 조건이다.

## 결과

| Runtime | Core norm CER | Core norm WER | Stress norm CER | Stress norm WER | 전체 norm CER | 전체 norm WER | Hint recall | False insertion | RTF | p50 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CPU / int8 | **1.94%** | **4.59%** | 6.77% | 14.29% | **2.93%** | **5.80%** | 94.12% | 0 | 0.213 | 3.022s | 3.155s |
| CUDA / float16 | 2.44% | 5.27% | 6.77% | 14.29% | 3.33% | 6.40% | 94.12% | 0 | **0.020** | **0.269s** | **0.438s** |

raw 전체 지표:

- CPU/int8: CER 4.62%, WER 7.60%
- CUDA/float16: CER 5.05%, WER 8.48%

총 425.17초 음성 처리시간:

- CPU/int8: 90.72초
- CUDA/float16: 8.33초

따라서 이 로컬 환경에서는 CUDA/float16이 aggregate RTF 기준 약 10.9배 빠르다.

## 전사 차이 확인

두 runtime의 prediction이 달랐던 문장은 4/30건이었다.

- real-19: 1,233 표기 여부 차이. spoken-form normalized score는 동일.
- real-21: 쉼표 차이. normalized score는 동일.
- real-25: CPU는 발화 시작의 "음.."을 보존했고 GPU는 생략했다.
- real-30: CPU는 reference와 완전 일치했지만 GPU는 문장 끝에 "다음 영상에서 만나요."를 추가했다.

특히 real-30은 CUDA/float16에서만 나타난 명확한 tail hallucination이며 core 정확도 차이에 영향을 주었다.

## 해석

- CPU/int8은 이번 devset에서 정확도가 소폭 더 좋았다.
- 기술 질문과 숫자·영문 stress 구간은 두 runtime이 사실상 동일했고, 차이는 natural/long 구간에 집중됐다.
- 기술용어 recall 94.12%, false insertion 0건은 동일했다.
- CUDA/float16은 로컬 데스크톱에서 latency가 크게 낮았다.
- 이 결과만으로 production device를 변경하지 않는다. CPU 결과는 Ryzen 데스크톱 로컬 측정이며 실제 Cloud Run CPU 성능을 대표하지 않는다.
- 기존 30건은 이미 여러 설정 선택에 사용된 dev/diagnostic set이므로 final acceptance 근거가 아니다.

## 현재 판단

서비스 기본 CPU/int8은 accuracy 관점에서 유지 가능한 상태다. 다만 p50 약 3초의 로컬 STT 지연은 실제 배포 환경에서 별도 측정해야 한다.

다음 단계:

1. 현재 서비스 Docker/배포 환경에서 STT p50/p95 및 E2E latency를 실측한다.
2. 새 multi-speaker acceptance set에서 production dynamic initial_prompt를 사용해 최종 품질을 검증한다.
3. GPU 사용을 검토한다면 real-30 유형의 tail hallucination을 함께 회귀 검증한다.
