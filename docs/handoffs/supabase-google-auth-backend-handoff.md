# Supabase Google 로그인 · 백엔드 인증 연동 인수인계

작성일: 2026-08-19
대상: 말해봄 Backend · Frontend 협업자

## 1. 이 작업의 목적

`말해봄`의 분석 API를 로그인 사용자만 호출하도록 보호한다. 사용자의 Google 계정 로그인은 Supabase Auth가 담당하고, FastAPI는 Supabase access token을 검증한다.

이 문서는 JWT 인증 단계의 인수인계 기록이다. 이후 영속 저장 구현으로 최신 실행·저장 계약은 [Supabase 영속 분석 Job 인수인계](supabase-persistent-analysis-handoff.md)를 따른다.

> 현재 상태: 프런트 Google 로그인과 access token 기반 분석·기록 API 호출 코드는 구현됐다. 실제 팀 Supabase의 Google OAuth 설정으로 브라우저 통합 검증하는 일은 환경 권한이 필요한 별도 단계다.

## 2. 현재 완료된 범위

| 영역 | 상태 | 내용 |
| --- | --- | --- |
| Supabase Project | 수동 설정 완료 | 팀용 Supabase 프로젝트 생성 |
| Google Provider | 수동 설정 완료 | Google OAuth Client ID/Secret을 Supabase Google Provider에 등록, 로컬 Redirect URL 설정 |
| FastAPI JWT 검증 | 구현 완료 | Supabase JWKS로 JWT 서명·issuer·audience·만료·`sub`를 검증 |
| 분석 Job 보호 | 구현 완료 | `POST /analysis-jobs`, `GET /analysis-jobs/{job_id}` 모두 Bearer token 필수 |
| Job 소유자 분리 | 구현 완료 | 생성한 사용자만 자신의 메모리 Job을 조회, 다른 사용자는 `404` |
| CORS | 구현 완료 | 로컬 기본 Origin 또는 `CORS_ALLOWED_ORIGINS`에 지정한 배포 Origin만 허용 |
| DB/Storage/RLS | 후속 구현 완료 | `analysis_jobs`, private `analysis-audio`, owner-only RLS는 영속 저장 인수인계 참고 |
| 프론트 로그인 화면 | 구현 완료 | Supabase Google OAuth 세션과 로그인·로그아웃 화면 연결 |

## 3. 백엔드 실행 설정

실제 Project URL은 Git에 기록하지 않는다. 백엔드 실행 터미널에서만 설정한다.

```powershell
$env:SUPABASE_URL = "https://your-project-ref.supabase.co"
python -m uvicorn app.main:app --app-dir backend --reload
```

- `SUPABASE_URL`: 백엔드 JWT 검증용 Project URL
- 사용 금지: `sb_secret_...`, service role key, Google Client Secret을 코드·로그·Git에 기록하는 행위
- `.env.example`은 변수명과 예시 URL만 제공하며 실제 비밀값 저장소가 아니다.

## 4. 프론트엔드 연결 계약

프론트엔드는 Supabase Google 로그인 성공 후 세션의 access token을 얻는다. 분석 API 호출 때마다 다음 헤더를 붙인다.

```http
Authorization: Bearer <Supabase access token>
```

| 요청 | 성공 조건 | 인증 실패 |
| --- | --- | --- |
| `POST /analysis-jobs` | 유효 token + 기존 음성 검증 통과 | `401`, Job 미생성 |
| `GET /analysis-jobs/{job_id}` | 유효 token + Job 생성자와 동일 사용자 | `401` 또는 다른 사용자면 `404` |

프런트는 Google 로그인 세션의 access token을 분석·연습 기록 API에 전달한다. 자동 테스트는 서명된 테스트 JWT와 가짜 JWKS 클라이언트로 백엔드 검증 경로를 확인하며, 실제 팀 OAuth 계정의 브라우저 통합 검증은 별도로 수행한다.

## 5. 오류 응답

인증 헤더가 없거나, 형식이 잘못됐거나, 만료·위조·검증 실패 토큰이면 다음 응답을 반환한다.

```json
{
  "detail": {
    "code": "UNAUTHORIZED",
    "message": "로그인이 필요하거나 세션이 만료되었습니다."
  }
}
```

HTTP status는 `401 Unauthorized`다. JWT 원문·내부 검증 오류·로컬 파일 경로는 응답에 포함하지 않는다.

## 6. 관련 코드와 검증

| 파일 | 역할 |
| --- | --- |
| `backend/app/core/auth.py` | Supabase JWT verifier와 FastAPI 인증 의존성 |
| `backend/app/main.py` | 인증 의존성, CORS, API 라우트 연결 |
| `backend/app/services/local_analysis_jobs.py` | 메모리 Job의 `user_id` 소유자 확인 |
| `backend/tests/test_auth.py` | 유효·만료·issuer 오류·`sub` 누락 JWT 검증 테스트 |
| `backend/tests/test_local_analysis_api.py` | 401, Job 소유자 404, CORS API 테스트 |
| `docs/specs/supabase-google-auth.md` | 인증 기능 Spec |

전체 백엔드 검증은 `python -m unittest discover -s backend/tests -v`로 실행한다. 이 문서에 과거 테스트 개수를 고정하지 않고 현재 CI·PR 결과를 기준으로 확인한다.

## 7. 당시 다음 백엔드 작업 (완료 기록)

1. 인증 PR 병합 후 새 브랜치에서 Supabase DB·비공개 Storage·RLS를 구현한다.
2. 녹음·전사문·분석 결과를 사용자 ID 기준으로 저장하고, 24시간 자동 삭제와 사용자 즉시 삭제를 적용한다.
3. 메모리 기반 Job을 영속 Job으로 교체하고, 질문·attempt·전후 비교·기록 조회/삭제 API를 추가한다.

TTS는 검수된 사전 생성 WAV만 연결하며, 사용자 음성을 TTS 입력·Voice Cloning·추가 학습에 사용하지 않는다.
