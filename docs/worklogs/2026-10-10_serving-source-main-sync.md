# 운영 실행 소스 main 동기화

사용자가 운영 사이트를 최신 기준으로 main과 동일하게 만들도록 지시했고, 운영 실행 코드 기준 통합 및 main 평가·개발 자료 보존을 승인했다. PR 생성·즉시 merge·배포 승인 범위에서 진행한다.

프런트 기준 dpl_JAwKCE3zfgof5TDxe2A6GevT3AxQ. 181파일 source SHA1=Vercel UID 전체 일치, JS/CSS 재빌드 동일. main 전용 테스트·문서를 보존하고 운영의 PDF/이력서·채팅 히스토리·페이지 화살표를 이관한다. 소개 entry와 URL 정합성 수정 포함. 운영 기존 3개 src 테스트는 자동 자료 이관 금지, 재시작 이전 채팅 보존, 다음 단계 user bubble 동작에 맞춰 기대값을 정합화했다. verification 개발 fixture는 제품 source에 포함하지 않는다. 프런트 279 tests/build 통과.

백엔드 기준 traffic100%=malhaebom-mk2-custom-question-1010, image sha256:a8a5ab966d8742dede8e1400426f20035dc7d71dc2b965c12394070d1f6eca19. 직접 추출본 runtime136파일 기존 원본과 동일. 서비스 template 최신 image는 traffic 기준과 달라 사용하지 않는다.

운영의 custom-question·resume-assist·README 추가·저장 동의 기능과 운영 Skill v6를 기준으로 통합한다. main의 Prompt 후보 선택, 보안 입력 경계, 버전 provenance 보완은 제거하지 않는다. 기존 main Skill v6.2 candidate는 evals/candidates/main-before-production-sync-20261010/skills/interview-coach/에 byte 그대로 보존한다. 원격 Prompt label과 DB 환경은 변경하지 않는다. 배포는 최종 main 소스로 수행해 통합 후 main과 운영 실행 소스를 맞춘다.

CI는 GitHub 계정 billing 문제로 job이 시작되지 않으므로 로컬 동등 검증으로 대체한다. 검증 완료 및 실제 배포 결과는 후속 기록한다.


### 운영 smoke에서 발견한 이력서 API 경계 수정
첫 staging revision의 정상 형식 비인증 요청이 401 대신 422였다. 개인정보를 숨기는 validation 응답이 관측 middleware에도 잘못 적용돼 모든 resume-assist 요청을 차단했다. middleware의 무조건 반환만 제거하고 RequestValidationError handler의 비식별 422는 유지한다. 실제 create_app 전체 middleware 경로를 검사하는 2개 회귀 테스트를 추가해 해당 모듈 11 tests 통과. 수정된 main 이미지를 새 revision에 재배포해 401/health 확인 후 전환한다.


### 최종 운영 반영
- PR #240–#249 생성·attach·merge. 제품 main fef359c4a243ba6935762cabd2f0d65fcec19119. 평가 candidate 자료 byte 보존, 운영 기능 통합 및 main 안전장치 유지.
- Vercel dpl_DzgZXQjBThyCAeweLygj13wQQ5dr에 양쪽 기존 도메인을 연결했다. 6 HTML 경로와 app CSS/JS 바이트가 production main build와 일치한다. 브라우저 양쪽 소개→기존 로그인 상태 채팅, 서비스 홈→소개 복귀 확인.
- Cloud Run malhaebom-mk2-main-sync-final-1010, immutable digest d62f8b285890a74e00a8b632de36311fefc2ca3954a4fedbf4c76b21e682bf36. 기존 운영 이미지의 dependency/model layer를 보존하고 main runtime source를 overlay한 이미지다. 추적 152파일 SHA256 전체 일치. 기존 revision의 env·secret 참조·CPU/메모리·서비스 계정·timeout/concurrency·probe 설정 비교 일치.
- frontend 279 tests/build, 기존 backend 832 tests + 신규 회귀 11 tests 통과. gitleaks 통합 commit 범위 no leaks. 원본 font license의 후행 공백 2줄은 source 원문 보존을 위해 수정하지 않았다.
- 신규 Google OAuth 완료 및 실녹음/STT/코칭/DB 전체 E2E는 이번 변경에서 재실행하지 않았다. 10/10 후속 배포이며 제출 마감 전 증거로 소급하지 않는다.

- 최종 공개 API health 200·비인증 polish 401 및 새 revision 트래픽 100%를 확인했다. Cloud Run은 업로드 OCI index d62f8b…의 linux/amd64 child manifest babddf0dd39af709e33841aeafc018479cfd22081807021cbe062fece61055f9로 실행한다.
