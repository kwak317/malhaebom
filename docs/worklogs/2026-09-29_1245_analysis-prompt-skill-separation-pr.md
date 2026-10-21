# Worklog — 비코칭 분석 Prompt와 Skill 본문 분리

## 목적

코칭을 제외한 분석 Prompt에서 versioned Skill 본문 전체 삽입을 제거하고, 필요한 판단 규칙과 출력 계약만 system prompt에 병합한다.

## 변경 파일

- `backend/app/services/github_readme_analysis.py`
- `backend/app/services/alio_requirement_analysis.py`
- `backend/tests/test_github_readme_analysis.py`
- `backend/tests/test_alio_requirement_analysis.py`

## 주요 판단

- Skill 파일은 계속 로드·검증하고 `skill_version`은 Prompt와 로그에 유지한다.
- 모델에는 Skill 문서 전체를 전달하지 않는다.
- README와 공고 분석에 실제 필요한 범위·금지·출력 계약만 Prompt에 명시적으로 병합한다.
- 코칭 Prompt의 `[고정 Skill]`과 `skill.text` 사용은 팀원 작업 범위이므로 변경하지 않았다.

## 검증

- `python -m py_compile backend/app/services/github_readme_analysis.py backend/app/services/alio_requirement_analysis.py` 통과
- `git diff --check` 통과
- `python -m unittest` 기반 단위 테스트는 현재 환경의 `httpx` 미설치로 import 단계에서 실행하지 못했다.
- `pytest`도 현재 환경에 설치되어 있지 않다.

## 미확인 사항

- 실제 provider 호출 품질·비용·지연 변화는 측정하지 않았다.
- 의존성 설치가 가능한 팀 실행 환경에서 두 분석 테스트와 전체 backend gate 재실행이 필요하다.
