# Worklog — STT clean continuation overnight prep

- 일시: 2026-09-21
- 목적: 기존 best STT adapter에서 placeholder label noise를 제거한 clean continuation 실험을 밤새 실행 가능하게 준비

## 판단 근거

- 원 train/validation의 약 4%가 익명화 placeholder label을 포함한다.
- 기존 Test A 500개에서 placeholder 포함 27개를 제외한 473 clean 발화 비교:
  - 기존 CER 7.6222%
  - retrain CER 6.7332%
  - 기존/retrain WER 모두 15.2279%
- 따라서 추가 epoch보다 clean data + low LR continuation을 우선한다.

## 준비 결과

- clean manifests
  - train 48,000 (2,000 제거)
  - validation 4,802 (198 제거)
- clean Test B
  - 20 source / 500 utterances
  - train/validation/Test A source와 overlap 0
  - placeholder reference 0
- clean continuation config
  - init adapter: 이전 retrain best_adapter
  - LR 2e-5
  - 0.5 epoch
  - effective batch 32
  - expected optimizer steps 750
  - eval/save 250
- overnight registry에 `stt-clean-continuation` 추가

## 검증

- input validator: PASS
- full preflight-only: PASS
- PEFT trainable adapter load API signature: PASS
- actual 2-step smoke: c2c command approval gate 때문에 자동 실행하지 않고 로컬 명령으로 남김

## 실행 명령

`.venvs/stt-train/bin/python backend/scripts/train_whisper_qlora.py --config configs/stt/finetune_clean_continuation_smoke.json`

smoke 통과 후:

`python3.12 backend/scripts/overnight_job.py start stt-clean-continuation`

## 완료 결과

- full clean continuation: 750/750 step, epoch 0.5, exit code 0
- best checkpoint: checkpoint-500
  - clean validation CER 7.4092%
  - clean validation WER 19.6174%
- final checkpoint-750:
  - CER 7.4457%
  - WER 19.7155%
- best_adapter는 checkpoint-500 weight와 SHA-256 동일
- clean best adapter를 CT2 float16으로 변환 완료

고정 Test B 500개 3-way 평가:

- baseline: CER 5.8024%, WER 13.7894%
- 1차 retrain: CER 5.6038%, WER 13.5489%
- clean continuation: CER 5.3738%, WER 13.1213%

clean continuation은 1차 retrain 대비 CER 상대 4.10%, WER 상대 3.16% 개선했고, historical baseline 대비 CER 상대 7.39%, WER 상대 4.84% 개선했다.
