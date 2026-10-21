"""설정 변경은 표시한 초기화 범위에 동의한 뒤 서버에서 실행한다."""
from copy import deepcopy
from datetime import UTC, datetime, timedelta
import re
from uuid import uuid4

from app.services.preparation_conversation_repository import PreparationConflict

LABELS = {"ncs": "NCS 선택", "resume": "이력서 제출", "readme": "리드미 제출", "jobs": "공고 선택", "questions": "질문 선택"}
PRESERVE = {
    "ncs": [], "resume": ["selected_ncs_ids"],
    "readme": ["selected_ncs_ids", "resume_profile"],
    "jobs": ["selected_ncs_ids", "resume_profile", "readme_analysis"],
    "questions": ["selected_ncs_ids", "resume_profile", "readme_analysis"],
}

def restart_target(message):
    if not re.search(r"바꿔|변경|교체|다시\s*선택|선택\s*다시|다시\s*제출|재선택|처음부터|돌아|이동|만\s*보여", message):
        return None
    if re.search(r"리드미|README|readme", message): return "readme"
    if re.search(r"NCS|ncs|직무\s*능력", message): return "ncs"
    if "이력서" in message and re.search(r"교체|다시\s*제출|새로\s*제출|제출.*이동", message): return "resume"
    if "공고" in message and not re.search(r"원본|원문|사이트", message): return "jobs"
    if "질문" in message and re.search(r"선택|처음|돌아|이동", message): return "questions"
    return None

# Review steps follow completed selection/submission; requirements follow job selection.
STEP_ORDER = {"ncs": 0, "ncs_review": 1, "resume": 2, "resume_review": 3,
    "readme": 4, "readme_review": 5, "jobs": 6, "requirements": 7,
    "questions": 8, "first_coaching": 9}
TARGET_ORDER = {"ncs": 0, "resume": 2, "readme": 4, "jobs": 6, "questions": 8}
STEP_LABELS = {**LABELS, "ncs_review": "NCS 선택 내용 확인", "resume_review": "이력서 검토",
    "readme_review": "리드미 검토", "requirements": "공고 요구사항 선택", "first_coaching": "답변 코칭"}

def restart_guidance(target, request):
    step = request.ui_context or ("first_coaching" if request.practice_session_id else request.current_stage)
    if step == "first_coaching" and not request.practice_session_id:
        return "현재 연습의 진행 기록을 확인할 수 없어 설정을 변경할 수 없어요. 현재 화면에서 연습을 이어가 주세요. 채팅 내역은 유지됩니다."
    if STEP_ORDER[step] > TARGET_ORDER[target]:
        return None
    if STEP_ORDER[step] == TARGET_ORDER[target]:
        return f"현재 {LABELS[target]} 단계에 있어요. 아직 이 단계를 지나지 않아 이전 단계로 이동할 필요는 없어요. 현재 화면에서 선택·입력을 진행해 주세요. 채팅 내역은 유지됩니다."
    return f"아직 {LABELS[target]} 단계를 진행하지 않아 다시 선택하거나 변경할 수 없어요. 현재는 {STEP_LABELS[step]} 단계예요. NCS 선택 → 이력서 제출 → 리드미 제출 → 공고 선택 → 질문 선택 순서로 진행해 주세요. 채팅 내역은 유지됩니다."

def record_restart_response(repository, user, row, state, request, fingerprint, response):
    state["responses"] = {**state.get("responses", {}), str(request.request_id): {"input": fingerprint, "response": response}}
    state["history"] = [*state.get("history", []), {"role": "user", "text": request.message}, {"role": "assistant", "message": response["message"], "follow_up_question": response["follow_up_question"]}]
    repository.save(user, row, state, request.practice_session_id)
    return response

def blocked_restart(repository, user, row, state, request, fingerprint, target):
    guidance = restart_guidance(target, request)
    if not guidance:
        return None
    state.pop("pending_restart", None)
    response = {"conversation_id": row["id"], "message": guidance, "follow_up_question": None, "action": "stay", "status": "ok"}
    return record_restart_response(repository, user, row, state, request, fingerprint, response)

def handle_restart(repository, user, row, state, request, fingerprint):
    confirmation = request.restart_confirmation
    retired = state.get("restart_completed")
    if retired:
        if confirmation and str(confirmation.token) == retired["token"] and confirmation.confirm:
            return deepcopy(retired["response"])
        raise PreparationConflict("이미 초기화된 대화입니다. 새 대화에서 요청해 주세요.")
    pending = state.get("pending_restart")
    positive = bool(re.fullmatch(r"(?:네|예|응|좋아|확인|동의|진행|해줘|진행해줘|확인했어|좋아\s*진행해줘)[\s.!]*", request.message.strip()))
    cancel = bool(re.fullmatch(r"(?:아니|아니요|취소|취소해줘|유지해줘)[\s.!]*", request.message.strip()))
    if confirmation or (pending and (positive or cancel)):
        if not pending or (confirmation and str(confirmation.token) != pending["token"]):
            raise PreparationConflict("설정 변경 확인이 만료됐어요. 다시 요청해 주세요.")
        if datetime.fromisoformat(pending["expires_at"]) <= datetime.now(UTC):
            raise PreparationConflict("설정 변경 확인이 만료됐어요. 다시 요청해 주세요.")
        accept = confirmation.confirm if confirmation else positive
        if accept:
            blocked = blocked_restart(repository, user, row, state, request, fingerprint, pending["target"])
            if blocked:
                return blocked
            response = {"conversation_id": str(uuid4()), "message": "설정 변경을 확인했어요. 새 선택부터 연습을 이어갑니다.",
                "follow_up_question": None, "action": "practice_restarted", "status": "ok",
                "execution_result": "verified", "restart": pending}
            return repository.restart(user, row, pending, response, str(request.request_id), fingerprint)
        state.pop("pending_restart", None)
        response = {"conversation_id": row["id"], "message": "변경을 취소했어요. 현재 연습과 대화 내역을 유지합니다.", "follow_up_question": None, "action": "stay", "status": "ok"}
    else:
        target = request.restart_target or restart_target(request.message)
        if not target:
            if pending:
                state.pop("pending_restart", None)
                repository.save(user, row, state)
                row.update(repository.load(user, row["id"]))
            return None
        blocked = blocked_restart(repository, user, row, state, request, fingerprint, target)
        if blocked:
            return blocked
        materials = request.review_context.model_dump(mode="json") if request.review_context else {}
        sid = row.get("practice_session_id") or (str(request.practice_session_id) if request.practice_session_id else None)
        if sid:
            materials = repository.session(user, sid).get("applicant_context") or materials
        materials = {key: deepcopy(materials.get(key)) for key in PRESERVE[target]}
        materials.setdefault("selected_ncs_ids", [])
        selection = request.selection.model_dump(mode="json") if request.selection else {}
        if target == "questions" and sid:
            context = repository.selection_context(user, session_id=sid)
            selection = {"job_posting_id": (context.get("job") or {}).get("id"), "requirement_ids": [str(r["id"]) for r in context.get("selected_requirements", [])]}
        if target != "questions": selection = {}
        selection.update(question_id=None, custom_question_text=None)
        if target != "questions": selection.update(job_posting_id=None, requirement_ids=[])
        pending = {"token": str(uuid4()), "target": target,
            "new_graduate_only": target == "jobs" and "신입" in request.message,
            "materials": materials, "selection": selection,
            "expires_at": (datetime.now(UTC) + timedelta(minutes=10)).isoformat()}
        preserved = {"ncs": "없음", "resume": "NCS", "readme": "NCS·이력서", "jobs": "NCS·이력서·리드미", "questions": "NCS·이력서·리드미·공고·요구사항"}[target]
        message = f"{LABELS[target]} 채팅으로 이동합니다. 현재 연습의 이전 채팅·추가 참고정보·코칭 내역은 삭제되고 녹음은 현재 연습에서 제거됩니다.\n유지: {preserved}. 다른 연습 기록은 유지됩니다."
        if pending["new_graduate_only"]: message += "\n신입 지원 가능 공고(신입·경력무관)만 표시합니다. 경력 조건이 확인되지 않은 공고는 제외합니다."
        response = {"conversation_id": row["id"], "message": message, "follow_up_question": "확인하고 진행할까요? ‘네’ 또는 ‘취소’로 답해 주세요.", "action": "stay", "status": "ok", "execution_result": "awaiting_confirmation", "restart": pending}
        state["pending_restart"] = pending
    return record_restart_response(repository, user, row, state, request, fingerprint, response)
