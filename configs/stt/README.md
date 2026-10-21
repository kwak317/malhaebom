# STT Worker 설정

> 2026-09-17 정적 audit 정정: 현재 API는 Bearer 인증과 question_type·attempt_no 등 Form 필드를 요구한다. 아래 source_id/audio만 쓰는 무인증 curl 예시는 현 API 계약에 맞지 않는 이전 기록이다. 현재 근거와 인수 제한은 [음성 인수 기록](../../docs/experiments/2026-09-17_voice-asset-intake.md)을 따른다.


이 디렉터리는 팀 GPU Worker의 STT 런타임 설정 계약만 관리합니다. 모델 가중치, checkpoint, AI-Hub 데이터와 실제 전사 결과는 저장소에 넣지 않습니다.

## 기본 모델

- 서비스 기준 후보: `faster-whisper`의 `large-v3-turbo`
- 학습 실험: `Whisper medium + LoRA` (성능 비교 전이며 서비스 모델로 확정하지 않음)
- 기본 디코딩: 한국어, `beam_size=1`, 단어 타임스탬프 사용, 내부 VAD 비활성화
- VAD는 별도 Silero VAD 단계에서 같은 입력을 기준으로 결합합니다.

## 환경변수

```text
STT_MODEL_NAME=large-v3-turbo
STT_DEVICE=cpu
STT_COMPUTE_TYPE=int8
STT_BEAM_SIZE=1
```

GPU Worker에서는 일반적으로 다음처럼 바꿉니다.

```text
STT_DEVICE=cuda
STT_COMPUTE_TYPE=float16
```

`STT_MODEL_NAME`에는 Hugging Face 모델명 또는 팀이 별도로 보관하는 CTranslate2 모델의 비공개 로컬 경로를 사용할 수 있습니다. 로컬 경로와 가중치는 커밋하지 않습니다.

## 실행

```bash
python -m pip install -r backend/requirements-stt.txt
python backend/scripts/transcribe_audio.py answer.wav \
  --source-id attempt-uuid \
  --output local-results/attempt-uuid.json
```

`local-results/`처럼 전사문이 포함되는 출력 디렉터리는 저장소 밖 또는 `.gitignore` 대상 위치를 사용합니다.

## 로컬 분석 Job API

개발 환경에서는 브라우저·Supabase 연결 없이 API와 Worker의 연결만 확인할 수 있습니다.
이 API는 프로세스 메모리에 Job 상태를 보관하므로 서버를 재시작하면 기록이 사라지며, 인증·영구 저장·배포 용도가 아닙니다.

```bash
python -m pip install -r backend/requirements-stt.txt
uvicorn app.main:app --app-dir backend --reload
```

다른 터미널에서 5~60초, 15MB 이하의 로컬 음성 파일을 요청합니다.

```bash
curl -X POST http://127.0.0.1:8000/analysis-jobs \
  -F "source_id=local-attempt-001" \
  -F "audio=@answer.wav"
```

응답의 `job_id`로 상태와 완료된 전사 결과, VAD 기반 전달력 분석 결과를 조회합니다.

```bash
curl http://127.0.0.1:8000/analysis-jobs/{job_id}
```

임시 음성은 `LOCAL_ANALYSIS_DIR`(기본 `local-analysis/`)에만 보관하고 Job 완료·실패 시 삭제합니다. API는 WAV·WebM·MP3를 받고, STT 모델은 기존 `large-v3-turbo` 기준선을 사용합니다. 완료 응답은 기존 `result`와 새 `delivery`를 함께 반환하며, VAD 또는 전달력 분석에 실패하면 전사문을 반환하지 않고 `ANALYSIS_FAILED` 상태로 종료합니다.

`silero-vad`는 PyTorch와 ONNX Runtime을 사용합니다. 현재 Worker는 Windows의 한글 경로에서도 동작하도록 Silero의 ONNX runtime 모드를 사용하고, WAV·WebM·MP3 디코딩은 PyAV로 처리합니다. CUDA 환경에서는 장치·CUDA 버전에 맞는 PyTorch wheel을 먼저 설치한 뒤 `backend/requirements-stt.txt`를 설치하세요. 모델 가중치·사용자 음성·전사 결과는 Git에 추가하지 않습니다.

## 테스트

외부 모델 다운로드 없이 실행됩니다.

```bash
python -m unittest discover -s backend/tests -v
```

## 아직 하지 않은 것

- 고정 평가셋에서 large-v3-turbo와 medium+LoRA의 CER·WER·RTF 비교
- 추임새 사건 단위 Precision·Recall·F1 측정
- GPU 메모리와 실패율 측정

위 평가 전에는 파인튜닝 모델이 더 좋다거나 서비스 모델이 확정됐다고 기록하지 않습니다.
