# Worklog — STT retrain setup

- 일시: 2026-09-19 22:54
- 작업자/에이전트: 김재훈 / ChatGPT
- 관련 요구사항/결정: 누락된 historical LoRA weight를 더 이상 continuation blocker로 기다리지 않고, 기존 CT2를 baseline으로 보존한 새 Whisper Medium QLoRA 실험을 준비한다.

## 1. 목적

- 승인된 STT 실험 예외를 문서화한다.
- 50k/5k dataset을 사용하는 새 QLoRA training entrypoint를 만든다.
- 기존 quick-eval 누수를 확인하고 source-disjoint holdout 생성 절차를 만든다.
- baseline 평가와 smoke/full run의 재현 명령을 고정한다.

## 2. 작업 전 상태

- historical `adapter_model.safetensors`는 원 Drive와 handoff에서 찾지 못했다.
- 기존 CT2 inference model은 로컬 `models/stt/`에 존재한다.
- `openai/whisper-medium`은 로컬 Hugging Face cache에 존재한다.
- train 50,000 / validation 5,000 데이터와 CUDA STT train environment는 준비돼 있다.

## 3. 수행 내용

- STT retrain Spec과 실험 기록을 추가했다.
- 5070 Ti용 full/smoke JSON config를 추가했다.
- lazy audio loading QLoRA training script를 추가했다.
- AI Hub Validation archive에서 source-disjoint holdout을 만드는 script를 추가했다.
- faster-whisper/CT2 CER·WER evaluator를 추가했다.
- 기존 handoff quick-eval source `DKSR20000058`을 현재 manifest와 대조했다.

## 4. 주요 판단

- quick-eval source `DKSR20000058`은 현재 train에 181 segment가 있어 새 retrain의 final test로 사용할 수 없다.
- test set은 학습 전에 고정하며 train/validation source와 겹치지 않는 AI Hub Validation source만 사용한다.
- 55k sample 전체의 Whisper feature를 사전 `.map()` 캐시하지 않고 Dataset `__getitem__`에서 lazy extraction한다. 고정 30초 Whisper feature를 전부 캐시하면 디스크 사용량이 과도해질 수 있기 때문이다.
- full run은 historical recipe와 비교 가능한 effective batch 32를 유지한다.

## 5. 변경 파일

- `docs/specs/stt-finetuning-retrain.md`
- `[REDACTED].json`
- `[REDACTED].json`
- `backend/scripts/train_whisper_qlora.py`
- `backend/scripts/prepare_stt_holdout_test.py`
- `[REDACTED].py`
- `[REDACTED].md`
- scope/decision/worklog index 문서

## 6. 검증

- STT train env: PASS — RTX 5070 Ti, CUDA, BF16, dependency/pip check 정상
- 50k/5k dataset validator: PASS — split 내부 중복·누락 0, cross-split audio/segment/source overlap 0
- training preflight: PASS — train 50,000 / validation 5,000, train batch 16, eval batch 8, grad accumulation 2, effective batch 32, 2 epoch, 예상 optimizer step 3,126, warmup 157
- holdout source plan: PASS — current train/validation source union 824개와 겹치지 않는 AI Hub Validation source 432개 확인
- holdout 실제 생성: PASS — deterministic 20 source × 25발화 = 500 utterance
- 첫 smoke 시도: `transformers 5.15.1`에서 `warmup_ratio` 인자 미지원 확인 → 계산된 `warmup_steps`로 수정
- 두 번째 smoke 시도: tokenizer의 `decoder_start_token_id` API 변경 확인 → model config 값을 collator에 전달하도록 수정
- 최종 smoke: PASS — 2 optimizer step, train/eval/save 완료
- batch 16 smoke: PASS — peak CUDA allocated 약 4.71 GiB / reserved 약 5.19 GiB
- smoke checkpoint: `adapter_model.safetensors`, `optimizer.pt`, scheduler, RNG, trainer state 생성 확인
- CT2 evaluator smoke: PASS — holdout 첫 10개에서 CER 12.5%, WER 21.54% (evaluator 동작 확인용)
- 500개 CT2 baseline: c2c 실행 시간 제한으로 미완료; 로컬 `make stt-baseline-holdout` 필요

## 7. 발견한 문제 / 미확인

- historical adapter weight가 없어 새 run은 continuation이 아니라 retrain이다.
- candidate의 CTranslate2 변환 script/절차는 아직 이번 setup 범위에 포함하지 않았다.
- full training과 500개 full holdout benchmark는 장시간 작업이라 로컬에서 별도 실행한다.

## 8. 다음 작업

- full run 완료: 3,126 step / 2 epoch.
- best checkpoint는 validation CER 기준 checkpoint-3000으로 선택됐고 `best_adapter`에 정상 저장됐다.
- best adapter를 HF merged model과 CTranslate2 float16 candidate로 변환했다.
- source-disjoint holdout 500개에서 기존 CT2와 동일 조건 비교를 완료했다.
- 기존 CT2: CER 9.1435%, WER 16.1931%.
- retrain CT2: CER 8.2708%, WER 16.2937%.
- CER는 상대 약 9.55% 개선, WER는 상대 약 0.62% 악화했다. WER 차이는 총 4 word edit이며 일부는 한국어 띄어쓰기 차이다.
- 다음 판단은 실제 면접 발화/domain test에서 두 모델을 비교한 뒤 제품 기본 모델 교체 여부를 결정하는 것이다.
