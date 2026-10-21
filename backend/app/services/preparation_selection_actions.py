"""선택 후보 검토·동의·검증은 서버 상태로 처리한다. 진행 중 세션은 변경하지 않는다."""
from __future__ import annotations

import re
from uuid import UUID, uuid4
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.applicant_context import ApplicantContext
from app.services.coaching_questions import PRESET_QUESTION_IDS, get_preset_coaching_question
from app.services.ncs_competency import _REVIEWED_OPTIONS
from app.services.preparation_conversation_repository import PreparationConflict


class SelectionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_posting_id: UUID | None = None
    requirement_ids: list[UUID] = Field(default_factory=list, max_length=2)
    question_id: str | None = None
    custom_question_text: str | None = Field(default=None, max_length=200)
    selected_ncs_ids: list[str] = Field(default_factory=list, max_length=9)

    @model_validator(mode="after")
    def validate_selection(self):
        if len(set(self.requirement_ids)) != len(self.requirement_ids):
            raise ValueError("중복 요구사항")
        ApplicantContext(selected_ncs_ids=self.selected_ncs_ids)
        self.custom_question_text = self.custom_question_text.strip() if self.custom_question_text else None
        if self.question_id and (self.custom_question_text or get_preset_coaching_question(self.question_id) is None):
            raise ValueError("질문 선택 오류")
        return self


class SelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: Literal["ncs", "job", "requirements", "question"]
    operation: Literal["replace", "add", "remove"]
    target_ids: list[str] = Field(max_length=9)


def selection_options(repository, user, selection):
    jobs = repository.selection_options(user) if hasattr(repository, "selection_options") else []
    current = (selection or {}).get("job")
    if current and current.get("id") and not any(str(j.get("id")) == str(current.get("id")) for j in jobs):
        jobs = [*jobs, current]
    return {
        "ncs": [{"id": r[0], "label": r[2]} for r in _REVIEWED_OPTIONS],
        "jobs": [{"id": str(j["id"]), "label": str(j.get("title", "")), "company": j.get("company", ""),
                  "requirements": [{"id": str(r["id"]), "label": r.get("requirement_text", r.get("text", ""))}
                                   for r in j.get("job_requirements", j.get("requirements", []))]} for j in jobs],
        "questions": [{"id": q, "label": get_preset_coaching_question(q).text} for q in sorted(PRESET_QUESTION_IDS)]}


def snapshot(request):
    values = request.selection.model_dump(mode="json") if request.selection else {}
    values["selected_ncs_ids"] = request.review_context.selected_ncs_ids if request.review_context else []
    return SelectionSnapshot.model_validate(values).model_dump(mode="json")


def validate_snapshot(repository, user, values):
    result = SelectionSnapshot.model_validate(values)
    if result.requirement_ids and result.job_posting_id is None:
        raise PreparationConflict("공고를 먼저 선택해 주세요.")
    if result.job_posting_id:
        repository.selection_context(user, result)
    return result.model_dump(mode="json")


def propose_selection(repository, user, values, revision, proposal, options, message):
    if re.search(r"[?？]|하지|말고|않|인가|하면|라면", message) or not re.search(r"선택|추가|취소|바꿔|바꾸|변경|빼|제외|골라", message):
        raise PreparationConflict("선택을 실제로 변경할지 먼저 알려 주세요.")
    p = SelectionRequest.model_validate(proposal)
    if len(set(p.target_ids)) != len(p.target_ids):
        raise PreparationConflict("선택 항목이 중복됐어요.")
    lists = {"ncs": options["ncs"], "job": options["jobs"], "question": options["questions"],
             "requirements": next((j["requirements"] for j in options["jobs"] if j["id"] == values.get("job_posting_id")), [])}
    known = {item["id"]: item["label"] for item in lists[p.kind]}
    if not set(p.target_ids).issubset(known):
        raise PreparationConflict("현재 선택할 수 없는 항목이에요.")
    next_values = dict(values)
    key = {"ncs": "selected_ncs_ids", "requirements": "requirement_ids", "job": "job_posting_id", "question": "question_id"}[p.kind]
    old = next_values[key]
    current = list(old) if isinstance(old, list) else [old] if old else []
    if p.operation == "replace":
        chosen = p.target_ids
    elif p.operation == "add":
        chosen = list(dict.fromkeys([*current, *p.target_ids]))
    else:
        if not p.target_ids or not set(p.target_ids).issubset(current):
            raise PreparationConflict("취소할 현재 선택 항목을 확인해 주세요.")
        chosen = [item for item in current if item not in p.target_ids]
    if p.kind in {"job", "question"}:
        if len(chosen) > 1:
            raise PreparationConflict("하나의 항목만 선택할 수 있어요.")
        next_values[key] = chosen[0] if chosen else None
    else:
        next_values[key] = chosen
    if p.kind == "job" and next_values[key] != old:
        next_values.update(requirement_ids=[], question_id=None, custom_question_text=None)
    if p.kind == "question":
        next_values["custom_question_text"] = None
    next_values = validate_snapshot(repository, user, next_values)
    if next_values == values:
        return None
    labels = [known[item] for item in chosen]
    return {"id": str(uuid4()), "base_revision": revision, "before": values, "after": next_values,
            "summary": "변경할 선택: " + (", ".join(labels) or "선택 해제") +
                       ("\n공고 변경 시 요구사항과 질문 선택을 초기화합니다." if p.kind == "job" else ""),
            "confirmation_requested": True}


def selection_consent(pending, history, message):
    if not pending or not pending.get("confirmation_requested"):
        return False
    if not history or history[-1].get("role") != "assistant" or history[-1].get("selection_candidate_id") != pending["id"]:
        return False
    normalized = re.sub(r"[,.!，。！]", " ", message).strip()
    return bool(re.fullmatch(r"(?:이\s*선택(?:대로|으로)?\s*)?(?:선택\s*)?(?:변경해\s*(?:줘|주세요)|적용해\s*(?:줘|주세요))|네|응|예|좋아요|맞아요", normalized))
