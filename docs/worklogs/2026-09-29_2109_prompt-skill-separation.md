# Worklog — Prompt와 도메인 Skill 분리

- 일시: 2026-09-29 21:09
- 작업자/에이전트: Codex
- 관련 이슈/PR: 생성하지 않음
- 관련 요구사항: 사용자 “프롬프트와 skill을 분리시켜줘” 요청
- Spec: [prompt-skill-separation.md](../specs/prompt-skill-separation.md)

## 1. 목적과 작업 전 상태

코칭·README 분석·공고 요구사항 분석·비교 후 면접 대화의 운영 Prompt와 도메인 판단 규칙을 독립적으로 관리하고 요청 구성 시 결합한다. 최신 GitHub 기준 로컬 통합이 끝난 `chore/sync-local-github-20260929`의 미커밋 변경을 유지한다. 사용자 선택으로 유지한 완료 대화 보관·접기/펼치기·실패 진단과 지정 문서 한 줄 삭제를 보존한다.

작업 전 소스·미커밋 변경을 `output/prompt-skill-separation-20260929`에 tar/patch/hash manifest로 백업했다. 실제 `.env`·인증 파일은 변경하지 않는다.

## 2. 변경과 주요 판단

- `prompts/`에 네 흐름의 역할·입력 지시 취급·응답 형식·계약 점검 템플릿을 추가했다. `skills/`에는 원문 근거·판정 기준·질문 우선순위·요약의 판단 범위를 남긴다.
- 공통 `prompt_templates.py`는 파일 경계·비공백·Skill 슬롯 하나·허용 변수만 검사하고 단일 치환으로 결합한다. 삽입한 Skill의 문자열을 다시 변수로 해석하지 않는다.
- 코칭 `SkillBundle.prompt_text`를 `rules_text`로 구분하고 운영·평가 caller를 갱신했다. `criteria.json`과 유형별 루브릭은 변경하지 않았다.
- README·공고 분석은 Skill version만 읽고 본문을 무시하던 하드코딩을 제거했다. 이제 front matter를 제외한 실제 본문을 적용하며 user prompt에는 원문 데이터를 전달한다.
- 면접 대화의 JSON 출력 계약을 별도 Prompt로 이동했다. 질문·보완 범위·출처를 보존하는 요약 규칙과 기존 대화 상태/저장 코드는 유지한다.
- 신규 코칭 기본값과 `.env.example`은 `coaching-output-v4.2`다. 실제 `.env`를 수정하지 않았다. v3/v4/v4.1 빌더는 동일 Skill 문자열·버전 입력에서 이전 hash를 유지한다. 과거 전체 입력 재현에는 당시 Skill snapshot도 필요하다.
- Langfuse 동기화 계획은 완성 Prompt 대신 템플릿을 생성한다. 런타임은 현재 Skill을 결합하고 슬롯 없는 원격 완성 Prompt는 로컬로 fallback한다. Cloud 게시·label 변경은 수행하지 않았다.
- 두 Dockerfile의 `prompts/` COPY를 추가하고 관련 구조·결정·평가 문서를 갱신했다. 컨테이너는 재빌드하지 않았다.

## 3. 검증

- 집중 검사 104개 통과 후, 정책/분리 경계 18개 통과.
- 최종 백엔드 전체 **547개 통과**: `Ran 547 tests in 10.977s / OK`.
- 실행: 저장소 root에서 `env -i PATH=/usr/bin:/bin:/opt/homebrew/bin PYTHONPATH=backend:backend/tests PYTHONDONTWRITEBYTECODE=1 STT_WARMUP_ENABLED=false <기존 검증 venv>/bin/python -m unittest discover -s backend/tests -p 'test_*.py'`.
- 실제 자격 증명을 넣지 않은 Python 3.13 격리 venv와 저장소의 기존 의존성으로 검증했다. 외부 provider·Langfuse 호출은 없었다.
- 분리 테스트: Skill 교체 시 템플릿 공통 부분 유지, 실제 Skill 본문 주입, 필수 슬롯·파일 실패, 재치환 차단, 원격 템플릿 결합·완성 Prompt fallback, Langfuse 템플릿 계획, legacy 세 버전 hash 보존.
- 작업 전 hash manifest 대조: 기존 파일 누락 0, frontend 변경 0, `skills/criteria.json` 변경 없음. 기존 문서의 지정 Out of Scope 문장은 계속 삭제 상태다.
- 기존 최신화 백업과 대조한 실제 설정 파일 2개의 hash도 그대로 유지됐다.
- Python 문법과 `git diff --check` 통과. Docker 리소스 포함은 정적으로 확인했다.
- 읽기 전용 검토 두 역할: 도메인 의미/회귀, 운영·평가/배포 리소스/변경 범위. 최종 재검토에서 추가적인 구체적 회귀를 발견하지 않았다.

## 4. 발견한 문제와 처리

- 모든 기준 충족 시 질문 없음 조건과 v3 입력 지시 경계가 분리 중 빠진 것을 검토에서 발견했다. 도메인 조건은 Skill에 복원하고 질문 없는 결과의 `null` 표기는 Prompt에 명시했다. 미보완 항목을 완료로 표현하지 않는 대화 요약 규칙도 보존했다.
- 전체 테스트 초기 실패 1건은 과거 하드코딩 Prompt에 특정 판정 문구가 있다고 가정한 검사였다. 실제 Skill bundle을 결합한 최종 입력에서 의미 규칙이 유지되는 검사로 갱신해 통과했다.
- Skill 작성 스킬의 일반 `quick_validate.py`는 검증 venv와 앱 번들 Python 모두 `PyYAML`이 없어 실행되지 못했다. 기존 프로젝트 Skill loader·front matter·카탈로그·본문 주입 검사는 통과했다. 서비스 전용 `version` front matter 구조를 임의로 변경하지 않았다.

## 5. 검증 범위와 다음 작업

실제 모델의 의미 품질 비교, 로그인 사용자 E2E, 최신 Python 3.12 이미지 빌드, 실행 컨테이너 갱신, Langfuse Cloud 동기화는 수행하지 않았다. 현재 실행 서비스는 이전 이미지이므로 이번 소스 변경이 브라우저에서 실행 중이라는 증거는 아니다. Git commit/push/PR·배포·DB migration도 수행하지 않았다.

백업과 실행 로그: `output/prompt-skill-separation-20260929`의 `before.tar.gz`, `manifest.json`, `separation-only.patch`, `focused-tests.log`, `policy-tests.log`, `full-backend-tests.log`. 원본·백업은 로컬에서 보관한다.
