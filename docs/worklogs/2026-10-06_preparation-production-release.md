# 준비 대화 v3.1 운영 적용 검증 (2026-10-06)

사용자 승인 범위의 PR 생성/push/배포를 완료했으며 GitHub PR merge는 수행하지 않았다. UI #191, Prompt/Skill #192, 합성 평가 #193, 서버 정책 #194, 실행 연결 #195를 분리했다.

운영 backend는 `malhaebom-mk2-preparation-1006-1803`, 100% traffic, image `sha256:95efe4b2b8036e90847d82643acf38323b15fa71f81cf8afd164a0928d1418c2`다. 기존 `malhaebom-mk2-prompt-cache-1006`의 workspace/cache/메인 코칭 Prompt·Skill 설정을 보존했다. frontend는 `dpl_6YGZMAyR77HnpU223uzrGqyXpZCQ`, 공개 주소는 https://malhaebom.xyz/practice 이다. JS `index-tssu52Ex.js`, CSS `index-BCcmAD_q.css`를 실제 내려받아 prebuilt bytes와 일치시켰다.

새 대화는 Gemini 3.5 Flash Lite, Langfuse `malhaebom-preparation-conversation` version 1이다. 실제 system Prompt hash `946cdf8eec01b3d3cd414299eea14477bc6a1d802baea042a2be4ab72ab22314`는 평가본과 같다. 준비 상태 table/RLS/권한 및 24시간 만료·정리 작업을 운영 DB에 적용했다.

검증: Cloud Build backend 124 tests, 운영 frontend 기준 157 tests 및 build 통과. 실제 임시 Auth 계정으로 대화 6턴/10 API·DB 검사(익명 401, 동의 저장, 재시도 idempotence, 본인 read/직접 write 차단, 연습 bind, 실제 코칭 후 질문, 명시적 재답변 action, 범위 밖 질문 stay)를 통과했다. 코칭 질문은 실제 저장된 1차 확정 답변/실제 provider 코칭을 조회해 답했다. 공개 브라우저에서 NCS 질문→응답, 경력 요약→확인→저장 완료를 표시하고 DB confirmed=1을 확인했다. 최종 스타일 수정 후에도 로그인 채팅 응답과 말풍선/입력창을 다시 확인했다. 임시 계정·세션·상태 파일을 정리했다.

발견/해결: JSON의 연속 `}}`를 공통 템플릿 검증기가 오류로 해석해 startup 503이 발생했다. 준비 대화에서 허용 슬롯만 단일 치환하도록 수정하고 system hash 동일성을 확인했다. 자연어 재답변 전환 표현을 서버가 거절하던 부분은 명확한 진행 표현과 부정 요청을 구분하도록 보완했다. 운영 frontend 합성 과정의 빈 CSS를 최종 스크린샷에서 발견해 기존 frontend로 즉시 복구한 뒤 운영 CSS 769줄+새 규칙 5줄로 재빌드/재적용했고 실제 스타일·asset hash를 검증했다.

Langfuse 실제 관측은 18개 observation 중 `preparation.chat` 7개이며 모델/버전 metadata를 확인했다. 기존 trace 조회 API 410에 따라 공식 Observations API v2로 조회했다. 합성 사용자 가명키와 호출 시간으로 대응하며 Cloud Run revision이 trace에 직접 저장된 증거는 아니다.

증거: `evals/results/preparation-production-20261006/`의 manifest, raw synthetic response, 관측 metadata, 공개 asset hash, 브라우저 스크린샷. Auth token/비밀키/실제 사용자 자료는 포함하지 않는다. STT 결과만 저장된 합성 fixture이며 실제 마이크→음성 업로드→STT 전체 E2E 검증을 뜻하지 않는다. 이전 12×3 평가 원본은 #193의 별도 로컬 provider 증거다.
