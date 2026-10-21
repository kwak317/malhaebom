# TTS 사전 생성 피드백 템플릿 Spec

## Why

면접 연습 사용자는 자신의 답변에서 가장 큰 전달 문제를 짧고 바로 들을 수 있어야 한다. 문제 코드에 정해진 고정 템플릿은 모델 대기 없이 일관되게 재생할 수 있어야 하므로, 사전 생성·청취 검수한 WAV로 유지한다.

질문자 `candidate_04_questioner`와 임시 코치 `candidate_01_coach`의 고정 템플릿 WAV를 로컬에서 생성·청취 검수하고, 런타임에는 다른 조원의 STT·VAD 분석 결과를 템플릿 ID로만 연결한다.

## Goal

- 분석 결과의 전달 문제 코드 최대 2개에 대해 수용된 코치 WAV를 재생한다.
- 기본 질문은 로그인 여부와 관계없이 수용된 질문자 WAV를 재생한다. WAV 원본은 비공개 Storage에 유지하며, 앱은 Storage에 직접 접근하지 않는다.
- 기본 질문과 고정 템플릿 코치 피드백 재생 경로에서는 Qwen3-TTS 모델 추론을 실행하지 않는다. 사용자가 직접 입력한 질문의 실시간 합성은 별도 [사용자 입력 면접 질문 TTS Spec](custom-question-tts.md)을, 분석 LLM 기반 코치 피드백의 실시간 합성은 [분석 결과 코치 피드백 TTS Spec](coach-feedback-tts.md)을 따른다.
- 새 코치 템플릿은 각각 수동 청취 수용 판정을 거친다.

Out of Scope: 사용자 답변 전체의 동적 TTS, 사용자 음성 복제·추가 학습, 분석 LLM 기반 코치 피드백의 실시간 TTS 구현, 재학습, 공개 Storage 전환, 사용자 입력 질문 WAV의 영구 보관이다.

## What

### Happy Path

1. 분석 어댑터가 다른 조원의 결과를 허용된 문제 코드 0~2개로 정규화한다.
2. 앱은 코드 순서대로 템플릿 매니페스트에서 수용된 코치 WAV와 화면 문구를 찾는다.
3. 앱은 최대 두 개의 코치 WAV를 재생하고, 분석 근거 수치는 화면에 남긴다.
4. 로그인하지 않은 사용자를 포함한 앱은 기본 질문 ID로 고정 질문 음성 API를 호출한다.
5. API는 수용된 질문자 WAV만 비공개 Storage에서 읽어 `audio/wav`로 반환한다.
6. 사용자는 템플릿을 들은 뒤 같은 질문으로 재녹음한다.

### Edge Case

- 알 수 없는 코드, 빈 코드, 누락된 WAV, 검수 미완료 WAV는 텍스트 안내만 표시하며 TTS를 동적 생성하지 않는다.
- 템플릿 생성 실패 또는 청취 검수 불합격 WAV는 앱 재생 대상으로 등록하지 않는다.
- 사용자 원문 전사문과 개인별 수치는 템플릿 문장이나 이 정적 템플릿 경로의 Qwen 입력으로 전달하지 않는다.
- 기본 질문 ID가 허용 목록에 없거나, 수용된 자산이 없거나, Storage 읽기에 실패하면 API는 WAV·Storage 경로·서명 URL을 반환하지 않는다. 앱은 질문 텍스트만 표시하며 Qwen3-TTS를 실행하지 않는다.

## How

- 허용 코드 값은 `SPEED_FAST`, `LONG_SILENCE`, `FILLER_REPEAT`, `LOW_VOLUME`, `TERMINAL_INTONATION`이다. 다른 조원의 STT·VAD 결과 형식은 별도 어댑터가 이 값으로만 변환한다.
- 저장소의 코치·질문 카탈로그는 `templateId`, `questionId` 또는 `issueCode`, `displayText`, `speakerRole`, `qcStatus`, `isPrimary`, 불투명 `audioAssetId`만 기록한다. 실제 Storage URL·서명 URL·로컬 절대 경로·WAV hash는 Git에 기록하지 않는다.
- 템플릿 WAV는 로컬 실험 환경에서만 생성한다. 원본 AI Hub 음성·파생 전사문·checkpoint·생성 WAV를 GitHub에 넣지 않는다.
- 기본 질문과 고정 템플릿 코치의 수동 검수 완료 WAV는 사용자 입력을 포함하지 않는 비공개 앱 운영 자산이다. 사용자 직접 입력 질문과 분석 LLM 기반 코치 피드백을 요청마다 실시간 합성해 만든 WAV·최소 메타데이터는 각각의 Spec에 따라 최대 24시간 보관 후 삭제한다.
- 새 WAV는 24 kHz / mono / PCM_16, 0 bytes 초과, SHA-256 기록을 확인하고 수동 청취에서 자연스러움·잡음·마지막 음절 완결을 수용한 뒤에만 `qcStatus`를 수용으로 바꾼다.
- Candidate01은 빠른 속도와 마지막 음절 잘림 이력이 있으므로, 기존 한 파일의 자동 통과만으로 다른 템플릿의 품질을 추정하지 않는다.
- 기본 질문 WAV는 사용자 입력 질문의 `question-tts-audio` 버킷과 분리된 비공개 `preset-question-audio` 버킷에만 둔다. `question-tts-audio`의 24시간 삭제·사용자별 RLS 정책을 기본 질문에 적용하지 않는다.
- 기본 질문 재생 API는 `GET /api/preset-questions/{questionId}/audio`이며 인증 헤더를 요구하지 않는다. 허용 ID는 `preset-01`부터 `preset-10`까지다.
- API는 서버 전용 `SUPABASE_SERVICE_ROLE_KEY`로 카탈로그의 `qcStatus: accepted`, `isPrimary: true`, 비어 있지 않은 `audioAssetId`를 모두 확인한 뒤에만 비공개 객체를 읽어 `audio/wav`로 반환한다. 프런트엔드는 Storage SDK·버킷명·객체 경로·서명 URL을 사용하지 않는다.
- 기본 질문 API는 `Cache-Control: public, max-age=300`을 반환할 수 있다. 응답에는 사용자 데이터·질문 원문·Storage 오류 상세를 넣지 않는다.
- 기본 질문 API는 로컬 더미 전용 `build_local_demo_app()`이 아니라 일반 `create_app()`에 등록한다. 별도 프런트·백엔드 도메인으로 배포하면 실제 프런트 Origin을 CORS 허용 목록에 추가하고, 프런트에는 실제 API 주소만 `VITE_API_BASE_URL`로 제공한다.

## AC

- Given 분석 결과가 `SPEED_FAST`, `FILLER_REPEAT` 두 코드일 때, When 앱이 피드백을 준비하면, Then 해당 순서의 수용된 코치 템플릿 WAV를 최대 두 개만 재생하고 Qwen 프로세스를 실행하지 않는다.
- Given 분석 결과에 알 수 없는 코드가 있거나 수용된 WAV가 없을 때, When 앱이 피드백을 준비하면, Then 텍스트 안내만 표시하고 동적 TTS를 호출하지 않는다.
- Given 기본 질문 ID가 있을 때, When 질문을 재생하면, Then `candidate_04_questioner`의 수용된 사전 생성 질문 WAV만 재생한다.
- Given 로그인하지 않은 사용자가 `preset-01`을 요청했을 때, When 승인된 질문자 자산이 비공개 Storage에 존재하면, Then API는 `200 audio/wav`를 반환하고 Storage URL·객체 경로·인증 정보를 노출하지 않는다.
- Given 기본 질문 ID가 허용 목록 밖이거나 수용된 질문자 자산이 없을 때, When 기본 질문 음성을 요청하면, Then API는 `404`를 반환하고 Qwen3-TTS·공식 화자·다른 WAV로 대체하지 않는다.
- Given 비공개 Storage 읽기가 실패했을 때, When 기본 질문 음성을 요청하면, Then API는 `503`을 반환하고 부분 WAV·서명 URL·Storage 오류 상세를 반환하지 않는다.
- Given 매니페스트에 등록된 WAV가 있을 때, When 등록을 검증하면, Then 24 kHz / mono / PCM_16, 0 bytes 초과, SHA-256, 수동 청취 수용 상태를 모두 확인할 수 있다.
- Given 새 코치 템플릿 WAV를 생성했을 때, When 검수하지 않았거나 청취 불합격이면, Then 해당 WAV는 앱 재생 대상이 되지 않는다.
- Given 사용자 녹음 또는 전사문이 있을 때, When 피드백을 준비하면, Then 사용자 원문·전사문·개인별 수치는 TTS 입력이나 학습 데이터로 전달되지 않는다.
