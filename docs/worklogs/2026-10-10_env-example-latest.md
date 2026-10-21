# 최신 운영 변수 이름 기반 .env.example 정리

- 요청: 최신 env를 확인하되 키 값을 읽지 않고 .env.example 작성.
- 기준: GitHub main e6ecc4b07e0e6c887ba42411e5eb93a3147450a9. Cloud Run 트래픽 100% revision malhaebom-mk2-main-sync-final-1010.
- 확인 방법: gcloud revision describe의 env.name 필드만 출력했다. 실제 .env 파일과 Secret Manager 값은 조회하지 않았다. GitHub에 공유되는 기존 .env.example 및 관련 소비 코드만 읽었다.
- 변경: LANGFUSE_HOST, PLAYMCP_AUTH_BUCKET, STT_REMOTE_URL, STT_MODEL_REVISION, FREE_CHAT_ENABLED 추가. 기존 로컬 기본값 보존, Langfuse Japan Cloud 주소 설정 방법과 BASE_URL 우선순위 안내, 키·토큰·secret 빈 값 정책 명시.
- 검증: 운영 환경변수 이름 전체 포함, 중복 변수 없음, 민감값 항목 빈 값, dotenv 파싱 및 git diff --check 확인.
- 범위: .env.example과 이 Worklog만 수정했다. 기존 trace 변경은 별도 worktree에 보존했다. frontend 예제에는 새 프런트 변수 추가가 필요하지 않았다.
- 업로드: 사용자 요청에 따라 codex/env-example-latest-20261010 브랜치를 커밋·push하고 main 대상 PR로 제출한다. 머지·배포는 포함하지 않는다.
- 미수행: 실제 키 유효성, compose 실행, runtime 설정 변경, merge/배포. 예제 추가만으로 Compose가 새 변수를 자동 전달하지는 않는다. 필요 시 관련 배포 설정에서 별도 전달한다.
