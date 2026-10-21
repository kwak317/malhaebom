# 말해봄 Mk.2 배포 통합 Spec

## Why

1차 프로젝트의 음성 면접 코칭 기능을 2차 프로젝트 저장소의 Skill·MCP·평가
구조와 함께 실행해야 한다. FastAPI와 React 프런트엔드가 별도 런타임이므로
신규 팀원이 전체 흐름을 한 명령으로 재현할 수 있는 계약이 필요하다.

## Goal

- `docker compose up --build` 한 번으로 API와 웹 화면을 실행한다.
- `GET /health`가 모델 추론 없이 `200 {"status":"ok"}`를 반환한다.
- 웹 컨테이너가 API·분석·연습 기록 경로를 같은 Origin으로 프록시한다.
- `.env`, 모델 가중치, 음성, 전사문, 생성물은 이미지와 Git에 포함하지 않는다.

Out of Scope: GPU 모델 가중치 배포, Supabase 운영 migration 적용, 2차 프로젝트
LLM 코칭 로직 구현, RAG 도입.

## What

Happy Path: 운영자가 `.env.example`을 참고해 환경변수를 넣고 Compose를 실행하면
웹은 18080, API는 8000에서 응답한다. 브라우저 요청은 웹 서버를 통해 API로 전달된다.

Edge Case: Supabase 또는 GPU TTS Worker가 준비되지 않으면 인증·TTS 기능은 명확한
401/503을 반환하되, 컨테이너와 `/health`는 정상 상태를 유지한다.

## How

- 루트 `Dockerfile`은 FastAPI와 STT 런타임을 설치하고 `backend.main:app`을 실행한다.
- `frontend/Dockerfile`은 Vite 결과물을 Nginx로 제공한다.
- Nginx는 `/api`, `/analysis-jobs`, `/practice-records`를 `api:8000`으로 전달한다.
- 로컬 FastAPI는 저장소 밖의 승인된 GPU Worker를 `TTS_WORKER_URL`로 연결한다.
- Docker API는 호스트 Worker를 `TTS_WORKER_DOCKER_URL`로 연결하며 기본값은 `http://host.docker.internal:8100`이다.
- 프런트의 `VITE_SUPABASE_*`가 비어 있으면 Compose는 공개 `SUPABASE_*` 값을 빌드 인자로 사용한다.
- 실제 비밀 값은 `.env`나 배포 플랫폼 Secret에만 둔다.

## AC

- Given 비밀 값이 없는 빌드 환경, When 프런트엔드를 빌드하면, Then 정적 빌드가 성공한다.
- Given API 의존성이 설치된 환경, When `backend.main:app`을 불러오면, Then `/health`가 등록된다.
- Given Compose 설정, When `docker compose config`를 실행하면, Then 설정 오류가 없다.
- Given Git에 추가할 파일, When 비밀·대용량 패턴을 검사하면, Then `.env`, 모델, 음성, 가상환경, `node_modules`가 없다.
