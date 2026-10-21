# Worklog — 보강 후보 v5 Langfuse·GitHub 등록

- 일시: 2026-10-06
- 작업자/에이전트: Codex
- 요청: 어제 보강한 Prompt를 v5로 Langfuse·GitHub에 올리고 PR만 생성, 병합 제외.

## 1. 목적
기존 후보 본문을 보존해 명시 선택 가능한 코드 v5와 Langfuse candidate로 등록한다.

## 2. 작업 전 상태
main `239b761`은 기본 v4다. 어제 후보는 배포 원본에서 만들었으며 SHA256 `ed39574026c68be510dad31fb9b8b5077fc92f11848a72c9105f3f16b8bfd9f9`다. 현재 운영은 `malhaebom-mk2-langfuse-v4-1006`, Langfuse v4 production 버전 1이다. 기존 로컬 checkout의 미커밋 변경은 사용하지 않았다.

## 3. 수행 내용
- 별도 `coaching-v5-reinforced-verification` 템플릿과 selector를 추가했다.
- Langfuse에 새 이름·candidate 라벨로 등록하고 고정 숫자 버전·본문·라벨을 재조회했다.
- 현재 운영 서비스 spec·트래픽과 v4 production 버전·본문이 변경되지 않았음을 확인했다.

## 주요 판단과 이유
기존 v5 Skill-owned는 별도 후보로 보존한다. 새 v5는 배포 v4의 규칙·예시를 보강한 계열이며 Skill-owned 구조라고 주장하지 않는다. 어제 runtime의 출력 상한·보정 수정은 이번 PR에 포함하지 않는다.

## 4. 변경 파일
- `prompts/coaching-v5-reinforced-verification.md`: 후보 본문 그대로.
- `backend/app/services/coaching_prompt.py`, `backend/tests/test_coaching_prompt.py`: 명시 선택과 회귀 검사.
- Spec·등록 manifest·CURRENT_STATE·Worklog 및 목록.

## 5. 검증
- Prompt·분리·runtime unittest 51건 통과. 테스트 파일 편집 시 인자를 잘못 추가한 오류 1건을 수정한 뒤 재실행했다.
- 원 후보·GitHub 파일·Langfuse 버전 본문 SHA256 일치.
- 기본 v4와 기존 v5 선택을 유지하는 기존 테스트 통과.
- Cloud Run spec·트래픽과 v4 production 버전 1 및 본문 동일.

## 6. 발견한 문제 / 남은 리스크
GitHub의 현재 Skill은 어제 평가 당시 운영 Skill v6와 다르다. 과거 25/30을 새 GitHub 조합의 검증으로 표현하지 않는다.

## 미확인 사항
새 실제 provider 호출·인젝션 재측정·사람 품질 검토·로그인 E2E는 수행하지 않았다. 후보 업로드는 운영 승격이 아니다.

## 7. 다음 작업
PR 리뷰. 배포와 병합은 이번 요청에서 제외한다.
