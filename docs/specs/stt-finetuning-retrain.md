# STT 재학습 실험 Spec

## Why

기존 부산/경상도 Whisper LoRA 계보의 CTranslate2 추론 모델은 남아 있지만, 추가 학습에 필요한 `adapter_model.safetensors`가 원 STT Drive와 최신 handoff 모두에서 누락됐다. 따라서 기존 adapter continuation은 재현할 수 없다.

현재 로컬에는 AI Hub 119 경상도 데이터에서 재구성한 train 50,000 / validation 5,000 segment와 `openai/whisper-medium` 학습 환경이 있다. 기존 CT2 모델은 baseline으로 보존하고, 동일 base와 확인된 LoRA 설정을 사용한 새 QLoRA run을 별도 실험으로 수행한다.

## Goal

- 기존 CT2 모델을 변경하지 않고 baseline artifact로 보존한다.
- `openai/whisper-medium` + 4-bit NF4 QLoRA로 새 학습 run을 재현 가능하게 준비한다.
- train 50,000 / validation 5,000 내부의 audio/segment/source overlap이 0인 상태를 유지한다.
- 최종 test는 train/validation에 등장하지 않은 source conversation으로 학습 전에 고정한다.
- RTX 5070 Ti 16GB에서 최소 2-step smoke train이 성공해야 full run을 시작할 수 있다.
- full run 결과는 동일한 test set과 decoding 조건으로 기존 CT2 baseline과 비교한다.

### Out of Scope

- 누락된 과거 LoRA adapter를 복원했다고 주장하지 않는다.
- 기존 CT2 `model.bin`을 PEFT weight로 역변환하지 않는다.
- final test를 보고 hyperparameter를 조정하지 않는다.
- 모델 artifact, AI Hub 원본, 음성 파일을 Git에 커밋하지 않는다.

## What

### Happy Path

1. training environment와 dataset preflight를 통과한다.
2. AI Hub Validation 원본에서 train/validation source와 겹치지 않는 source를 deterministic하게 고른다.
3. holdout test set을 고정하고 manifest를 생성한다.
4. 기존 CT2 모델의 CER/WER baseline을 기록한다.
5. smoke config로 2-step QLoRA 학습을 실행해 forward/backward/save 경로를 검증한다.
6. full config로 새 run을 실행한다.
7. validation CER로 candidate checkpoint를 선택한다.
8. 고정 test set에서 candidate를 평가하고 baseline과 비교한다.

### Edge Cases

- holdout 후보 source가 부족하면 test set 생성을 중단한다.
- train/validation과 holdout source가 겹치면 test set 생성을 실패 처리한다.
- CUDA 또는 BF16/FP16 학습 환경이 준비되지 않으면 학습을 시작하지 않는다.
- output directory에 기존 checkpoint가 있으면 `resume=auto`일 때 같은 새 run만 이어서 재개한다.
- 과거 누락 checkpoint를 현재 새 run의 resume 지점으로 사용하지 않는다.

## How

- base model: `openai/whisper-medium`
- quantization: 4-bit NF4, double quantization
- LoRA: `q_proj`, `v_proj`, rank 16, alpha 32, dropout 0.05
- full config: train batch 16, eval batch 8, grad accumulation 2, LR 1e-4, warmup ratio 0.05, 2 epochs
- model selection: validation CER
- final metrics: normalized CER/WER
- dataset root: `data/stt/handoff-reconstructed`
- training artifact root: `artifacts/stt/`
- large files remain ignored by Git.

## AC

- **Given** current train/validation manifests, **when** dataset validator runs, **then** duplicate audio/segment/source and cross-split audio/segment/source are all 0.
- **Given** original AI Hub validation archives, **when** holdout planner runs, **then** every selected source is absent from both training manifests.
- **Given** the full training config, **when** training is run with `--preflight-only`, **then** paths, sample counts, CUDA environment, effective batch and expected optimizer steps are printed without model training.
- **Given** the smoke config, **when** training runs, **then** at least 2 optimizer steps complete and an adapter/checkpoint artifact is created under ignored output paths.
- **Given** the fixed holdout test manifest, **when** the baseline and candidate are evaluated, **then** both use the same normalization, decoding parameters and CER/WER implementation.
