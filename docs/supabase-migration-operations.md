# Supabase migration 운영 방침

## 실행·저장 경계

- 발표·개발 환경에서 FastAPI, STT, VAD, cleanup은 각 담당자의 로컬 노트북에서 실행한다.
- 로그인 사용자, 분석 Job, 분석 결과, 원본 음성은 Supabase Auth·Database·private Storage에 저장한다.
- 사용자 입력 질문으로 생성한 TTS WAV와 최소 메타데이터도 private Storage·Database에 저장하며, 질문 원문은 저장하지 않는다.
- 원본 음성과 질문 TTS WAV는 사용자 삭제 또는 24시간 만료 cleanup 전까지만 보관한다.
- `.env`, 사용자 JWT, Publishable/Secret key, 음성·전사문·모델 파일은 Git에 올리지 않는다.

## 변경 원칙

1. DB 테이블·RLS·Storage 버킷·정책 변경은 먼저 `supabase/migrations/`의 새 migration 파일로 기록한다.
2. 원격 Supabase 반영은 담당자가 연결된 Supabase CLI에서 `supabase db push`로 수행한다.
3. Dashboard SQL Editor는 조회·점검용을 우선한다. 긴급하게 SQL Editor로 구조 변경을 했다면, 같은 담당자가 즉시 CLI migration history를 실제 상태와 맞춘다.
4. migration history를 맞추기 위한 CLI 계정 인증은 담당자 개인 Supabase Access Token 또는 DB password로 한다. 프로젝트 Publishable key·Secret key·사용자 JWT를 CLI 인증에 재사용하지 않는다.
5. 원격 적용 전에는 생성·변경 대상과 rollback 또는 복구 방법을 PR에 기록하고, 적용 뒤에는 RLS·Storage owner isolation을 실제 사용자 두 명으로 검증한다.

## 현재 프로젝트 상태

- `20260819022119_persistent_analysis_jobs.sql`은 `malhaebom-local` Dashboard SQL Editor로 적용됐다.
- `20260819090000_question_tts_audio.sql`은 PR 검토 뒤 Supabase 운영 담당자가 CLI로 적용할 예정이다. 적용 전에는 `question-tts-audio` bucket이나 `question_tts_audio` table이 원격에 있다고 가정하지 않는다.
- `20260824064309_practice_history_lookup.sql`은 연습 기록 조회용 partial index만 추가하는 PR 대상 migration이다. 원격 적용 전에는 index가 있다고 가정하지 않으며, 운영 담당자가 history를 확인한 뒤 한 번만 적용한다.
- 원격 프로젝트에는 아직 CLI migration history 운영이 시작되지 않았다.
- 팀이 처음 CLI를 연결할 때, 이미 적용된 migration을 중복 실행하지 않도록 history를 확인하고 `migration repair` 적용 여부를 담당자와 합의한다.

## 책임 경계

| 역할 | 담당 |
| --- | --- |
| 백엔드 담당 | migration SQL, API·RLS·Storage contract, 테스트 증적 |
| Supabase 운영 담당 1명 | CLI 연결, 원격 apply, migration history 관리 |
| 프론트엔드 담당 | Publishable key와 사용자 JWT를 사용한 API 호출; DB migration·Secret key 사용 금지 |
