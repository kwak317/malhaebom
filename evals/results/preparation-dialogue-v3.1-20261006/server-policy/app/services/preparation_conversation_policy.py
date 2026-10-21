"""서버 소유 문맥으로 준비 대화의 요청을 검증한다. 저장·화면 전환을 직접 실행하지 않는다.

호출자는 인증된 사용자·연습 범위의 문맥을 조회하고, 승인 후에도 저장 직전
초안 버전을 재확인해야 한다. 완료 안내는 저장소/화면 처리 성공 후에만 만든다.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from app.schemas.preparation_conversation import PreparationConversationOutput


class PreparationPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class PreparationDecision:
    action: str
    message: str
    follow_up_question: str | None
    draft_id: str | None = None
    draft_version: int | None = None
    requested_stage: str | None = None
    response_source: str = "model"


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise PreparationPolicyError(code)


def explicit_profile_consent(context: dict[str, Any]) -> bool:
    """명확한 반영 요청만 인정한다. 모호한 발화는 확인을 다시 받아야 한다.

    confirmation_requested는 모델 값이 아니라 검증된 최신 요약과 확인 질문을
    실제 표시한 뒤 서버가 기록한 값이어야 한다.
    """
    pending = context.get("pending_profile_update") or {}
    if pending.get("status") != "awaiting_confirmation" or not pending.get("confirmation_requested"):
        return False
    text = str(context.get("user_message") or "").strip()
    if re.search(r"[?？]|(?:하지|말고|않|취소|아니|잘못|수정|바꿔|고쳐|라면|하면|인가|친구)", text):
        return False
    request = re.search(r"(?:반영|저장)(?:해\s*줘|해\s*주세요|해\s*주십시오)", text)
    if request:
        # 새로운 정보 추가와 동의를 혼합하면 원문을 다시 확인한다.
        return bool(re.search(r"(?:맞아|맞아요|맞습니다|네[, .]|정리한|요약한)", text)) and not bool(
            re.search(r"(?:새로운|근무했|담당했|개발했|기업에서)", text)
        )
    if text.rstrip(".! ") not in {"네", "예", "응", "맞아", "맞아요", "맞습니다"}:
        return False
    history = context.get("conversation_history") or []
    if not history or history[-1].get("role") != "assistant":
        return False
    question = history[-1].get("follow_up_question") or ""
    return bool(re.search(r"반영.*(?:할까요|동의)|저장.*(?:할까요|동의)", question))


def decide_preparation_action(raw: dict[str, Any], context: dict[str, Any]) -> PreparationDecision:
    """모델 출력은 제안이며 서버의 최신 상태·원문·동의가 최종 권한이다."""
    out = PreparationConversationOutput.model_validate(raw)
    message, question = out.message, out.follow_up_question
    response_source = "model"
    # 내용과 상태 필드는 그대로 검증한다. 반복 안내의 표시 문구만 서버가 소유한다.
    if out.next_action == "stay" and out.requested_stage is None and out.profile_update is None:
        if out.intent == "out_of_scope":
            message, question = "저는 직무와 면접 준비를 돕고 있어요. 현재 검토 중인 내용을 이어서 도울 수 있어요.", None
            response_source = "server_fixed"
        elif out.intent == "refusal":
            message, question = "요청하신 내용은 도와드리기 어려워요. 실제 경험을 바탕으로 직무와 면접 준비를 도울 수 있어요.", None
            response_source = "server_fixed"
        elif out.intent == "answer" and re.fullmatch(
            r"(?:알겠어\s*[,，]?\s*)?(?:고마워|고마워요|고맙습니다|감사해|감사해요|감사합니다)[.!\s]*",
            str(context.get("user_message") or "").strip(),
        ):
            message, question = "도움이 되었다니 다행이에요.", None
            response_source = "server_fixed"
        elif out.intent == "answer" and question is None:
            # 선택적인 대화 초대는 정보 확인 질문과 구분한다. 실제 답변을 보존한다.
            parts = re.split(r"(?<=[.!])\s+", message)
            kept = [part for part in parts if not re.search(
                r"(?:있으면|있으시면|있다면|있으시다면).*(?:알려|말씀해)\s*주세요[.!]*$", part
            )]
            if kept != parts:
                message = " ".join(kept) or "현재 준비 내용을 이어서 확인할 수 있어요."
                response_source = "server_trimmed_invitation"
    _require(not re.search(r"[?？]|(?:알려|말씀해|설명해)\s*주세요|(?:할까요|하실까요|하시겠습니까|인가요|무엇인가요)", message), "question_in_message")
    if question:
        _require(question.count("?") + question.count("？") == 1 and question.endswith(("?", "？")), "single_question_required")
    actions = context.get("available_actions") or {}
    stage = context.get("current_stage")
    text = str(context.get("user_message") or "")
    pending = context.get("pending_profile_update") or {}
    u = out.profile_update
    _require((u is not None) == (out.intent == "profile_update"), "profile_intent_relationship")
    if context.get("event") == "stage_enter":
        _require(out.intent == "answer" and out.next_action == "stay" and out.requested_stage is None, "stage_enter_gate")
    if out.intent == "clarify":
        _require(bool(question), "clarify_question_required")
    if out.next_action == "stay":
        _require(out.requested_stage is None, "stay_target")
    else:
        _require(out.intent == "change_step" and u is None, "change_intent_required")
        _require(not re.search(r"[?？]|(?:하지|말고|취소|않)", text), "explicit_action_required")
        if out.next_action == "request_rerecord":
            _require(stage == "first_coaching" and actions.get("can_rerecord") is True and out.requested_stage is None, "rerecord_gate")
            _require(bool(re.search(r"(?:다시\s*녹음|재녹음|재답변).*(?:할게|할래|시작해|열어|하겠)", text)), "explicit_rerecord_required")
        elif out.next_action == "request_skip":
            _require(actions.get("can_skip") is True and out.requested_stage is None and bool(re.search(r"건너뛰|넘어가|넘겨", text)), "skip_gate")
        else:
            _require(out.requested_stage != stage and out.requested_stage in actions.get("change_stage_targets", []), "change_stage_gate")
            names = {"ncs": "NCS", "readme": "README", "resume": "이력서", "interview": "면접"}
            _require(names[out.requested_stage].lower() in text.lower() and bool(re.search(r"이동|넘어|시작|부터|하고\s*싶", text)), "explicit_stage_required")
        return PreparationDecision(out.next_action, "진행 요청 의사를 확인했어요.", None, requested_stage=out.requested_stage)
    if u is None:
        if re.search(r"저장\s*완료|저장했|저장되었|이미\s*저장된|반영했", message):
            _require(pending.get("status") == "saved" or bool(context.get("confirmed_supplemental_context")), "unverified_save_completion")
        _require(not re.search(r"취소했|이동했|시작했|열었", message), "unverified_progress_completion")
        if stage == "first_coaching" and question:
            _require(not re.search(r"재녹음|다시\s*녹음|2차\s*답변|확인.*(?:과정|결과).*설명", question), "unsolicited_coaching_progress_question")
        return PreparationDecision("stay", message, question, response_source=response_source)
    _require(out.requested_stage is None, "profile_stay")
    if u.action == "propose":
        _require(bool(question) and bool(u.facts) and u.review_stage is not None, "proposal_required")
        active = pending.get("status") in {"collecting", "awaiting_confirmation"}
        _require((u.draft_id, u.draft_version) == ((pending.get("draft_id"), pending.get("draft_version")) if active else (None, None)), "latest_draft_propose")
        sources = {m["message_id"]: m["text"] for m in context.get("source_messages", [])}
        for fact in u.facts:
            _require(fact.source_message_id in sources and fact.source_excerpt in sources[fact.source_message_id], "invalid_source_quote")
        if u.review_stage == "awaiting_confirmation":
            _require(bool(re.search(r"(?:반영|저장).*?(?:할까요|동의)", question)), "summary_confirmation_question_required")
        return PreparationDecision("propose", message, question, u.draft_id, u.draft_version)
    _require(not u.facts and u.review_stage is None and question is None, "terminal_update_payload")
    _require(bool(pending) and (u.draft_id, u.draft_version) == (pending.get("draft_id"), pending.get("draft_version")), "latest_draft_terminal")
    if u.action == "request_save":
        _require(actions.get("can_save_profile") is True and explicit_profile_consent(context), "save_consent_gate")
        _require(not any((item.get("draft_id"), item.get("draft_version")) == (u.draft_id, u.draft_version) for item in context.get("confirmed_supplemental_context", [])), "duplicate_save")
        return PreparationDecision("request_save", "정리한 내용에 대한 반영 동의를 확인했어요.", None, u.draft_id, u.draft_version)
    _require(pending.get("status") in {"collecting", "awaiting_confirmation"} and bool(re.search(r"(?:반영하지\s*마|취소|저장하지\s*마)", text)), "discard_gate")
    return PreparationDecision("discard", "초안 반영을 취소하려는 의사를 확인했어요.", None, u.draft_id, u.draft_version)


def preparation_completion_message(decision: PreparationDecision, *, succeeded: bool) -> str:
    """실제 처리 결과를 확인한 호출자가 사용하는 서버 완료 문구."""
    _require(decision.action in {"request_save", "discard", "request_rerecord", "request_skip", "request_change_stage"}, "not_a_completion_action")
    if not succeeded:
        return "요청을 처리하지 못했어요. 현재 단계에서 다시 시도해 주세요."
    return {
        "request_save": "확인한 경력을 이번 연습의 참고 정보로 저장했어요.",
        "discard": "미저장 초안을 취소했어요.",
        "request_rerecord": "재답변 입력 화면을 열었어요.",
        "request_skip": "다음 단계로 이동했어요.",
        "request_change_stage": "요청한 단계로 이동했어요.",
    }[decision.action]
