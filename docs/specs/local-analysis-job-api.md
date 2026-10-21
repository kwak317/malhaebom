# 로컬 분석 Job API Spec

## Why

- **페르소나**: 개발 환경에서 STT Worker와 API 연결을 먼저 검증하려는 팀 개발자
- **상황**: 프론트엔드, Supabase, 배포 환경 없이 로컬 음성 파일 하나의 분석 요청과 결과 조회 흐름을 확인해야 한다.
- **문제**: 현재 전사 Worker는 CLI로만 실행되어 작업 상태, 입력 검증, 실패 결과를 API 계약으로 확인할 수 없다.
- **측정 지표**: 유효 WAV의 Job 완료, 잘못된 입력의 모델 미호출, STT 실패의 명시적 상태 반환

## Goal

- **성공 기준**: 로컬 API가 WAV·WebM·MP3 파일을 받아 5~60초·15MB 이하 조건을 검증하고, `queued → processing → completed | failed` 상태와 STT·전달력 분석 결과를 조회할 수 있다.
- **Out of Scope**: 브라우저 UI, Supabase Auth·Storage·DB, 배포, TTS 자산 재생, LoRA 모델 교체·학습·성능 선정

## What

### Happy Path

1. 개발자가 `POST /analysis-jobs`에 비민감 `source_id`와 WAV·WebM·MP3 파일을 보낸다.
2. API는 확장자, 파일 크기, 디코딩 가능한 길이를 검증한 뒤 로컬 임시 작업 파일로 저장한다.
3. API는 `job_id`와 `queued` 상태를 즉시 반환하고 백그라운드에서 기존 `FasterWhisperTranscriber`를 호출한다.
4. 개발자가 `GET /analysis-jobs/{job_id}`로 완료 상태, 기존 STT 표준 결과와 VAD 기반 전달력 분석 결과를 조회한다.
5. 완료 또는 실패 후 임시 음성 파일은 삭제한다.

### Edge Case

- 파일이 없거나 확장자가 다르면 `INVALID_FORMAT`으로 거절하며 모델을 호출하지 않는다.
- 15MB 초과 파일은 `FILE_TOO_LARGE`, 5초 미만 또는 60초 초과 파일은 `INVALID_DURATION`으로 거절한다.
- 디코딩 실패는 `INVALID_AUDIO`로 거절한다.
- Worker 전사 실패는 Job의 `failed` 상태와 `STT_FAILED` 코드로 반환하며 전사문·로컬 절대경로를 로그나 오류 메시지에 넣지 않는다.
- 없는 Job 조회는 HTTP 404를 반환한다.

## How

- API 프레임워크는 FastAPI를 사용한다.
- 음성 길이는 WAV는 표준 `wave` 모듈, WebM·MP3는 PyAV로 확인한다.
- Job 메타데이터는 프로세스 메모리에만 보관한다. 서버 재시작 시 사라지는 로컬 개발용 구현이다.
- 임시 파일은 `LOCAL_ANALYSIS_DIR`(기본값 `local-analysis`)에 두고 완료·실패 후 제거한다. 해당 경로는 Git에서 제외한다.
- STT 기준선은 환경변수의 `STT_MODEL_NAME` 기본값 `large-v3-turbo`이며, `FasterWhisperTranscriber` 생성자 주입으로 테스트 모델 교체를 허용한다.
- `POST /analysis-jobs`는 multipart form-data의 `source_id`, `audio`를 받는다. `GET /analysis-jobs/{job_id}`는 상태와 완료된 `SttResult` JSON, `delivery` JSON을 반환한다. VAD 세부 계약은 `vad-delivery-worker-integration.md`를 따른다.

## AC

- **Given**: 길이 6초의 유효 WAV와 fake STT가 있다. **When**: Job을 생성·실행한다. **Then**: 상태는 `completed`이고 STT 결과의 `source_id`가 요청값과 일치하며 임시 파일은 삭제된다.
- **Given**: 5초 미만 WAV 또는 60초 초과 WAV가 있다. **When**: Job을 생성한다. **Then**: `INVALID_DURATION` 오류가 발생하고 fake STT는 호출되지 않는다.
- **Given**: Worker가 예외를 발생시킨다. **When**: Job을 실행한다. **Then**: 상태는 `failed`, 오류 코드는 `STT_FAILED`이며 오류 메시지에 로컬 경로가 없다.
- **Given**: 존재하지 않는 Job ID다. **When**: 조회한다. **Then**: API는 HTTP 404를 반환한다.
