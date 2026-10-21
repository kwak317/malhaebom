# Worklog — 최신 main의 공통 provider SDK 전환

- 직접 HTTP 호출만 SDK with_raw_response.create로 바꿨다. 모델·키·의존성은 유지한다.
- SDK retry=0이며 main의 전송 재시도·계약 repair·비용 제한·usage·관측 규칙은 보존한다.
- 테스트 transport를 실제 httpx.MockTransport로 바꿔 SDK 전송과 서버 오류 매핑을 검증한다.
- 전체 backend 461테스트(14.293초), frontend 24파일/90테스트 및 TypeScript·Vite build 통과.
- 실제 사용자 E2E는 별도이며 제출용 평가/mock/프롬프트 자료는 포함하지 않는다. PR만 생성하고 머지하지 않는다.
