# React Mock 기반 프론트엔드 MVP Spec

## Why

- **페르소나**: 혼자 신입 개발자 면접을 연습하며, 준비한 답변의 전달 방식을 짧게 반복 점검하려는 취업준비생
- **상황**: STT·TTS 모델의 최종 평가와 검수 WAV 준비가 끝나기 전에도, 녹음부터 분석 결과·재연습·비교까지의 사용 흐름을 구현·시연해야 한다.
- **문제**: 모델 완성을 기다리면 브라우저 녹음 UX와 화면 상태, 오류 안내, 재녹음 흐름을 늦게 검증하게 된다.
- **측정 지표**: 로컬 브라우저에서 1차 녹음부터 1차·2차 비교까지 완료할 수 있고, 실제 모델 연결 시 화면 컴포넌트를 바꾸지 않고 서비스 구현체만 교체할 수 있다.

## Goal

- React + Vite 로컬 앱에서 기본 질문 선택, 마이크 권한 확인, 5~60초 브라우저 녹음·재생, mock 분석 결과, 재녹음, 전후 비교를 제공한다.
- 분석 결과는 기존 백엔드의 `result`·`delivery` 응답 모양을 따르는 mock 데이터로 표시한다.
- 분석과 TTS는 서비스 인터페이스로 분리한다. 실제 STT/VAD API와 검수 완료 TTS WAV가 준비되면 해당 구현체만 교체한다.
- **Out of Scope**: 실제 STT/VAD API 호출, 실제 TTS WAV 재생, 로그인·Supabase·영구 저장, 직접 질문, 답변 내용 평가, 동적 TTS, Voice Cloning, 음량·억양 분석, 배포.

## What

### Happy Path

1. 사용자는 `/practice`에서 기본 면접 질문 10개 중 하나를 선택한다.
2. 사용자는 마이크 권한을 확인하고, 허용된 상태에서 1차 답변 녹음을 시작한다.
3. 녹음은 경과 시간을 표시하고 60초에 자동 종료된다. 사용자는 완료된 녹음을 재생한 뒤 분석을 요청한다.
4. `MockAnalysisClient`가 `result` STT와 `delivery` 전달력 분석을 반환한다.
5. 화면은 전사문, 답변 시간, 발화 시간, CPM, 긴 침묵, 반복 표현과 최대 두 개의 피드백을 표시한다.
6. TTS 자산이 없으면 재생 버튼 대신 검수 완료 음성 미준비 안내를 표시한다.
7. 사용자는 같은 질문으로 2차 녹음을 완료하고, 1차·2차의 CPM·긴 침묵·반복 표현을 비교한다.
8. 질문과 결과 요약은 현재 탭의 `sessionStorage`에만 보관한다.

### Edge Case

- 질문을 선택하지 않으면 마이크 확인과 녹음 시작 버튼은 비활성화한다.
- 마이크 권한이 거부되거나 장치를 찾지 못하면 녹음하지 않고 재확인 안내를 표시한다.
- 녹음이 5초 미만이면 분석 요청 버튼을 비활성화하고 최소 길이 안내를 표시한다.
- 녹음 파일 생성이나 mock 분석에 실패하면 현재 질문과 녹음 재생 기회를 유지하며 재시도 버튼을 표시한다.
- mock 결과가 `NO_SPEECH` 또는 `ANALYSIS_FAILED`라면 전사문·전달력 지표 대신 안전한 오류 안내를 표시한다.
- 2차 결과가 없으면 비교 화면으로 이동할 수 없다.

## How

- Vite가 생성한 React + TypeScript 앱을 `frontend/`에 둔다. 브라우저 UI와 상태만 담당하며 Python 백엔드를 포함하거나 실행하지 않는다.
- 주요 상태는 와이어프레임의 `PracticeSession`을 따른다: `landing`, `recording`, `recordComplete`, `analyzing`, `firstResult`, `secondRecording`, `secondResult`, `compare`.
- 녹음은 브라우저 `MediaRecorder`를 사용한다. 녹음 Blob은 메모리와 object URL로만 관리하며 `sessionStorage`에는 저장하지 않는다.
- `AnalysisClient` 인터페이스는 `analyze(audio, sourceId)`를 제공하고, MVP에서는 `MockAnalysisClient`를 사용한다. 실제 연결 단계에서는 multipart 업로드와 Job polling을 수행하는 구현체로 교체한다.
- mock 성공 결과는 백엔드 응답 형태인 `{ status, result, delivery, error }`를 따른다. `result`는 전사문을, `delivery`는 `metrics`와 최대 두 개 `feedback`을 제공한다.
- `TtsAssetResolver`는 현재 항상 `unavailable`을 반환한다. 이후에는 허용된 피드백 코드에 연결된 검수 WAV URL만 반환한다. 런타임 TTS 모델 합성은 하지 않는다.
- 1차·2차 비교는 프론트에서 같은 질문의 두 `delivery.metrics`를 이용해 표시만 한다. 개선 여부를 합격·불합격 또는 좋음·나쁨으로 판정하지 않는다.
- `sessionStorage`에는 비민감 질문 ID, 질문 문구, attempt 번호, 지표 요약만 저장한다. 음성 Blob, 전사문, TTS URL은 저장하지 않는다.
- UI는 와이어프레임의 고정 이용안내 카드, 질문 선택·마이크 확인의 동일 페이지 상태 전환, 오류 텍스트와 키보드 접근 가능한 질문 선택을 따른다.

## AC

- **Given**: 사용자가 `/practice`에 처음 진입했다. **When**: 질문을 선택하지 않는다. **Then**: 질문 목록과 비활성 시작 CTA가 표시되며 마이크 권한 요청은 발생하지 않는다.
- **Given**: 사용자가 질문을 선택했다. **When**: 마이크 권한 확인에 성공한다. **Then**: 같은 페이지에서 `연습 시작하기` CTA가 활성화된다.
- **Given**: 사용자가 녹음을 시작했다. **When**: 60초가 경과한다. **Then**: 녹음은 자동으로 종료되고 완료 녹음 재생·분석 CTA가 표시된다.
- **Given**: 5초 미만 녹음이 완료됐다. **When**: 사용자가 분석을 시도한다. **Then**: mock 분석은 호출되지 않고 최소 5초 안내가 표시된다.
- **Given**: 유효한 1차 녹음과 mock 성공 결과가 있다. **When**: 분석이 완료된다. **Then**: 기존 `result` 전사문과 `delivery.metrics`, 최대 두 개의 피드백이 함께 표시된다.
- **Given**: TTS 자산 resolver가 `unavailable`을 반환한다. **When**: 결과 화면을 표시한다. **Then**: 음성 재생 컨트롤 대신 자산 미준비 안내가 표시되며 재녹음 CTA는 활성화된다.
- **Given**: 같은 질문의 1차·2차 mock 결과가 완료됐다. **When**: 비교를 요청한다. **Then**: 두 attempt의 CPM, 긴 침묵 수, 반복 표현 수가 나란히 표시된다.
- **Given**: 마이크 권한 거부 또는 mock 분석 실패가 발생한다. **When**: 오류 상태를 표시한다. **Then**: 내부 예외·로컬 파일 경로 없이 재시도 방법을 표시한다.
