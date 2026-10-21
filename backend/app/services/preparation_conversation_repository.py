"""서버만 쓰는 준비 대화 상태. 사용자·만료·버전 조건을 모든 요청에 유지한다."""
from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import quote
import httpx

from app.services.supabase_persistence import SupabaseAnalysisRepository, SupabasePersistenceError


class PreparationConflict(ValueError):
    pass


class PreparationRepository:
    def __init__(self, settings, http_client=None):
        if not settings.service_role_key:
            raise ValueError("서버 저장소 설정이 필요합니다.")
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=20.0)
        self.records = SupabaseAnalysisRepository(settings, self.http)

    def _request(self, method, path, **kwargs):
        key = self.settings.service_role_key
        try:
            response = self.http.request(method, self.settings.url + path,
                headers={"apikey": key, "Authorization": f"Bearer {key}", "Prefer": "return=representation"}, **kwargs)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            raise SupabasePersistenceError("PREPARATION_PERSISTENCE_FAILED", "대화 상태를 저장하거나 불러오지 못했습니다.") from None

    def _scope(self, user, conversation_id):
        return (f"id=eq.{quote(str(conversation_id), safe='')}&user_id=eq.{quote(user.user_id, safe='')}"
                f"&expires_at=gt.{quote(datetime.now(UTC).isoformat(), safe='')}")

    def create(self, user, conversation_id):
        # 요청 ID와 같은 UUID를 사용해 응답 유실 후 시작 재요청도 같은 행을 조회한다.
        try:
            rows = self._request("POST", "/rest/v1/preparation_conversations",
                json={"id": str(conversation_id), "user_id": user.user_id, "state": {}})
            return rows[0]
        except SupabasePersistenceError:
            # 동일 시작 요청의 경합/응답 유실. 타인 행은 load의 소유자 조건으로 가려진다.
            return self.load(user, conversation_id)

    def load(self, user, conversation_id):
        rows = self._request("GET", "/rest/v1/preparation_conversations?" + self._scope(user, conversation_id) + "&select=*")
        if not rows or rows[0]["user_id"] != user.user_id:
            raise KeyError(str(conversation_id))
        return rows[0]

    def save(self, user, row, state, session_id=None):
        values = {"state": state, "version": row["version"] + 1}
        if session_id is not None:
            values["practice_session_id"] = str(session_id)
        rows = self._request("PATCH", "/rest/v1/preparation_conversations?" + self._scope(user, row["id"])
            + f"&version=eq.{row['version']}", json=values)
        if len(rows) != 1:
            raise PreparationConflict("다른 요청이 먼저 처리됐어요. 현재 대화에서 다시 보내 주세요.")
        return rows[0]

    def restart(self, user, row, pending, response, request_id, fingerprint):
        result = self._request("POST", "/rest/v1/rpc/restart_preparation_practice", json={
            "p_user_id": user.user_id, "p_conversation_id": row["id"], "p_version": row["version"],
            "p_token": pending["token"], "p_new_id": response["conversation_id"],
            "p_response": response, "p_request_id": request_id, "p_input_hash": fingerprint})
        if not isinstance(result, dict) or result.get("action") != "practice_restarted":
            raise PreparationConflict("초기화 결과를 확인하지 못했어요. 다시 요청해 주세요.")
        return result

    def session(self, user, session_id):
        result = self.records.get_practice_session(user, str(session_id))
        expiry = datetime.fromisoformat(str(result["expires_at"]).replace("Z", "+00:00"))
        if expiry <= datetime.now(UTC):
            raise KeyError(str(session_id))
        return result

    def history(self, user, session_id):
        self.session(user, session_id)  # Verify ownership and the existing retention period first.
        rows = self._request("GET", supplemental_context_path(session_id, user.user_id) + "&order=created_at.asc")
        return [
            {"role": message["role"],
             "message": message.get("text", "") if message["role"] == "user" else message.get("message", ""),
             "follow_up_question": message.get("follow_up_question") if message["role"] == "assistant" else None}
            for row in rows for message in row.get("state", {}).get("history", [])
            if message.get("role") in {"user", "assistant"}
        ]

    def selection_options(self, user):
        response = self.records._request("GET", "/rest/v1/job_postings"
            "?review_status=eq.reviewed&is_active=eq.true&order=captured_at.desc&limit=20"
            "&select=id,company,title,job_requirements(id,requirement_text)", user=user)
        return response.json()

    def selection_context(self, user, selection=None, session_id=None):
        """식별자만 받아 사용자 JWT로 조회한다. 연습 생성 후에는 저장된 선택이 우선이다."""
        selected = selection.model_dump(mode="json") if selection else {}
        if session_id:
            session = self.session(user, session_id)
            if selected.get("job_posting_id") not in (None, session["job_posting_id"]):
                raise PreparationConflict("현재 연습과 다른 공고를 사용할 수 없어요.")
            selected["job_posting_id"] = session["job_posting_id"]
            selected["question_id"] = session.get("question_id")
            selected["custom_question_text"] = session.get("custom_question_text")
            response = self.records._request("GET", "/rest/v1/practice_session_requirements"
                f"?practice_session_id=eq.{quote(str(session_id), safe='')}&select=requirement_id", user=user)
            selected["requirement_ids"] = [row["requirement_id"] for row in response.json()]
        job = None
        requirements = []
        posting_id = selected.get("job_posting_id")
        if posting_id:
            response = self.records._request("GET", "/rest/v1/job_postings"
                f"?id=eq.{quote(str(posting_id), safe='')}&review_status=eq.reviewed&is_active=eq.true"
                "&select=id,company,title,source_url,captured_at,data_origin,"
                "job_requirements(id,code,requirement_text,source_excerpt,display_order)", user=user)
            rows = response.json()
            if not rows:
                if session_id:
                    # 기존 연습의 코칭은 유지한다. 현재 조회할 수 없는 공고를 추측하지 않는다.
                    return {"job": None, "selected_requirements": [], "question": None,
                            "source_type": "server_loaded_reference", "unavailable": "selected_job"}
                raise KeyError(str(posting_id))
            job = rows[0]
            requirements = job.get("job_requirements") or []
        chosen = set(selected.get("requirement_ids") or [])
        if not chosen.issubset({str(item["id"]) for item in requirements}):
            raise PreparationConflict("선택한 요구사항이 현재 공고에 속하지 않아요.")
        question = None
        if selected.get("question_id"):
            from app.services.coaching_questions import get_preset_coaching_question
            preset = get_preset_coaching_question(selected["question_id"])
            if preset is None:
                raise PreparationConflict("선택한 질문을 확인할 수 없어요.")
            question = preset.model_dump(mode="json")
        elif selected.get("custom_question_text"):
            question = {"text": selected["custom_question_text"], "source_type": "user_provided_reference"}
        return {"job": job, "selected_requirements": [item for item in requirements if str(item["id"]) in chosen],
                "question": question, "source_type": "server_loaded_reference",
                "missing_fields": ["deadline", "experience_condition"] if job else []}

    def first_coaching(self, user, session_id):
        session = self.session(user, session_id)
        rows = self.records.get_completed_session_jobs(user, str(session_id))
        first = next((r for r in rows if r.get("attempt_no") == 1), None)
        if first is None or any(r.get("attempt_no") == 2 for r in rows):
            raise PreparationConflict("1차 코칭을 완료한 뒤 재답변 전에 질문해 주세요.")
        revisions = first.get("answer_revisions") or []
        if not revisions:
            raise PreparationConflict("1차 전사문을 먼저 확인해 주세요.")
        revision = max(revisions, key=lambda r: r["confirmed_at"])
        runs = revision.get("coaching_runs") or []
        if not runs:
            raise PreparationConflict("1차 코칭을 먼저 완료해 주세요.")
        run = max(runs, key=lambda r: r["created_at"])
        from app.services.coaching_questions import get_preset_coaching_question
        question = get_preset_coaching_question(str(session.get("question_id")))
        return {"question_id": session.get("question_id"), "question_text": question.text if question else session.get("custom_question_text"),
                "answer_revision_id": revision["id"], "coaching_run_id": run.get("id") or run["created_at"],
                "confirmed_answer": revision["confirmed_text"], "answer_segments": revision.get("answer_segments") or [],
                "coaching": run["response"],
                "delivery_metrics": revision.get("delivery_metrics"),
                "selection_context": self.selection_context(user, session_id=session_id)}


def confirmed_context(rows):
    """DB의 같은 연습에 묶인 자료만 반환한다. 출처와 확인 상태를 재명시한다."""
    return [dict(item, source_type="user_chat", user_confirmed=True, usage="reference_only")
            for row in rows for item in row.get("state", {}).get("confirmed", [])]


def supplemental_context_path(session_id, user_id):
    now = quote(datetime.now(UTC).isoformat(), safe="")
    return ("/rest/v1/preparation_conversations"
            f"?practice_session_id=eq.{quote(str(session_id), safe='')}&user_id=eq.{quote(str(user_id), safe='')}"
            f"&expires_at=gt.{now}&select=state")
