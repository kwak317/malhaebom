# Worklog — maintained 문서 참조 정리와 링크 회귀 검사

- 날짜: 2026-10-01
- 목적: 배포 관련 코드·설정을 수정하지 않고 현재 문서의 링크·Skill 경로 불일치를 고치고 재발을 차단한다.
- 기준: 최신 origin/main. 오래된 docs/document-consistency-cleanup worktree는 origin/main에 없는 별도 고유 커밋이 없고 269개 커밋 뒤에 있어 변경하지 않는다.

## 작업 전 상태

- 루트 README의 `skills/SKILL.md` 링크가 존재하지 않았다.
- 공식 체크리스트의 세 항목이 이동 전 Skill 경로를 가리켰고 Prompt v0 근거가 현재 기본 Prompt 버전을 과거 v4.1로 설명했다.
- README의 서론·구성·runtime 설명 일부는 초기 scaffold 상태를 현재 상태처럼 기술했다.
- 기존 Worklog와 계획서는 당시 시점의 기록이므로 교정 범위에서 제외한다.

## 수행 내용

1. 루트 README의 문서 링크와 현재 구성 설명을 현재 Skill·Prompt·코칭 runtime 구조에 맞춰 조정한다. 운영 배포 검증을 완료했다고 표현하지 않는다.
2. 공식 체크리스트의 이동 전 Skill 경로 세 곳과 오래된 현재 Prompt 설명을 수정한다.
3. `scripts/check_doc_references.py`에서 유지관리 대상 6개 진입점 문서의 상대경로 Markdown 링크를 검사하고, README·공식 체크리스트의 인라인 Skill 파일 경로도 검사한다. 외부 URL, 문서 내부 anchor, 코드 블록과 기존 Worklog는 제외한다.
4. 정상 링크·누락 링크·인라인 Skill·외부 URL·코드 블록을 검증하는 단위 테스트 3개를 추가한다. 해당 테스트는 기존 backend unittest/pytest CI에서 자동 수집된다.

## 검증

- `python scripts/check_doc_references.py`: 6개 문서 모두 PASS.
- `python backend/tests/test_doc_references.py`: 3 tests PASS.
- 기존 과거 Worklog, 운영 배포/환경변수, 프런트엔드/백엔드 런타임 코드는 수정하지 않는다.

## 남은 작업 및 한계

- 검사는 *현재 유지관리 대상* 문서 6개의 상대 링크 및 두 핵심 문서의 Skill 경로에 한정한다. 과거 Worklog·연구 계획·실험 snapshot의 옛 경로까지 무차별 검증하지 않는다.
- 문서 의미 전체가 현재 구현과 맞는지 여부는 별도의 사용자 흐름 검증이 필요하다. 이 PR은 확인한 현재 참조 불일치와 회귀 방지에만 집중한다.

## 공식 안내 문서의 개인 실행 환경 설명 정리

- 루트 README의 최초 실행 검증 설명에서 개인 PC 운영 절차를 제거하고, 누구나 따라 할 수 있는 새 clone 검증 범위만 남겼다.
- 문서 안내에서 특정 작업자 로컬 절대경로 예시를 없애고, 실험 기록과 팀 공통 상대경로·로컬 설정의 경계를 일반적인 정책으로 설명했다.
- Python 환경 재현 안내에서 외부 실행 도구 전용 프로필 이름을 제거하고, 기존 가상환경 재사용 안내를 새 clone에도 적용되는 조건부 절차로 변경했다. GPU·CUDA와 FlashAttention 검증 사양은 재현 조건이므로 보존했다.
- 현재 PR 정책 Spec의 외부 실행 도구 언급을 제품·저장소 중심으로 일반화했다. 과거 Worklog, 실험 snapshot, 원 기획서는 변경하지 않았다.
- 문서 검사 대상을 Python 환경 안내까지 7개로 늘리고, 공식 유지관리 문서 본문에 개인 PC 절대경로가 다시 기입되면 실패하도록 회귀 검사 한 건을 추가했다.
