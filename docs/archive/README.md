# 과거 자산 보관

현재 제품 파일은 backend/frontend/skills/prompts/configs/supabase/mcp_server의 기존 경로를 따른다. 이 폴더는 실행에 사용하지 않는 공개 자산을 보존한다.

## 소개페이지 과거 데모

[원본·이동 hash](showcase-demo-assets/manifest.json): PR #251로 교체된 소개용 WebP 4개. 실행 HTML/JS/CSS/스크립트에서 참조하지 않는 것을 확인하고 이동했다.

- [질문 선택](showcase-demo-assets/demo-start.webp)
- [녹음 준비](showcase-demo-assets/demo-record-ready.webp)
- [녹음](showcase-demo-assets/demo-recording.webp)
- [분석](showcase-demo-assets/demo-analysis.webp)

[최초 이관 manifest](../showcase/import-manifest.json)는 당시 목적지와 hash 기록이며, 해당 네 자산의 현재 보존 위치는 위 manifest를 따른다. frontend/src/assets의 PNG 데모는 demoRouter/디자인 화면에서 참조되므로 유지한다. 과거 문서·평가 결과는 재현 경로를 보존하기 위해 이동하거나 삭제하지 않는다.
