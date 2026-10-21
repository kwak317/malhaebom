"""질문·경력 정리 후보를 인증된 DB 상태와 연결한다. 모델 출력으로 직접 저장하지 않는다."""
from __future__ import annotations

from copy import deepcopy
import json
import hashlib
import re
from pathlib import Path
from uuid import uuid4

from app.schemas.preparation_conversation import PreparationConversationOutput
from app.schemas.applicant_context import ApplicantContext
from app.services.preparation_conversation_generation import generate_preparation_response
from app.services.preparation_conversation_policy import decide_preparation_action, preparation_completion_message, explicit_profile_consent, explicit_profile_rejection, explicit_rerecord_request, profile_confirmation_question, PreparationPolicyError, PreparationDecision
from app.services.preparation_information import stored_information_response
from app.services.preparation_restart import handle_restart
from app.services.preparation_conversation_repository import PreparationConflict
from app.services.supabase_persistence import SupabasePersistenceError
from app.services.prompt_templates import PromptTemplateError
from app.services.preparation_selection_actions import SelectionSnapshot, snapshot, validate_snapshot, selection_options, propose_selection, selection_consent
from app.services.coaching_observability import CoachingGenerationObservation, observation_trace_id, record_generation_safely

PROMPT_VERSION = "preparation-conversation-v3.3-reference-finish"
SKILL_VERSION = "preparation-conversation-v3.2-local-candidate"
PROFILE_CONSENT_GUIDANCE = "반영하려면 ‘반영해줘’라고 입력해 주세요."


def load_preparation_prompt(client=None):
    root = Path(__file__).resolve().parents[3]
    source = (root / "prompts/preparation-conversation-v3.1.md").read_text()
    body = source.split("## System 본문\n", 1)[1].split("## 계약 예시", 1)[0].strip()
    if client is not None:
        try:
            managed = client.get_prompt("malhaebom-preparation-conversation", version=1,
                type="text", cache_ttl_seconds=60, fallback=body)
            # 評가된 본문과 같을 때만 고정 버전 사용. 관리 서비스 장애는 동일 로컬 후보로 복구.
            if not getattr(managed, "is_fallback", False) and managed.prompt == body:
                body = managed.prompt
        except Exception:
            pass
    skill = (root / "skills/preparation-conversation/SKILL.md").read_text().split("---", 2)[2].strip()
    values = {"skill_text": skill, "skill_version": SKILL_VERSION, "prompt_version": PROMPT_VERSION}
    slots = re.findall(r"\{\{(.*?)\}\}", body, flags=re.DOTALL)
    if set(slots) != set(values) or slots.count("skill_text") != 1 or not skill:
        raise PromptTemplateError("준비 대화 Prompt 변수와 Skill 본문을 확인해야 합니다.")
    # JSON 객체의 연속 닫는 중괄호는 변수 문법이 아니다. 평가와 같은 단일 치환을 사용한다.
    return re.sub(r"\{\{(.*?)\}\}", lambda match: values[match.group(1)], body, flags=re.DOTALL)


class PreparationConversationService:
    def __init__(self, repository, generate, system_prompt=None, observation_sink=None, free_chat=None,
                 model_name="google/gemini-3.5-flash-lite"):
        self.repository, self.generate = repository, generate
        self.observation_sink = observation_sink
        self.free_chat = free_chat
        self.model_name = model_name
        self.system_prompt = system_prompt if system_prompt is not None else load_preparation_prompt()

    def bind(self, user, conversation_id, session_id):
        row = self.repository.load(user, conversation_id)
        if row["state"].get("restart_completed"):
            raise PreparationConflict("초기화된 대화를 연결할 수 없어요.")
        session = self.repository.session(user, session_id)
        saved_selection = row["state"].get("selection")
        if saved_selection:
            actual = self.repository.selection_context(user, session_id=session_id)
            expected = self.repository.selection_context(user, SelectionSnapshot.model_validate(saved_selection))
            if actual != expected or (session.get("applicant_context") or {}).get("selected_ncs_ids", []) != saved_selection["selected_ncs_ids"]:
                raise PreparationConflict("연습 세션과 현재 선택이 달라요. 현재 선택으로 새 연습을 시작해 주세요.")
        if row.get("practice_session_id") not in (None, str(session_id)):
            raise PreparationConflict("다른 연습의 대화를 연결할 수 없어요.")
        if row.get("practice_session_id") is None:
            self.repository.save(user, row, row["state"], session_id)

    def selection_recovery(self, user, conversation_id):
        row = self.repository.load(user, conversation_id)
        if row.get("practice_session_id") or not row["state"].get("selection"):
            return None
        selection = SelectionSnapshot.model_validate(row["state"]["selection"])
        validate_snapshot(self.repository, user, selection)
        context = self.repository.selection_context(user, selection)
        job = context.get("job")
        if job:
            job = {**job, "requirements": [{**r, "text": r.get("requirement_text", r.get("text", ""))}
                for r in job.get("job_requirements", job.get("requirements", []))]}
        return {"selection_state": selection.model_dump(mode="json"),
                "selection_revision": row["state"].get("selection_revision", 0), "selection_job": job}

    def respond(self, user, request):
        cid = request.conversation_id or request.request_id
        try:
            row = self.repository.load(user, cid)
        except KeyError:
            if request.conversation_id is not None:
                raise
            row = self.repository.create(user, cid)
        state = deepcopy(row["state"])
        rid = str(request.request_id)
        completed = state.get("responses", {})
        fingerprint = hashlib.sha256(json.dumps(request.model_dump(mode="json"), ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        # Retain main's expiry/stage gate before replaying a cached response.
        if rid in completed and not state.get("restart_completed"):
            if request.practice_session_id:
                self.repository.session(user, request.practice_session_id)
            if request.current_stage == "first_coaching":
                self.repository.first_coaching(user, request.practice_session_id)
        if rid in completed:
            previous = completed[rid]
            if previous["input"] != fingerprint:
                raise PreparationConflict("같은 요청 ID로 내용을 바꿀 수 없어요.")
            response = deepcopy(previous["response"])
            if response.get("action") == "selection_updated" and (response.get("selection_state") != state.get("selection") or response.get("selection_revision") != state.get("selection_revision")):
                response.update(selection_state=state["selection"], selection_revision=state["selection_revision"],
                    selection_job=None, message="이 요청은 이미 처리됐어요. 최신 서버 선택을 유지합니다.")
                if state["selection"].get("job_posting_id"):
                    job = self.repository.selection_context(user, SelectionSnapshot.model_validate(state["selection"]))["job"]
                    response["selection_job"] = {**job, "requirements": [{**r, "text": r.get("requirement_text", r.get("text", ""))}
                        for r in job.get("job_requirements", job.get("requirements", []))]}
            return response
        if state.get("restart_completed"):
            return handle_restart(self.repository, user, row, state, request, fingerprint)
        if len(completed) >= 60:
            raise PreparationConflict("이번 대화가 길어졌어요. 새 연습에서 이어서 준비해 주세요.")
        if request.practice_session_id:
            self.repository.session(user, request.practice_session_id)
            if row.get("practice_session_id") not in (None, str(request.practice_session_id)):
                raise PreparationConflict("다른 연습의 대화를 사용할 수 없어요.")
        elif row.get("practice_session_id"):
            raise PreparationConflict("현재 연습 세션을 함께 보내 주세요.")
        restart = handle_restart(self.repository, user, row, state, request, fingerprint)
        if restart is not None:
            return restart
        coaching = None
        if request.current_stage == "first_coaching":
            if request.practice_session_id is None:
                raise PreparationConflict("1차 코칭의 연습 기록이 필요해요.")
            coaching = self.repository.first_coaching(user, request.practice_session_id)
        selection_values = snapshot(request)
        selection_revision = state.get("selection_revision", 0)
        locked = bool(request.practice_session_id or row.get("practice_session_id"))
        if state.get("selection") and not locked:
            selection_values = {**state["selection"], **(request.selection.model_dump(mode="json") if request.selection else {})}
            if request.review_context is not None:
                selection_values["selected_ncs_ids"] = request.review_context.selected_ncs_ids
            if request.selection_revision is not None:
                if request.selection_revision != selection_revision:
                    raise PreparationConflict("선택이 다른 요청에서 변경됐어요. 최신 선택을 확인하고 다시 보내 주세요.")
                if selection_values != state["selection"]:
                    selection_values = validate_snapshot(self.repository, user, selection_values)
                    state.update(selection=selection_values, selection_revision=selection_revision + 1, pending_selection=None)
                    selection_revision += 1
            else:
                selection_values = state["selection"]
        selection = (coaching or {}).get("selection_context")
        if selection is None and (request.selection is not None or state.get("selection")):
            selected = SelectionSnapshot.model_validate(selection_values)
            selection = self.repository.selection_context(user, selected, request.practice_session_id)
        source = {"message_id": str(uuid4()), "text": request.message}
        sources = [*state.get("sources", []), source]
        pending = state.get("pending")
        profile_task_requested = state.get("profile_task_requested")
        if profile_task_requested is None:
            # 이전 버전에서 초안 없이 정보 확인만 시작한 사용자 요청도 이어받는다.
            history = state.get("history", [])[-12:]
            requested = any(item.get("role") == "user" and re.search(
                r"(?:경험|경력|이력서|참고정보).*(?:추가|반영|저장)|(?:추가|반영|저장).*(?:경험|경력|이력서|참고정보)", item.get("text", "")) for item in history)
            asked = any(item.get("role") == "assistant" and item.get("follow_up_question") and re.search(
                r"추가.*경험|경험.*추가|추가\s*대상|어떤\s*경험", item.get("message", "") + item["follow_up_question"]) for item in history)
            profile_task_requested = requested and asked and bool(history[-1].get("follow_up_question") if history else None) and not (pending and pending.get("status") == "saved")
        cancelled_profile_task = bool(profile_task_requested and not pending and not state.get("pending_selection") and re.fullmatch(
            r"(?:(?:경험|경력|참고정보)\s*추가\s*)?(?:취소(?:해\s*줘|해주세요|할게|할래)?|추가하지\s*말고\s*취소(?:할게|해줘|해주세요))[.!]?", request.message.strip()))
        if cancelled_profile_task:
            profile_task_requested = False
        materials = request.review_context.model_context() if request.review_context else None
        if materials is not None and not locked:
            materials["selected_ncs"] = ApplicantContext(selected_ncs_ids=selection_values["selected_ncs_ids"]).model_context()["selected_ncs"]
        if locked and self.free_chat:
            session_materials = self.repository.session(user, request.practice_session_id or row["practice_session_id"]).get("applicant_context")
            materials = ApplicantContext.model_validate(session_materials).model_context() if session_materials else None
        focus_kind = request.ui_context or request.current_stage
        focus_options = {"ncs": (materials or {}).get("selected_ncs", []), "ncs_review": (materials or {}).get("selected_ncs", []),
            "requirements": (selection or {}).get("selected_requirements", []), "jobs": (selection or {}).get("job"),
            "questions": (selection or {}).get("question"), "resume": (materials or {}).get("resume_profile"),
            "resume_review": (materials or {}).get("resume_profile"), "readme": (materials or {}).get("readme_analysis"),
            "readme_review": (materials or {}).get("readme_analysis"), "first_coaching": (coaching or {}).get("question_text")}
        current_item = focus_options.get(focus_kind)
        if selection:
            if "요구사항" in request.message:
                focus_kind, current_item = "requirements", selection.get("selected_requirements") or None
            elif "질문" in request.message:
                focus_kind, current_item = "questions", selection.get("question")
            elif "공고" in request.message:
                focus_kind, current_item = "jobs", selection.get("job")
        context = {"current_stage": request.current_stage, "event": "message",
            "current_item": current_item,
            "verified_context": {"source_type": "user_provided_reference", "independently_verified": False,
                "materials": materials},
            "selection_context": selection,
            "focus_context": {"kind": focus_kind, "items": current_item},
            "selection_options": selection_options(self.repository, user, selection) if self.free_chat and not locked and not state.get("new_graduate_only") else None,
            "response_requirements": {"answer_known_information_first": True,
                "include_requested_result_in_message": True, "do_not_only_announce_future_help": True,
                "do_not_reask_information_already_in_context": True,
                "supplemental_experience_usage": "reference_only", "original_resume_is_not_modified": True},
            "coaching_context": coaching, "user_statements": [], "source_messages": sources,
            "pending_selection": state.get("pending_selection"), "pending_profile_update": pending, "profile_task_requested": bool(profile_task_requested), "confirmed_supplemental_context": state.get("confirmed", []),
            "conversation_history": state.get("history", [])[-12:],
            "available_actions": {"can_skip": False, "can_rerecord": coaching is not None, "can_change_selection": not locked,
                "can_save_profile": bool(pending and pending.get("status") == "awaiting_confirmation"),
                "change_stage_targets": []}, "user_message": request.message}
        def retry_confirmation(message):
            return {"conversation_id": str(cid),
                    "message": message + "\n" + pending["summary"] + "\n" + PROFILE_CONSENT_GUIDANCE,
                    "follow_up_question": None,
                    "action": "stay", "status": "unavailable"}

        pending_selection = state.get("pending_selection")
        selection_event = None
        if selection_consent(pending_selection, state.get("history", []), request.message):
            if locked or pending_selection["base_revision"] != selection_revision:
                raise PreparationConflict("선택 변경 후보가 만료됐어요. 현재 선택에서 다시 요청해 주세요.")
            selected_after = validate_snapshot(self.repository, user, pending_selection["after"])
            state.update(selection=selected_after, selection_revision=selection_revision + 1, pending_selection=None)
            selection_event = "verified"
        elif pending_selection and re.fullmatch(r"(?:선택\s*변경|이\s*선택)\s*취소해\s*(?:줘|주세요)[.!]?", request.message.strip()):
            state["pending_selection"] = None
            selection_event = "cancelled"

        awaiting = bool(pending and pending.get("status") == "awaiting_confirmation"
                        and pending.get("confirmation_requested"))
        if pending and pending.get("status") == "saved" and any(
            (item.get("draft_id"), item.get("draft_version")) == (pending.get("draft_id"), pending.get("draft_version"))
            for item in state.get("confirmed", [])
        ):
            retry_context = dict(context, pending_profile_update=dict(pending,
                status="awaiting_confirmation", confirmation_requested=True))
            if explicit_profile_consent(retry_context):
                return {"conversation_id": str(cid), "message": "확인한 경력은 이미 이번 연습의 참고 정보로 저장되어 있어요.",
                        "follow_up_question": None, "action": "stay", "status": "ok"}
        # 공고 원문 조회의 빠른 경로는 단순 조회에만 적용한다.
        # "공고 원본 사이트에서 오늘 운세 알려줘"처럼 다른 의도가 있으면 모델이 분류한다.
        original_site_request = re.search(r"공고.*(?:원본|원문|사이트|출처)|(?:원본|원문|출처).*공고", request.message)
        simple_original_site_request = re.fullmatch(
            r"(?:현재\s*|선택한\s*|선택된\s*)?공고(?:의)?\s*(?:원본|원문|출처)(?:\s*(?:사이트|링크|URL))?\s*(?:를|을)?\s*(?:(?:보여|알려)\s*(?:줘|주세요)|확인(?:해줘|해주세요)?|어디(?:야|인가요)\??)[.!?]?",
            request.message.strip(), flags=re.IGNORECASE)
        stored_answer = (None if original_site_request and not simple_original_site_request
                        else stored_information_response(context))
        if cancelled_profile_task:
            stored_answer = "경험 추가 요청을 취소했어요. 기존 저장 정보는 유지됩니다."
        if selection_event:
            raw = {"intent": "answer", "message": "선택 변경 결과를 확인하고 있어요.", "follow_up_question": None,
                   "next_action": "stay", "requested_stage": None, "profile_update": None}
        elif explicit_profile_rejection(context):
            raw = {"intent": "profile_update", "message": "반영 거절을 확인했어요.",
                   "follow_up_question": None, "next_action": "stay", "requested_stage": None,
                   "profile_update": {"action": "discard", "draft_id": pending["draft_id"],
                       "draft_version": pending["draft_version"], "review_stage": None, "facts": []}}
        elif explicit_profile_consent(context):
            # 이미 표시한 최신 초안에 대한 동의는 모델을 거치지 않는다.
            raw = {"intent": "profile_update", "message": "반영 동의를 확인했어요.",
                   "follow_up_question": None, "next_action": "stay", "requested_stage": None,
                   "profile_update": {"action": "request_save", "draft_id": pending["draft_id"],
                       "draft_version": pending["draft_version"], "review_stage": None, "facts": []}}
        elif explicit_rerecord_request(context):
            # 명확한 진행 요청은 모델 분류 없이 기존 재답변 화면 동작으로 연결한다.
            raw = {"intent": "change_step", "message": "재답변 입력 요청을 확인했어요.",
                   "follow_up_question": None, "next_action": "request_rerecord",
                   "requested_stage": None, "profile_update": None}
        elif stored_answer is not None:
            raw = None
        else:
            generation = generate_preparation_response(lambda: (
                self.free_chat.respond(self.generate, self.system_prompt, context)
                if self.free_chat is not None else self.generate(self.system_prompt, context)))
            for number, attempt in enumerate(generation.attempts, 1):
                if (attempt.provider_response or {}).get("_free_chat_observed"):
                    continue
                usage = (attempt.provider_response or {}).get("usage") or {}
                record_generation_safely(self.observation_sink, CoachingGenerationObservation(
                    trace_id=observation_trace_id(), model=self.model_name,
                    prompt_version=context.get("generation_prompt_version", PROMPT_VERSION), skill_version=SKILL_VERSION,
                    contract_attempt=number, transport_attempt=1, outcome="contract_error" if attempt.error else "success",
                    will_retry=number < len(generation.attempts), latency_ms=attempt.latency_seconds * 1000,
                    input_tokens=usage.get("prompt_tokens"), output_tokens=usage.get("completion_tokens"),
                    cost_usd=usage.get("cost"), output_is_json_object=attempt.output is not None))
            if generation.output is None:
                if awaiting:
                    return retry_confirmation("응답을 확인하지 못했어요. 정리한 내용을 확인하고 다시 동의해 주세요.")
                return {"conversation_id": str(cid), "message": generation.failure_message,
                        "follow_up_question": None, "action": "stay", "status": "unavailable"}
            raw = generation.output
        raw = deepcopy(raw)
        update = raw.get("profile_update") if raw else None
        # 프로젝트와 실제 본인 수행이 확인되면 선택적인 세부 수집은 끝낸다.
        if update and update.get("action") == "propose" and update.get("review_stage") == "collecting":
            kinds = {fact["kind"] for fact in update.get("facts", [])}
            projects = {fact["value"] for fact in update.get("facts", []) if fact["kind"] == "project"}
            fact_sources = {fact["source_message_id"] for fact in update.get("facts", [])}
            history = context.get("conversation_history") or []
            role_question = history[-1].get("follow_up_question", "") if history else ""
            asked_personal_work = bool(re.search(r"본인.*(?:직접|맡|수행|담당|구현|개발)|직접.*(?:맡|수행|담당|구현|개발|적용|측정|비교|했)", role_question or ""))
            personal_reply_sources = set()
            user_turns = [(index, item) for index, item in enumerate(history) if item.get("role") == "user"]
            # 저장된 사용자 턴과 출처가 순서·본문 모두 일치할 때만 이전 역할 확인을 연결한다.
            if user_turns and len(user_turns) <= len(sources) - 1:
                for previous_source, (index, turn) in zip(sources[-len(user_turns) - 1:-1], user_turns):
                    previous_question = history[index - 1].get("follow_up_question") or "" if index else ""
                    if (previous_source["text"] == turn.get("text") and index
                            and history[index - 1].get("role") == "assistant"
                            and re.search(r"본인.*(?:직접|맡|수행|담당|구현|개발)|직접.*(?:맡|수행|담당|구현|개발|적용|측정|비교|했)", previous_question)):
                        personal_reply_sources.add(previous_source["message_id"])
            direct_work = any(item["message_id"] in fact_sources
                and (re.search(r"제가|내가|저는|나는", item["text"]) or item["message_id"] in personal_reply_sources
                     or (asked_personal_work and item["message_id"] == sources[-1]["message_id"]))
                and (re.search(r"직접\s*(?:했|하였|맡았|담당했|수행했|구현했|개발했|적용했|측정했|비교했)", item["text"])
                     or ((item["message_id"] in personal_reply_sources or (asked_personal_work and item["message_id"] == sources[-1]["message_id"]))
                         and re.search(r"(?:구현|개발|적용|측정|비교|담당|수행|작성|분석|개선)(?:했습니다|하였습니다|했어요|했어|했다|하였다)(?=$|[\s.!?,])", item["text"])))
                and not re.search(r"(?:팀원|동료|친구)[이가은는]|다른\s*(?:사람|개발자)|팀이|직접\s*(?:하지|안|못)|직접[^.!?]{0,20}(?:않았|아니|했는지|했을|한\s*것\s*같|할\s*예정)|(?:구현|개발|담당|수행)하지\s*(?:않았|못했)", item["text"]) for item in sources)
            if len(projects) == 1 and kinds.intersection({"action", "responsibility"}) and direct_work:
                update["review_stage"] = "awaiting_confirmation"
                raw["follow_up_question"] = "이 내용을 연습 참고정보로 저장할까요?"
        # 후보를 보여주며 동의를 묻는 응답은 실제 승인 대기 상태와 연결한다.
        # facts의 원문 출처 검증은 아래 정책에서 그대로 수행한다.
        if update and update.get("action") == "propose" and profile_confirmation_question(raw.get("follow_up_question")):
            update["review_stage"] = "awaiting_confirmation"
            raw["follow_up_question"] = "이 내용을 연습 참고정보로 저장할까요?"
        try:
            decision = (PreparationDecision("stay", stored_answer, None, response_source="server_stored")
                        if raw is None else decide_preparation_action(raw, context))
        except PreparationPolicyError:
            if awaiting:
                return retry_confirmation("반영 동의를 확인하지 못했어요. 정리한 내용을 확인하고 다시 동의해 주세요.")
            raise
        message = decision.message
        question = decision.follow_up_question
        # 복합 조회에서도 모델이 빠뜨린 원문 링크를 서버에서 확인한 값으로 보완한다.
        selected_job = (selection or {}).get("job") or {}
        source_url = selected_job.get("source_url")
        if (decision.action == "stay" and source_url and not (raw and raw.get("intent") == "out_of_scope")
                and re.search(r"공고.*(?:원본|원문|사이트|출처)|(?:원본|원문|출처).*공고", request.message)
                and not re.search(r"말고|하지\s*마|추가|삭제|수정|변경", request.message)
                and source_url not in message):
            message += "\n선택한 공고 원문: " + source_url
        if context.get("selection_proposal"):
            if locked:
                raise PreparationConflict("이미 시작한 연습의 선택은 변경할 수 없어요. 새 연습에서 선택해 주세요.")
            candidate = propose_selection(self.repository, user, selection_values, selection_revision,
                context["selection_proposal"], context["selection_options"], request.message)
            if candidate:
                state.update(selection=selection_values, selection_revision=selection_revision, pending_selection=candidate)
                message, question = candidate["summary"], "이 선택으로 변경할까요?"
                selection_event = "awaiting_confirmation"
            else:
                message, question = "이미 같은 항목이 선택되어 있어요.", None
        if selection_event == "verified":
            message, question = "선택 변경을 저장하고 결과를 확인했어요.", None
        elif selection_event == "cancelled":
            message, question = "미적용 선택 변경 후보를 취소했어요.", None
        u = raw.get("profile_update") if raw else None
        if decision.action == "propose":
            state["pending_selection"] = None
            labels = {"company": "회사", "period": "기간", "role": "직무", "responsibility": "담당 업무", "project": "프로젝트", "action": "실제 행동", "outcome": "확인한 결과", "technology": "기술"}
            # 사용자에게 실제 저장 후보 전체를 보여준다. 모델 message와 별개인 숨은 facts에 동의시키지 않는다.
            message = "원본 문서는 유지해요. **연습 참고정보 후보**:\n" + "\n".join(f"{labels[f['kind']]}: {f['value']}" for f in u["facts"])
            state["pending"] = {"draft_id": decision.draft_id or str(uuid4()),
                "draft_version": (decision.draft_version or 0) + 1,
                "facts": u["facts"], "summary": message, "status": u["review_stage"],
                "confirmation_requested": u["review_stage"] == "awaiting_confirmation"}
        elif decision.action == "request_save":
            saved = dict(pending, source_type="user_chat", user_confirmed=True, usage="reference_only")
            state["confirmed"] = [*state.get("confirmed", []), saved]
            state["pending"] = dict(pending, status="saved", confirmation_requested=False)
            message = preparation_completion_message(decision, succeeded=True)
        elif decision.action == "discard":
            state["pending"] = None
            message = preparation_completion_message(decision, succeeded=True)
        elif decision.action == "request_rerecord":
            # 화면은 응답을 받은 클라이언트가 열어야 한다. 열었다고 미리 말하지 않는다.
            message = "재답변 입력으로 이어갈게요. 녹음하거나 WAV 파일을 올릴 수 있어요."
        if decision.action == "propose" and state["pending"]["confirmation_requested"]:
            message += "\n" + PROFILE_CONSENT_GUIDANCE
        response = {"conversation_id": str(cid), "message": message,
                    "follow_up_question": question,
                    "action": "selection_updated" if selection_event == "verified" else "request_rerecord" if decision.action == "request_rerecord" else "stay", "status": "ok"}
        if state.get("selection"):
            response.update(selection_state=state["selection"], selection_revision=state["selection_revision"],
                            execution_result="awaiting_confirmation" if selection_event == "awaiting_confirmation" else "verified" if selection_event == "verified" else None)
        if selection_event == "verified" and state["selection"]["job_posting_id"]:
            job = self.repository.selection_context(user, SelectionSnapshot.model_validate(state["selection"]))["job"]
            response["selection_job"] = {**job, "requirements": [{**r, "text": r.get("requirement_text", r.get("text", ""))}
                for r in job.get("job_requirements", job.get("requirements", []))]}
        # 모델이 첫 요청에서 초안 대신 대상 질문만 했어도 추가 요청은 유지한다.
        if (re.search(r"이력서|경험|경력|참고정보", request.message)
                and re.search(r"(?:추가|반영|저장)\s*해\s*(?:줘|주세요)|추가하고\s*싶", request.message)
                and not re.search(r"하지\s*마|말고|취소|친구|가정|예시|만약", request.message)):
            context["profile_task_requested"] = True
        state["profile_task_requested"] = bool(context.get("profile_task_requested"))
        if decision.action in {"request_save", "discard"}:
            state["profile_task_requested"] = False
        state["sources"] = sources
        state["history"] = [*state.get("history", []), {"role": "user", "text": request.message},
            {"role": "assistant", "message": message, "follow_up_question": question,
             "answer_kind": context.get("free_chat_answer_kind"),
             "selection_candidate_id": state["pending_selection"]["id"] if selection_event == "awaiting_confirmation" else None}]
        state["responses"] = dict(completed, **{rid: {"input": fingerprint, "response": response}})
        # 실제 저장 실패/경쟁이면 완료 응답을 반환하지 않는다. CAS가 초안 버전을 고정한다.
        try:
            self.repository.save(user, row, state, request.practice_session_id)
        except PreparationConflict:
            if decision.action != "request_save":
                raise
            # 경쟁 요청이 초안을 바꿨다면 오래된 요약으로 다시 동의받지 않는다.
            latest = self.repository.load(user, cid)["state"]
            pending = latest.get("pending")
            if pending and pending.get("status") == "awaiting_confirmation" and pending.get("confirmation_requested"):
                return retry_confirmation("다른 요청이 먼저 처리됐어요. 최신 정리 내용을 확인하고 다시 동의해 주세요.")
            if pending and pending.get("status") == "saved" and any(
                (item.get("draft_id"), item.get("draft_version")) == (decision.draft_id, decision.draft_version)
                for item in latest.get("confirmed", [])
            ):
                return response
            raise
        except SupabasePersistenceError:
            if decision.action == "request_save":
                # 응답 유실이면 DB에는 저장됐을 수도 있다. 재요청은 최신 상태/요청 ID로 중복을 막는다.
                return retry_confirmation("저장 결과를 확인하지 못했어요. 다시 동의해 주시면 최신 저장 상태를 확인한 뒤 처리할게요.")
            raise
        if decision.action in {"request_save", "discard"} or selection_event:
            try:
                actual = self.repository.load(user, cid)["state"]
                if any(actual.get(key) != state.get(key) for key in ["confirmed", "pending", "selection", "selection_revision", "pending_selection"]):
                    raise PreparationConflict("실행 결과가 최신 상태와 달라요. 다시 확인해 주세요.")
            except (SupabasePersistenceError, PreparationConflict, KeyError):
                return {"conversation_id": str(cid), "message": "처리 결과를 확인하지 못했어요. 현재 상태를 다시 확인하고 요청해 주세요.",
                        "follow_up_question": None, "action": "stay", "status": "unavailable", "execution_result": "failed"}
        return response
