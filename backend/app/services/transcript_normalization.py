"""Optional transcript editing; never replaces persisted STT or confirms an answer."""
from __future__ import annotations
import hashlib
import json
import logging
import time
import os
import re
from uuid import UUID, uuid4
from fastapi import Depends, HTTPException
from openai import OpenAI, APIConnectionError, APIStatusError
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.services.loading_progress import report_progress
from app.core.auth import AuthenticatedUser
from app.services.supabase_persistence import SupabasePersistenceError

logger = logging.getLogger(__name__)

PROMPT_NAME = "malhaebom-transcript-normalization"
PROMPT_VERSION = 3
PROMPT_SHA256 = "559994bc6f9cb5fd9e22dfd5bc1628997e80aa8549f6b62a568b0eaff0545c84"

class NormalizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transcript: str = Field(min_length=1, max_length=5000)

    @field_validator("transcript")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("전사문을 입력해 주세요.")
        return value

class Edit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    original: str = Field(min_length=1, max_length=5000)
    replacement: str = Field(max_length=5000)
    edit_type: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)

class Confirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    original: str = Field(min_length=1, max_length=5000)
    replacement: str = Field(max_length=5000)
    reason: str = Field(min_length=1, max_length=2000)
    applied: bool

class NormalizedTranscript(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transcript: str = Field(min_length=1, max_length=5000)
    edit_log: list[Edit] = Field(max_length=200)
    confirmations: list[Confirmation] = Field(max_length=200)
    meaning_preservation_check: str = Field(min_length=1, max_length=3000)

class NormalizeResponse(NormalizedTranscript):
    prompt_name: str
    prompt_version: int
    trace_id: str

class ProviderEdit(Edit):
    requires_confirmation: bool
    applied: bool

class ProviderTranscript(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transcript: str = Field(min_length=1, max_length=5000)
    edits: list[ProviderEdit] = Field(max_length=200)
    meaning_preservation_check: str = Field(min_length=1, max_length=3000)

OUTPUT_CONTRACT = """
Conservative uncertainty policy for this output: when repairing a nonstandard connector, joined words, or broken sentence boundary by interpreting context, flag requires_confirmation=true even if a dialect interpretation is plausible. This also applies when changing an unclear spoken measurement verb into a standard measurement verb. Prefer flagging an ambiguous repair over silently treating it as dialect. Before returning, check every rewritten sentence for such repairs and set the flag on the relevant edit. Write the final transcript with 합니다/했습니다 endings only, including clauses that originally ended in 했고요.
Before serialization, audit each changed span: a clearly understood dialect ending needs no confirmation, but reconstructing a malformed word, unclear connector, or broken sentence boundary ALWAYS requires_confirmation=true, even when the context makes one interpretation likely. If a span combines ordinary dialect and an inferred reconstruction, flag the whole edit. Do not hide an inferred repair inside a dialect or tone edit. Account explicitly for removed words as flagged deletions. Use consistent 합니다/했습니다 sentence endings throughout the final transcript. The meaning check must mention remaining uncertainty and must not claim verified accuracy.
Output serialization contract: Preserve every v3 editorial, dialect, inference, deletion and meaning safeguard above. Only the serialization differs from the four-section presentation: return the supplied JSON schema with transcript, edits, meaning_preservation_check. Do not output edit_log or confirmations separately.
Represent each substantive change once in edits: original, replacement, edit_type, reason, requires_confirmation, applied. The server derives edit_log from applied edits and confirmations from requires_confirmation edits. This preserves v3's reporting requirements without duplicated entries.
Every inferred reconstruction or deletion must be flagged requires_confirmation=true. Every unapplied suggestion must also be flagged true and its original must remain verbatim in the final transcript. Applied replacements must be exact substrings of the final transcript. Original spans must be exact substrings of the input. For deletion, replacement is empty and applied=true. Log all substantive dialect, recognition and tone edits; omit routine punctuation, spacing, number spelling and polite-ending-only changes. Use short Korean reasons and edit types. Keep the full transcript, never summarize or omit it. Keep the meaning check to one short Korean sentence. All text values are Korean. No markdown.
"""

def provider_schema():
    # Keep length limits in server validation; send the portable JSON-schema subset.
    def strip(value):
        if isinstance(value, dict):
            return {k: strip(v) for k, v in value.items() if k not in {"minLength", "maxLength", "maxItems", "title"}}
        if isinstance(value, list):
            return [strip(v) for v in value]
        return value
    return strip(ProviderTranscript.model_json_schema())


class NormalizationContractError(ValueError):
    def __init__(self, message, output):
        super().__init__(message)
        self.output = output
        self.code = message


class TranscriptNormalizationService:
    def __init__(self, langfuse_client, llm_client=None):
        self.langfuse = langfuse_client
        self.llm = llm_client

    def normalize(self, transcript: str) -> NormalizeResponse:
        operation_id = uuid4().hex
        try:
            return self._normalize_once(transcript, operation_id=operation_id, attempt=1)
        except NormalizationContractError as error:
            report_progress("추정 표현과 변경 내역을 다시 확인하고 있어요…")
            return self._normalize_once(transcript, repair={"output": error.output, "violation": error.code}, operation_id=operation_id, attempt=2)
        except ValueError:
            report_progress("변환 결과 형식을 다시 확인하고 있어요…")
            return self._normalize_once(transcript, repair=True, operation_id=operation_id, attempt=2)
        except (APIConnectionError, APIStatusError) as error:
            status = getattr(error, "status_code", None)
            if isinstance(error, APIStatusError) and status not in {429, 500, 502, 503, 504}:
                raise
            report_progress("모델 연결을 다시 시도하고 있어요…")
            time.sleep(0.5)
            return self._normalize_once(transcript, operation_id=operation_id, attempt=2)

    def _normalize_once(self, transcript: str, repair: dict | bool = False, *, operation_id: str = "", attempt: int = 1) -> NormalizeResponse:
        if self.langfuse is None:
            raise RuntimeError("Managed prompt unavailable")
        report_progress("표준어 변환 기준을 불러오고 있어요…")
        prompt = self.langfuse.get_prompt(PROMPT_NAME, version=PROMPT_VERSION, type="text", cache_ttl_seconds=60)
        if hashlib.sha256(prompt.prompt.encode()).hexdigest() != PROMPT_SHA256:
            raise RuntimeError("Managed prompt content mismatch")
        client = self.llm or OpenAI(
            api_key=os.getenv("COACHING_LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("COACHING_LLM_BASE_URL", "https://openrouter.ai/api/v1"),
            timeout=90, max_retries=0,
        )
        model = "google/gemini-3.1-pro-preview"
        trace_id = uuid4().hex
        observation = None
        metadata = {"prompt_code_version": "v3", "output_contract_version": "single-edits-v1", "input_characters": len(transcript), "operation_id": operation_id, "attempt": attempt}
        try:
            observation = self.langfuse.start_observation(
                trace_context={"trace_id": trace_id}, name="transcript-normalization",
                as_type="generation", model=model, prompt=prompt,
                model_parameters={"reasoning_effort": "low", "max_tokens": 5000, "temperature": 0},
                metadata=metadata,
            )
        except Exception:
            pass
        stage = "provider"
        started = time.monotonic()
        usage_details = {}
        finish_reason = None
        try:
            report_progress("사투리와 구어체를 표준어로 다듬고 있어요…")
            response = client.chat.completions.create(
                model=model, temperature=0, max_tokens=5000,
                extra_body={"reasoning": {"effort": "low", "exclude": True}, "provider": {"require_parameters": True}},
                messages=[{"role": "system", "content": prompt.prompt + OUTPUT_CONTRACT},
                    {"role": "user", "content": json.dumps({"transcript": transcript, **({"previous_output": repair if isinstance(repair, dict) else None, "format_reminder": "Fix the reported contract violation. Return only transcript, edits, and meaning_preservation_check. Each applied replacement must exactly occur in the final transcript; each unapplied original must remain verbatim. Original spans must occur in the input. Preserve meaning and all v3 editorial safeguards. Do not retain rhetorical interview questions."} if repair else {})}, ensure_ascii=False)}],
                response_format={"type": "json_schema", "json_schema": {
                    "name": "transcript_normalization", "strict": True,
                    "schema": provider_schema()}},
            )
            usage = response.usage
            if usage is not None:
                usage_details = {"input": usage.prompt_tokens, "output": usage.completion_tokens}
            report_progress("원문 의미와 수정 내역을 검토하고 있어요…")
            stage = "validation"
            finish_reason = response.choices[0].finish_reason
            if finish_reason != "stop":
                raise NormalizationContractError("INCOMPLETE_OUTPUT", None)
            result = ProviderTranscript.model_validate_json(response.choices[0].message.content)
            payload = result.model_dump()
            if not result.transcript.strip():
                raise NormalizationContractError("EMPTY_TRANSCRIPT", payload)
            if re.search(r"습니까|아닙니까|(?:뭐|무엇|뭘)\s*하겠|맞아야지", result.transcript):
                raise NormalizationContractError("RHETORICAL_TONE", payload)
            for item in result.edits:
                if item.original not in transcript:
                    raise NormalizationContractError("SOURCE_SPAN_MISSING", payload)
                if item.applied and item.replacement and item.replacement not in result.transcript:
                    raise NormalizationContractError("REPLACEMENT_SPAN_MISSING", payload)
                if not item.applied and item.original not in result.transcript:
                    raise NormalizationContractError("UNAPPLIED_SOURCE_MISSING", payload)
                if not item.applied and not item.requires_confirmation:
                    raise NormalizationContractError("UNAPPLIED_EDIT_NOT_FLAGGED", payload)
                if item.applied and not item.replacement and not item.requires_confirmation:
                    raise NormalizationContractError("DELETION_NOT_FLAGGED", payload)
            # Both existing UI lists come from the same validated entry; no model-authored duplicate spans.
            edit_log = [Edit(original=e.original, replacement=e.replacement, edit_type=e.edit_type, reason=e.reason) for e in result.edits if e.applied]
            confirmations = [Confirmation(original=e.original, replacement=e.replacement, reason=e.reason, applied=e.applied) for e in result.edits if e.requires_confirmation]
            duration_ms = round((time.monotonic() - started) * 1000, 1)
            logger.info("normalization_attempt_complete operation_id=%s attempt=%s trace_id=%s duration_ms=%s input_tokens=%s output_tokens=%s", operation_id, attempt, trace_id, duration_ms, usage_details.get("input"), usage_details.get("output"))
            if observation is not None:
                try:
                    observation.update(metadata={**metadata, "duration_ms": duration_ms, "output_characters": len(result.transcript), "confirmation_count": len(confirmations), "finish_reason": finish_reason}, usage_details=usage_details)
                except Exception:
                    pass
            return NormalizeResponse(transcript=result.transcript, edit_log=edit_log, confirmations=confirmations, meaning_preservation_check=result.meaning_preservation_check, prompt_name=PROMPT_NAME, prompt_version=PROMPT_VERSION, trace_id=trace_id)
        except Exception as error:
            status = getattr(error, "status_code", None)
            code = error.code if isinstance(error, NormalizationContractError) else ("INVALID_JSON_SCHEMA" if stage == "validation" and isinstance(error, ValueError) else "PROVIDER_ERROR" if stage == "provider" else "INTERNAL_ERROR")
            duration_ms = round((time.monotonic() - started) * 1000, 1)
            logger.warning("normalization_attempt_failed operation_id=%s attempt=%s trace_id=%s stage=%s failure_code=%s error_type=%s status=%s duration_ms=%s finish_reason=%s input_tokens=%s output_tokens=%s", operation_id, attempt, trace_id, stage, code, type(error).__name__, status, duration_ms, finish_reason, usage_details.get("input"), usage_details.get("output"))
            if observation is not None:
                try:
                    observation.update(level="ERROR", status_message=code, metadata={**metadata, "failure_stage": stage, "failure_code": code, "error_type": type(error).__name__, "provider_status": status, "duration_ms": duration_ms, "finish_reason": finish_reason}, usage_details=usage_details)
                except Exception:
                    pass
            raise
        finally:
            if observation is not None:
                try:
                    observation.end()
                except Exception:
                    pass


def install_transcript_normalization(app, require_authenticated_user):
    app.state.transcript_normalization = TranscriptNormalizationService(
        getattr(app.state.coaching_observation_sink, "client", None))

    @app.post("/analysis-jobs/{job_id}/normalize-transcript", response_model=NormalizeResponse)
    def normalize_transcript(job_id: UUID, payload: NormalizeRequest,
                             user: AuthenticatedUser = Depends(require_authenticated_user)):
        try:
            report_progress("전사문과 변환 요청을 확인하고 있어요…")
            jobs = app.state.analysis_jobs
            # This same authenticated get applies repository RLS and ownership checks.
            from app.services.persistent_analysis_jobs import PersistentAnalysisJobService
            if isinstance(jobs, PersistentAnalysisJobService):
                job = jobs.get(str(job_id), user)
            else:
                job = jobs.get(str(job_id), user_id=user.user_id).to_dict()
        except KeyError:
            raise HTTPException(404, "분석 작업을 찾을 수 없습니다.") from None
        except SupabasePersistenceError:
            raise HTTPException(503, "분석 작업을 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.") from None
        if job.get("status") != "completed":
            raise HTTPException(409, "전사가 완료된 답변만 변환할 수 있어요.")
        try:
            return app.state.transcript_normalization.normalize(payload.transcript)
        except Exception:
            raise HTTPException(503, "표준어로 바꾸지 못했어요. 원문은 유지됩니다. 잠시 후 다시 시도해 주세요.") from None
