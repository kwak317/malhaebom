"""이미 선택·확정된 자료의 조회. 새 평가·문서 수정·단계 이동은 하지 않는다."""
import re

LABELS = {"problem_context": "문제 상황", "cause_observation": "원인 관찰", "cause_inference": "원인 추론",
          "own_action": "본인의 해결 행동", "action_rationale": "행동 선택 이유", "result_verification": "결과 확인"}


def stored_information_response(context):
    text = context["user_message"]
    history = context.get("conversation_history") or []
    if history and history[-1].get("role") == "assistant" and history[-1].get("follow_up_question"):
        # 대상·정보 보완 발화는 직전 작업을 이어야 한다. 동의는 runtime이 먼저 처리한다.
        return None
    # 단순 조회 최적화는 변경·비교·작성·검토 요청보다 앞서지 않는다.
    if re.search(r"바꿔|바꾸|변경|비교|차이|정정|수정|제외|검토|과장|작성|선택(?!한|된)|골라", text):
        return None
    # 새 사실 추가·정정은 기존 초안/동의 흐름으로 보낸다.
    if re.search(r"추가(?!로|된|한)|취소|삭제|반영(?!한|된)|저장(?!한|된|완료)|경력.*수정", text):
        return None
    if re.search(r"그리고|또한|(?:보여|알려)\s*주고|말고|하지\s*마", text):
        return None
    selection = context.get("selection_context") or {}
    job = selection.get("job") or {}
    if re.search(r"공고.*(?:원본|원문|사이트|출처)|(?:원본|원문|출처).*공고", text):
        if job.get("source_url"):
            return "선택한 공고 원문: " + job["source_url"]
        return "현재 선택한 공고를 확인할 수 없어요. 먼저 공고를 선택해 주세요."
    if "공고" in text and re.search(r"회사|마감", text):
        if not job:
            return "현재 선택한 공고를 확인할 수 없어요. 먼저 공고를 선택해 주세요."
        return f"회사: {job['company']}\n공고: {job['title']}\n마감일은 저장된 공고 자료에 없어 확인할 수 없어요.\n공고 원문: {job['source_url']}"
    if re.search(r"(?:아까|저장한|정리한).*경험.*(?:보여|알려|다시)", text):
        if "저장한" not in text:
            drafts = [item["message"] for item in context.get("conversation_history", [])
                      if item.get("role") == "assistant" and
                      (item.get("answer_kind") == "draft" or item.get("message", "").startswith("연습용 작성안:"))]
            generic = re.fullmatch(r"(?:아까|정리한|아까\s*정리한)\s*(?:프로젝트\s*)?경험\s*(?:다시\s*)?(?:보여|알려)\s*(?:줘|주세요)[.!]?", text.strip())
            if drafts and (len(drafts) != 1 or not generic):
                return None
            if drafts:
                return "앞서 대화에서 작성한 초안이에요.\n" + drafts[-1]
            pending = context.get("pending_profile_update") or {}
            if pending.get("status") in {"collecting", "awaiting_confirmation"} and pending.get("summary") and generic:
                return "아직 저장하지 않은 연습 참고정보 초안이에요.\n" + pending["summary"]
            if pending.get("status") in {"collecting", "awaiting_confirmation"} and not generic:
                return None
        confirmed = context.get("confirmed_supplemental_context") or []
        if confirmed:
            return "이번 연습의 참고 정보:\n" + "\n".join(item["summary"] for item in confirmed)
        return "이번 대화에서 확인 후 저장한 참고 경험은 아직 없어요."
    coaching = context.get("coaching_context") or {}
    answer = coaching.get("confirmed_answer")
    assessments = (coaching.get("coaching") or {}).get("criterion_assessments") or []
    if not answer or not assessments:
        return None

    def quotes(item):
        # 이미 코칭 단계에서 검증한 인용만 원래 확정 답변과 다시 대조한다.
        return [q for e in item.get("evidence") or []
                if (q := e.get("quote") if isinstance(e, dict) else e) and q in answer]

    def describe(item):
        evidence = quotes(item)
        return (LABELS.get(item["criterion_id"], item["criterion_id"]) + ": " + item["reason"]
                + ("\n답변 근거: " + " / ".join(evidence) if evidence else "\n현재 코칭에 인용된 답변 근거는 없어요."))

    gaps = [item for item in assessments if item["assessment"] != "met"]
    next_actions = [item["action"] for item in (coaching.get("coaching") or {}).get("next_actions", [])
                    if isinstance(item, dict) and item.get("action")]
    if re.search(r"역할|본인.*행동", text) and re.search(r"불명확|부족|왜|이유", text):
        own = next((item for item in assessments if item["criterion_id"] == "own_action"), None)
        if own:
            prefix = "현재 코칭에서는 본인의 해결 행동이 확인된 것으로 평가했어요.\n" if own["assessment"] == "met" else ""
            return prefix + describe(own)
    if re.search(r"어느.*문장|어떤.*문장|판단.*근거|근거.*(?:보여|알려)", text):
        return "현재 코칭의 판단과 실제 답변 근거:\n" + "\n\n".join(describe(item) for item in assessments)
    if re.search(r"가장.*(?:고칠|개선|보완)|먼저.*고칠|한\s*번에\s*하나|피드백.*하나", text):
        if not gaps:
            return ("현재 코칭에서는 모든 항목의 근거가 확인됐어요.\n다음 연습에서 할 일: " + next_actions[0]
                    if next_actions else None)
        first = gaps[0]
        return "현재 코칭에서 보완할 항목 중 첫 번째:\n" + describe(first) + "\n보완할 내용: " + (first.get("needed") or first["reason"])
    if re.search(r"잘한|잘했던|좋았던|강점", text):
        strengths = [item for item in assessments if item["assessment"] == "met"]
        if strengths:
            return "현재 코칭에서 확인한 부분:\n" + "\n\n".join(describe(item) for item in strengths)
        return "현재 코칭에는 충족된 것으로 평가한 항목이 없어요. 이 결과만으로 경험이나 역량이 없다고 판단하지는 않아요."
    if "답변" in text and re.search(r"핵심만|짧게|줄여|축약", text):
        kept = list(dict.fromkeys(q for item in assessments
                    if item["criterion_id"] in {"problem_context", "own_action", "result_verification"}
                    for q in quotes(item)))
        if kept:
            return "원래 답변의 문제·행동·확인 결과를 남긴 연습용 축약본:\n" + " ".join(kept)
    if "답변" in text and re.search(r"1분|일\s*분", text):
        return None
    if re.search(r"요약|정리", text) and re.search(r"오늘|연습|피드백|코칭|고칠|다음", text):
        missing = "\n".join(LABELS.get(item["criterion_id"], item["criterion_id"]) + ": " + (item.get("needed") or item["reason"]) for item in gaps)
        if not missing and not next_actions:
            return None
        return ("현재 연습에서 확정한 답변:\n" + answer + "\n\n현재 코칭에서 다음에 보완할 내용:\n"
                + (missing or "현재 코칭에서는 추가로 부족하다고 판정한 항목이 없어요.")
                + ("\n다음 연습에서 할 일:\n" + "\n".join(next_actions) if next_actions else ""))
    return None
