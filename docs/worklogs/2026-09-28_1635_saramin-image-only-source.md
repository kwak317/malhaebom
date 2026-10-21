# Worklog — 이미지 전용 사람인 공고의 선택 오류

- 일시: 2026-09-28 16:35~16:40 KST
- 관련 요청: 공고 선택 후 503 및 원문 근거 요구사항 실패 화면
- 관련 명세: [백엔드 공고 후보 추천](../specs/saramin-backend-recommendations.md)

## 목적과 원인

검색 결과의 공고를 선택할 때 분석 가능한 모집 상세만 전달하고, 이미지 전용 상세를 주변 사이트 문구로 잘못 분석하는 경로를 차단한다.

메일플러그 `rec_idx=55032635` 원문은 HTTP 200이지만 `user_content jobsViewDetail_55032635`가 이미지 한 장이었다. 기존 `상세요강~근무지위치` 추출 결과는 개인정보 보호 안내와 복리후생 542자였고 실제 업무·자격요건이 아니었다. 이 입력에서 원문에 근거한 요구사항을 만들 수 없어 분석 API가 503을 반환했다. 검색 연결이나 토큰 만료 오류가 아니다.

## 변경

- 명세를 먼저 보완하고 `SaraminPostingVerifier`에 상세 영역 추출기를 추가했다. 중첩 태그의 표시 텍스트를 수집하며 script/style/noscript와 영역 밖 문구는 제외한다.
- 상세 영역이 존재하지만 비어 있거나 20자 미만이면 추천에서 제외한다. 영역이 없는 구형 페이지의 기존 추출 경로는 안내문 시작점에서 자른다.
- 이미 표시된 이미지 공고를 선택하면 분석할 상세 텍스트를 확인하지 못했다고 안내한다. LLM 호출·목록 조회·저장 전에 거부한다.
- OCR이나 요구사항 추측을 추가하지 않았다. 기존 모델의 재시도·원문 인용 검증, 웹검색 클래스와 UI를 유지했다.
- 기존 미커밋 변경을 보존했다. 수정 전 관련 소스·테스트·명세·상태 문서는 workspace 루트 `output/mcp/saramin-source-details-20260928/before/`에 백업했다. commit/push/PR/merge 없음.

## 검증

```text
격리된 기존 API 이미지 + 수정 소스 read-only mount + --network none
test_saramin_recommendation.py: 39 PASS
test_playmcp_job_search.py: 14 PASS
전체 backend/tests: 338 PASS (11.529초)
docker compose up -d --build --no-deps api: PASS
```

추가 회귀 테스트 4개는 상세 본문만 추출, 이미지의 alt/주변 문구로 대체 금지, 짧은 상세 거부, 이미지 선택 API의 모델·저장 미호출을 확인한다.

실행 이미지에서 실제 외부 원문·모델을 사용한 TestClient 검증:

| 요청 | 결과 |
| --- | --- |
| 메일플러그 이미지 공고 선택 | 503과 정확한 안내, 분석/목록/저장 호출 모두 0회 |
| 펄포즌 `rec_idx=54626054` 텍스트 공고 선택 | 201, 상세 1,064자, 실제 모델 요구사항 5개, 모든 인용이 실제 상세 본문과 일치, 5.491초 |
| `skill-server` PlayMCP 검색 | 200, 원문 검증된 3건, 메일플러그 제외, 2.090초 |

실제 모델은 `google/gemini-3.5-flash-lite`다. 선택 API는 테스트 인증과 메모리 저장소를 사용해 실제 사용자 DB에 쓰지 않았다. 검색 결과는 펄포즌·폴리큐브·솔트룩스이며 속도는 이번 단일 측정값이다.

- 새 API: `8c51d6bc6185`, 이미지 `sha256:1f83cebbea4d87dd04a7fe6d2557e8a8baaaf865474b44a53a4d6b964268d34a`, healthy.
- frontend: 기존 `a097d23271ce` 유지, healthy.
- 실행 API health와 frontend `/practice` HTTP 200, 실제 미인증 공고 선택 HTTP 401을 확인했다. 호스트/실행 컨테이너의 추천 소스 SHA256은 `39954854a341b42c0e69dbc31a569c59e360ea740d7d5ae4c96208026b044775`로 일치한다.
- 초기 백업과 변경 범위를 검토했고 기존 `SaraminWebSearch` 본문은 정확히 일치한다. 변경 줄과 상태/아키텍처 문서의 whitespace 검사는 통과했다. 전체 `git diff --check`는 이번에 수정하지 않은 `.github/PULL_REQUEST_TEMPLATE.md`의 기존 trailing whitespace 2건 때문에 실패했으며 그 파일은 변경하지 않았다.
- 실행 증빙: workspace 루트 `output/mcp/saramin-source-details-20260928/live-api-verification.json`. 비밀값은 기록하지 않았다.

## 제한과 사용 안내

실제 로그인 브라우저의 공고 저장·요구사항 선택·녹음·코칭 E2E는 수행하지 않았다. 이미지뿐인 상세는 현재 지원하지 않으며 추천 수가 줄어들 수 있다. 이전 결과의 메일플러그 카드는 화면에서 `다시 검색`을 눌러 갱신한다.

## 최신 main 기준 수정 PR

- 최신 `origin/main` `5c495d5`의 별도 checkout에 이미지 상세 수정만 적용했다. PlayMCP 공급자 변경과 팀의 다른 기능은 이 PR에 포함하지 않는다.
- 중복 확인 후 [Issue #98](https://github.com/aihuman-7th/proj2-3/issues/98)에 재현·원인·기대 동작을 기록했다.
- 최신 main 요구에 맞춘 검증 이미지에서 backend 전체 475개가 통과했다(추천 테스트 39개 포함). 변경 범위·diff·비밀값 검사를 통과했다.
- 위 로컬 실모델·실행 컨테이너 기록은 원래 작업 당시 검증이다. 최신 main 통합 branch의 로그인/저장 E2E를 새로 확인했다고 주장하지 않는다. 사용자 요청으로 commit/push/PR만 수행하며 merge하지 않는다.
