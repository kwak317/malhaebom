# STT 동적 initial prompt

## Why

- **사용자 상황**: 사용자는 검수된 채용공고의 요구사항을 선택한 뒤 같은 연습 세션에서 면접 답변을 녹음한다.
- **문제**: 실사용 devset에서 기본 STT는 일반 한국어보다 영어 기술용어를 더 자주 놓쳤고, 고정 initial_prompt를 제공했을 때 core normalized CER/WER와 기술용어 recall이 개선됐다.
- **제약**: 고정 15개 기술용어를 제품 전체에 넣으면 공고와 무관한 bias가 생길 수 있고, 클라이언트가 prompt를 직접 정하게 하면 신뢰 경계가 불필요하게 넓어진다.
- **측정 지표**: 새 acceptance set에서 no-prompt 대비 core CER/WER 비악화, 기술용어 recall 개선, false insertion 증가 여부.

## Goal

- **해결 목표**: 사용자가 선택한 연습 세션의 검수 공고 문맥에서 기술용어를 서버가 동적으로 추출해 faster-whisper의 initial_prompt로 전달한다.
- **성공 기준**:
  1. prompt는 서버가 RLS 범위 안의 세션 문맥으로만 생성한다.
  2. 최대 12개 기술용어만 전달한다.
  3. context 조회 실패 또는 매칭 용어 없음이면 기존 no-prompt STT로 정상 fallback한다.
  4. 로그에 공고/요구사항/질문 원문과 완성 prompt를 남기지 않는다.
  5. 기존 local analysis와 no-prompt 호출 계약을 깨지 않는다.
- **Out of Scope**: GitHub/포트폴리오 데이터 수집 자체, LLM 기반 용어 추출, hotwords 병용, 모델 재학습, acceptance 녹음 결과 확정.

## What

**Happy Path**

1. 사용자가 공고와 1~2개 요구사항을 선택해 practice session을 만든다.
2. 녹음 분석 job이 해당 practice_session_id를 가진다.
3. 서버가 사용자 JWT/RLS 범위에서 custom question(있을 때), 공고 title, 선택 requirement text를 조회한다.
4. allowlist extractor가 실제 문맥에 등장한 기술용어를 최대 12개 선택한다.
5. initial_prompt를 생성해 FasterWhisperTranscriber에 전달한다.
6. faster-whisper가 기존 beam/language/VAD 조건과 함께 initial_prompt를 사용해 전사한다.

**Edge Cases**

| # | 상황 | 처리 방식 |
|---|---|---|
| EC-01 | 세션에 기술용어가 없음 | initial_prompt 없이 기존 STT 실행 |
| EC-02 | hint context REST 조회 실패 | 경고 로그 후 no-prompt STT로 fallback |
| EC-03 | 오래되거나 소유하지 않은 세션 | RLS/세션 조회 실패를 prompt 실패로만 처리하고 사용자 원문을 로그에 남기지 않음 |
| EC-04 | 기술용어가 12개 초과 | source text 등장 순서 기준 앞 12개만 선택 |
| EC-05 | Spring이 먼저 등장한 뒤 Spring Boot도 매칭 | 등장 순서와 무관하게 더 구체적인 Spring Boot를 우선하고 generic Spring 제외 |
| EC-06 | Git이 먼저 등장한 뒤 GitHub Actions도 매칭 | 등장 순서와 무관하게 더 구체적인 GitHub Actions를 우선하고 generic Git/GitHub 제외 |
| EC-07 | local analysis 또는 hint loader 없는 repository | 기존 2-argument transcribe 경로 유지 |

## How

입력 경계:

    practice_session_id
      → SupabaseAnalysisRepository.get_stt_hint_context()
      → build_stt_prompt_hints()
      → FasterWhisperTranscriber.transcribe(initial_prompt=...)
      → WhisperModel.transcribe(initial_prompt=...)

서버가 읽는 문맥:

- practice_sessions.custom_question_text
- job_postings.title
- practice_session_requirements → job_requirements.requirement_text

추출 구현:

- backend/app/services/stt_prompt_hints.py
- NFKC + case-insensitive alias matching
- 보수적 기술 스택 allowlist
- MAX_HINT_TERMS = 12
- 매칭 순서는 source text 내 첫 등장 위치 우선
- prompt prefix: "기술 면접 답변입니다. 다음 기술 용어가 등장할 수 있습니다:"

데이터/보안:

- 기존 사용자 JWT를 그대로 사용한다.
- job_postings / job_requirements / practice_sessions / practice_session_requirements의 기존 SELECT grant와 RLS를 재사용한다.
- service-role key를 사용하지 않는다.
- DB schema migration은 추가하지 않는다.
- 로그에는 추출 term 개수만 기록한다.

현재 포트폴리오/GitHub 문맥은 STT 처리 경로에 영속화되어 있지 않다. 이후 해당 소스가 추가되면 extractor의 context_texts 입력만 확장한다.

## AC (Given-When-Then)

**AC-01 · 공고 문맥 기술용어 prompt 생성**
- GIVEN: 소유한 practice session의 공고/선택 요구사항에 Python, FastAPI, Docker가 있다.
- WHEN: 녹음 STT를 시작한다.
- THEN: 서버가 해당 용어를 포함한 initial_prompt를 생성해 transcriber에 전달한다.

**AC-02 · 최대 용어 수 제한**
- GIVEN: 문맥에서 allowlist 기술용어가 12개를 초과해 매칭된다.
- WHEN: prompt를 생성한다.
- THEN: 최대 12개만 source 등장 순서에 따라 포함한다.

**AC-03 · 빈 문맥 fallback**
- GIVEN: 공고/질문/요구사항에 매칭되는 기술용어가 없다.
- WHEN: STT를 실행한다.
- THEN: initial_prompt를 전달하지 않고 기존 전사를 수행한다.

**AC-04 · context 조회 실패 fallback**
- GIVEN: Supabase context 조회가 KeyError 또는 persistence 오류로 실패한다.
- WHEN: STT를 실행한다.
- THEN: 분석 job 전체를 실패시키지 않고 no-prompt STT를 수행한다.

**AC-05 · 신뢰 경계 유지**
- GIVEN: 클라이언트가 analysis job을 생성한다.
- WHEN: STT hint가 필요하다.
- THEN: 클라이언트 요청에서 prompt 문자열을 받지 않고 practice_session_id로 서버가 문맥을 재조회한다.

**AC-06 · 관측 개인정보 제한**
- GIVEN: prompt가 생성된다.
- WHEN: 서버가 로그를 남긴다.
- THEN: 공고/질문/요구사항 원문이나 prompt 전체가 아니라 추출 term 개수만 로그에 남긴다.
