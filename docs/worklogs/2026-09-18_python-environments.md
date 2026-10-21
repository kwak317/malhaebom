# Worklog — STT/TTS Python 환경 재구성

- 일시: 2026-09-18
- 작업자/에이전트: 김재훈 / ChatGPT
- 관련 이슈/PR: PR #11
- 관련 요구사항/결정: 최신 STT/TTS handoff와 원 전달 폴더를 함께 사용해 재현 가능한 로컬 Python 환경을 정의한다.

## 1. 목적

말해봄 Mk.2의 STT/TTS 관련 Python 환경을 역할별로 분리하고, 실제 전달물에서 확인 가능한 버전과 로컬 호환성 핀을 구분해 재현 가능한 설치·검증 경로를 만든다.

완료 조건은 다음과 같다.

- STT runtime과 STT train 환경을 분리한다.
- TTS runtime과 TTS train 환경을 분리한다.
- 전달 자료에서 확인된 버전을 우선 반영한다.
- 원본 근거가 없는 버전은 로컬 compatibility pin임을 문서화한다.
- RTX 5070 Ti에서 실제 CUDA/import 검증을 수행한다.
- TTS train에서 FlashAttention GPU 커널을 실제 실행해 확인한다.

## 2. 작업 전 상태

- 기존 로컬에는 `.venv`, `.venvs/stt-train`, `.venvs/tts-train`이 있었다.
- 이전 환경설정 커밋은 현재 브랜치 HEAD에 포함되지 않은 상태였고, 환경 파일 일부가 브랜치에 실제로 존재하지 않았다.
- 최신 STT handoff에는 최종 CT2 모델과 50,000/5,000 train/validation manifest가 있었지만 원본 `requirements-train.txt`는 포함되지 않았다.
- STT 전달 checkpoint metadata에서 `peft_version=0.20.0`, merged model metadata에서 `transformers_version=5.15.1`을 확인했다.
- 전달된 STT 학습 코드는 NF4 4-bit QLoRA를 사용하므로 `bitsandbytes`가 필요했다.
- TTS 원 전달 번들에는 questioner runtime 기준 `qwen-tts==0.1.1`, `faster-qwen3-tts==0.3.2`, `fastapi==0.115.12`, `uvicorn==0.34.2`, `numpy==2.2.6`이 명시돼 있었다.
- TTS train 환경은 이미 존재했지만 runtime 주변 라이브러리 버전이 전달본과 달랐다.
- AI Hub 다운로드/복구 스크립트 작업이 같은 브랜치 working tree에 섞여 있었다.

## 3. 수행 내용

1. AI Hub 다운로드/복구 관련 변경 6개를 `stash@{0}: wip-aihub-download-reconstruction`로 분리했다.
2. 환경 역할을 다음처럼 정리했다.
   - `.venv`: backend/general runtime
   - `.venvs/stt-runtime`: 전달된 CTranslate2 STT 모델 평가
   - `.venvs/stt-train`: Whisper QLoRA 학습
   - `.venvs/tts-runtime`: 전달된 Qwen3-TTS 모델 실행
   - `.venvs/tts-train`: Qwen3-TTS 학습/실험
3. STT runtime requirements를 `faster-whisper==1.2.1`, `ctranslate2==4.8.1`로 고정했다.
4. STT train requirements에 `transformers==5.15.1`, `peft==0.20.0`, `bitsandbytes==0.48.0` 등을 반영했다.
5. TTS runtime requirements를 전달 번들과 맞췄다.
6. TTS train의 `qwen-tts`, `faster-qwen3-tts`, `fastapi`, `uvicorn`, `numpy`를 runtime과 동일하게 맞췄다.
7. TTS train의 `torch/torchaudio==2.8.0+cu128`, `accelerate==1.12.0`, `datasets==4.8.5`, `tensorboard==2.21.0`, `soundfile==0.14.0`은 기존 검증값을 유지했다.
8. `qwen-tts==0.1.1`이 `transformers==4.57.3`을 정확히 요구하고 `faster-qwen3-tts==0.3.2`도 `transformers<5`를 요구하므로 TTS train의 transformers는 STT train과 통일하지 않았다.
9. TTS train에 `flash-attn==2.8.3.post1+cu.12.8.torch.2.8` prebuilt wheel을 추가했다.
10. bootstrap/verification 스크립트와 `docs/PYTHON_ENVIRONMENT.md`를 추가했다.
11. 작업 종료 시 Worklog 누락을 줄이기 위해 `AGENTS.md` 상단 완료 체크리스트와 PR 템플릿 Worklog 체크 항목을 추가했다.

## 주요 판단과 이유

- 최신 handoff는 최종 모델·dataset artifact의 source of truth로 사용한다.
- 최신 handoff에 없는 환경 버전은 원 STT 학습 폴더와 TTS 원 전달 번들의 metadata/requirements로 보완한다.
- 과거 학습 머신의 완전한 `pip freeze`를 복원할 수 없는 경우, 확인된 버전과 현재 로컬 compatibility pin을 문서에서 구분한다.
- TTS train의 transformers는 STT train과 억지로 통일하지 않는다. Qwen 패키지 자체의 버전 제약이 4.57.3을 요구하기 때문이다.
- RTX 5070 Ti에서는 일반적인 소스 빌드보다 검증된 CUDA 12.8/PyTorch 2.8용 FlashAttention prebuilt wheel을 사용했다.
- Worklog 규칙은 기존에도 있었지만 문서 하단에 있어 놓치기 쉬웠으므로 commit/push/PR 전에 확인하는 완료 체크리스트와 PR 템플릿을 추가했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/requirements-stt-runtime.txt` | STT runtime 고정 버전 |
| `backend/requirements-stt-training.txt` | STT QLoRA 학습 의존성 |
| `backend/requirements-tts-runtime.txt` | 전달 TTS runtime 버전 |
| `backend/requirements-tts-training.txt` | TTS 학습/실험 의존성 |
| `backend/scripts/bootstrap_project_venv.py` | 프로젝트 기본 venv bootstrap |
| `backend/scripts/bootstrap_training_venvs.py` | STT/TTS 역할별 환경 bootstrap 및 FlashAttention 설치 |
| `backend/scripts/verify_training_env.py` | 패키지/import/CUDA/FlashAttention 검증 |
| `docs/PYTHON_ENVIRONMENT.md` | 환경 source-of-truth와 재현 기준 문서 |
| `docs/README.md` | Python 환경 문서 링크 추가 |
| `AGENTS.md` | 작업 완료 체크리스트 추가 |
| `.github/pull_request_template.md` | Worklog/문서 갱신 체크 추가 |
| `docs/worklogs/2026-09-18_python-environments.md` | 이번 작업 기록 |
| `docs/worklogs/README.md` | 이번 Worklog 링크 추가 |

## 5. 검증

STT train:

```text
Python 3.12.3
torch 2.8.0+cu128
transformers 5.15.1
peft 0.20.0
bitsandbytes 0.48.0
CUDA available: true
GPU: NVIDIA GeForce RTX 5070 Ti
BF16 supported: true
pip check: No broken requirements found.
Whisper/PEFT/BitsAndBytesConfig import smoke: OK
```

STT runtime:

```text
faster-whisper 1.2.1
CTranslate2 4.8.1
CUDA device count: 1
pip check: No broken requirements found.
```

TTS train:

```text
torch 2.8.0+cu128
qwen-tts 0.1.1
faster-qwen3-tts 0.3.2
fastapi 0.115.12
uvicorn 0.34.2
numpy 2.2.6
transformers 4.57.3
accelerate 1.12.0
datasets 4.8.5
tensorboard 2.21.0
soundfile 0.14.0
flash-attn 2.8.3.post1+cu.12.8.torch.2.8
CUDA available: true
GPU: NVIDIA GeForce RTX 5070 Ti
BF16 supported: true
pip check: No broken requirements found.
flash_attn_func BF16 CUDA smoke: OK
```

Python bootstrap/verification 스크립트는 `py_compile`을 통과했다.

## 6. 발견한 문제 / 남은 리스크

- STT 원본 `requirements-train.txt`는 문서에서 사용 흔적은 확인했지만 현재 전달 폴더에서 찾지 못했다.
- STT merged model의 `transformers_version=5.15.1`은 저장/병합 환경의 직접 증거이며 실제 최초 학습 시점의 정확한 버전까지 독립적으로 증명하지는 못한다.
- TTS 원 training script와 완전한 training requirements snapshot은 현재 전달 자료에 없다.
- 별도 `tts-runtime` venv의 전체 설치/실행 검증은 이번 작업에서 완료하지 못했다. requirements 정의 자체는 원 전달 번들 기준으로 작성했다.
- 최초 환경 커밋 메시지 `Add reproducible STT and TTS Python environments`는 현재 `AGENTS.md`의 `<type>: <summary>` 규칙과 형식이 다르지만 이미 원격 PR에 push된 상태라 history rewrite는 하지 않았다.

## 미확인 사항

- 전달된 실제 TTS 모델을 `.venvs/tts-runtime`에서 end-to-end 생성까지 실행하는 검증은 아직 수행하지 않았다.
- STT/TTS 실제 재학습 작업은 아직 시작하지 않았다.
- FlashAttention을 실제 Qwen3-TTS 전체 학습 loop에서 사용하는 장시간 안정성 검증은 아직 하지 않았다.

## 7. 다음 작업

- PR #11 리뷰/CI 결과를 확인한다.
- 환경 PR 작업이 끝난 뒤 `stash@{0}`의 AI Hub 다운로드/복구 작업으로 복귀한다.
- 실제 STT/TTS 학습을 시작할 때 모델/데이터 경로와 학습 command를 Worklog에 별도로 남긴다.
