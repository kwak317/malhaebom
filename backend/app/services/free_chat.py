"""자유 채팅 생성과 기존 준비 동작의 연결. 저장 권한은 기존 서버 정책에 둔다."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from app.services.preparation_selection_actions import SelectionRequest
from app.services.preparation_conversation_policy import OUT_OF_SCOPE_MESSAGE, profile_confirmation_question
from app.services.free_chat_evidence import evidence_catalog, validate_draft_claims
from app.services.coaching_observability import CoachingGenerationObservation, observation_trace_id, record_generation_safely

PROMPT_VERSION = "free-chat-v4.6-reference-finish"
MODEL = "anthropic/claude-haiku-5.5"


class DraftClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str = Field(min_length=1, max_length=800)
    actor: Literal["self", "team", "reference"]
    source_ids: list[str] = Field(min_length=1, max_length=8)


class FreeChatOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    intent: Literal["answer", "clarify", "delegate", "unsupported", "refusal", "request_selection", "out_of_scope"]
    answer_kind: Literal["explanation", "draft", "suggestion"]
    message: str = Field(min_length=1, max_length=800)
    follow_up_question: str | None = Field(max_length=280, pattern=r"[?？]$")
    delegate: Literal["supplemental_experience", "rerecord"] | None
    draft_claims: list[DraftClaim] = Field(max_length=12)
    selection_request: SelectionRequest | None


def free_chat_output_schema(context=None):
    # 공급자는 복잡한 길이/개수 제약을 컴파일하지 못할 수 있다.
    # 구조·필수 필드·enum은 유지하고 세부 제약은 서버 Pydantic 검증에 둔다.
    schema = FreeChatOutput.model_json_schema()
    def simplify(value):
        if isinstance(value, dict):
            for key in ["minLength", "maxLength", "minItems", "maxItems", "pattern"]:
                value.pop(key, None)
            for child in value.values():
                simplify(child)
        elif isinstance(value, list):
            for child in value:
                simplify(child)
    simplify(schema)
    if context is not None:
        catalog = context.get("evidence_catalog", evidence_catalog(context))
        ids = list(dict.fromkeys(item["id"] for item in catalog))
        if ids:
            schema["$defs"]["DraftClaim"]["properties"]["source_ids"]["items"]["enum"] = ids
    return schema


def load_free_chat_prompt():
    root = Path(__file__).resolve().parents[3]
    source = (root / "prompts/free-chat-v4.md").read_text()
    body = source.split("## System 본문\n", 1)[1].split("## 끝", 1)[0].strip()
    skill = (root / "skills/free-chat-request-handling/SKILL.md").read_text().split("---", 2)[2].strip()
    if body.count("{{skill_text}}") != 1 or not skill:
        raise ValueError("free_chat_skill_template")
    return body.replace("{{skill_text}}", skill)


def claims_unverified_execution(message, answer_kind="explanation"):
    # 원본/선택 상태를 바꿨다는 주장과 대상 없는 완료 안내는 실행 증거가 없다.
    # 작성안 속 지원자 과거 행동과 명시적인 자료 인용은 별도로 취급한다.
    completed = r"(?:저장|반영|수정|삭제|제외|취소|선택|변경|이동)(?:해\s*드렸|했|되었|됐|완료)"
    target = r"(?:원본(?:\s*이력서)?|이력서(?:에|에서|를)|파일(?:에|에서|을)|프로필(?:에|에서|을)|선택\s*상태|화면(?:을|으로)|NCS\s*선택|이\s*(?:내용|정보|항목|경력)(?:을|를))"
    # Emphasis must not hide an unverified execution claim.
    for sentence in re.split(r"[\n.!?]", message.replace("**", "")):
        if not re.search(completed, sentence):
            continue
        quoted_source = bool(re.search(r"(?:README|자료|기록|원문).*(?:다고|다는|적혀|기재)", sentence))
        if quoted_source:
            continue
        if re.search(target + r".{0,60}" + completed, sentence):
            return True
        if re.search(r"(?:시스템이|도구로|실제로).{0,30}" + completed, sentence):
            return True
        if re.search(r"^\s*(?:네[,， ]*)?(?:제가\s*)?" + completed, sentence):
            return True
    return False


def known_interview_preparation_answer(text):
    """명확한 준비 질문의 오분류만 보완한다. 관련 단어만 있는 복합 요청은 제외한다."""
    text = text.strip()
    if re.fullmatch(r"면접\s*전(?:에)?\s*(?:너무\s*)?(?:긴장|불안)(?:돼|되|되어|한|해|되는데|돼서|되어서|한데|해서).*?(?:어떻게\s*(?:준비|연습|하면)|준비\s*방법|도와)(?:.*?(?:좋을까|할까|해줘|해주세요|알려줘|알려주세요))?[.!?]?", text):
        if not re.search(r"날씨|운세|여행|맛집|예약|투자|구매", text):
            return "핵심 경험과 예상 질문을 정리하고, 짧게 소리 내어 답변하는 연습부터 해보세요. 면접 전에는 천천히 호흡하며 첫 답변을 미리 떠올려 보세요."
    if re.fullmatch(r"면접\s*전(?:에)?\s*(?:먹기\s*좋은|먹을)\s*(?:점심|식사|메뉴)\s*(?:를|을)?\s*추천(?:해줘|해주세요|해\s*줄래)[.!?]?", text):
        return "면접 전에는 평소 편하게 먹던 익숙한 메뉴를 가볍게 드세요. 준비 시간을 확보할 수 있는 간단한 식사를 골라보세요."
    return None


README_ADDITION_QUESTION = "리드미에 추가하고 싶은 내용은 무엇인가요? 본인이 수행한 작업과 해당 프로젝트를 알려주세요."


def readme_addition_requested(text):
    return (bool(re.search(r"리드미|read\s*\.?\s*me", text, re.I))
            and bool(re.search(r"추가|반영|저장", text))
            and not re.search(r"추가하지|반영하지|저장하지|하지\s*마|말고|취소|예시|가정|만약", text))


def preparation_reply(message, question, update=None):
    output = {"intent": "profile_update" if update else "clarify", "message": message,
              "follow_up_question": question, "next_action": "stay", "requested_stage": None,
              "profile_update": update}
    return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(output, ensure_ascii=False)}}]}


class FreeChatDispatcher:
    def __init__(self, generate, system_prompt=None, observation_sink=None):
        self.generate = generate
        self.system_prompt = system_prompt or load_free_chat_prompt()
        self.observation_sink = observation_sink

    def respond(self, preparation_generate, preparation_prompt, context):
        pending = context.get("pending_profile_update") or {}
        text = context["user_message"].strip()
        history = context.get("conversation_history") or []
        readme_answer = bool(history and history[-1].get("follow_up_question") == README_ADDITION_QUESTION)
        if readme_answer and not re.search(r"취소|추가하지|반영하지|저장하지", text):
            context["profile_task_requested"] = True
            context.pop("generation_prompt_version", None)
            if len(text) > 3600 or re.fullmatch(r"(?:네|예|응|ㅇㅇ|맞습니다|좋아요)[.!\s]*", text):
                return preparation_reply("저장할 실제 경험 내용을 입력해 주세요. 내용은 3,600자 이내로 적어주세요.", README_ADDITION_QUESTION)
            source = context["source_messages"][-1]
            facts = [{"kind": "responsibility", "value": text[start:start + 300],
                      "source_message_id": source["message_id"], "source_excerpt": text[start:start + 300]}
                     for start in range(0, len(text), 300)]
            active = pending.get("status") in {"collecting", "awaiting_confirmation"}
            return preparation_reply("추가할 내용을 확인했어요.", "이 내용을 이번 연습의 근거 자료실에 참고정보로 저장할까요?", {
                "action": "propose", "draft_id": pending.get("draft_id") if active else None,
                "draft_version": pending.get("draft_version") if active else None,
                "review_stage": "awaiting_confirmation", "facts": facts})
        if readme_addition_requested(text) and pending.get("status") not in {"collecting", "awaiting_confirmation"}:
            context["profile_task_requested"] = True
            context.pop("generation_prompt_version", None)
            return preparation_reply("원본 README는 유지하고, 확인한 내용을 이번 연습의 참고정보로 추가할 수 있어요.", README_ADDITION_QUESTION)
        # 이미 시작한 경력의 정보 보완에는 분류 모델을 다시 호출하지 않는다.
        writing_request = bool(re.search(r"문장|작성안|짧게|축약|질문.*추천|답변.*(?:정리|작성)", context["user_message"]))
        if (pending.get("status") in {"collecting", "awaiting_confirmation"} or context.get("profile_task_requested")) and not writing_request:
            context.pop("generation_prompt_version", None)
            return preparation_generate(preparation_prompt, context)
        focus = context.get("focus_context") or {}
        items = focus.get("items")
        ambiguous_ncs = (focus.get("kind") in {"ncs", "ncs_review"} and isinstance(items, list) and len(items) > 1
                and re.search(r"이\s*항목|이것|이거", context["user_message"])
                and not any(item.get("label") and item["label"] in context["user_message"] for item in items))
        compact = {key: context.get(key) for key in (
            "current_stage", "user_message", "current_item", "selection_context", "verified_context",
            "coaching_context", "conversation_history", "confirmed_supplemental_context", "pending_profile_update", "available_actions", "focus_context", "selection_options")}
        compact["evidence_catalog"] = evidence_catalog(context)
        compact["server_capabilities"] = {
            "supplemental_experience": "검토·확인 동의 후 연습용 참고정보 저장",
            "rerecord": context["available_actions"].get("can_rerecord", False),
            "selection_change": context["available_actions"].get("can_change_selection", False),
            "search": False, "edit_original_document": False,
            "replace_readme": False, "advance_stage": False}
        if context.get("_free_chat_relation_retry"):
            compact["validation_feedback"] = {
                "code": "free_chat_unlinked_experiences",
                "instruction": "서로 다른 relation_id의 출처를 한 claim으로 합치지 마세요. 현재 사용자 답변 자체가 수행 내용을 명시하면 그 답변의 source_id만 사용하세요. 단순 수긍·추가 안내는 개인 경력 사실을 재작성하지 않아도 됩니다. 사실 연결이 불명확하면 연결 여부만 질문하세요. 원본 수정·저장·선택 완료를 주장하지 마세요."}
        context["generation_prompt_version"] = PROMPT_VERSION
        started = time.perf_counter()
        raw = self.generate(self.system_prompt, compact)
        def observe(outcome):
            usage = raw.get("usage") or {}
            if self.observation_sink is not None:
                record_generation_safely(self.observation_sink, CoachingGenerationObservation(
                    trace_id=observation_trace_id(), model=MODEL, prompt_version=PROMPT_VERSION,
                    skill_version="free-chat-request-handling-v1.1", contract_attempt=1, transport_attempt=1,
                    outcome=outcome, will_retry=False, latency_ms=(time.perf_counter()-started)*1000,
                    input_tokens=usage.get("prompt_tokens"), output_tokens=usage.get("completion_tokens"),
                    cost_usd=usage.get("cost"), output_is_json_object=outcome == "success"))
        try:
            choice = raw["choices"][0]
            if choice.get("finish_reason") == "length":
                raise ValueError("free_chat_truncated")
            payload = json.loads(choice["message"]["content"])
            question = payload.get("follow_up_question")
            # 질문 뒤 부가 안내는 버리지 않고 본문으로 옮겨 질문 필드를 하나로 보존한다.
            if isinstance(question, str) and question.count("?") + question.count("？") == 1:
                parts = re.fullmatch(r"(.*?[?？])\s*(.+)", question, flags=re.DOTALL)
                if parts and isinstance(payload.get("message"), str):
                    payload["follow_up_question"] = parts[1]
                    payload["message"] += "\n" + parts[2]
            if payload.get("intent") == "out_of_scope":
                # Scope guidance cannot carry a follow-up, draft, delegation, or selection action.
                related_answer = known_interview_preparation_answer(context["user_message"])
                payload.update(intent="answer" if related_answer else "out_of_scope",
                    message=related_answer or OUT_OF_SCOPE_MESSAGE, answer_kind="explanation",
                    follow_up_question=None, delegate=None, draft_claims=[], selection_request=None)
            elif ambiguous_ncs and payload.get("intent") in {"answer", "clarify", "request_selection"}:
                payload.update(intent="clarify", message="현재 NCS 항목이 여러 개 선택되어 있어요.",
                    answer_kind="explanation", follow_up_question="어떤 항목을 말씀하시는지 항목 이름을 알려주시겠어요?",
                    delegate=None, draft_claims=[], selection_request=None)
            out = FreeChatOutput.model_validate(payload)
            if re.search(r"검토|과장.*(?:보|봐|인지)", context["user_message"]) and out.answer_kind == "draft":
                # 검토 결과와 안전한 대안을 작성 문장만 남기는 정규화로 지우지 않는다.
                out.answer_kind = "explanation"
            if (out.intent == "delegate") != (out.delegate is not None):
                raise ValueError("free_chat_delegate_relationship")
            if out.intent == "clarify" and not out.follow_up_question:
                raise ValueError("free_chat_clarification_required")
            if (out.intent == "request_selection") != (out.selection_request is not None):
                raise ValueError("free_chat_selection_relationship")
            if out.intent == "request_selection" and (out.follow_up_question or out.delegate):
                raise ValueError("free_chat_selection_payload")
            validate_draft_claims(out, compact["evidence_catalog"])
            if claims_unverified_execution(out.message, out.answer_kind):
                raise ValueError("free_chat_unverified_completion")
        except (ValueError, KeyError, IndexError, TypeError) as error:
            observe("contract_error")
            # 출처 관계 오류만 한 번 교정한다. 아직 저장·선택·위임은 실행하지 않았다.
            if str(error) == "free_chat_unlinked_experiences" and not context.get("_free_chat_relation_retry"):
                context["_free_chat_relation_retry"] = True
                try:
                    return self.respond(preparation_generate, preparation_prompt, context)
                finally:
                    context.pop("_free_chat_relation_retry", None)
            raise
        if out.answer_kind == "draft":
            out.message = ("연습용 작성안:\n" + "\n".join(dict.fromkeys(claim.text for claim in out.draft_claims))
                           + "\n이 작성안으로 원본 문서나 저장된 참고정보를 변경하지 않았어요.")
            if re.search(r"1분|일\s*분", context["user_message"]):
                out.message += "\n현재 확인된 사실만 담았어요. 실제 발화 시간은 읽는 속도에 따라 달라지므로 직접 시간을 확인해 주세요."
        context["free_chat_answer_kind"] = out.answer_kind
        observe("success")
        if out.selection_request is not None:
            context["selection_proposal"] = out.selection_request.model_dump(mode="json")
        # 자유 대화의 저장 동의 질문을 먼저 노출하지 않는다. 출처가 검증된
        # 실제 후보를 준비 경로에서 만들고 그 후보에 대한 동의만 받는다.
        if out.intent in {"answer", "clarify"} and profile_confirmation_question(out.follow_up_question):
            context["profile_task_requested"] = True
            context.pop("generation_prompt_version", None)
            return preparation_generate(preparation_prompt, context)
        if out.intent == "delegate":
            if out.delegate == "supplemental_experience":
                context["profile_task_requested"] = True
                context.pop("generation_prompt_version", None)
                return preparation_generate(preparation_prompt, context)
            result = {"intent": "change_step", "message": "재답변 입력 요청을 확인했어요.",
                      "follow_up_question": None, "next_action": "request_rerecord",
                      "requested_stage": None, "profile_update": None}
        else:
            # 자유 채팅은 별도 질문 필드 계약을 검증했다. 인용·예시 질문은 본문에 허용한다.
            context["allow_generated_question_text"] = True
            context["free_chat_execution_claim_checked"] = True
            result = {"intent": "out_of_scope" if out.intent == "out_of_scope" else "refusal" if out.intent == "refusal" else "clarify" if out.intent == "clarify" else "answer",
                      "message": out.message, "follow_up_question": out.follow_up_question,
                      "next_action": "stay", "requested_stage": None, "profile_update": None}
        context["generation_prompt_version"] = PROMPT_VERSION
        # 공급자 증거는 원본 로그에 남기고 기존 서버 계약으로만 정규화한다.
        return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(result, ensure_ascii=False)}}],
                "usage": raw.get("usage"), "model": raw.get("model", MODEL),
                "_free_chat_observed": self.observation_sink is not None}
