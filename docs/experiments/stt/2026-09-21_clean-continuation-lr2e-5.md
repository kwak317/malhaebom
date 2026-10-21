# STT clean continuation — LR 2e-5, 0.5 epoch

## 목적

기존 50k/5k retrain에서 CER는 개선됐지만, train/validation의 약 4%가 `#이름#`, `&company-name...&` 같은 익명화 placeholder label을 포함했다. 실제 음성과 label이 불일치할 가능성이 높은 이 샘플을 제외한 뒤, 기존 best adapter를 작은 learning rate로 짧게 추가 학습한다.

## 고정 조건

- base: `openai/whisper-medium`
- init adapter: `artifacts/stt/whisper-medium-busan-qlora-retrain/best_adapter`
- optimizer: fresh AdamW
- resume: 이 clean-continuation output의 최신 checkpoint만 `auto` resume
- clean train: 48,000
- clean validation: 4,802
- LR: 2e-5
- epochs: 0.5
- train batch: 16
- grad accumulation: 2
- effective batch: 32
- eval batch: 8
- warmup ratio: 0.03 -> 23 optimizer steps
- 예상 optimizer steps: 750
- eval/save: 250 step
- seed: 43
- output: `[REDACTED]`

## 데이터 정제

원본 manifest는 변경하지 않는다.

- 원 train 50,000 -> clean train 48,000
- 원 validation 5,000 -> clean validation 4,802
- 제거 조건: text에 `#...#` 또는 `&...&`가 포함된 row

clean manifest:
`data/stt/handoff-reconstructed/dataset-clean-no-placeholders/`

## Test B

기존 Test A를 이미 확인했으므로 새로운 clean Test B를 학습 전에 고정했다.

- 20 source x 25 = 500 utterances
- 원 train/validation source와 overlap 0
- 기존 Test A 20 source도 전부 제외
- placeholder 없는 reference만 사용
- 후보 412 clean source 중 deterministic하게 20 source 선택
- 경로: `data/stt/holdout-test-b-clean/`

Test B는 이 실험의 hyperparameter 조정에 사용하지 않는다. 우선 clean validation으로 checkpoint를 선택한 뒤 최종 비교 단계에서만 연다.

## 실행

실제 2-step smoke:

```bash
.venvs/stt-train/bin/python backend/scripts/train_whisper_qlora.py \
  --config configs/stt/finetune_clean_continuation_smoke.json
```

밤샘 full run:

```bash
python3.12 backend/scripts/overnight_job.py start stt-clean-continuation
```

상태/로그:

```bash
python3.12 backend/scripts/overnight_job.py status stt-clean-continuation
python3.12 backend/scripts/overnight_job.py logs stt-clean-continuation --lines 80
```

## 검증 완료

- clean manifest 생성: PASS
- clean experiment input validator: PASS
- Test B 500개 생성 및 source leakage 0: PASS
- PEFT `PeftModel.from_pretrained(..., is_trainable=True)` API 확인: PASS
- full config preflight-only: PASS
- CUDA: RTX 5070 Ti / BF16: PASS
- smoke/full training 완료
- full run: 750/750 step, epoch 0.5, exit code 0
- best checkpoint: checkpoint-500
  - clean validation CER 7.4092%
  - clean validation WER 19.6174%
- checkpoint-750:
  - clean validation CER 7.4457%
  - clean validation WER 19.7155%
- `best_adapter` weight는 checkpoint-500과 SHA-256 동일

## Test B 최종 평가 준비

clean continuation `best_adapter`를 Whisper Medium에 merge하고 CTranslate2 float16으로 변환했다.

- merged HF: `[REDACTED]`
- CT2: `[REDACTED]`
- CT2 `model.bin`: 1,527,906,453 bytes

Test B 최종 평가에서는 아래 3개 모델을 동일한 500 utterance에 비교했다.

1. historical baseline CT2
2. 1차 50k retrain CT2
3. clean continuation CT2

세 모델의 `config.json`, `tokenizer.json`, `vocabulary.json` SHA-256은 서로 동일함을 preflight에서 확인했다.

공통 decoding 조건:

- beam size 5
- CTranslate2 float16
- language ko
- task transcribe
- temperature 0
- condition_on_previous_text false
- VAD off

최종 실행:

```bash
python3.12 backend/scripts/overnight_job.py start stt-test-b-three-way
```

직접 foreground로 실행하려면:

```bash
python3.12 backend/scripts/run_stt_test_b_three_way.py
```

완료 결과:

- `artifacts/stt/test-b/baseline/metrics.json`
- `artifacts/stt/test-b/retrain/metrics.json`
- `artifacts/stt/test-b/clean-continuation/metrics.json`
- `artifacts/stt/test-b/comparison.json`

## Test B 최종 결과

고정 clean Test B 500 utterance에서 3개 모델을 동일한 decoding 조건으로 비교했다.

| 모델 | CER | WER | char edits | word edits |
| --- | ---: | ---: | ---: | ---: |
| historical baseline | 5.8024% | 13.7894% | 555 | 516 |
| 1차 retrain | 5.6038% | 13.5489% | 536 | 507 |
| clean continuation | **5.3738%** | **13.1213%** | **514** | **491** |

clean continuation은 1차 retrain 대비:

- CER: -0.2300%p, 상대 -4.10%
- WER: -0.4276%p, 상대 -3.16%
- char edits: 536 -> 514
- word edits: 507 -> 491

historical baseline 대비:

- CER: -0.4286%p, 상대 -7.39%
- WER: -0.6681%p, 상대 -4.84%
- char edits: 555 -> 514
- word edits: 516 -> 491

학습 중 model selection에 사용하지 않은 Test B에서도 CER/WER가 모두 개선됐으므로, 이번 clean continuation 실험은 일반화 성능 측면에서 성공으로 기록한다. 다만 이 결과만으로 제품 기본 STT 모델 교체를 자동 결정하지 않으며, 실제 서비스 도메인 발화 비교는 별도 판단 단계로 남긴다.
