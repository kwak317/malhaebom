# 2026-10-06 운영 이력서 기능 GitHub 반영

현재 main에 빠진 기존 운영 이력서 기능을 별도 PR로 복원한다. 운영 backend sha256:82b0cae6f08df6242f827f2b24791759e318c4a73b7cf6c0066e13caaa7bab75와 frontend dpl_4D2b5S8QZ1jS6gvHcbVM1n7s6KzS의 이력서 변경만 이식했다. 기존 main 코칭 v5/Skill 및 다른 운영·로컬 변경은 이 PR 범위 밖이다.

인증 PDF 업로드→개인정보 제외/텍스트 추출→Gemini 3.1 Flash Lite 사실 추출→페이지·원문 검증→사용자 수정·확인→확인 기술/프로젝트로 공고 검색·매칭을 연결한다. 제출·개인정보 안내/근거 접기 UI와 스타일을 포함한다. README 모델 설정을 바꾸지 않고 resume 모델을 3.1로 명시하여 main의 README 선택과 분리했다.

backend resume/recommendation/practice setup 61 tests, frontend 설정/API 37 tests와 production build 검증. 외부 Gemini·실제 로그인 개인 PDF E2E를 이번 PR 검증으로 주장하지 않는다. 운영 이력서 기능 자체는 이전 배포이며 이번 PR을 운영에 재배포하지 않는다. PR은 미머지 상태로 남긴다. 자료 전달/NCS fallback은 이 브랜치를 base로 하는 별도 후속 PR에서 다룬다. 기존 프로젝트 checkout은 수정/정리하지 않았다.

## PR CI 수정

PR #177/#178의 Backend tests가 `test_resume_analysis.py` 수집 단계에서 `ModuleNotFoundError: pypdf`로 실패했다. 운영 requirements에는 존재하지만 경량 CI requirements에서 누락된 것이 원인이다. `requirements-ci.txt`에 동일한 `pypdf==6.19.0`만 추가했다. ML 런타임 의존성을 설치하거나 테스트를 건너뛰지 않는다. 수정 후 전체 CI 명령과 GitHub 검사 결과를 확인한다.

검증: fresh Python 3.12-slim + CI requirements + git 환경에서 `python -m pytest backend/tests -q -p no:cacheprovider`: 607 passed. 첫 컨테이너 실행의 2개 실패는 slim image에 git 미설치였고, GitHub runner와 같이 git을 설치한 뒤 전체 통과했다.
