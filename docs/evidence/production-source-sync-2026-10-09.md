# GitHub main과 운영 소스 비교 · 2026-10-09

운영 사이트를 변경하지 않고 GitHub 수정 후보를 준비했다. 운영 서버와 Vercel 원본이 기준이며, 기존 로컬 checkout을 운영 원본으로 사용하지 않았다. PR은 미병합 상태다.

## 1. 폴더·파일

| 구분 | 파일 수 |
| --- | ---: |
| 내용 동일 | 423 |
| 같은 경로, 내용 다름 | 72 |
| 운영 원본에만 존재 | 45 |
| GitHub에만 존재 | 589 |
| GitHub main 추적 파일 | 1,084 |
| 확보한 운영 소스 | 540 (API 이미지 378 + Vercel 162) |

상태는 배포 패키징 기준이며 GitHub 전용 589개를 삭제 대상으로 보지 않는다. .github, 문서, 테스트, migration, 개발·학습 도구 등 저장소 자산을 보존한다. cache, .env, binary model/audio, emotion_data와 API 이미지의 5 MB 초과 파일은 제외했다.

신규 활성 경로는 `skills/free-chat-request-handling/`, 자유채팅/재시작/선택/전사/추적 서비스 파일과 프런트 로딩·텍스트 컴포넌트다. 평가 전용 Skill v7/v8·과거 Prompt 및 eval runner의 차이는 활성 운영 기능과 분리하고 기존 GitHub 실험 자산을 보존했다.

전 경로와 SHA256·처리 결정은 [파일 비교 CSV](production-sync-20261009/file-comparison.csv), 폴더 목록은 [폴더 비교 CSV](production-sync-20261009/folder-comparison.csv), 버전·제외 범위는 [manifest](production-sync-20261009/manifest.json)를 따른다. 폴더의 공유/한쪽 전용 개수도 manifest에 기록한다.

## 2. 주요 기능 차이와 반영

| 운영에 먼저 반영된 기능 | 저장소 반영 경로 |
| --- | --- |
| 필요한 요청만 자유채팅 모델로 분기·범위 안내·근거 검증 | free_chat.py, free_chat_evidence.py, free-chat Skill/Prompt |
| 역질문 보존·경험 확인 뒤 추가 동의·참고정보 저장 | preparation runtime/policy/generation |
| 지난 단계만 재선택, 삭제 범위 동의, 초기화 범위 보존 | preparation_restart.py, selection_actions.py, repository/router |
| 서버에 있는 공고 원문·기록 조회 | preparation_information.py |
| 현재 대화와 참고자료실·재답변·기록 화면 | PracticePage, PreparationConversationChat, PracticeWorkspace |
| 진행 상태와 코치 로딩 일러스트 | loading_progress.py, frontend loading API/components/assets |
| GPU STT 연결·전사 후처리 @3 | remote_stt.py, transcript_normalization.py, AnalysisPage |
| HTTP 요청/LLM trace ID 연결·헤더 노출 | request_trace.py, main.py, coaching_observability.py |
| 확인 질문 강조·순서·스크롤·버튼/배경 스타일 | ChatMessageText, scroll hook, styles |

GitHub에만 있는 버전 provenance 전달·실제 Skill 버전 로딩·캐시 응답 전 소유/만료/단계 검사·안전 경계 4섹션·pypdf 재현 의존성·기존 회귀 테스트는 보존한다. 단순 운영 파일 덮어쓰기는 이 개선을 제거하기 때문이다. 따라서 수정 후보는 활성 운영 기능의 동기화이며 운영 이미지의 byte-for-byte 복제는 아니다.

## 3. Prompt·Skill·모델

| 항목 | 실제 조회 결과 |
| --- | --- |
| 운영 코칭 Langfuse | malhaebom-coaching-v5-reinforced-verification @4, latest=production |
| 코칭 모델 | google/gemini-3.5-flash-lite |
| 자유채팅 모델 | anthropic/claude-haiku-5.5, 운영 소스에 고정 |
| 운영 코칭 Skill | interview-coach-v6; main v6.1과 판정 본문은 같고 catalog version 문자열만 다름 |
| 준비 채팅 | 운영 local v3.3-reference-finish + Skill v3.2; Langfuse @1과 본문이 달라 managed @1을 채택하지 않음 |
| 전사 후처리 | malhaebom-transcript-normalization @3, latest=production, 숫자 버전/hash 검증 |

Langfuse 원격 최신 본문은 `prompts/managed/`에 숫자 버전별 정확한 snapshot으로 저장했다. 기존 frozen v4·과거 평가 Prompt는 덮어쓰지 않는다. 준비 채팅의 원격 @1을 운영 local 최신보다 우선 적용하면 최근 기능이 없어지므로, 현재 운영의 선택 로직과 본문을 유지한다. 이번 작업은 Langfuse 라벨/본문 등록이나 기본 모델 변경을 수행하지 않았다.

Skill catalog·provenance·테스트의 버전 표시는 운영 v6에 맞추지만 도메인 규칙은 바꾸지 않는다. 별도 PR #220의 met 정합화 후보나 #219의 전문가 검토 메타데이터는 이번 작업에 합치지 않는다.

## 4. 의존성·배포 설정

프런트 package.json과 npm/pnpm lockfile, Vite/TypeScript/Vercel 설정은 원본과 같다. API 이미지의 requirements에는 pypdf 선언이 없지만 실제 pypdf 6.19.0이 설치되어 있다. GitHub의 기존 pypdf 선언을 유지해 clone/build 재현을 보존한다. 실제 주요 설치 버전은 manifest에 기록한다.

Cloud Run traffic revision/image, 공개 모델/Prompt 선택 값과 Vercel deployment/framework/Node 값을 고정했다. `.env`와 secret 값은 저장·커밋하지 않는다. 운영 설정을 내보낸 manifest는 비교 증거이며 적용 스크립트가 아니다. API 이미지에 빌드용 Dockerfile·Compose·Git 원본 전체가 없으므로 그 파일이 운영과 동일하다고 추정하지 않는다. 기존 배포·CI 파일은 보존한다.

## 검증과 한계

- main 핵심 회귀 baseline: 70 tests 통과.
- 통합 후보 프런트: 220 tests 통과, TypeScript/Vite build 통과.
- 통합 후보 백엔드: 준비 채팅 68, 코칭/추적/STT/로딩 92, 분석/Skill/면접 회귀 122 tests 통과.
- 추가 회귀 3 tests 통과: 직접 수행 확인 → 별도 저장 동의 → 참고정보 저장, 지난 단계 재선택 제한, 강조 표시 속 허위 완료 문구 거부. fake provider/repository 기반으로 실제 LLM 품질·운영 DB E2E와 구분한다.
- 최초 운영 이미지의 backend discover는 exit 137로 종료됐고 정확한 강제 종료 원인은 확정하지 못했다. 이후 GitHub CI와 같은 `requirements-ci.txt` 의존성·Python 3.12 환경에서 전체 `pytest backend/tests -q -p no:cacheprovider`를 다시 실행하여 **814 passed, exit 0 (31.39s)**를 확인했다. 컨테이너 메모리 제한은 3 GB이며 실제 ML 모델 실행·LLM 품질·운영 DB E2E 검증과 구분한다. [전체 재검증 환경](production-sync-20261009/full-backend-result.json)을 따른다.
- 실제 로그인 세션의 준비 채팅 → Haiku 응답 → 개인 역할 확인 → 별도 저장 동의 → DB 저장/재조회 → 자료실 2건 및 항목 펼침을 검증했다. 9개 체크 중 7개 통과, 자연어 동의 문구 2개 실패이며 HTTP 200을 기능 성공으로 간주하지 않는다. [실제 검증과 한계](production-sync-20261009/authenticated-chat-e2e-result.json)를 따른다.
- 신규 OAuth 로그인, 실제 마이크/STT/코칭/비교 전체 제품 흐름 및 150건 모델 품질 평가는 실행하지 않았다. 마지막 native 화면 캡처는 과거 화면이 남아 최신 자료실 증거로 사용하지 않았고 갱신된 접근성 상태·서버 GET·DB로 보완했다. 운영과 소스 동기화 범위에서 동의 정책은 변경하지 않았다.
- 실제 production이 비교 기준에서 바뀌면 다시 revision/원본을 고정해야 한다. PR stack은 순서대로 검토하되 이번 작업에서는 머지·배포하지 않는다.
