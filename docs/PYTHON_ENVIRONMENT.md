# Python 환경 재현 기준

## 목적

말해봄 Mk.2의 Python 환경은 역할별로 분리한다. 최신 인수인계 폴더는 모델·manifest의 최종 전달본을 기준으로 삼고, 그 폴더에 빠진 실행환경 정보는 원 STT 학습 폴더와 TTS 전달 번들의 metadata/requirements로 보완한다.

환경 정의가 과거 작업 머신의 완전한 `pip freeze`를 뜻하지는 않는다. 특히 STT 원본 `requirements-train.txt`는 문서에서 사용 흔적만 확인되고 최신 인수인계에는 포함되지 않았다.

## 환경 구조

```text
proj2-3/
├─ .venv/                    # Backend/LLM/일반 프로젝트 runtime
└─ .venvs/
   ├─ stt-runtime/           # 전달된 부산 LoRA CTranslate2 모델 재현/평가
   ├─ stt-train/             # 전달된 Whisper QLoRA 학습 코드 재실행
   ├─ tts-runtime/           # 전달된 Qwen3-TTS questioner/coach runtime
   └─ tts-train/             # Qwen3-TTS 학습/실험용 재현 환경
```

모델 가중치, AI Hub 데이터, 생성 WAV와 checkpoint는 이 환경 정의와 별개이며 Git에 넣지 않는다.

## Source of truth

### STT 데이터·모델

최신 `MALHAEBOM_STT_TTS_HANDOFF_20260917`을 최종 artifact 기준으로 사용한다.

- `STT/dataset/train.jsonl`: 50,000행
- `STT/dataset/validation.jsonl`: 5,000행
- `STT/models/whisper-medium-busan-lora-a100-fast-ct2-v3/model.bin`: 최종 전달된 CTranslate2 추론 모델
- `STT/scripts/train_whisper_lora.py`: 전달된 QLoRA 학습 코드

### STT runtime

동일조건 평가 문서에 다음 버전이 직접 기록돼 있다.

- `faster-whisper==1.2.1`
- `CTranslate2==4.8.1`
- GPU compute type: `float16`

따라서 `backend/requirements-stt-runtime.txt`는 이 두 패키지를 그대로 고정한다.

### STT train

완전한 과거 package snapshot은 없다. 현재 정의는 전달된 코드와 artifact metadata를 합친 best-evidence 환경이다.

직접 확인된 정보:

- checkpoint `adapter_config.json`: `peft_version == 0.20.0`
- merged model `config.json`: `transformers_version == 5.15.1`
- `train_whisper_lora.py`: `BitsAndBytesConfig(load_in_4bit=True)`, NF4 QLoRA 사용

주의:

- `transformers==5.15.1`은 merged model을 저장한 환경의 직접 증거다. 실제 학습 시작 시점에도 정확히 같은 버전이었다는 변환 로그는 없다.
- 원본 `requirements-train.txt`는 최신 전달 폴더에서 찾지 못했다.
- `bitsandbytes==0.48.0`과 datasets/accelerate/evaluate/jiwer/tensorboard/soundfile 버전은 현재 Python 3.12 + RTX 50xx/cu128 재현 환경을 위한 compatibility pin이다. 과거 Colab freeze라고 주장하지 않는다.

### TTS runtime

원 전달 번들의 `questioner_candidate04/requirements.txt`를 우선 기준으로 사용한다.

```text
qwen-tts==0.1.1
faster-qwen3-tts==0.3.2
fastapi==0.115.12
uvicorn==0.34.2
numpy==2.2.6
```

전달 README에는 Python `3.12.13`과 CUDA-enabled PyTorch가 필요하다고 기록돼 있다. 사용 가능한 Python이 다른 3.12 patch release인 경우 bootstrap은 경고를 출력하고 호환 환경을 만든다. 정확한 3.12.13 재현이 필요한 경우 해당 interpreter를 별도로 준비한다.

### TTS train

`tts-train`은 전달받은 완전한 training snapshot이 아니라, 재구성 가능한 학습/실험 환경으로 전달 runtime과 겹치는 패키지 버전을 맞춘다.

runtime과 동일하게 고정하는 패키지:

```text
qwen-tts==0.1.1
faster-qwen3-tts==0.3.2
fastapi==0.115.12
uvicorn==0.34.2
numpy==2.2.6
```

STT train과 공통으로 유지하는 호환 핀:

- `torch==2.8.0` / `torchaudio==2.8.0` (cu128)
- `accelerate==1.12.0`
- `datasets==4.8.5`
- `tensorboard==2.21.0`
- `soundfile==0.14.0`

추가로 RTX 5070 Ti 기반 검증 환경에서 GPU smoke test를 통과한 FlashAttention wheel을 사용한다.

```text
flash-attn==2.8.3.post1+cu.12.8.torch.2.8
index: https://wheels.astral.sh/simple/cu128/
```

검증은 단순 import에 그치지 않고 BF16 CUDA tensor로 `flash_attn_func`를 실제 실행한다.

`transformers`는 예외다. `qwen-tts==0.1.1`이 `transformers==4.57.3`을 정확히 요구하고, `faster-qwen3-tts==0.3.2`도 `transformers<5`를 요구한다. 따라서 STT train의 `transformers==5.15.1`과 통일하지 않고 TTS train에서는 `4.57.3`을 유지한다.

현재 전달 자료에는 TTS training script와 원 training requirements 전체가 포함돼 있지 않으므로, 이 환경은 과거 학습 머신의 완전한 freeze라고 주장하지 않는다.

## PyTorch / CUDA

RTX 50xx 로컬 재현 환경은 다음을 명시적으로 설치한다.

- `torch==2.8.0`
- `torchaudio==2.8.0`
- PyTorch wheel index: `cu128`

이 값은 RTX 5070 Ti 검증 환경에서 확인한 호환성 핀이다. 과거 STT Colab 또는 TTS 학습 환경의 정확한 PyTorch 버전을 의미하지 않는다.

`stt-runtime`은 CTranslate2 기반이므로 bootstrap에서 PyTorch를 강제 설치하지 않는다.

## 생성

프로젝트 runtime:

```bash
python3.12 backend/scripts/bootstrap_project_venv.py
source .venv/bin/activate
```

FastAPI 프로세스 안에서 질문 TTS까지 직접 로드할 때만:

```bash
python3.12 backend/scripts/bootstrap_project_venv.py --with-question-tts
```

개발 도구(Node 22, npm, npx, Supabase CLI)를 프로젝트 로컬 환경에 함께 준비할 때:

```bash
python3.12 backend/scripts/bootstrap_project_venv.py --with-dev-tools
source .venv/bin/activate

python --version
node --version      # v22.14.0
npm --version       # 10.9.2
npx --version       # 10.9.2
supabase --version  # 2.117.0
```

`--create-only --with-dev-tools`를 함께 전달하면 무거운 Python 패키지 설치는 건너뛰고 프로젝트 로컬 도구만 빠르게 준비할 수 있다.


모델별 환경:

```bash
python3.12 backend/scripts/bootstrap_training_venvs.py --target stt-runtime
python3.12 backend/scripts/bootstrap_training_venvs.py --target stt-train
python3.12 backend/scripts/bootstrap_training_venvs.py --target tts-runtime
python3.12 backend/scripts/bootstrap_training_venvs.py --target tts-train
```

세 환경을 모두 만들려면:

```bash
python3.12 backend/scripts/bootstrap_training_venvs.py --target all
```

생성만 하고 패키지 설치를 생략하려면 직접 bootstrap에 `--create-only`를 사용한다.

```bash
python3.12 backend/scripts/bootstrap_training_venvs.py --target stt-runtime --create-only
python3.12 backend/scripts/bootstrap_training_venvs.py --target stt-train --create-only
python3.12 backend/scripts/bootstrap_training_venvs.py --target tts-runtime --create-only
python3.12 backend/scripts/bootstrap_training_venvs.py --target tts-train --create-only
```

## 검증

```bash
.venvs/stt-runtime/bin/python backend/scripts/verify_training_env.py --require-cuda
.venvs/stt-train/bin/python backend/scripts/verify_training_env.py --require-cuda
.venvs/tts-runtime/bin/python backend/scripts/verify_training_env.py --require-cuda
.venvs/tts-train/bin/python backend/scripts/verify_training_env.py --require-cuda
```

검증 스크립트는 패키지 import, `pip check`, CUDA 접근 여부와 환경별 핵심 버전을 JSON으로 출력한다.

## 가상환경 재사용

위 프로젝트 상대경로의 가상환경이 이미 있으면 재사용할 수 있다. 다만 설치된 의존성 버전이 다를 수 있으므로 각 `bootstrap_training_venvs.py` 명령으로 동기화하고 검증 스크립트를 다시 실행한다. 가상환경이 없으면 같은 명령으로 새로 생성한다.

`tts-runtime`은 전달 모델을 최대한 원 runtime 조건에 가깝게 재현하기 위한 별도 환경이다.
