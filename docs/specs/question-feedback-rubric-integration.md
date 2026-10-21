# 질문 피드백 Rubric·LLM 연결 Spec

## Why

- **페르소나**: 기본 면접 질문에 답한 뒤 전달 방식 결과와 답변 구성 피드백을 함께 확인하려는 로그인 사용자
- **상황**: 프런트·질문자 TTS catalog은 `preset-01` 형식의 질문 ID를 사용하지만, 답변 구성 rubric은 `1` 형식을 사용한다. 또한 `OllamaQuestionRubricGenerator`는 구현돼 있으나 앱 시작 시 분석 서비스에 연결되지 않는다.
- **문제**: 활성화된 LLM이 있어도 기본 질문 rubric을 찾지 못하거나, 생성기가 연결되지 않아 `content_feedback`과 `improved_answer`가 생성되지 않는다.
- **측정 지표**: `preset-01`~`preset-10`의 rubric 조회 성공 10/10, `LLM_FEEDBACK_ENABLED=false` 상태 분석 성공, 활성화·정상 Ollama 상태의 preset 피드백 생성 성공, LLM 실패가 분석 Job 실패로 전파되는 건수 0건.

## Goal

- **해결 목표**: 기본 질문 ID를 `preset-01`~`preset-10`으로 통일하고, 명시적으로 활성화된 경우에만 로컬 Ollama 기반 피드백 생성기를 persistent 분석 서비스에 연결한다.
- **성공 기준**: 활성화 상태에서 persistent 분석 서비스가 동일한 generator 인스턴스를 받음; 비활성·초기화 실패·Ollama 요청 실패 상태에서도 전달 방식 분석 Job은 `completed` 처리됨; 새 DB table·Storage object·API endpoint·브라우저 LLM 호출 0건.
- **Out of Scope**: 모델 다운로드·설치·자동 실행, Ollama 원격 호스팅, LLM 응답 품질 평가, 사용자 음성 복제·TTS 입력, 과거 numeric ID 기록의 migration, LLM prompt/response 장기 보관, 신규 화면·endpoint 추가.

## What

### Happy Path

1. 사용자는 프런트의 기본 질문 `preset-01`~`preset-10` 중 하나에 답한다.
2. 분석 Job은 동일한 `question_id`를 저장한다.
3. `LLM_FEEDBACK_ENABLED=true`이면 Backend가 앱 시작 중 `OllamaQuestionRubricGenerator`를 만든다.
4. persistent 분석 서비스는 generator에서 동일한 ID의 rubric을 찾고, 전사문을 설정된 로컬 Ollama에 보내 답변 구성 피드백과 예시 답변을 생성한다.
5. 결과 화면은 기존 `content_feedback`과 `improved_answer` 필드를 사용할 수 있다.

### Edge Cases

| 상황 | 처리 방식 |
| --- | --- |
| `LLM_FEEDBACK_ENABLED`가 없거나 `false` | generator를 연결하지 않는다. 전달 방식 분석만 완료한다. |
| rubric JSON을 읽지 못함 | generator를 연결하지 않고 전달 방식 분석만 완료한다. |
| 등록되지 않은 `preset-*` ID | 답변 구성 피드백 없이 전달 방식 분석을 완료한다. |
| Ollama 연결·응답·형식 오류 | 해당 Job의 답변 구성 피드백만 건너뛰고 전달 방식 분석은 완료한다. |
| custom 질문 | 활성화된 generator가 일회성 rubric을 생성할 수 있으며, 사용자 질문·전사문은 그 요청에만 사용한다. |
| LLM이 꺼진 상태 | 질문·전사문을 새 로그·DB·Storage·TTS 요청으로 복사하지 않는다. |

## How

- 질문 ID의 정본은 `preset-01`~`preset-10`이다. `frontend/src/data/presetQuestions.ts`, `configs/tts/tts_template_catalog.json`, 분석 Job의 `question_id`, `configs/feedback/question-rubrics.json`이 이 형식을 사용한다.
- `configs/feedback/question-rubrics.json`의 질문 문구·필수 개념·추천 키워드는 바꾸지 않고 `question_id`만 정본 형식으로 바꾼다.
- Backend는 `LLM_FEEDBACK_ENABLED`가 `1`, `true`, `yes` 중 하나일 때만 `OllamaQuestionRubricGenerator`를 초기화한다. 그 외 값이면 `None`을 반환한다.
- generator 초기화가 `QuestionRubricUnavailableError`를 내면 `None`으로 폴백하며 앱 시작과 STT·VAD·전달 방식 분석을 막지 않는다.
- persistent Supabase 분석 서비스 생성 시에만 `question_feedback_generator` 인자로 generator 또는 `None`을 전달한다. local analysis 서비스, TTS 서비스, 브라우저 코드는 바꾸지 않는다.
- LLM 요청은 기존 generator의 설정된 Ollama URL로만 보낸다. 질문·전사문·rubric·LLM 응답을 새 파일, DB, Storage, 브라우저 로그, TTS 입력으로 보관하거나 전송하지 않는다.
- 새 환경 변수·비밀값을 추가하지 않는다. 기존 `LLM_FEEDBACK_ENABLED`, `LLM_FEEDBACK_OLLAMA_URL`, `LLM_FEEDBACK_MODEL`, `LLM_FEEDBACK_TIMEOUT_SECONDS`만 사용한다.

## AC

### AC-01 · 기본 질문 ID 통일

- **Given**: rubric JSON과 `OllamaQuestionRubricGenerator`
- **When**: `get_preset("preset-01")`을 호출함
- **Then**: `자기소개를 해주세요.` rubric을 반환하고 `get_preset("1")`은 `None`을 반환함

### AC-02 · LLM 비활성 폴백

- **Given**: `LLM_FEEDBACK_ENABLED=false`
- **When**: Backend가 persistent 분석 서비스를 준비함
- **Then**: generator는 `None`이며 분석 Job의 전달 방식 결과는 기존 경로로 완료됨

### AC-03 · LLM 활성 연결

- **Given**: `LLM_FEEDBACK_ENABLED=true`, 읽을 수 있는 rubric JSON, 준비된 로컬 Ollama 설정
- **When**: Backend가 persistent 분석 서비스를 준비함
- **Then**: 생성된 `OllamaQuestionRubricGenerator` 인스턴스가 `PersistentAnalysisJobService.question_feedback_generator`에 연결됨

### AC-04 · generator 초기화 실패

- **Given**: `LLM_FEEDBACK_ENABLED=true`이지만 rubric JSON을 읽지 못함
- **When**: Backend가 persistent 분석 서비스를 준비함
- **Then**: generator는 `None`이며 앱 시작과 전달 방식 분석 준비는 실패하지 않음

### AC-05 · 보관 경계

- **Given**: LLM 활성·비활성 어느 상태든
- **When**: 질문 피드백을 처리함
- **Then**: 이 기능 때문에 새 API endpoint, DB table, Storage object, 원문 로그, TTS 요청이 생성되지 않음
