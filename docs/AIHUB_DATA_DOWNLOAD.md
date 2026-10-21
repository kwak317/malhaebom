# AI Hub STT 119 데이터 준비 및 재구성

## 범위

현재 말해봄 Mk.2에서 이 문서가 다루는 AI Hub 원천데이터는 **STT용 dataset 119, 한국어 방언 발화 데이터(경상도)** 뿐이다.

- dataset key: `119`
- 기본 저장 위치: `data/stt/aihub/119/`
- 원본 archive, 생성 WAV, handoff manifest는 모두 `data/` 아래의 Git ignore 대상이다.
- TTS dataset 71349는 현재 말해봄의 데이터 provenance로 사용하지 않는다. 관련 downloader와 문서 절차도 유지하지 않는다.

## 현재 로컬 상태

2026-09-18 기준 현재 프로젝트 로컬에는 필요한 STT archive 4개가 있다.

| 용도 | AI Hub filekey | 파일 | 로컬 크기 |
| --- | ---: | --- | ---: |
| Training label | `572701` | `(비식별화완료)경상도_학습데이터_1.zip` | 323,123,858 bytes |
| Training source | `572702` | `(비식별화완료)경상도_1.zip` | 29,686,321,494 bytes |
| Validation label | `572713` | `(비식별화완료)경상도_학습데이터_2.zip` | 34,001,449 bytes |
| Validation source | `572714` | `(비식별화완료)경상도_2.zip` | 29,919,002,736 bytes |

전체 약 59.96 GB이며, dataset 119 전체를 받은 것이 아니라 현재 handoff manifest 재구성에 필요한 archive만 보관한다.

현재 handoff manifest:

```text
data/stt/handoff/
├─ train.jsonl       # 50,000 rows / 413 source conversations
└─ validation.jsonl  # 5,000 rows / 411 source conversations
```

재구성 결과:

```text
data/stt/handoff-reconstructed/
└─ dataset/
   ├─ train.jsonl
   ├─ validation.jsonl
   ├─ train/audio/       # 50,000 WAV
   └─ validation/audio/  # 5,000 WAV
```

즉 최신 handoff의 50,000 + 5,000 학습 manifest를 현재 AI Hub 119 archive에서 모두 재구성한 상태다.

## API key

프로젝트 루트의 `.env`에 다음 값을 둔다.

```dotenv
AIHUB_API_KEY=발급받은_API_KEY
```

`.env`는 Git ignore 대상이다. 스크립트는 키 값을 출력하지 않는다.

AI Hub 공식 `aihubshell`은 download mode에서 API key를 command-line argument로 받으므로 실행 중 로컬 OS process table에는 잠시 노출될 수 있다. 공동 서버에서는 다른 사용자가 프로세스 인자를 볼 수 있는지 확인한다.

## 다운로드 스크립트

사용 파일:

```text
backend/scripts/aihub_download_common.py
backend/scripts/download_aihub_stt.py
```

추가 Python 패키지는 필요하지 않는다. 공식 `aihubshell`이 없으면 처음 실행할 때 `.cache/aihub/aihubshell`에 설치한다.

명시적으로 설치만 하려면:

```bash
python backend/scripts/download_aihub_stt.py install-shell
```

### 현재 AI Hub tree 확인

```bash
python backend/scripts/download_aihub_stt.py tree
```

AI Hub 측 파일 구조나 filekey가 바뀔 수 있으므로 새로 다운로드할 때는 먼저 live tree를 확인한다.

### filekey 계획

```bash
python backend/scripts/download_aihub_stt.py plan --match '경상도'
```

### 현재 재구성에 필요한 archive 다운로드

```bash
python backend/scripts/download_aihub_stt.py download \
  --filekey 572701 \
  --filekey 572702 \
  --filekey 572713 \
  --filekey 572714
```

스크립트는 실수로 전체 dataset을 받지 않도록 `--filekey` 또는 명시적 `--all` 없이는 다운로드를 거부한다.

## handoff manifest와 AI Hub 119의 관계

handoff manifest의 한 행은 다음과 같은 segment WAV를 가리킨다.

```json
{"audio":"dataset/train/audio/DKSR20000718_1_1_1.wav","text":"어떤 동물 키우세요?"}
```

AI Hub archive에는 이 segment 파일 자체가 있는 것이 아니라 대화 단위 원본 WAV와 label JSON이 있다.

```text
manifest WAV        DKSR20000718_1_1_1.wav
source conversation DKSR20000718.wav
label utterance id  DKSR20000718.1.1.1
```

`backend/scripts/reconstruct_aihub119_segments.py`는 label의 utterance `start` / `end`를 사용해 원본 대화 WAV에서 필요한 구간만 잘라 handoff의 파일명과 디렉터리 구조로 다시 만든다.

handoff의 `text`는 AI Hub label JSON의 `form`이 아니라 **`dialect_form`** 과 대응한다. `form`에는 `(쫌)/(조금)` 같은 이중 표기가 남을 수 있으므로 manifest 동일성 검증 기준으로 사용하지 않는다.

현재 확보한 handoff에서는 train 50,000행과 validation 5,000행이 모두 `dialect_form`과 일치하는 것으로 검증했다.

## 재구성 검증

WAV를 만들지 않고 manifest ↔ label/source 대응만 확인:

```bash
python backend/scripts/reconstruct_aihub119_segments.py \
  --train-manifest data/stt/handoff/train.jsonl \
  --validation-manifest data/stt/handoff/validation.jsonl
```

검증 항목:

- manifest audio filename 형식
- 필요한 source conversation 존재 여부
- label JSON 존재 여부
- utterance id 존재 여부
- start/end 구간 유효성
- manifest `text`와 label `dialect_form`의 정규화 일치

## WAV 재구성

검증 후 실제 segment WAV를 만들 때:

```bash
python backend/scripts/reconstruct_aihub119_segments.py \
  --train-manifest data/stt/handoff/train.jsonl \
  --validation-manifest data/stt/handoff/validation.jsonl \
  --build
```

기본 출력 위치는:

```text
data/stt/handoff-reconstructed/
```

이미 생성된 WAV는 기본적으로 건너뛰며, 다시 만들려면 `--overwrite`를 명시한다.

## 데이터 취급 원칙

- 원본 AI Hub 데이터는 승인된 계정으로만 다운로드한다.
- 원본 archive, 생성 WAV, handoff manifest를 Git에 커밋하지 않는다.
- API key를 코드·문서·로그에 기록하지 않는다.
- 필요한 archive만 선택적으로 받는다.
- handoff manifest를 재구성할 때 원문 기준은 `dialect_form`이다.
- STT 학습환경과 데이터 준비 절차는 분리해서 관리한다. Python package 버전은 [Python 환경 재현 기준](PYTHON_ENVIRONMENT.md)을 따른다.
