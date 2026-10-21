# Worklog — Skill의 긍정·부정 참고 사례

- 일시: 2026-09-30 16:16 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항: 네 Skill에 긍정·부정 사례를 추가하고 시스템 프롬프트 템플릿은 유지

## 1. 목적과 범위

코칭, 공고 요구사항 추출, GitHub README 분석, 비교 후 면접 대화의 Skill 본문에 판단 예시를 추가한다. 예시는 가상이며 실제 사용자 근거나 평가셋 정답으로 사용하지 않는다.

## 2. 변경

- `skills/interview-coach/SKILL.md`: 결과 관찰과 개인 행동의 긍정·부정 사례를 추가했다.
- `skills/job-requirement-extraction/SKILL.md`: 공고 원문의 우대 조건과 명시된 역할에 관한 사례를 추가했다.
- `skills/github-readme-evidence/SKILL.md`: README 원문 근거와 설치 안내의 의미에 관한 사례를 추가했다.
- `skills/interview-conversation/SKILL.md`: `start`, `message`, `finish` 각각의 사례를 추가했다.
- 사례가 실제 Skill 본문 변경임을 표시하도록 Skill 버전을 코칭 v6, 공고·README v2, 면접 대화 v2로 올렸다. 기본 관측 버전, 예시 설정과 관련 테스트의 기대값도 맞췄다.
- `prompts/*.md` 템플릿과 Prompt 버전, JSON 출력 계약은 이 PR에서 변경하지 않았다.

## 3. 검증

- 기존 API 이미지에 이 PR 작업트리를 읽기 전용 마운트해 Skill·Prompt·분석·코칭·면접 대화 관련 단위 테스트 93개와 면접 대화 API 테스트 13개를 실행했다. 모두 통과했다.
- 네 Skill에 각각 긍정·부정 사례가 있으며, 네 Prompt 템플릿에는 새 사례가 없는지 확인했다.
- 변경 범위의 `git diff --check`로 공백 오류를 확인했다.

## 4. 제한

- 실행 중 API 컨테이너는 재빌드하지 않았다. 새 Skill이 실제 요청에 반영됐다는 뜻은 아니다.
- 실제 LLM 품질·비용과 Langfuse trace는 이번 작업에서 측정하지 않았다.
- 전체 `git diff --check`의 기존 `.github/PULL_REQUEST_TEMPLATE.md` 공백 오류는 범위 밖이라 수정하지 않았다.
