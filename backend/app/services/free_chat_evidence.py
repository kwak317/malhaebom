"""출처·행위자·경험 관계를 서버가 구분해 생성 근거로 제공한다."""
from __future__ import annotations
import re


def evidence_catalog(context):
    result = []
    def add(id, text, actor, relation):
        result.append(dict(id=id, text=text, actor=actor, relation_id=relation))
    materials = (context.get("verified_context") or {}).get("materials") or {}
    for i, fact in enumerate((materials.get("resume_profile") or {}).get("facts", [])):
        add(f"resume:{i}", fact["value"], "self", f"resume-fact:{i}")
    readme = materials.get("readme_analysis") or {}
    for kind in ["technology_stack", "project_flow"]:
        for i, item in enumerate(readme.get(kind, [])):
            add(f"readme:{kind}:{i}", item.get("source_excerpt") or item.get("description", ""), "team", "readme-project")
    for item in context.get("source_messages", []):
        relation = "statement:" + item["message_id"]
        # 기술 정정에서 기존 사실과 최신 진술은 같은 대상이다. 대상이 하나로
        # 식별될 때만 연결하며, 무관한 경력/기술 사실의 관계는 합치지 않는다.
        if re.search(r"빼|제외|정정|안\s*썼|사용하지", item["text"]):
            tokens = {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9+#.]+", item["text"])}
            targets = [source for source in result if source["id"].startswith("resume:")
                       and tokens.intersection(token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9+#.]+", source["text"]))]
            if len(targets) == 1:
                relation = targets[0]["relation_id"]
        add("statement:" + item["message_id"], item["text"], "self", relation)
    for draft in context.get("confirmed_supplemental_context", []):
        for i, fact in enumerate(draft.get("facts", [])):
            add(f"confirmed:{draft['draft_id']}:{i}", fact["value"], "self", "statement:" + fact["source_message_id"])
    coaching = context.get("coaching_context") or {}
    answer = coaching.get("confirmed_answer") or ""
    relation = "answer:" + str(coaching.get("answer_revision_id") or "current")
    for segment in coaching.get("answer_segments") or []:
        # 현재 세션의 확정 답변 원문과 일치하는 서버 조회 segment만 허용한다.
        if segment.get("segment_id") and segment.get("text") and segment["text"] in answer:
            actor = "team" if re.search(r"(?:팀|동료|다른\s*사람)(?:이|은|가|에서|의)\s", segment["text"]) else "self"
            add(segment["segment_id"], segment["text"], actor, relation)
    if answer and not any(item["relation_id"] == relation for item in result):
        # 구세션에 segment가 없으면 문장별로 보존해 팀·개인 수행을 섞지 않는다.
        for i, sentence in enumerate(re.split(r"(?<=[.!?])\s+", answer)):
            actor = "team" if re.search(r"(?:팀|동료|다른\s*사람)(?:이|은|가|에서|의)\s", sentence) else "self"
            add(f"{relation}:{i}", sentence, actor, relation)
    return result


def validate_draft_claims(out, catalog):
    # 설명 속 개인 경험 주장도 작성안과 같은 출처·관계 검증을 받는다.
    if out.answer_kind == "draft" and not out.draft_claims:
        raise ValueError("free_chat_draft_evidence_required")
    known = {item["id"]: item for item in catalog}
    for claim in out.draft_claims:
        if claim.text not in out.message or not claim.source_ids or len(set(claim.source_ids)) != len(claim.source_ids):
            raise ValueError("free_chat_draft_claim_mismatch")
        if not set(claim.source_ids).issubset(known):
            raise ValueError("free_chat_unknown_evidence")
        sources = [known[id] for id in claim.source_ids]
        if claim.actor == "self" and any(item["actor"] != "self" for item in sources):
            raise ValueError("free_chat_team_as_personal_experience")
        if len({item["relation_id"] for item in sources}) > 1:
            raise ValueError("free_chat_unlinked_experiences")
