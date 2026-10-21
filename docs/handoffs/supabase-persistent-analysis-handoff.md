# Supabase 영속 분석 Job 인수인계

## 현재 적용 상태

- Supabase 프로젝트에 private `analysis-audio` 버킷과 `public.analysis_jobs` 테이블을 만들었다.
- DB와 Storage 정책은 인증 사용자가 자신의 UUID로 시작하는 경로와 자신의 Job만 다루도록 제한한다.
- 백엔드는 사용자의 Supabase JWT를 그대로 전달해 RLS가 적용된 상태로 업로드·조회·삭제한다.
- 만료 cleanup만 서버 전용 `SUPABASE_SERVICE_ROLE_KEY`를 사용한다. 이 값은 프런트·Git·로그에 절대 넣지 않는다.

## 로컬 백엔드 환경변수

`.env.example`을 참고해 로컬 `.env`에만 다음을 설정한다.

```text
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
SUPABASE_SERVICE_ROLE_KEY=sb_secret_...
```

`SUPABASE_SERVICE_ROLE_KEY`는 `backend/scripts/cleanup_expired_analysis_jobs.py` 실행 때만 필요하다.

## 만료 cleanup 수동 실행과 스케줄

```powershell
$env:SUPABASE_URL = "https://your-project-ref.supabase.co"
$env:SUPABASE_PUBLISHABLE_KEY = "sb_publishable_..."
$env:SUPABASE_SERVICE_ROLE_KEY = "sb_secret_..."
python backend/scripts/cleanup_expired_analysis_jobs.py
```

Windows 작업 스케줄러에서 위 스크립트를 **매시간** 실행하도록 수동 등록한다. 코드가 작업 스케줄러를 자동으로 생성하지는 않는다. 종료 코드 `0`은 모두 삭제 성공 또는 대상 없음, `1`은 다음 실행에서 재시도할 삭제 실패가 있었음을 뜻한다.

## 검증 경계

- 단위 테스트는 JWT 전달, owner-only API 응답, Storage-first 삭제, DB 실패 보상, cleanup 재시도를 검증한다.
- 실제 Supabase에서 임시 사용자 두 명으로 DB·Storage 교차 접근 차단과 테스트 데이터 삭제를 확인했다. 실제 만료 시각을 지난 Job을 cleanup 스크립트로 삭제하는 운영 환경 검증은 별도로 수행한다.
