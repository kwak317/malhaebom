# Supabase 분석 Job 영속 저장 Spec

> 이 Spec은 첫 구현 계약이다. STT 모델·응답 구조·보관 정책이 바뀌면 기존 데이터를 임의로 덮어쓰지 않고, 새 migration과 이 Spec 갱신을 함께 적용한다.

## Why

- **페르소나**: Google 로그인 후 면접 답변을 녹음하고, 분석 결과와 재연습을 확인하려는 취업준비생
- **상황**: 현재 FastAPI 분석 Job은 메모리에만 있어 서버 재시작 뒤 사라지고, 사용자 음성의 저장·삭제 경계가 없다.
- **문제**: 로그인 사용자의 음성·전사문·분석 결과를 사용자별로 비공개 저장하고, 24시간 뒤 안전하게 삭제할 영속 계층이 필요하다.
- **측정 지표**: 다른 사용자의 DB 행·Storage 객체 조회/삭제 0건, 만료 Job의 DB 행과 Storage 객체 모두 삭제, 사용자 직접 삭제 뒤 관련 데이터 조회 0건.

## Goal

- 유효한 Supabase JWT를 가진 사용자만 자신의 음성·분석 Job을 비공개 Storage와 DB에 생성·조회·삭제할 수 있다.
- 기존 `POST /analysis-jobs`, `GET /analysis-jobs/{job_id}`가 영속 `analysis_jobs` 레코드를 사용하도록 교체하고, 질문·재녹음 비교에 필요한 최소 메타데이터를 함께 저장한다.
- 생성 후 24시간이 지나면 cleanup 작업이 Storage API로 원본 음성을 삭제하고 DB Job을 제거한다.
- **Out of Scope**: 프론트엔드 코드, 직접 브라우저 Storage 업로드, 로그인 UI, TTS 런타임 합성, 사용자 음성 학습·Voice Cloning, 장기 기록·추세 분석, 배포 환경의 scheduler 구성.

## What

### Happy Path

1. 인증된 사용자가 유효한 5~60초 음성과 `question_type`, `attempt_no`를 `POST /analysis-jobs`로 보낸다.
2. `preset`이면 `question_id`를, `custom`이면 공백 제외 1~200자의 `custom_question_text`를 함께 검증한다.
3. 백엔드는 기존 형식·크기·길이 검증을 통과시킨 뒤, 사용자 ID와 새 Job ID로 Storage 경로를 만든다.
4. 백엔드는 요청자의 access token으로 비공개 `analysis-audio` 버킷에 원본 음성을 업로드하고 `analysis_jobs` 행을 `queued`로 만든다.
5. 기존 STT → VAD → 전달력 분석이 완료되면 `result`, `delivery`, `completed_at`, `status=completed`를 같은 Job에 기록한다.
6. 사용자는 자기 Job만 `GET /analysis-jobs/{job_id}`로 조회한다.
7. 사용자가 `DELETE /analysis-jobs/{job_id}`를 요청하면 Storage API로 음성을 먼저 삭제한 뒤 DB 행을 삭제한다.
8. 만료 cleanup은 1시간마다 24시간이 지난 Job을 같은 순서로 삭제한다.

### Edge Case

| 상황 | 처리 방식 |
| --- | --- |
| Storage 업로드 실패 | DB Job을 만들지 않고 기존 업로드 오류 안내를 반환한다. |
| DB 행 생성 실패 | Storage API로 방금 업로드한 객체를 삭제한 뒤 오류를 반환한다. |
| `preset`에 `question_id`가 없음 | Storage 저장과 STT 호출 없이 `422`를 반환한다. |
| `custom`에 질문이 없거나 200자를 초과함 | Storage 저장과 STT 호출 없이 `422`를 반환한다. |
| 동일 `practice_session_id`에서 attempt 2가 attempt 1과 다른 질문임 | Storage 저장과 STT 호출 없이 `422`를 반환한다. |
| 분석 실패 | 원본 음성과 Job은 만료 시각까지 유지하고 `failed`와 안전한 오류만 저장한다. |
| 다른 사용자의 Job 조회·삭제 | 존재 여부를 노출하지 않고 `404`를 반환한다. |
| 사용자 직접 삭제 중 Storage 삭제 실패 | DB 행을 유지하고 오류를 반환해 다음 삭제 요청에서 재시도한다. |
| 자동 cleanup 중 삭제 실패 | DB 행을 유지하고 `cleanup_attempted_at`, `cleanup_error_code`만 갱신해 다음 실행에서 재시도한다. |
| Storage 객체는 삭제됐지만 DB 삭제 실패 | 다음 cleanup에서 객체 없음은 삭제 완료로 취급하고 DB 행 삭제를 재시도한다. |

## How

### 데이터 구조

`public.analysis_jobs`:

| 필드 | 타입 | 제약·용도 |
| --- | --- | --- |
| `id` | uuid | primary key, 서버 생성 |
| `user_id` | uuid | `auth.users(id)` 참조, null 불가 |
| `source_id` | text | 기존 요청 식별자, null 불가 |
| `practice_session_id` | uuid | 같은 질문의 1·2차 시도를 연결하는 서버 생성 ID |
| `question_type` | text | `preset` 또는 `custom`, null 불가 |
| `question_id` | text | `preset`일 때 null 불가, `custom`이면 null |
| `custom_question_text` | text | `custom`일 때 공백 제외 1~200자, `preset`이면 null |
| `attempt_no` | smallint | `1` 또는 `2`, null 불가 |
| `audio_path` | text | `user_id/id/original.<extension>`, null 불가 |
| `audio_content_type` | text | 허용된 audio MIME type |
| `status` | text | `queued`, `processing`, `completed`, `failed` 중 하나 |
| `result` | jsonb | 기존 STT 응답, 완료 전 null 가능 |
| `delivery` | jsonb | 기존 전달력 분석 응답, 완료 전 null 가능 |
| `error` | jsonb | 사용자 노출 가능한 code/message만 저장 |
| `created_at` | timestamptz | 기본값 `now()` |
| `completed_at` | timestamptz | 완료 시각, null 가능 |
| `expires_at` | timestamptz | `created_at + interval '24 hours'` |
| `cleanup_attempted_at` | timestamptz | cleanup 마지막 시도, null 가능 |
| `cleanup_error_code` | text | 안전한 내부 오류 코드, null 가능 |

Storage 버킷 `analysis-audio`은 private으로 생성한다. 객체 경로 첫 조각은 반드시 `user_id`이고, 두 번째 조각은 Job ID다.

DB 제약:

- `question_type in ('preset', 'custom')`
- `attempt_no in (1, 2)`
- `question_type='preset'`이면 `question_id`는 null이 아니고 `custom_question_text`는 null이다.
- `question_type='custom'`이면 `question_id`는 null이고 `custom_question_text`는 공백 제거 뒤 1~200자다.
- `(user_id, practice_session_id, attempt_no)`는 unique다.

### 권한과 RLS

- `analysis_jobs`는 RLS를 활성화한다. `anon`에는 모든 권한을 부여하지 않는다.
- `authenticated`는 `user_id = auth.uid()`인 행만 SELECT·INSERT·UPDATE·DELETE한다. INSERT와 UPDATE에는 `WITH CHECK`도 같은 조건으로 둔다.
- `storage.objects` 정책은 `bucket_id = 'analysis-audio'`와 `(storage.foldername(name))[1] = auth.uid()::text`를 모두 확인한다.
- 일반 분석 API·사용자 삭제 API는 요청자의 access token을 Supabase API에 전달한다. 프런트에서 전달한 user ID, user metadata, Storage 경로를 권한 판단에 사용하지 않는다.
- 24시간 cleanup만 로컬 백엔드의 `SUPABASE_SERVICE_ROLE_KEY`로 Storage API와 DB를 정리한다. 키는 `.env`에만 두며 프런트·Git·로그에 포함하지 않는다.

### API와 처리 경계

- `POST /analysis-jobs`: 기존 multipart 입력과 `Authorization: Bearer <token>`을 유지한다. 성공 응답은 기존 Job 형식을 유지한다.
- `POST /analysis-jobs`의 multipart에는 `source_id`, `question_type`, `attempt_no`, `audio`가 필수다. `preset`은 `question_id`를, `custom`은 `custom_question_text`를 추가로 요구한다. attempt 1은 `practice_session_id`를 생략하면 서버가 생성하고, attempt 2는 attempt 1이 반환한 값을 필수로 보낸다.
- `GET /analysis-jobs/{job_id}`: 인증 사용자 자신의 영속 Job만 반환한다.
- `DELETE /analysis-jobs/{job_id}`: 인증 사용자 자신의 Storage 객체를 삭제한 뒤 DB 행을 삭제한다. 성공 시 `204 No Content`를 반환한다.
- cleanup은 `backend/scripts/cleanup_expired_analysis_jobs.py`로 제공하며, Windows 작업 스케줄러에서 매시간 실행한다. 자동 실행 등록 자체는 문서화만 하고 코드가 임의로 OS 작업을 만들지 않는다.
- 기존 로컬 임시 음성은 분석이 끝난 직후 삭제한다. Storage의 원본 음성은 직접 삭제 또는 cleanup 전까지 유지한다.

### 변경 가능성

- STT·VAD 결과는 `result`, `delivery` JSON으로 저장하므로 모델 출력의 추가 필드는 migration 없이 수용할 수 있다.
- status enum, 보관 기간, 비교용 지표 정규화 테이블은 후속 요구가 확정되면 새 migration과 API Spec으로 추가한다.
- 현재 한 Job은 한 원본 음성과 한 분석 결과만 가진다. `practice_session_id`와 `attempt_no`는 재녹음 전후 비교를 위한 연결 키이며, 비교 응답과 기록 목록 API는 다음 기능 Spec에서 추가한다.

## AC

- **Given**: 유효한 JWT와 5~60초의 허용 음성이 있다. **When**: 사용자가 `POST /analysis-jobs`를 요청한다. **Then**: 본인 경로의 private Storage 객체와 `analysis_jobs` 행이 생성되고 Job이 반환된다.
- **Given**: `question_type=preset`과 `question_id`, attempt 1이 있다. **When**: 사용자가 분석을 요청한다. **Then**: 서버가 `practice_session_id`를 만들고 `attempt_no=1` Job에 저장한다.
- **Given**: attempt 1과 동일 질문의 `practice_session_id`, `attempt_no=2`가 있다. **When**: 사용자가 재녹음 분석을 요청한다. **Then**: 같은 session의 두 Job이 저장되어 이후 비교 대상이 된다.
- **Given**: custom 질문이 공백만 있거나 200자를 초과한다. **When**: 사용자가 분석을 요청한다. **Then**: Storage 저장·STT 호출·Job 생성 없이 `422`를 반환한다.
- **Given**: 다른 사용자의 Job ID가 있다. **When**: 조회 또는 삭제를 요청한다. **Then**: `404`를 반환하며 DB 행·Storage 객체는 변경되지 않는다.
- **Given**: 분석이 완료됐다. **When**: 같은 사용자가 Job을 조회한다. **Then**: 기존 응답 모양의 `result`, `delivery`, `status=completed`가 반환된다.
- **Given**: 사용자가 자기 Job 삭제를 요청한다. **When**: Storage 객체 삭제가 성공한다. **Then**: DB 행도 삭제되고 이후 조회는 `404`다.
- **Given**: Job의 `expires_at`이 지났다. **When**: cleanup 작업이 실행된다. **Then**: Storage API로 원본 객체를 삭제한 뒤 DB 행을 삭제한다.
- **Given**: cleanup의 Storage 또는 DB 삭제가 실패한다. **When**: 작업이 끝난다. **Then**: 재시도 가능한 DB 행을 남기고 음성 원문·JWT·서비스 키를 로그에 남기지 않는다.
- **Given**: Supabase SQL migration이 적용됐다. **When**: RLS 검증을 한다. **Then**: `anon`은 접근하지 못하고, 두 인증 사용자 간 DB 행·Storage 객체 교차 접근은 거부된다.
