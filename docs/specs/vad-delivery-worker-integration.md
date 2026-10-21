# VAD·전달력 분석 Worker 연결 Spec

## Why

한국어 취업준비생은 전사문만으로 실제 발화 시간, 긴 침묵, 말속도를 판단하기 어렵다. 현재 백엔드는 STT 작업 API와 전달력 분석 계약을 각각 갖고 있지만, 실제 음성에서 VAD 발화 구간을 추출해 둘을 연결하지 않는다.

## Goal

- 완료된 로컬 분석 Job은 STT 결과와 VAD 기반 전달력 분석 결과를 함께 반환한다.
- `DeliveryAnalyzer`는 실제 Silero VAD 발화 구간을 받아 CPM, 긴 침묵, 반복 표현과 최대 두 개의 피드백을 만든다.
- VAD 모델은 첫 요청 때만 로드해 이후 Job에서 재사용한다.
- VAD 또는 전달력 분석 실패는 내부 예외를 노출하지 않고 Job을 `failed`와 `ANALYSIS_FAILED`로 끝낸다.

### Out of Scope

- Whisper·LoRA 모델 교체, 학습, 성능 선정
- TTS WAV 생성·자산 재생
- VAD 임계값의 사용자 연구 기반 최종 조정
- 브라우저 화면, Supabase, Vercel, 배포
- 음량·F0·문장 마무리 지표

## What

### Happy Path

1. `LocalAnalysisJobService`가 유효한 음성 Job을 처리한다.
2. 기존 STT 전사가 `SttResult`를 반환한다.
3. `SileroVadDetector`가 동일한 임시 음성 파일에서 정렬된 `SpeechSegment` 목록을 반환한다.
4. `DeliveryAnalyzer.analyze(stt_result, vad_segments)`가 `DeliveryAnalysisResult`를 만든다.
5. Job 상태는 `completed`가 되며 기존 `result` STT JSON과 새 `delivery` JSON을 함께 반환한다.
6. 임시 음성 파일은 완료·실패 뒤에도 기존 정책대로 삭제한다.

### Edge Case

- VAD가 발화 구간을 찾지 못하면 빈 구간을 전달한다. `DeliveryAnalyzer`는 발화 시간 `0`, CPM `null`, 긴 침묵 빈 목록을 반환한다.
- VAD 모델 로드·오디오 읽기·분석 중 예외가 발생하면 Job은 `failed`, 오류 코드는 `ANALYSIS_FAILED`가 된다. 응답에는 원본 경로·traceback·전사문을 넣지 않는다.
- STT가 실패하면 기존과 동일하게 Job은 `failed`, 오류 코드는 `STT_FAILED`가 된다.

## How

- `backend/app/services/vad_detector.py`에 `SpeechSegmentDetector` Protocol과 `SileroVadDetector`를 둔다.
- `SileroVadDetector.detect(audio_path: Path) -> list[SpeechSegment]`는 PyAV로 입력을 16kHz mono tensor로 디코드한 뒤 `get_speech_timestamps(..., return_seconds=True)`를 사용한다. 각 타임스탬프를 소수 셋째 자리 `SpeechSegment`로 변환한다.
- `SileroVadDetector`는 Windows 한글 경로 호환을 위해 `load_silero_vad(onnx=True)`로 만든 모델을 인스턴스에 캐시한다. 테스트에서는 가짜 detector를 생성자 주입한다.
- `LocalAnalysisJobService` 생성자는 기존 transcriber 외에 `SpeechSegmentDetector`와 `DeliveryAnalyzer`를 받는다. `process()`는 STT 성공 후 VAD, 전달력 분석 순으로 실행한다.
- `LocalAnalysisJob`은 선택적 `delivery: DeliveryAnalysisResult | None`를 보관하고 `to_dict()`에 `delivery`를 추가한다. 기존 `result` 필드와 상태 이름은 유지한다.
- `backend/app/main.py`의 기본 서비스는 `FasterWhisperTranscriber`, `SileroVadDetector`, `DeliveryAnalyzer`를 연결한다.
- `backend/requirements-stt.txt`에는 `silero-vad`와 CPU/GPU 환경에 맞는 PyTorch 의존성 설치 안내를 추가한다. 모델 파일·사용자 음성·체크포인트는 Git에 추가하지 않는다.
- **향후 수정 가능:** VAD threshold와 침묵 임계값은 현재 코드 기본값으로 시작하며, 사용자 테스트와 고정 평가 음성 측정 뒤 별도 Spec으로 조정한다.

## AC

- Given 가짜 STT와 가짜 VAD가 발화 구간 두 개를 반환할 때, When Job을 처리하면, Then 상태는 `completed`이고 응답의 `result`와 `delivery.metrics`가 모두 존재한다.
- Given VAD 구간 사이가 1초 이상일 때, When Job을 처리하면, Then `delivery.metrics.long_silences`에 시작·끝·길이가 반환된다.
- Given VAD가 빈 구간을 반환할 때, When Job을 처리하면, Then `speech_duration_sec`은 `0`, CPM은 `null`이고 Job은 `completed`다.
- Given VAD detector가 예외를 일으킬 때, When Job을 처리하면, Then 상태는 `failed`, 오류 코드는 `ANALYSIS_FAILED`이며 응답에 원본 경로·traceback·전사문이 없다.
- Given 기존 STT API 테스트를 실행할 때, When VAD가 주입된 서비스로 Job을 처리하면, Then 기존 `result` STT JSON 계약은 유지된다.
