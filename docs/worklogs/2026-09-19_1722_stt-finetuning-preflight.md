# Worklog — STT fine-tuning preflight

- 일시: 2026-09-19 17:22
- 작업자/에이전트: 김재훈 / ChatGPT
- 관련 이슈/PR: 미생성
- 관련 요구사항/결정: 실제 STT fine-tuning을 실행하기 전에 로컬 학습환경과 재구성된 50,000/5,000 dataset의 학습 준비 상태를 확인한다. 이번 작업에서는 모델 학습을 실행하지 않는다.

## 1. 목적

STT fine-tuning 착수 전에 다음을 확인한다.

- 현재 `.venvs/stt-train` 환경이 RTX 5070 Ti에서 CUDA 학습 가능한 상태인지 검증한다.
- AI Hub 119에서 재구성한 train 50,000 / validation 5,000 manifest와 WAV에 누락·중복·cross-split 누수가 없는지 자동 검사한다.
- 실제 학습 전에 해결해야 할 provenance·scope·재현성 blocker를 분리한다.

## 2. 작업 전 상태

- 최신 STT handoff 기준 train 50,000 / validation 5,000 manifest와 segment WAV 재구성이 완료돼 있었다.
- `backend/requirements-stt-training.txt`와 `.venvs/stt-train`은 Whisper QLoRA 재현용으로 준비돼 있었다.
- 과거 6,000개 fine-tuning 기록은 `openai/whisper-medium + LoRA`, T4 FP16, `q_proj/v_proj`, rank 16 / alpha 32 / lr 1e-4로 남아 있다.
- 최신 전달 학습 코드는 4-bit NF4 QLoRA를 사용한 것으로 기록돼 있어 과거 6,000개 실험과 동일 계보인지 단정할 수 없다.
- 과거 1·2차 6,000개 전체 `segment_id` 목록은 복구되지 않았다.
- 이 preflight 시점의 저장소 정책 문서에는 새로운 STT/TTS 학습이 out-of-scope로 남아 있었다. 이후 2026-09-19 사용자 승인으로 STT retrain만 별도 실험 예외가 추가됐다.

## 3. 수행 내용

1. `make stt-train-env-verify`를 실행해 CUDA 학습환경을 검증했다.
2. `backend/scripts/validate_stt_finetuning_dataset.py`를 추가했다.
3. validator가 다음을 검사하도록 했다.
   - manifest JSONL 형식과 `audio` / `text` 필드
   - split 내부 audio path / segment id 중복
   - manifest가 가리키는 WAV 존재 여부
   - train/validation 간 audio path 중복
   - train/validation 간 segment id 중복
   - train/validation 간 source conversation 중복
   - normalized text 중복은 정보성 지표로만 집계
4. 현재 로컬 `data/stt/handoff-reconstructed`에 validator를 실행했다.

## 주요 판단과 이유

- 동일 문장은 서로 다른 발화에서 반복될 수 있으므로 normalized text 중복만으로 데이터 누수로 판정하지 않는다.
- 동일 segment, 동일 audio path 또는 동일 source conversation이 train/validation 양쪽에 존재하면 평가 누수 가능성이 있으므로 blocker로 처리한다.
- 이번 작업의 목표는 base model 신규 학습이 아니라 **기존 fine-tuned STT model을 시작점으로 한 continuation fine-tuning**이다.
- 기존 Drive STT 학습 폴더에는 `train_whisper_lora.py`가 있었고, 해당 스크립트는 latest checkpoint 자동 재개 또는 명시적 checkpoint 경로 재개를 지원한 것으로 확인됐다.
- continuation에는 inference용 CTranslate2 `model.bin`만으로 부족하며, 시작 adapter/checkpoint의 PEFT 가중치와 재개 수준에 따라 trainer/optimizer/scheduler/RNG state를 확보해야 한다.
- 이번 작업은 preflight이며 실제 model fine-tuning이나 checkpoint 생성은 수행하지 않았다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/scripts/validate_stt_finetuning_dataset.py` | STT train/validation manifest·WAV preflight 검사 |
| `[REDACTED].md` | 이번 준비 작업 기록 |
| `docs/worklogs/README.md` | Worklog 목록 추가 |

## 5. 검증

STT train 환경:

```text
make stt-train-env-verify
ok: true
Python 3.12.3
torch 2.8.0+cu128
transformers 5.15.1
peft 0.20.0
bitsandbytes 0.48.0
CUDA available: true
GPU: NVIDIA GeForce RTX 5070 Ti
BF16 supported: true
pip check: No broken requirements found.
```

Dataset preflight:

```text
.venvs/stt-train/bin/python backend/scripts/validate_stt_finetuning_dataset.py
train rows=50,000
unique audio=50,000
unique segments=50,000
unique source conversations=413
duplicate audio=0
duplicate segments=0
missing audio=0

validation rows=5,000
unique audio=5,000
unique segments=5,000
unique source conversations=411
duplicate audio=0
duplicate segments=0
missing audio=0

cross split audio paths=0
cross split segment ids=0
cross split source conversations=0
normalized duplicate texts=56 (informational)

STT fine-tuning dataset preflight PASSED
```

## 6. 발견한 문제 / 남은 리스크

- 기존 continuation 시작점으로 사용한 정확한 adapter/checkpoint를 로컬 handoff만으로 아직 확정하지 못했다.
- 과거 Drive 조사에서는 `[REDACTED]`의 best checkpoint가 validation CER 기준 checkpoint-2500으로 기록됐지만, 당시 전달 폴더에서는 `adapter_model.safetensors`와 optimizer state가 확인되지 않았다.
- 최신 최종 CTranslate2 모델이 정확히 어떤 PEFT checkpoint/data/config에서 만들어졌는지 training lineage를 추가 확인해야 한다.
- 이 preflight 당시 프로젝트 scope는 새로운 STT/TTS 학습을 제외하고 있었다. 이후 historical adapter weight 유실이 확정된 뒤 STT retrain 실험 예외를 별도 결정·Spec으로 추가했다.
- 저장소 추적 파일에는 `STT/scripts/train_whisper_lora.py`가 없지만, 원 STT Drive 학습 폴더에서 해당 스크립트가 존재했던 기록은 확인됐다. continuation 실행 전 로컬 재현 위치로 다시 확보해야 한다.

### 2026-09-19 Drive 재확인 결과

- 공개 Drive HTML을 직접 따라가 원 STT 학습 폴더와 최신 handoff를 재확인했다. 상위 폴더는 `gdown 6.4.0` 재귀 탐색에서 timeout이 발생했지만, 공개 HTML의 `data-id`를 따라가는 방식으로 하위 폴더와 개별 file ID는 정상 확인됐다.
- 원 STT 학습 폴더의 `whisper-medium-busan-lora` 아래 `checkpoint-500/1000/1500/2000`, `best_adapter`, 그리고 `[REDACTED]` 아래 `checkpoint-2500/3126`, `best_adapter`를 모두 확인했지만 `adapter_model.safetensors`와 `optimizer.pt`는 어느 폴더에도 없었다.
- 최신 handoff의 `[REDACTED]`에도 adapter config, scheduler, RNG, trainer state, training args만 있고 PEFT weight와 optimizer state는 없다. merged 폴더에도 config/tokenizer 계열만 있고 HF model weight가 없다.
- 최신 handoff의 CTranslate2 모델에는 `model.bin`이 있으나 inference artifact이므로 현재 PEFT continuation 시작점으로 직접 사용할 수 없다.
- handoff의 `COLAB_STT_TRAINING.md`는 정상 checkpoint 구성에 `adapter_model.safetensors`와 `optimizer.pt`가 포함돼야 한다고 명시한다. 따라서 현재 공유본은 원 학습 산출물에서 두 핵심 파일이 누락된 전달본으로 판단한다.
- handoff의 `train_whisper_lora.py`는 base `openai/whisper-medium`에 새 QLoRA adapter를 만든 뒤 `trainer.train(resume_from_checkpoint=...)`로 checkpoint 전체 재개를 시도한다. 현재처럼 adapter weight가 없는 checkpoint로는 정상 resume할 수 없다.
- validation CER 기준 현재 확인된 best checkpoint는 `checkpoint-2500`이며 CER는 약 `0.086534`다.

## 미확인 사항

- continuation 시작점 adapter/checkpoint의 정확한 위치와 가중치 존재 여부.
- 원 Colab 런타임, Drive 휴지통/이전 위치, 로컬 백업 중 현재 공유되지 않은 곳에 `adapter_model.safetensors`가 남아 있는지 여부.
- `checkpoint-2500`의 adapter weight만 찾으면 fresh optimizer로 weights-only continuation을 검토할 수 있고, 같은 checkpoint의 `optimizer.pt`까지 확보하면 Trainer state 전체 resume을 검증할 수 있다.
- 전달된 최종 CTranslate2 모델과 PEFT checkpoint, 50,000/5,000 dataset의 정확한 training lineage.
- 실제 training script의 실행 당시 hyperparameter와 checkpoint resume 수준(PEFT-only continuation인지 Trainer state 전체 resume인지).
- baseline / final test용 고정 benchmark의 최종 구성.

## 7. 다음 작업

- 실제 학습 범위를 확정하고 `docs/CONSTRAINTS.md`, `AGENTS.md` 등 현재 scope 문서와 모순을 해소한다.
- 원 Colab 런타임, Drive 휴지통/이전 위치, 로컬 백업에서 `adapter_model.safetensors`를 우선 검색한다. 1순위는 CER best인 `checkpoint-2500`, 2순위는 같은 계보의 `best_adapter`다.
- exact Trainer resume까지 필요하면 같은 checkpoint의 `optimizer.pt`도 함께 확보한다. weight만 찾으면 optimizer를 새로 시작하는 adapter continuation으로 별도 기록한다.
- Drive의 STT 학습 원본과 최신 handoff에서 `train_whisper_lora.py`, 시작 adapter/checkpoint 가중치, trainer state를 확보해 continuation 시작점을 확정한다.
- 기존 fine-tuned model을 고정 benchmark에서 재평가해 continuation 전 baseline을 확정한다.
- 시작 checkpoint와 추가 학습 dataset policy가 확정된 뒤 별도 experiment 기록을 만들고 continuation fine-tuning을 실행한다.
