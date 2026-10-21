# 운영 소스의 GitHub 동기화

## Why
운영 Cloud Run 이미지와 Vercel 업로드 원본이 GitHub main보다 앞선 기능을 포함한다. 운영을 수정하지 않고 저장소에서 재현·검토할 수 있어야 한다.

## Goal
확보한 운영 파일의 차이를 전부 분류하고 활성 기능을 저장소에 반영한다. Langfuse latest/production 숫자 버전과 본문 해시를 별도 고정한다. 머지·배포·원격 설정·DB 변경은 범위 밖이다.

## What
- Cloud Run traffic 100% revision의 immutable image를 기준으로 백엔드 소스를 추출한다.
- 실제 도메인이 가리키는 Vercel deployment의 업로드 원본을 조회하고 SHA1을 검증한다.
- 동일·수정·운영 전용·GitHub 전용 파일과 폴더를 분류한다. GitHub 전용 파일을 배포 누락만으로 삭제하지 않는다.
- 자유채팅, 동의·단계 변경, 참고정보, 로딩, 전사 후처리, 요청 추적 및 화면을 복원한다.
- 기존 GitHub의 인증·만료·버전 기록·출력 안전 경계 개선과 테스트는 보존한다. 이는 운영 원본과의 의도적인 차이로 기록한다.

## How
- 기준 main: fd9a6b9b0770124ba8ea7c77f017018d648e12c7.
- Cloud Run: malhaebom-mk2-request-trace-linkage-1009, image sha256:fbfb2840cd3d3190d321cfb2a2c86af8931f5970cdca8e884ceaa31fc17b7465.
- Vercel: dpl_CAho6AFsXoDTorgn3V8X9i47QVbE.
- Langfuse: 운영 설정이 선택한 이름의 latest와 production을 각각 조회한다. 실험 Prompt와 실제 선택 Prompt를 섞지 않는다.
- 과거 평가 snapshot·문서와 local fallback을 원격 최신 본문으로 덮어쓰지 않는다. 최신 원격 본문은 숫자 버전별 독립 snapshot에 보존한다.
- secret·사용자 데이터·checkpoint·cache·빌드 산출물은 커밋하지 않는다.
- 기능/책임 단위 커밋 및 PR로 리뷰 크기 정책을 준수한다.

## AC
- Given 고정 운영 원본, When 비교, Then 모든 비교 경로의 상태와 해시·제외 이유를 기록한다.
- Given 현재 GitHub 회귀 테스트, When 운영 기능을 통합, Then 인증·만료·기록 provenance 검사는 유지한다.
- Given Langfuse latest/production, When snapshot, Then name/version/hash로 재검증할 수 있다.
- Given 검증된 수정, When PR 생성, Then OPEN이며 mergedAt=null이고 운영에는 변경이 없다.
