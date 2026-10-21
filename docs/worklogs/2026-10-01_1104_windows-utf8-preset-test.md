# Worklog — Windows preset catalog test encoding

- 일시: 2026-10-01 11:04
- 작업자/에이전트: Codex (서정현 작업 공간)
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: AGENTS.md 테스트 통과·Worklog 기록 규칙

## 1. 목적

Windows 기본 코드 페이지(CP949)에서도 preset 질문 카탈로그 검증 테스트가 UTF-8 TypeScript 파일을 안정적으로 읽게 한다.

## 2. 작업 전 상태

`backend/tests/test_preset_coaching.py::PresetCoachingTest::test_catalog_matches_every_visible_question_and_skill`가 `presetQuestions.ts`를 인코딩 지정 없이 읽었다. Windows에서 기본 CP949 디코딩이 적용되어 한국어 UTF-8 바이트를 읽을 때 `UnicodeDecodeError`가 발생했다.

## 3. 수행 내용

- 카탈로그 읽기 호출에 `encoding="utf-8"`을 명시했다.
- 실패했던 단일 테스트와 백엔드 전체 pytest 스위트를 다시 실행했다.

## 주요 판단과 이유

소스 파일의 저장 인코딩은 UTF-8이므로, 실행 환경의 기본 코드 페이지에 의존하지 않고 읽기 지점에서 명시하는 것이 가장 작은 수정이다. 테스트 의미와 제품 런타임 동작은 변경하지 않았다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/tests/test_preset_coaching.py` | `presetQuestions.ts`를 UTF-8로 읽도록 고정 |
| `docs/worklogs/2026-10-01_1104_windows-utf8-preset-test.md` | 원인·수정·검증 결과 기록 |

## 5. 검증

```text
$env:PYTHONPATH = "$PWD;$PWD\\backend;$PWD\\backend\\tests"
.\\.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_preset_coaching.py::PresetCoachingTest::test_catalog_matches_every_visible_question_and_skill -q
1 passed, 2 warnings, 10 subtests passed

.\\.venv\\Scripts\\python.exe -m pytest backend\\tests -q
569 passed, 2 warnings, 240 subtests passed in 71.57s
```

## 6. 발견한 문제 / 남은 리스크

- `.pytest_cache` 디렉터리에 대한 접근 거부 경고가 남지만, 테스트 결과와 종료 코드는 정상이다.

## 미확인 사항

- GitHub Actions의 Linux 환경은 CP949 기본 인코딩 문제가 없지만, 후속 CI pytest 작업에서 같은 전체 스위트를 실행하도록 별도 구성한다.

## 7. 다음 작업

- 별도 브랜치에서 GitHub Actions product CI에 pytest 실행 단계를 추가한다.
