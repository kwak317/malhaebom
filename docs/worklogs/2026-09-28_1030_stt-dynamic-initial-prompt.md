# 2026-09-28 STT 동적 initial prompt 연동

## 목적

고정 기술용어 A/B에서 선택한 initial_prompt 전략을 실제 연습 세션의 공고 문맥으로 생성하도록 연결한다.

## 선행 근거

30건 dev/diagnostic A/B:

- none: core normalized CER 3.29%, WER 6.63%, hint term recall 82.35%
- initial_prompt: core normalized CER 2.44%, WER 5.27%, hint term recall 94.12%
- hotwords: core normalized CER 3.64%, WER 6.12%, hint term recall 94.12%
- initial_prompt / hotwords false insertion: 0

initial_prompt가 core와 기술 질문에서 가장 균형 잡힌 결과를 보여 다음 서비스 후보로 사용했다.

## 구현

- `stt_prompt_hints.py`
  - 기술용어 allowlist 기반 extractor
  - 최대 12개
  - 공고/요구사항/질문에서 실제 등장한 용어만 선택
  - source 등장 순서와 무관하게 Spring Boot/GitHub Actions 같은 specific term을 generic term보다 우선
  - 매칭이 없으면 prompt 없음
- `SupabaseAnalysisRepository.get_stt_hint_context()`
  - practice session 소유권/RLS 경계에서 custom question, job title, selected requirement text 조회
- `PersistentAnalysisJobService`
  - STT 직전에 context를 읽고 initial_prompt 생성
  - context 조회 실패 시 no-prompt STT로 fallback
- `FasterWhisperTranscriber`
  - optional kw-only initial_prompt를 faster-whisper에 전달

## 보안/관측

- 클라이언트가 prompt 문자열을 직접 결정하지 않는다.
- 기존 사용자 JWT와 RLS를 유지한다.
- service-role 우회 없음.
- 원문 prompt는 로그에 남기지 않고 추출 term 개수만 기록한다.
- 기존 public table grant/RLS를 사용하므로 schema migration 없음.

## 검증

- `test_stt_prompt_hints.py`: 5 tests PASS
- `test_stt_transcriber.py`: 5 tests PASS
- `test_supabase_persistence.py`: PASS (project runtime)
- `test_persistent_analysis_api.py`: PASS (project runtime + repository root import path)
- `test_local_analysis_jobs.py`: PASS
- 기존 prompt A/B / matrix / spoken-form scorer 테스트도 직전 단계에서 PASS

## 다음 작업

- 실제 검수 공고를 사용한 E2E에서 추출 term과 전사 결과를 확인한다.
- GitHub/포트폴리오 문맥이 서비스 데이터 경로에 추가되면 extractor 입력을 확장한다.
- 고정 30건 devset에서 추가 prompt 튜닝은 하지 않는다.
- 최종 후보는 새 미공개 acceptance 녹음셋에서 검증한다.

## 2026-09-28 PR #73 main 병합 충돌 해결

- `backend/app/services/stt_transcriber.py`의 충돌에서 main의 모델 lock·warmup과 #73의 optional `initial_prompt` 인자를 함께 유지했다.
- `/tmp/proj2-3-merge-conda/bin/python -m unittest backend.tests.test_stt_transcriber backend.tests.test_stt_prompt_hints backend.tests.test_stt_real_user_prompt_ab -q`: 16개 통과.
- 전체 백엔드 suite 337개 중 `test_isolated_provider_failure_returns_without_cost` 1개는 1초 제한에서 timeout으로 실패했다. 동일 Python 3.12 환경의 변경 전 main에서도 재현했다.
