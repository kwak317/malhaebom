# 2026-09-28 실사용 STT 모델 × beam 비교

## 상태

COMPLETED — 9개 조합 실행 완료

2026-09-27에 고정한 1인 화자 실사용 녹음 30건을 dev/diagnostic set으로 사용해 모델 차이와 beam size 차이를 분리한다. 이 데이터는 이미 결과를 확인하고 정규화 규칙을 만든 데이터이므로 최종 acceptance 성능 근거로 재사용하지 않는다.

## 목적

다음 두 질문을 순서대로 확인한다.

1. 동일한 추론 조건에서 large-v3-turbo, B0, C2 중 어떤 모델 특성이 실제 면접형 녹음에 유리한가?
2. 각 모델에서 beam_size=1/3/5가 정확도와 처리시간에 어떤 trade-off를 만드는가?

이번 단계에서는 추가 fine-tuning, hotwords, initial prompt를 사용하지 않는다.

## 비교 행렬

| 모델 ID | 모델 |
| --- | --- |
| large-v3-turbo | mobiuslabsgmbh/faster-whisper-large-v3-turbo |
| b0 | clean continuation CT2 |
| c2 | AI Hub 71592 + historical replay 20% CT2 |

각 모델에 beam 1, 3, 5를 적용해 총 9개 조합을 비교한다.

### Immutable model provenance

- large-v3-turbo
  - Hugging Face repo: `mobiuslabsgmbh/faster-whisper-large-v3-turbo`
  - pinned revision: `0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf`
  - full matrix 실행 후 로컬 Hugging Face cache의 `refs/main`과 snapshot directory에서 동일 revision을 확인했다.
  - 재현 runner는 alias가 아니라 repo ID와 위 revision을 `WhisperModel(..., revision=...)`에 명시적으로 전달한다.
- B0 local CT2 fingerprint: `dff88625c0265bc33398942d295085edca4d06c17661d6246bcbb1cfd4e723b5`
- C2 local CT2 fingerprint: `29ec9fad29442a2af027843e7c773a275e97d97213c1c215710747a3a65ac333`

로컬 CT2 fingerprint는 config.json, model.bin, tokenizer.json, vocabulary.json,
preprocessor_config.json 각각의 SHA-256을 파일명 순서와 함께 다시 SHA-256한 값이다.
preflight와 각 metrics.json의 run.model_provenance에 같은 정보를 기록한다.

## 고정 추론 조건

서비스 FasterWhisperTranscriber와 비교 가능하도록 다음 조건을 고정한다.

- device: CUDA
- compute type: float16
- language: ko
- task: transcribe
- temperature: 0.0
- word_timestamps=True
- vad_filter=False
- condition_on_previous_text=False

서비스 기본값의 CPU/int8는 이번 모델 품질 비교에서는 사용하지 않는다. 세 모델의 GPU 조건을 동일하게 맞추고, 추후 선택 후보에 대해 실제 배포 장치 조건을 별도로 검증한다.

## 데이터

- frozen dev/diagnostic set: 30개 M4A
- 원본 ZIP은 Git에 포함하지 않음
- ZIP SHA-256: c53c3161562a9b86ef5b5da27772eca0cc6dea7f1d80082e7e619c46fe5fbf39
- 대본: assets/2026-09-27_real-user-recording-script.md
- 구성
  - 01~10 일반 면접
  - 11~18 기술 질문
  - 19~24 숫자·영문 stress
  - 25~30 자연/긴 답변

## 측정값

각 조합에서 다음을 기록한다.

- 전체 raw CER / WER
- 전체 spoken-form normalized CER / WER
- 19~24 stress 제외 core normalized CER / WER
- 19~24 stress normalized CER / WER
- aggregate RTF
- utterance latency p50 / p95
- RTF p50 / p95
- 모델 load time
- 문장별 prediction / 처리시간 / RTF

모델 load/download 시간은 별도 기록하고 utterance latency에는 포함하지 않는다.

## 실행

STT runtime 확인:

    .venvs/stt-runtime/bin/python backend/scripts/verify_training_env.py --require-cuda

로컬 ZIP에서 frozen devset 준비:

    python3.12 backend/scripts/prepare_stt_real_user_devset.py \
      --audio-zip "<path-to-소리 녹음.zip>"

모델/데이터/CUDA preflight:

    .venvs/stt-runtime/bin/python backend/scripts/run_stt_real_user_matrix.py \
      --preflight-only

B0 1건 실제 CUDA smoke:

    .venvs/stt-runtime/bin/python backend/scripts/run_stt_real_user_matrix.py \
      --models b0 --beam-sizes 1 --max-samples 1

전체 9개 조합 실행:

    .venvs/stt-runtime/bin/python backend/scripts/run_stt_real_user_matrix.py \
      --resume

전체 실행은 --resume을 사용하므로 완료된 동일 조합만 재사용한다. resume은 schema v2,
model provenance, manifest SHA-256과 순서가 반영된 ID/오디오 내용 SHA-256,
model/beam/device/compute 설정, predictions.json 30건 존재 여부와 metrics
필수 구조를 모두 확인한다. 손상 JSON, 누락된 predictions, 다른 model fingerprint/revision,
구버전 provenance 없는 metrics는 완료 결과로 재사용하지 않는다.

## 출력

Git 제외 경로:

- local-results/stt-real-user-devset/
- local-results/stt-real-user-matrix/summary.json
- local-results/stt-real-user-matrix/SUMMARY.md
- 조합별 metrics.json
- 조합별 predictions.json

## 결과

전체 9개 조합은 실패 없이 완료됐다.

| 모델 | Beam | Core 정규화 CER | Core 정규화 WER | 전체 Raw CER | 전체 Raw WER | RTF | p50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| large-v3-turbo | 1 | **3.29%** | **6.63%** | **6.06%** | 10.09% | **0.020** | **0.258s** |
| large-v3-turbo | 3 | **3.29%** | **6.63%** | **6.06%** | **9.80%** | 0.023 | 0.316s |
| large-v3-turbo | 5 | **3.29%** | **6.63%** | **6.06%** | **9.80%** | 0.026 | 0.361s |
| B0 | 1 | 7.22% | 10.20% | 14.89% | 19.15% | 0.049 | 0.660s |
| B0 | 3 | 9.27% | 12.76% | 16.24% | 20.32% | 0.062 | 0.869s |
| B0 | 5 | 8.82% | 11.90% | 16.03% | 19.59% | 0.067 | 0.912s |
| C2 | 1 | 7.32% | 10.20% | 15.61% | 21.49% | 0.048 | 0.659s |
| C2 | 3 | 7.22% | 10.54% | 15.14% | 21.49% | 0.056 | 0.759s |
| C2 | 5 | 7.27% | 10.88% | 15.18% | 21.05% | 0.058 | 0.805s |

숫자·영문 stress 구간의 spoken-form normalized 결과:

| 모델 | Beam | CER | WER |
| --- | ---: | ---: | ---: |
| large-v3-turbo | 1 | **6.00%** | **17.86%** |
| B0 | 1 | 32.88% | 44.05% |
| C2 | 1 | 46.23% | 71.43% |
| C2 | 5 | 37.72% | 46.43% |

large-v3-turbo beam 1의 기술 질문 11~18 구간은 정규화 CER 1.28%, WER 8.38%였다. C2 beam 5는 같은 구간에서 CER 10.27%, WER 11.73%였다.

실제 prediction에서도 large-v3-turbo는 날짜/시간 문장을 완전 일치로 전사했고, Python, CUDA, CI, CD, PR, API, DB 등 주요 기술 표기를 안정적으로 보존했다. 남은 대표 오류는 Whisper → Hisper, CTranslate2 → C Translate Tool, CER/WER 일부 약어 변형 등이다.

large-v3-turbo 최초 model load 162.1초에는 로컬 cache 부재로 인한 최초 모델 다운로드가 포함됐다. 이 값은 utterance latency 및 RTF 계산에서 제외했으므로 서비스 추론 지연으로 해석하지 않는다. 이후 pinned revision smoke에서는 같은 snapshot을 cache에서 1.617초에 로드하고 실제 CUDA 추론까지 성공했다.

## 해석

- 동일 CUDA/float16 조건에서 large-v3-turbo가 B0/C2보다 core 정확도와 처리속도 모두 크게 앞섰다.
- large-v3-turbo는 beam 1/3/5에서 core 정규화 CER/WER가 동일했다.
- beam 증가에 따른 유일한 작은 변화는 전체 raw WER 10.09% → 9.80%였고, 동시에 p50 latency는 0.258초 → 0.316초 → 0.361초로 증가했다.
- 따라서 현재 dev/diagnostic set에서는 large-v3-turbo + beam 1을 다음 실험의 기준선으로 사용한다.
- B0/C2는 Whisper Medium 계열 파인튜닝의 효과를 검증하는 연구 후보로는 의미가 있지만, 현재 서비스 후보 비교에서는 우선순위를 낮춘다.
- 이 데이터는 이미 모델/beam 선택에 사용했으므로 최종 acceptance 성능 근거로 사용하지 않는다.

## 다음 단계 판정

이 행렬은 제품 기본 모델을 바로 결정하기 위한 final test가 아니다.

1. large-v3-turbo + beam 1을 고정 기준선으로 사용한다.
2. 동일한 기술용어 hint content로 none / initial_prompt / hotwords를 비교한다.
3. 전체 CER/WER뿐 아니라 기술용어 hit와 false insertion을 함께 본다.
4. prompt/hotwords 설정 선택이 끝난 뒤 새로운 미공개 acceptance 녹음셋에서 최종 검증한다.
