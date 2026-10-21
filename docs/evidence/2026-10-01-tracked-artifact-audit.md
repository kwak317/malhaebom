# Tracked artifact and ignore-rule audit — 2026-10-01

## 범위와 방법

최신 `origin/main` 기준 로컬 저장소의 Git 추적 파일에 대해 **파일명·확장자·크기**와 `.gitignore`의 예상 제외 정책을 점검했다. 비밀 파일의 내용을 열거나 원본 값을 수집하지 않았다.

```text
Tracked artifact policy: OK (835 files; ignore rules verified)
```

- Git 추적 파일: **835개**
- 예상치 못한 `.env`, `auth.json`, `credentials.json`, 개인 키 파일명: **0개**. `.env.example`과 `frontend/.env.example`은 의도적으로 허용한다.
- 추적된 로컬 실행 결과·모델 자산·음성 파일 및 파일 크기 5 MiB 초과: **0개**
- `.env`, `.env.job-source-e2e`, `.env.playmcp/auth.json`, 로컬 결과 디렉터리, 음성·모델 파일의 Git 제외 규칙: 정상
- CI 반복 점검: `scripts/check_tracked_artifacts.py`와 `backend/tests/test_tracked_artifacts.py`

## 주의 및 한계

본 점검은 **파일명·파일 크기·제외 규칙 검사**다. 허용된 소스·설정 예시 파일의 **내용 안에 실수로 기록된 secret**까지 없다고 증명하지 않는다. 기존 저장소 지침은 별도의 gitleaks secret-scan workflow를 명시한다. 그 workflow의 실제 실행·결과 확인과 권한 있는 콘텐츠 수준의 추가 점검은 별도다. Git history의 이전 커밋을 포렌식 검사하지 않았으며, 예전에 노출된 비밀의 폐기·재발급 여부도 판정하지 않는다.

검사 완료로 운영 배포의 보안 검토가 완료된 것으로 간주해서는 안 된다.

[점검 Worklog](../worklogs/2026-10-01_1520_tracked-artifact-guard.md)
