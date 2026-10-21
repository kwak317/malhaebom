# STT/TTS/VAD 인수 전 확인 — 2026-09-17

> `STATIC_CONFIRMED` / 인수 완료 아님. 코드 기준 `73525a159e3faa61114d968e6dbdd14d0fb85a82`. 이번에는 파일·호출 경로만 읽었으며 모델·데이터 다운로드, dependency 설치, 환경 재구축, 추론, 학습, benchmark를 하지 않았다. [통합 Worklog](../worklogs/2026-09-17_docs-code-integration.md).

## 환경·재현 정보

저장소 Docker 기준 Python 3.12, frontend Node 22. 실제 음성 환경의 OS/GPU/CUDA/cuDNN·설치 package·checkpoint hash는 미확인이다. [기본 requirements](../../backend/requirements.txt), [STT](../../backend/requirements-stt.txt), [TTS](../../backend/requirements-question-tts.txt), emotion용 별도 requirements가 존재한다. 아래 명령은 코드에 대응하는 후속 재현 진입점이며 실행 결과가 아니다.

## STT

- [설정](../../backend/app/core/stt_settings.py): `large-v3-turbo`, cpu/int8, beam size 1 기본값. `STT_MODEL_NAME`으로 모델명/로컬 CTranslate2 경로를 지정한다. 실제 checkpoint는 전달받지 않았다.
- [추론](../../backend/app/services/stt_transcriber.py): faster-whisper 1.2.1, 한국어, temperature 0, word timestamps, 내부 VAD off, previous-text conditioning off. 세그먼트·단어·추임새·처리시간·RTF를 반환한다.
- 전처리/검증: WAV/WebM/MP3 입력, job 경로의 5~60초·15 MiB 제한, VAD의 PyAV mono 16 kHz 변환. STT 세부 decoding은 faster-whisper에 위임한다.
- CLI: `python backend/scripts/transcribe_audio.py <승인된-음성> --source-id <ID> --output <비공개-결과>` — [script](../../backend/scripts/transcribe_audio.py).
- 학습·데이터 참조: [STT 파일럿 기록](../stt-current-status.md), [6,000개 LoRA 기록](../stt-finetuning-6000.md), [Colab 절차](../stt-colab-workflow.md). `openai/whisper-medium`, LoRA q_proj/v_proj, r16/alpha32, 부산·경상도 방언, 비공개 ZIP·metadata_train.csv·validation/test CSV를 기술한다.
- 이전 문서에는 300 train/50 validation 파일럿 loss 5.1789/3.9790 및 checkpoint-19, 후속 1,000+5,000개 학습·T4 FP16 기록이 있다. 서로 다른 실험 기록이며 이번에 수치·파일·학습 이력을 재검증한 것이 아니다.
- 추적 파일 목록에서 STT fine-tuning notebook/script와 CER/WER 고정 benchmark 실행 코드는 확인되지 않았다. 문서의 Colab·ZIP·adapter 참조만으로 재현 가능하다고 판단하지 않는다.
- CER/WER·추임새 event P/R/F1·RTF·실패율 비교 계획은 있으나 고정 test·checkpoint·원시 결과 인수가 필요하다. 서비스 모델 우수성·baseline 확정은 미완료.

## VAD·전달력

- [vad_detector.py](../../backend/app/services/vad_detector.py): Silero VAD 5.1.2, ONNX, PyAV mono 16 kHz decode, speech timestamps.
- [persistent_analysis_jobs.py](../../backend/app/services/persistent_analysis_jobs.py): VAD → 무발화 실패 처리 → STT → [전달력](../../backend/app/services/delivery_analysis.py) 계산 연결.
- CPM, 1초 이상 침묵, 반복 표현과 피드백 선택 코드·[단위 테스트](../../backend/tests/test_vad_detector.py)가 있다. 실음성 정확도·noise robustness·GPU 지연은 미측정.

## TTS

| 경로 | 확인한 위치·설정 | 인수 상태 |
| --- | --- | --- |
| preset WAV | [selector](../../backend/app/services/tts_asset_selector.py), [repository](../../backend/app/services/preset_question_audio.py), [catalog](../../configs/tts/tts_template_catalog.json) | 질문자 10개 accepted, 코치 90개 draft. metadata 존재와 실제 WAV/Storage 접근 성공은 별개 |
| API 내 질문 합성 | [qwen_question_tts.py](../../backend/app/services/qwen_question_tts.py), [settings](../../backend/app/core/question_tts_settings.py) | `QUESTION_TTS_MODEL_PATH` 로컬 디렉터리, CUDA 필요, FasterQwen3TTS custom voice streaming. 실제 모델 hash/가중치 미확인 |
| 별도 코치 Worker | [tts_worker/app/main.py](../../backend/tts_worker/app/main.py), [coach_tts.py](../../backend/app/services/coach_tts.py) | `TTS_WORKER_MODEL_PATH`, `TTS_WORKER_URL` 필요. custom voice WAV·NDJSON·PCM stream 코드. Compose에 Worker service 없음 |

- [기존 자산 기록](../tts-current-status.md)은 Qwen3-TTS 1.7B Base·candidate_04_questioner/candidate_03_coach·비공개 참조 음성 청취를 기술한다. 현재 runtime의 CustomVoice loader와 과거 사전 생성 실험을 같은 checkpoint라고 간주하지 않는다.
- `qwen-tts==0.1.1`, `faster-qwen3-tts==0.3.2`, `soundfile==0.14.0` 선언. 고정 음성 생성·업로드 script는 있으나 TTS training/fine-tuning 실행 코드는 확인되지 않았다.
- [evaluate_question_tts.py](../../backend/scripts/evaluate_question_tts.py): 13개 질문의 첫 오디오 시간, 생성 시간, RTF, GPU peak allocation, 종료 이유, WAV format, manual review 상태를 `metrics.jsonl`/`summary.json`에 기록하는 코드.
- 후속 진입점: `python backend/scripts/evaluate_question_tts.py --output-dir <새-비공개-결과-디렉터리>` 및 `uvicorn backend.tts_worker.app.main:app --port 8100`. CUDA·승인 모델·별도 의존성 환경이 선행되어야 하며 이번에는 실행하지 않았다.
- 저장소에서 해당 평가의 실제 metrics artifact·WAV·checkpoint는 확인되지 않았다. 과거 개인 Supabase 검증 진술은 팀 환경 인수 완료 증거가 아니다.

## 별도 emotion 실험 코드

[finetune_pilot.py](../../backend/emotion/finetune_pilot.py), [model_loader.py](../../backend/emotion/model_loader.py), [emotion_data](../../backend/emotion_data/)는 wav2vec2 한국어 감정 분류 실험이다. STT/TTS 학습 코드로 분류하지 않는다. 5,000행 manifest.csv·audio, train/validation/test, seed 42, accuracy/macro-F1 코드가 있으며 현재 API 호출 연결은 확인되지 않는다. 기존 실험 코드 보존은 이번 학습 실행 또는 제품 범위 추가 승인이 아니다.

## 다음 인수 단계

1. 담당자에게 모델 hash·데이터 출처/동의·split·고정 benchmark·전처리·실험 환경·원시 결과와 누락된 학습 notebook 전달 위치를 확인한다.
2. 별도 승인 작업에서 기존 환경 재구축 → 기존 checkpoint benchmark 재현 → baseline 확정한다.
3. 신규 STT/TTS 학습 제외를 유지한다. 향후 학습은 범위 승인과 신규 데이터/누수 방지 규칙을 먼저 충족해야 한다.
