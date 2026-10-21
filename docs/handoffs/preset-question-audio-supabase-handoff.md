# 기본 질문 WAV · Supabase 연결 인수인계

작성일: 2026-08-24
대상: Supabase 운영 담당자, 백엔드 담당자, 프런트엔드 담당자

## 1. 이 문서의 범위

이 문서는 앱의 기본 면접 질문 10개를 검수된 질문자 WAV로 재생하기 위한 연결 절차다. 대상은 `preset-01`부터 `preset-10`까지이며, 사용자 직접 입력 질문의 실시간 TTS와 코치 피드백은 포함하지 않는다.

기본 질문은 로그인하지 않은 사용자도 들을 수 있다. 그렇다고 Storage 버킷을 공개하는 것은 아니다.

```text
브라우저
  └─ GET /api/preset-questions/{questionId}/audio
       └─ FastAPI 서버 (server-only service-role key)
            └─ private Storage: preset-question-audio
```

브라우저는 Supabase Storage URL, 버킷명, 객체 경로, service-role key를 알거나 사용하지 않는다.

## 2. 먼저 준비할 것

| 항목 | 담당 | 준비 기준 |
| --- | --- | --- |
| 팀 Supabase 프로젝트 | Supabase 운영 담당자 | CLI가 연결되고 migration history를 확인할 수 있다. |
| 검수 WAV 10개 | 음성 자산 담당자 | `question_01.wav`부터 `question_10.wav`까지, 모두 24 kHz / mono / PCM_16이다. |
| 백엔드 실행 환경 | 백엔드 담당자 | `httpx`, FastAPI 등 프로젝트 의존성이 설치되어 있고 server secret을 설정할 수 있다. |
| 프런트 배포 환경 | 프런트 담당자 | 빌드 시 공개 Vite 환경변수와 백엔드 공개 주소를 설정할 수 있다. |
| 사용·보관 권한 | 팀 | 질문자 음성과 검수 WAV의 비공개 보관·앱 재생 권한을 확인했다. |

WAV는 GitHub, PR 첨부, 공개 Storage에 넣지 않는다. 팀 내부의 승인된 비공개 전달 경로로만 운영 담당자에게 전달한다.

## 3. 필요한 환경변수

실제 값은 팀의 배포 비밀 저장소 또는 각 담당자의 Git-ignored 환경 파일에만 둔다. 예시 값·키 원문·프로젝트 URL을 Git이나 채팅에 기록하지 않는다.

### 백엔드

| 변수 | 용도 | 공개 여부 |
| --- | --- | --- |
| `SUPABASE_URL` | 팀 Supabase Project URL | 서버 환경변수 |
| `SUPABASE_PUBLISHABLE_KEY` | 기존 JWT·RLS 경로의 공개 키 | 서버 환경변수 |
| `SUPABASE_SERVICE_ROLE_KEY` | private 기본 질문 WAV 읽기와 업로드 도구 실행 | **서버 전용 비밀값** |
| `CORS_ALLOWED_ORIGINS` | 프런트 Origin 목록. 여러 개면 쉼표로 구분 | 서버 환경변수 |

`SUPABASE_SERVICE_ROLE_KEY`는 FastAPI 프로세스와 업로드 도구에만 제공한다. `VITE_` 접두사, 프런트 코드, 브라우저 콘솔, API 응답, 로그에는 절대 넣지 않는다.

백엔드는 루트 `.env` 파일을 자동으로 읽지 않는다. 운영 환경이 위 값을 실제 프로세스에 주입하는지 확인해야 한다.

### 프런트엔드

| 변수 | 용도 | 공개 여부 |
| --- | --- | --- |
| `VITE_SUPABASE_URL` | Google 로그인 등 브라우저 Supabase client | 공개 가능 |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | 브라우저 Supabase client | 공개 가능 |
| `VITE_API_BASE_URL` | 기본 질문 WAV를 제공하는 FastAPI의 공개 주소 | 공개 가능 |

`VITE_API_BASE_URL`은 프런트에서 실제 도달 가능한 HTTPS API 주소여야 한다. `localhost`나 `127.0.0.1`은 각 사용자의 자기 컴퓨터를 가리키므로 배포 앱 설정값으로 사용하면 안 된다.

## 4. 운영 연결 순서

### 4-1. migration 적용

Supabase 운영 담당자가 먼저 `supabase/migrations/20260824034429_preset_question_audio.sql`을 검토한다. 이 migration은 `preset-question-audio` 버킷을 만들거나 기존 버킷을 `public = false`로 유지한다.

팀의 연결된 Supabase CLI 환경에서 migration history를 확인한 뒤 적용한다.

```powershell
supabase db push
```

Dashboard SQL Editor는 점검용으로 사용한다. 이미 적용된 migration을 SQL Editor에서 다시 실행하거나, CLI history 확인 없이 새 구조를 수동 적용하지 않는다.

적용 뒤에는 Dashboard 또는 CLI에서 다음을 확인한다.

- `preset-question-audio` 버킷이 존재한다.
- 버킷의 Public 설정이 꺼져 있다.
- 브라우저의 anon/authenticated 역할에 이 버킷 객체를 직접 읽게 하는 신규 정책을 만들지 않았다.

기본 질문 API는 서버의 service-role key로만 객체를 읽으므로, 이 버킷에 사용자용 Storage 정책은 필요하지 않다.

### 4-2. 검수 WAV 10개 업로드

백엔드 담당자는 파일 이름과 WAV 형식을 확인한 뒤에만 업로드한다. 아래 도구는 10개가 모두 있는지, 24 kHz / mono / PCM_16인지 먼저 검사한다. 중간 업로드가 실패하면 이번 실행에서 성공한 객체를 정리한다.

```powershell
Set-Location backend
$env:PRESET_QUESTION_SOURCE_DIR = "승인된_비공개_WAV_폴더"
python scripts/upload_preset_question_audio.py --source-dir $env:PRESET_QUESTION_SOURCE_DIR
```

도구가 성공하면 Storage에는 아래 경로로만 객체가 생긴다.

```text
preset-question-audio/questioner/questioner-preset-01-v1.wav
...
preset-question-audio/questioner/questioner-preset-10-v1.wav
```

업로드 도구는 기존 객체를 덮어쓰지 않는다. 같은 ID의 파일을 교체해야 하면, 새 자산 버전·청취 검수·카탈로그 변경을 별도 PR로 처리한다. Dashboard에서 임의 파일을 직접 올려 기존 객체를 덮어쓰지 않는다.

> 중요: 현재 카탈로그는 질문자 10개를 이미 `accepted` 상태로 가리킨다. 따라서 migration과 10개 업로드가 모두 끝나기 전에는 이 기능을 배포하거나 사용자에게 노출하지 않는다. 파일이 없으면 API는 안전하게 `404`를 반환한다.

### 4-3. 백엔드와 프런트 환경 설정

1. 백엔드 실행 환경에 위의 네 환경변수를 설정한다.
2. `CORS_ALLOWED_ORIGINS`에는 실제 프런트 Origin만 넣는다. 예: 운영 URL과 승인된 스테이징 URL을 쉼표로 구분한다. 끝 슬래시는 넣지 않는다.
3. 프런트 빌드 환경에는 세 개의 `VITE_*` 변수를 설정하고 다시 빌드·배포한다.
4. 프런트의 Supabase 프로젝트와 백엔드의 Supabase 프로젝트는 반드시 같은 팀 프로젝트를 가리켜야 한다.

## 5. 배포 전 확인

백엔드가 실행 중인 상태에서 다음 결과를 확인한다. 실제 Project URL·비밀값·WAV 파일 내용은 기록하지 않는다.

| 요청 | 기대 결과 |
| --- | --- |
| `GET /api/preset-questions/preset-01/audio` | `200`, `Content-Type: audio/wav` |
| `GET /api/preset-questions/preset-10/audio` | `200`, `Content-Type: audio/wav` |
| `GET /api/preset-questions/preset-11/audio` | `404`, WAV·Storage 경로 미반환 |
| Storage 읽기 실패 상황 | `503`, 내부 Storage 오류·키 미반환 |
| 프런트 기본 질문 10개 | 각 질문 텍스트와 음성이 일치하고 청취 가능한 WAV가 재생됨 |

브라우저 Network에서도 확인한다.

- 요청 대상은 FastAPI의 `/api/preset-questions/.../audio`여야 한다.
- 브라우저가 `storage/v1/object`, signed URL, `SUPABASE_SERVICE_ROLE_KEY`를 직접 사용하면 안 된다.
- 다른 Origin에서 호출하는 경우 CORS 오류가 없어야 한다. 오류가 나면 `CORS_ALLOWED_ORIGINS`의 실제 Origin부터 확인한다.

## 6. 자주 발생하는 문제

| 증상 | 우선 확인할 것 |
| --- | --- |
| `404` | `preset-01`~`preset-10` ID인지, 10개 객체가 같은 asset ID로 업로드됐는지 확인한다. |
| `503` | 백엔드 프로세스에 service-role key가 주입됐는지, 버킷이 private 상태로 존재하는지, Storage 접근이 가능한지 확인한다. 키 원문을 출력하지 않는다. |
| 브라우저 CORS 오류 | 프런트 Origin이 `CORS_ALLOWED_ORIGINS`에 정확히 등록됐는지 확인한다. |
| 버튼은 바뀌지만 소리가 나지 않음 | `VITE_API_BASE_URL`이 실제 공개 FastAPI 주소인지, Network 요청이 `200 audio/wav`인지, 브라우저 자동재생 정책·기기 출력을 확인한다. |
| 팀 Supabase와 개인 테스트가 섞임 | 프런트와 백엔드의 URL이 같은 팀 프로젝트인지 확인하고, 개인 Supabase 키·버킷을 운영 환경에 사용하지 않는다. |

## 7. 금지 사항과 책임 경계

- Storage 버킷을 public으로 바꾸지 않는다.
- service-role key를 프런트·Vercel 공개 환경변수·GitHub·PR·로그에 넣지 않는다.
- WAV·참조 음성·모델 가중치·학습 데이터·전사문을 저장소나 PR에 넣지 않는다.
- 기본 질문 실패 시 Qwen3-TTS, 공식 화자, 다른 WAV로 자동 대체하지 않는다.
- Supabase migration 적용과 WAV 업로드는 각각 외부 상태를 바꾸는 작업이다. Supabase 운영 담당자의 승인과 실제 프로젝트 확인 뒤에만 수행한다.
- 기본 질문은 비로그인 재생이 허용되지만, 사용자 입력 질문 TTS와 사용자 녹음의 보관·RLS 규칙을 재사용하거나 완화하지 않는다.

## 8. 완료 기준

다음이 모두 충족되면 팀 Supabase 연결이 끝난다.

- [ ] migration history에 `20260824034429_preset_question_audio.sql`이 적용됐다.
- [ ] `preset-question-audio` 버킷은 private다.
- [ ] 검수 WAV 10개가 도구 검증을 통과해 업로드됐다.
- [ ] backend와 frontend가 같은 팀 Supabase 및 실제 API 주소를 사용한다.
- [ ] `preset-01`, `preset-10`은 `200 audio/wav`, `preset-11`은 `404`다.
- [ ] 로그인하지 않은 브라우저에서도 기본 질문 10개를 직접 청취해 문구 일치·잡음·마지막 음절을 검수했다.
- [ ] Git diff와 배포 환경에 WAV·키·로컬 절대 경로·사용자 음성·전사문이 남지 않았다.

관련 계약은 [TTS 사전 생성 피드백 템플릿 Spec](../specs/tts-사전생성-피드백템플릿.md)과 [Supabase migration 운영 방침](../supabase-migration-operations.md)을 따른다.
