# GitHub README 제출 후 Gemini 기술 스택·프로젝트 흐름 분석

## Why

- 사용자가 역량을 선택하고 프로젝트 README를 제출한 뒤, 문서에 적힌 기술과 서비스 흐름을 한눈에 확인할 수 있게 한다.
- 이전 [README 링크 제출 Spec](github-readme-link-chat.md)은 링크 표시까지만 다뤘다. 이번 후속 요청은 실제 README 조회와 Gemini 분석을 추가한다.
- 새 OpenRouter 키에서 짧은 모델 요청은 성공하지만 README 구조화 요청은 출력 상한이 없어 최대 65,536토큰 예약 비용으로 402가 발생했다. GitHub의 일시적인 연결 실패도 현재는 즉시 503으로 표시된다.

## Goal

- 유효한 공개 GitHub README 링크를 제출하면 서버가 README를 읽고 `google/gemini-3.8-flash`로 기술 스택 1~8개와 프로젝트 흐름 1~6단계를 분석해 채팅에 표시한다.
- 모든 기술·흐름 항목은 README에 존재하는 원문 근거를 포함한다. 팀 README만으로 개인 구현·역량을 확정하지 않는다.
- **Out of Scope**: 저장소 전체 코드 검토, 비공개 저장소 접근, 사용자별 기여도 판정, 코칭 점수 반영, DB 저장.

## What

1. 기존 링크 입력이 제출되면 사용자 링크 말풍선을 보이고 분석 중 메시지를 표시한다.
2. 서버는 GitHub REST API에서 저장소 기본 README 또는 제출한 `blob/{ref}/.../README.md` 파일을 가져온다. `5Headers/team_project_backend` 저장소 주소도 이 경로로 처리한다.
3. Gemini 3.8 Flash가 README에 명시된 기술과 기능 흐름을 한국어로 정리한다. 서버는 JSON 형식과 각 원문 근거의 실제 포함 여부를 확인하고 검증된 결과만 반환한다.
4. 채팅에 기술 스택·프로젝트 흐름·README 출처를 표시한다.

**예외**

- 잘못된 링크, README 없음, 비공개/접근 불가, 파일 과대, GitHub 또는 모델 오류는 결과를 만들지 않고 오류와 재시도·주소 수정 동작을 제공한다.
- 로그아웃 사용자는 분석 API를 호출하지 않는다.

## How

- 인증된 `POST /api/github/readme/analyze` 요청 본문은 `source_url` 하나를 받는다. 응답은 `source_url`, `readme_sha`, `model`, `technology_stack[]`, `project_flow[]`을 가진다.
- 서버가 URL의 HTTPS GitHub 호스트·저장소/README 경로를 검증한 뒤 고정된 `api.github.com` 호스트의 GitHub REST contents/README endpoint만 호출한다. 리디렉션·임의 호스트 조회는 허용하지 않는다.
- 공개 README는 UTF-8 Markdown, 최대 256 KiB로 제한한다. README 원문은 서버에서 모델로 전달하며 브라우저나 DB에 저장하지 않는다.
- 기존 `OPENROUTER_API_KEY`와 OpenAI 호환 JSON provider를 재사용하고 README 분석 모델 ID는 `google/gemini-3.8-flash`로 고정한다.
- README 분석 요청의 출력은 최대 3,072토큰으로 제한한다. 다른 코칭 요청의 출력 한도는 바꾸지 않는다. OpenRouter 402는 키의 크레딧·사용 한도 안내로 구분한다.
- GitHub README 조회의 일시적인 연결·시간 초과·서버 5xx에는 한 번 재시도한다. 404와 다른 영구 오류는 재시도하지 않는다.
- 근거 문구를 검증할 때 Markdown의 `**` 강조와 코드 백틱은 제거하고 나머지 문자가 원문에 연속해서 있는지 확인한다. 배지·URL 조합 등 불일치 항목은 한 번 재요청한다. 마지막 응답에서도 불일치 항목이 남으면 그 항목만 제외하고 각 범주에 검증된 항목이 하나 이상 있을 때만 결과를 반환한다. README 내 지시는 분석 대상 데이터로만 취급한다.

## AC (Given-When-Then)

- **AC-01** GIVEN 로그인 사용자가 공개 GitHub README 주소를 제출함, WHEN API와 Gemini가 정상 응답함, THEN 기술 스택과 프로젝트 흐름이 근거와 출처를 포함해 코치 메시지로 나타난다.
- **AC-02** GIVEN `https://github.com/5Headers/team_project_backend` 주소, WHEN 서버가 README를 조회함, THEN 저장소 기본 `README.md`를 가져온다.
- **AC-03** GIVEN 모델이 README에 없는 근거를 반환함, WHEN 검증함, THEN 해당 항목을 사용자에게 표시하지 않고 한 번 재시도한다. 이후에도 불일치가 있으면 검증된 기술·흐름만 표시하며 어느 범주든 검증된 항목이 없으면 실패를 알린다.
- **AC-04** GIVEN 외부 호스트·다른 파일·비공개/없는 README·과대 본문, WHEN 분석을 요청함, THEN 모델을 호출하지 않거나 안전한 실패 상태를 반환한다.
- **AC-05** GIVEN 링크 제출 후 분석 중 또는 실패, WHEN 채팅을 볼 때, THEN 진행 상태 또는 오류와 재시도·주소 수정 동작이 보인다.
- **AC-06** GIVEN 적은 사용 가능 크레딧의 키, WHEN README 분석 요청, THEN 요청 출력 한도를 명시해 과도한 토큰 예약 없이 분석한다. 그래도 402면 키 한도 안내를 보여준다.
- **AC-07** GIVEN GitHub가 일시적으로 연결 실패 또는 5xx를 반환함, WHEN README를 조회함, THEN 한 번 재시도하고 성공하면 분석을 계속한다.
