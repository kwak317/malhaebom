# Whisper Medium 50k QLoRA retrain

## 상태

- setup/smoke 검증 완료
- full training 미실행
- 500개 full holdout baseline 미완료

## 목적

기존 부산/경상도 LoRA adapter weight가 전달본에서 누락되어 continuation이 불가능하므로, 기존 CT2 모델은 baseline으로 보존하고 `openai/whisper-medium`에서 새 QLoRA candidate를 학습한다.

## 코드

- 학습: `backend/scripts/train_whisper_qlora.py`
- dataset preflight: `backend/scripts/validate_stt_finetuning_dataset.py`
- holdout 생성: `backend/scripts/prepare_stt_holdout_test.py`
- CT2 평가: `[REDACTED].py`
- full config: `[REDACTED].json`
- smoke config: `[REDACTED].json`

## 환경

현재 검증된 STT train venv:

- Python 3.12.3
- torch 2.8.0+cu128
- torchaudio 2.8.0+cu128
- transformers 5.15.1
- peft 0.20.0
- bitsandbytes 0.48.0
- CUDA: RTX 5070 Ti 16GB
- BF16 지원

## 모델

- base: `openai/whisper-medium`
- quantization: NF4 4-bit, double quant
- LoRA target: `q_proj`, `v_proj`
- rank 16 / alpha 32 / dropout 0.05
- 기존 CT2 baseline: `[REDACTED]`

## 데이터

- train: 50,000
- validation: 5,000
- 현재 validator 기준 train/validation source overlap: 0
- dataset root: `data/stt/handoff-reconstructed`
- 기존 quick-eval의 `DKSR20000058`은 새 train에 181 segment가 포함되어 있어 final test로 사용 금지
- final test는 AI Hub 공식 Validation archive에서 train/validation에 없는 source를 학습 전에 고정한다.

## Full training config

- batch size: 16
- eval batch size: 8
- gradient accumulation: 2
- effective batch: 32
- epochs: 2
- learning rate: 1e-4
- warmup ratio: 0.05
- save/eval interval: 500 optimizer steps
- selection metric: validation CER
- seed: 42

RTX 5070 Ti smoke에서 train batch 16 / eval batch 8이 정상 동작했고 peak CUDA reserved는 약 5.19 GiB였다. 따라서 full run은 전달 기록에도 남아 있던 batch 16 / gradient accumulation 2 조합으로 effective batch 32를 유지한다.

## 실행 순서

```bash
make stt-train-env-verify
.venvs/stt-train/bin/python backend/scripts/validate_stt_finetuning_dataset.py

.venvs/stt-train/bin/python backend/scripts/prepare_stt_holdout_test.py --plan-only
.venvs/stt-train/bin/python backend/scripts/prepare_stt_holdout_test.py

make stt-baseline-holdout

make stt-finetune-smoke

make stt-finetune-full
```

## 평가 규칙

- validation은 checkpoint 선택에만 사용한다.
- holdout test는 final comparison에만 사용하며 hyperparameter 조정에 사용하지 않는다.
- baseline/candidate 비교 시 동일한 holdout, normalization, beam size, temperature와 VAD 설정을 유지한다.
- candidate는 평가 전에 CTranslate2 변환 절차를 별도로 기록한다.

## 결과

- dataset preflight: PASS, train 50,000 / validation 5,000, cross-split audio/segment/source overlap 0
- holdout: AI Hub Validation의 미사용 source 20개 × 25발화 = 500개 생성 완료
- holdout candidate pool: current train/validation source union 824개를 제외하고 432개 source 사용 가능
- smoke training: 2 optimizer step PASS
- smoke peak CUDA: allocated 약 4.71 GiB / reserved 약 5.19 GiB
- smoke adapter: `artifacts/stt/whisper-medium-busan-qlora-smoke/best_adapter/adapter_model.safetensors` 생성 확인
- smoke checkpoint: `adapter_model.safetensors`, `optimizer.pt`, scheduler/RNG/trainer state 저장 확인; 새 run의 `resume=auto` 경로 검증
- baseline evaluator smoke: holdout 앞 10개에서 기존 CT2 CER 12.5%, WER 21.54%. 이 값은 evaluator 검증용이며 최종 비교값으로 사용하지 않는다.
- full training: PASS — 3,126 optimizer step / 2 epoch 완료
- validation best: checkpoint-3000, CER 8.5512%, WER 20.2180%
- final checkpoint-3126: CER 8.7073%, WER 20.3493%
- `best_adapter`의 adapter weight SHA-256은 checkpoint-3000과 동일하고 checkpoint-3126과 다름을 확인했다.
- 새 best adapter를 `openai/whisper-medium`에 merge한 뒤 CTranslate2 float16으로 변환했다.
- 기존/신규 CT2의 `config.json`, `tokenizer.json`, `vocabulary.json`은 해시까지 동일했다. preprocessor config는 신규 쪽에 `processor_class` 필드만 추가됐고 feature 설정은 동일하다.

### 고정 holdout 500개 최종 비교

동일한 500 utterance, `beam_size=5`, `temperature=0.0`, `condition_on_previous_text=False`, VAD off, float16 CTranslate2 조건으로 비교했다.

| 지표 | 기존 CT2 | retrain CT2 | 변화 |
| --- | ---: | ---: | ---: |
| CER | 9.1435% | 8.2708% | -0.8727%p / 상대 -9.545% |
| WER | 16.1931% | 16.2937% | +0.1006%p / 상대 +0.621% |

- CER edit count: 901 -> 815, 총 86 edit 감소
- WER edit count: 644 -> 648, 총 4 edit 증가
- 발화별 CER: 개선 32 / 악화 38 / 동일 430
- 발화별 WER: 개선 38 / 악화 38 / 동일 424
- WER 악화 사례 일부는 `따로국밥 -> 따로 국밥`, `즐겨 보고 -> 즐겨보고`, `물류 센터 -> 물류센터`처럼 문자 내용은 동일하지만 한국어 띄어쓰기 경계가 달라 발생했다.
- 기존 모델이 `&company-name1&` 같은 placeholder를 출력한 일부 발화에서 retrain 모델이 실제 발음에 가까운 문자열을 복원하며 CER가 크게 감소한 사례가 있었다.

현재 holdout에서는 retrain 모델이 문자 단위 내용 보존(CER)은 개선됐고, whitespace-sensitive WER는 사실상 비슷하지만 아주 소폭 높다. 제품 기본 모델 교체 여부는 실제 면접 발화/domain set에서도 추가 비교 후 결정한다.
