# 코칭 도메인 규칙의 Skill 관리

## 범위와 결과
- 사용자 승인에 따라 로컬 코칭 Prompt/Skill 분리 수정. Spec: `docs/specs/coaching-domain-rules-in-skill.md`.
- 새 영문 `prompts/coaching-v5-skill-owned.md`를 기본값으로 선택. 템플릿에는 입력 경계·Skill 적용·출력 계약만 두고 판정 의미와 도메인 예시를 제거.
- 기존 v4의 가상 positive/negative 예시는 Skill 본문으로 옮김. 상충하는 결과 검증 예시는 기존 Skill의 방법·조건·실제 관찰 결과 기준으로 통일. 수치·반복 횟수를 일괄 필수 조건으로 요구하지 않음.
- Skill 버전 `interview-coach-v6.1-domain-rules`. `criteria_version`, enum 및 서버 validator는 유지.
- 과거 v4 템플릿과 실험 결과는 수정하지 않음. 과거 실행 재현에는 당시 Skill도 필요.
- `.env.example`과 로컬 `.env`의 Prompt/Skill 버전 두 항목을 갱신. 키 값은 변경하지 않음. `.env`는 임시 경로에 권한 600으로 백업.
- 편집 전 관련 소스 백업: 프로젝트 상위 `output/skill-domain-separation-20261001/before-174033/`.

## 검증
- 실제 수정 소스를 `/app`에 읽기 전용 마운트한 기존 API 이미지에서 실행. `--network none`, 외부 provider 호출 없음.
- Prompt·Skill 분리·Skill loader·runtime·preset·API 테스트 75건 통과.
- validator·평가 규칙·관측 회귀 테스트 52건 통과. 합계 127건.
- 최초 실행에서 preset 테스트의 `test_coaching_api` import 경로 누락 발견. `PYTHONPATH=/app/backend/tests:/app/backend:/app`로 수정해 정상 검증.
- 기본 템플릿의 도메인 예시 부재, Skill 교체 시 기존 규칙 잔존 없음, 이전 v4 로딩 보존을 검사.
- 버전 메타데이터 및 기존 출력 계약 결합을 검사.

## 제한 및 후속 작업
- 실행 중 로컬 API 이미지를 재빌드/재시작하지 않았으므로 현재 컨테이너는 이전 코드/설정 사용. 다음 재빌드/재시작에 새 버전 적용.
- Cloud Run은 사용자 요청에 따른 일시 중지 상태 유지. 운영 배포와 Langfuse 원격 Prompt 수정 없음.
- Langfuse에 이전 관리 템플릿을 지정한 환경은 별도 갱신 필요.
- 실제 LLM 30건 재평가·TTFT·품질 비교는 수행하지 않음. 테스트 통과를 모델 품질 개선으로 해석하지 않음.
- 기존 기능 제거·STT·README 등 다른 미커밋 변경 보존. push/commit 없음.

## PR 검증
- 최신 `origin/main` (`3dde470`)에서 `codex/coaching-skill-domain-rules` 브랜치로 변경분만 분리했다.
- main에서 삭제된 과거 실험용 Prompt 분기는 복원하지 않고 새 v5 분기만 추가했다.
- 해당 PR checkout에서 동일한 관련 테스트 11개 모듈을 실행해 117건 통과. 원래 로컬 checkout의 127건과 구분한다.
- PR은 사용자 요청에 따라 생성/게시하되 merge하지 않는다. 배포·인증 정보·다른 작업의 변경은 포함하지 않는다.
