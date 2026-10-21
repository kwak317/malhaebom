# Supabase 연습 기록 조회 Spec

> 이 Spec은 기존 `analysis_jobs`에 저장된 24시간 이내 분석 결과를 연습 기록 화면에서 안전하게 조회·삭제하기 위한 계약이다. 새 장기 보관 테이블이나 사용자 음성 재사용을 추가하지 않는다.

## Why

- **페르소나**: Google 로그인 뒤 면접 답변을 녹음하고, 같은 질문의 1차·2차 연습 결과를 다시 확인하려는 취업준비생
- **상황**: 분석 Job과 원본 음성은 Supabase에 저장되지만, 현재 연습 기록 화면은 mock 데이터만 표시한다.
- **문제**: 사용자가 실제 자신의 완료된 연습 결과를 목록·결과·상세 화면에서 볼 수 없고, 필요할 때 직접 삭제할 수도 없다.
- **측정 지표**: 본인 완료 연습 세션 조회 성공, 다른 사용자의 세션 조회·삭제 0건, 삭제한 세션의 DB 행과 원본 음성 재조회 0건, 만료 후 목록 노출 0건.

## Goal

- 인증된 사용자는 생성 후 24시간이 지나지 않은 자신의 완료된 연습 세션을 최신순으로 조회할 수 있다.
- 같은 `practice_session_id`의 1차·2차 시도는 목록에서 하나의 연습 기록으로 표시하고, 상세에서 전후 지표를 비교할 수 있다.
- 사용자는 자신의 연습 세션 하나 또는 현재 목록의 모든 연습 기록을 삭제할 수 있다.
- **Out of Scope**: 24시간을 넘는 장기 기록·추세 분석, 새 `practice_records` 테이블, 원본 음성 재생·다운로드, 브라우저의 Supabase DB·Storage 직접 접근, 익명 사용자 기록, TTS·STT 모델 변경, cleanup scheduler 등록.

## What

### Happy Path

1. 로그인 사용자가 연습 기록 화면을 연다.
2. 프런트엔드는 Bearer JWT로 `GET /practice-records`를 호출한다.
3. 백엔드는 요청자 권한으로 만료되지 않은 `status=completed` `analysis_jobs`만 조회하고 `practice_session_id`별로 묶는다.
4. 백엔드는 최신 완료 시각 기준 최대 50개 세션의 질문 메타데이터, 시도별 전사문·전달력 지표·피드백만 반환한다.
5. 프런트엔드는 preset 질문 ID를 기존 기본 질문 목록의 문구로 표시하고, custom 질문은 저장된 사용자 질문 원문을 표시한다.
6. 사용자가 기록을 선택하면 프런트엔드는 `GET /practice-records/{practice_session_id}`를 호출해 최신 세션 데이터를 결과·상세 화면에 표시한다.
7. 사용자가 세션 삭제를 확인하면 프런트엔드는 `DELETE /practice-records/{practice_session_id}`를 호출한다. 백엔드는 연결된 원본 음성을 모두 먼저 삭제하고, 성공한 뒤 해당 세션의 DB 행을 모두 삭제한다.
8. 사용자가 전체 삭제를 확인하면 프런트엔드는 `DELETE /practice-records`를 호출하고, 백엔드는 요청자 자신의 현재 기록만 같은 방식으로 삭제한다.

### Edge Case

| 상황 | 처리 방식 |
| --- | --- |
| Authorization 헤더가 없거나 토큰이 만료됨 | 모든 연습 기록 API는 `401`을 반환하고 프런트엔드는 로그인 안내를 표시한다. |
| 목록에 완료 Job이 없음 | `200`과 빈 배열을 반환하고 프런트엔드는 빈 상태를 표시한다. |
| Job이 `queued`, `processing`, `failed` 상태 | 목록·상세에 포함하지 않는다. 분석 화면의 기존 polling 처리만 유지한다. |
| 다른 사용자의 `practice_session_id` 조회·삭제 | 존재 여부를 드러내지 않고 `404`를 반환한다. |
| 삭제 중 한 원본 음성 삭제가 실패함 | DB 행은 하나도 삭제하지 않고 안전한 `503`을 반환한다. 이미 삭제된 객체는 다음 삭제에서 없는 객체로 허용해 재시도한다. |
| 만료 cleanup과 사용자의 삭제가 동시에 실행됨 | 이미 없어진 행·객체는 삭제 완료로 취급하고, 사용자 화면은 다음 목록 조회에서 해당 세션을 제거한다. |
| preset 질문 ID가 프런트엔드 기본 질문 목록에 없음 | 질문 문구 대신 `기본 면접 질문`을 표시하며, 분석·삭제·권한 처리는 계속한다. |
| 응답이 50개를 초과함 | 최신 50개만 반환한다. 24시간 제한 안의 추가 페이지 조회는 이번 범위에 포함하지 않는다. |

## How

### 데이터와 보관 경계

- 기존 `public.analysis_jobs`만 사용한다. 새 테이블·새 Storage 버킷은 만들지 않는다.
- 조회 대상은 요청자 자신의 `expires_at > now()` 그리고 `status = 'completed'` 행이다.
- 목록의 한 항목은 동일한 `practice_session_id`를 공유하는 attempt 1과 선택적 attempt 2로 구성한다.
- 목록·상세 API 응답에는 `audio_path`, `audio_content_type`, `user_id`, Storage URL, 원본 음성 bytes, 내부 `cleanup_error_code`를 포함하지 않는다.
- 사용자 질문 원문·전사문·분석 결과는 기존 정책대로 해당 사용자에게만 24시간 이내에 노출한다. 만료 cleanup은 기존 `cleanup_expired_analysis_jobs.py` 계약을 변경하지 않는다.
- 코치 스트림은 요청 연결·서버 메모리에서만 처리하며 세션 데이터·WAV·TTS 메타데이터를 남기지 않는다. 사용자 직접 질문의 요청별 TTS WAV는 `question_tts_audio`에서 독립적으로 24시간 정리되며 현재 `practice_session_id`가 없으므로, 연습 기록 삭제 API가 그 WAV를 세션 단위로 삭제하지 않는다.

### API 계약

```
GET /practice-records
인증: Authorization: Bearer <Supabase access token>

성공 200:
{
  "records": [
    {
      "practice_session_id": "uuid",
      "question_type": "preset" | "custom",
      "question_id": "string | null",
      "custom_question_text": "string | null",
      "practiced_at": "ISO 8601",
      "attempts": [
        {
          "attempt_no": 1 | 2,
          "job_id": "uuid",
          "transcript": "string",
          "metrics": {
            "cpm": "number | null",
            "long_silence_count": "number",
            "repetition_count": "number"
          },
          "feedback": ["string", "string"]
        }
      ]
    }
  ]
}

GET /practice-records/{practice_session_id}
인증: Authorization: Bearer <Supabase access token>
성공 200: 목록의 records 항목 한 개와 같은 구조
실패: 401 인증 없음·만료, 404 본인 완료 기록 없음, 503 저장소 조회 실패

DELETE /practice-records/{practice_session_id}
인증: Authorization: Bearer <Supabase access token>
성공 204: 본인 세션의 Storage 객체와 DB 행 모두 삭제
실패: 401 인증 없음·만료, 404 본인 기록 없음, 503 삭제 재시도 가능 오류

DELETE /practice-records
인증: Authorization: Bearer <Supabase access token>
성공 204: 요청자의 현재 완료 기록만 모두 삭제
실패: 401 인증 없음·만료, 503 일부 Storage 삭제 오류로 재시도 필요
```

- 기존 `POST /analysis-jobs`, `GET /analysis-jobs/{job_id}`, `DELETE /analysis-jobs/{job_id}` 계약은 변경하지 않는다.
- 백엔드 Repository는 사용자 access token을 Supabase REST·Storage 호출에 전달해 기존 RLS 범위를 유지한다. `SUPABASE_SERVICE_ROLE_KEY`는 cleanup 이외의 조회·사용자 삭제에 사용하지 않는다.
- 새 migration에는 `analysis_jobs`의 완료 기록 조회를 위한 partial index `analysis_jobs_history_lookup_idx (user_id, completed_at desc) where status = 'completed'`만 추가한다. 기존 테이블·RLS 정책·Storage 정책은 수정하지 않는다. migration 파일명은 Supabase CLI로 생성하고, 원격 적용은 Supabase 운영 담당자가 PR 병합 뒤 수행한다.
- 프런트엔드는 기존 `PracticeHistoryItem` mock type을 실제 API 응답용 타입·매퍼로 교체한다. 네트워크 오류에는 기존 오류 상태 문구와 재시도 버튼을 사용한다.

## AC (Given-When-Then)

**AC-01 · 본인 완료 기록 목록 조회**
- GIVEN: 인증 사용자에게 만료되지 않은 완료 Job 1개와 다른 사용자의 완료 Job 1개가 있다.
- WHEN: 사용자가 `GET /practice-records`를 호출한다.
- THEN: 응답에는 자신의 세션만 포함되고 다른 사용자의 질문·전사문·지표는 포함되지 않는다.

**AC-02 · 1차·2차 시도 묶기**
- GIVEN: 같은 `practice_session_id`의 완료된 attempt 1과 attempt 2가 있다.
- WHEN: 사용자가 목록 또는 해당 세션 상세를 조회한다.
- THEN: 하나의 record에 attempt 1·2가 번호 오름차순으로 포함되고 두 시도의 전사문·CPM·긴 침묵 수·반복 표현 수가 반환된다.

**AC-03 · 1차만 완료된 기록**
- GIVEN: attempt 1만 `completed`이고 attempt 2는 없거나 `processing`이다.
- WHEN: 사용자가 목록을 조회한다.
- THEN: 한 개의 attempt만 가진 record가 반환되며 processing Job은 노출되지 않는다.

**AC-04 · 만료·실패 Job 제외**
- GIVEN: 요청자에게 만료된 completed Job, failed Job, queued Job이 있다.
- WHEN: 사용자가 목록을 조회한다.
- THEN: 세 Job 모두 응답에 포함되지 않는다.

**AC-05 · 다른 사용자 세션 보호**
- GIVEN: 사용자 A가 소유한 `practice_session_id`를 사용자 B가 안다.
- WHEN: 사용자 B가 해당 세션 상세 조회 또는 삭제를 요청한다.
- THEN: API는 `404`를 반환하고 사용자 A의 DB 행·Storage 객체는 변경되지 않는다.

**AC-06 · 세션 삭제 순서**
- GIVEN: 요청자 자신의 한 세션에 attempt 1·2 원본 음성과 DB 행이 있다.
- WHEN: 사용자가 해당 세션 삭제를 요청하고 Storage 삭제가 성공한다.
- THEN: 두 Storage 객체가 먼저 삭제되고 DB 행 두 개가 삭제되며 이후 세션 조회는 `404`다.

**AC-07 · 삭제 실패 재시도**
- GIVEN: 세션 삭제 중 두 번째 Storage 객체 삭제가 실패한다.
- WHEN: 삭제 요청이 끝난다.
- THEN: 어떤 DB 행도 삭제하지 않고 `503`을 반환하며, 같은 요청을 재시도하면 이미 없는 첫 번째 객체를 허용하고 삭제를 계속한다.

**AC-08 · 프런트엔드 실제 연결**
- GIVEN: 로그인 사용자가 실제 API가 설정된 앱에서 연습 기록 화면을 연다.
- WHEN: 목록 API가 성공한다.
- THEN: mock 데이터가 아니라 API 응답의 질문·일시·상태·지표가 표시되고, 빈 배열이면 빈 상태가 표시된다.

**AC-09 · 24시간 보관 경계**
- GIVEN: 한 세션의 모든 Job `expires_at`이 지났다.
- WHEN: 기존 cleanup이 실행되고 사용자가 목록을 새로고침한다.
- THEN: 해당 세션은 목록·상세에 나타나지 않고 원본 음성·DB 행도 남아 있지 않다.
