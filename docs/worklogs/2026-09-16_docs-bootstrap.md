# Worklog — 문서 bootstrap 및 기존 구조 병합

- 일시: 2026-09-16 (Asia/Seoul)
- 작업자: Codex
- 요청: 루트 bootstrap ZIP의 기획 초안을 기존 문서 구조에 병합하고 Worklog 체계를 설정한다.
- 관련 결정: [DECISIONS](../DECISIONS.md)

## 목적 / 완료 조건

문서 역할 15개를 구분하고 canonical 문서를 중복 생성하지 않는다. 기획과 현재 구현을 구분하고, README 링크·Worklog 규칙·원본 보존·비문서 파일 무변경을 검증한다. 검증 후 ZIP과 임시 파일을 제거한다. 기존 프로젝트 코드 이관·기능 구현·리팩터링·의존성·DB 변경·commit/push는 수행하지 않는다.

## 작업 전 상태

`git status --short`에는 `?? malhaebom-docs-bootstrap-20260916.zip`만 있었다. 기존 tracked 파일 변경과 staged 파일은 없었다.

```text
README.md, AGENTS.md, CLAUDE.md
EVAL_REPORT.md
docs/.gitkeep
docs/SCAFFOLD.md
docs/specs/_example.md
skills/SKILL.md
evals/README.md, dataset.jsonl
backend/main.py, services/llm.py, requirements.txt
mcp_server/server.py
Dockerfile, docker-compose.yml, .env.example, .gitignore
.github/PULL_REQUEST_TEMPLATE.md, workflows/secret-scan.yml
```

`requirements/` 디렉터리, 프로젝트별 기존 기획서·조사·설계·Worklog는 없었다. `backend/requirements.txt`는 의존성 파일이며 제품 요구사항 문서와 역할이 다르다. `CLAUDE.md`는 AGENTS 위임 문서이므로 그대로 보존했다. 스캐폴드 안내를 읽고 파일 존재만 확인했으며 1차 소스 탐색·실행·구현 추정은 하지 않았다.

## 수행 내용 / ZIP 전체 문서 매핑

ZIP 경로 안전성을 확인한 뒤 `/tmp/malhaebom-docs-achfkz64/`에 압축 해제했다. ZIP 내 상위 `malhaebom-docs-bootstrap/` 폴더는 패키지 포장 경로이므로 저장소에 만들지 않았다.

| ZIP 상대 경로 | 최종 경로 또는 통합 위치 | 처리 |
| --- | --- | --- |
| `AGENTS.md` | `AGENTS.md` | 기존 문서 병합 |
| `MANIFEST.md` | `이번 Worklog (별도 MANIFEST 미생성)` | 패키지 안내를 기록에 통합; 즉시 코드 실사 지시는 이관 후로 변경 |
| `README.md` | `README.md` | 기존 문서 병합 |
| `docs/00_PROJECT_OVERVIEW.md` | `docs/PROJECT_OVERVIEW.md` | 번호 접두어 제거; 기존 대문자 설명형 명명 관례 적용 |
| `docs/01_CURRENT_STATE.md` | `docs/CURRENT_STATE.md` | 번호 접두어 제거; 기존 대문자 설명형 명명 관례 적용 |
| `docs/02_TARGET_STATE.md` | `docs/TARGET_STATE.md` | 번호 접두어 제거; 기존 대문자 설명형 명명 관례 적용 |
| `docs/03_REQUIREMENTS.md` | `docs/REQUIREMENTS.md` | 번호 접두어 제거; 기존 대문자 설명형 명명 관례 적용 |
| `docs/04_CONSTRAINTS.md` | `docs/CONSTRAINTS.md` | 번호 접두어 제거; 기존 대문자 설명형 명명 관례 적용 |
| `docs/05_DOMAIN_KNOWLEDGE.md` | `skills/SKILL.md` | 기존 문서 병합 |
| `docs/06_ARCHITECTURE.md` | `docs/ARCHITECTURE.md` | 번호 접두어 제거; 기존 대문자 설명형 명명 관례 적용 |
| `docs/07_IMPLEMENTATION_PLAN.md` | `docs/IMPLEMENTATION_PLAN.md` | 번호 접두어 제거; 기존 대문자 설명형 명명 관례 적용 |
| `docs/08_EVALUATION_PLAN.md` | `evals/README.md` | 기존 문서 병합 |
| `docs/09_DECISIONS.md` | `docs/DECISIONS.md` | 번호 접두어 제거; 기존 대문자 설명형 명명 관례 적용 |
| `docs/proposal/MALHAEBOM_PROJECT_PROPOSAL_SOURCE.md` | `docs/proposal/MALHAEBOM_PROJECT_PROPOSAL_SOURCE.md` | 신규 생성 |
| `docs/proposal/README.md` | `docs/proposal/README.md` | 신규 생성 |
| `docs/research/COMPETITOR_RESEARCH.md` | `docs/research/COMPETITOR_RESEARCH.md` | 신규 생성 |
| `docs/research/DOMAIN_RESEARCH.md` | `docs/research/DOMAIN_RESEARCH.md` | 신규 생성 |
| `docs/research/JOB_POSTING_RESEARCH.md` | `docs/research/JOB_POSTING_RESEARCH.md` | 신규 생성 |
| `docs/worklogs/README.md` | `docs/worklogs/README.md` | 신규 생성 |
| `docs/worklogs/TEMPLATE.md` | `docs/worklogs/TEMPLATE.md` | 신규 생성 |

## 주요 판단과 이유

- README: 프로젝트 소개·문서 목차·이관 대기·Worklog 규칙을 추가하고 기존 조원 표·협업·시크릿·수업 안내를 보존했다.
- AGENTS: 기존 Spec의 Why/Goal/What/How/AC, Out of Scope, 테스트 완료 기준을 유지하고 프로젝트 범위·데이터·검증·문서 갱신·Worklog 규칙을 병합했다.
- 도메인 지식은 기존 `skills/SKILL.md`가 같은 역할을 하므로 통합했다. 기존 양식의 섹션을 유지하며 빈칸을 기획으로 채웠다. RAG 수업 안내와 프로젝트 범위는 구분했다.
- 평가 계획은 기존 `evals/README.md`의 구성·시점·판정 지침에 프로젝트 계획을 추가했다. `EVAL_REPORT.md`는 실측 결과 양식으로 역할이 달라 그대로 유지했다. `dataset.jsonl`은 수정하지 않았다.
- `docs/SCAFFOLD.md`와 `docs/specs/_example.md`는 수업용 설명/Spec 예시이므로 프로젝트 아키텍처·요구사항과 구분해 보존했다. `requirements/`는 추가하지 않았다.
- 새 운영 문서의 번호 접두어를 제거해 기존 `SCAFFOLD.md` 관례에 맞췄다. 운영 문서 내 참조도 수정했다.
- `docs/05_DOMAIN_KNOWLEDGE.md`, `docs/08_EVALUATION_PLAN.md`, 별도 README/AGENTS 복사본, `MANIFEST.md`는 생성하지 않았다. Manifest의 반영 절차·후속 갱신 대상은 이 기록에 통합했다.
- 기획서 원문은 ZIP과 바이트 동일하게 보존했다. 통과본 v1.0 설명과 원문 v0.10 헤더의 차이는 `proposal/README.md`에 남겼다.
- 원문의 기존 구현 진술은 현재 저장소 사실이 아니다. 운영 문서에서 재사용 계획으로 표시하고 실사는 이관 이후로 미뤘다. 목표 아키텍처·API·평가 숫자는 구현/실측 결과로 표시하지 않았다.

## 변경 파일

기존 수정 4개: `README.md`, `AGENTS.md`, `skills/SKILL.md`, `evals/README.md`.

신규 문서는 위 매핑 중 신규 생성 및 번호 접두어 제거 항목과 이 Worklog다. 총 16개: 운영 8개, 조사 3개, 원본 보관 2개, Worklog 안내·템플릿·이번 기록 3개.

## 검증

문서 작업의 AC로 링크·원본·범위·상태·기록·정리를 검사했다. 서비스 기능 테스트는 이번 작업 대상이 아니다.

- 결과: 운영 상대 링크 34개 통과, 원본의 접근 불가 로컬 링크 8개는 보존 예외로 확인.
- `python3 /tmp/verify_malhaebom_docs.py`: 운영 Markdown 상대 링크의 실제 경로, 원본 SHA256/ZIP 바이트 일치, 기존 변경 파일 4개 제한, staging 공백, Worklog 규칙, 이관 대기 문구, 중복 문서 미생성을 assert로 확인.
- 원본 SHA256: `3fb7be1ec1750f621956394bfd9278c142dcf8986325dcec6ab5e2b5ccd92721`.
- `git diff --check`: 공백 오류 없음.
- `git diff --name-only`: 문서 4개 외 기존 코드·설정·의존성·DB·평가 데이터 변경 없음.
- `git status --short --untracked-files=all`: 수정 4개, 신규 문서 16개. staging/commit/push 없음.
- 정리 후 ZIP·압축 해제 폴더·이번 작업의 보조 스크립트가 없으며, `git ls-files --cached --others --exclude-standard`에 bootstrap ZIP이나 임시 파일이 남지 않았는지 확인.

## 발견한 문제

- 원본에는 작성자의 `/Users/kkwakbab/...` 로컬 자료 링크가 남아 있다. 제공되지 않은 자료이므로 복구를 추정하지 않고 원문을 보존했으며 `proposal/README.md`에 안내했다. 운영 문서 링크와 분리한 알려진 원본 예외다.
- 기획 원본의 버전 헤더와 패키지의 통과본 설명이 다르다. 임의로 원문 헤더를 수정하지 않았다.
- Manifest/아키텍처 초안의 즉시 코드 실사 지시는 현재 미이관 상태와 맞지 않아 후속 작업으로 변경했다.

## 미확인 사항

기존 1차 코드의 실제 구조·호출 경로·기능·인증·DB·만료·배포는 모두 미확인이다. 경쟁 서비스는 제공 기획 요약을 이관했을 뿐 이번에 웹 재검증하지 않았다. 도메인 검수, 실제 공고 수집, 모델 비교, 30건/100건 평가, 서비스 실행/배포 테스트도 수행하지 않았다.

## 다음 작업 / 이관 후 갱신 대상

별도로 승인된 코드 이관 작업 이후 다음 문서를 실제 파일·실행 증거와 연결해 갱신한다.

1. `docs/CURRENT_STATE.md`: 재사용 자산·문제 후보의 실제 상태.
2. `docs/ARCHITECTURE.md`: 현재 서비스·호출 경로·DB·권한·배포 구조.
3. `README.md`: 실제 실행·배포·재현 절차.
4. `docs/IMPLEMENTATION_PLAN.md`: baseline 실사와 재사용/교체 순서.
5. `docs/TARGET_STATE.md`, `docs/REQUIREMENTS.md`, `docs/CONSTRAINTS.md`: 구현 차이와 정책 검증; 계획을 자동 완료 처리하지 않음.
6. `skills/SKILL.md`, `evals/README.md`, `EVAL_REPORT.md`: 모델 연결·검수·평가 구성 및 실측 결과가 생길 때 갱신.
7. `docs/DECISIONS.md`: 이관 후 확인으로 달라진 결정의 근거를 추가.

## 정리 대상

- 루트 `malhaebom-docs-bootstrap-20260916.zip` (작업 전 untracked, 80,367 bytes).
- `/tmp/malhaebom-docs-achfkz64/` (이번 작업에서 생성한 압축 해제 디렉터리).
- `/tmp/merge_malhaebom_docs.py`, `/tmp/verify_malhaebom_docs.py` (이번 병합·검증용 임시 스크립트).
