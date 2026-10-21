# 최신 운영 배포 구성 합성 30건 × 3회 원본 결과

2026-10-06에 운영 트래픽 100% revision의 불변 이미지에서 새로 실행했다. GitHub main의 미배포 변경과 기존 10/5 응답을 혼합하지 않았다.

- [평가 보고서](../../../docs/evidence/coaching-repeat3-2026-10-06.md)
- [배포 구성](deployment-pin.json), [통합 결과](aggregate.json), [SHA256](sha256.json)
- [평가 입력·기대 정답](dataset.v2.jsonl), [실제 system Prompt](system_prompt.txt), [Skill 번들](skill_bundle.txt), [평가 runner](run_deployed_eval.py)
- [1회 원본](run-1/responses.jsonl) · [manifest](run-1/manifest.json) · [summary](run-1/summary.json)
- [2회 원본](run-2/responses.jsonl) · [manifest](run-2/manifest.json) · [summary](run-2/summary.json)
- [3회 원본](run-3/responses.jsonl) · [manifest](run-3/manifest.json) · [summary](run-3/summary.json)

## 원본 형식

JSONL 한 행이 한 사례다. question/context는 합성 입력, expected는 채점용 정답이다. 모델 입력은 question와 server_context만이며 expected·평가 라벨은 전달하지 않는다. attempts[].raw_output과 http_responses[].content는 실제 모델 출력, response는 서버 계약 검증 후 결과, score와 overall_automatic_pass는 자동 채점이다. 토큰·비용·응답 완료 시간·오류·복구 시도도 보존했다.

응답 파일은 이번 실행 산출물과 byte 일치한다. 실제 사용자 답변·공고·JWT·API key·세션 개인정보는 없다. 가상 case/segment ID는 평가셋의 ID다. 응답 문자열을 편집하거나 성공 사례만 고르지 않았다.

## 재현 조건

배포 pin의 image를 사용하고 runner와 dataset을 /results에 마운트한다. manifest와 동일한 공개 코칭 설정 및 승인된 제공자 자격증명을 환경변수로 전달한 뒤 /results/run_deployed_eval.py를 실행한다. 기존 responses.jsonl이 있으면 runner가 덮어쓰기를 거부한다. 원본 열람·집계에는 유료 runner 실행이 필요하지 않다.

배포 이미지의 생성·계약 검증·복구 경로를 평가 runner에서 호출했다. 인증 HTTP·MCP·STT·DB 저장 경로를 실행한 운영 사용자 E2E나 새 사람 평가가 아니다. 3회의 intent/C/A/V 판정 일치는 원문 동일성이나 사람 품질 일치도가 아니다. R/D·공고 관련성·실제 사용자 일반화는 평가하지 않았다.
