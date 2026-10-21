from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.auth import (  # noqa: E402
    AuthConfigurationError,
    DevelopmentAccessTokenVerifier,
    build_access_token_verifier_from_env,
)
from app.services.coaching_observability import (  # noqa: E402
    CoachingGenerationObservation,
    CoachingObservation,
    CoachingValidationObservation,
    LangfuseCoachingObservationSink,
    activate_coaching_trace,
    observation_identity,
    reset_coaching_trace,
    set_active_coaching_identity,
)
from app.schemas.errors import FailureState  # noqa: E402


class FakeObservation:
    def __init__(self, client, payload) -> None:
        self.client = client
        self.payload = payload

    def end(self) -> None:
        self.client.ended.append(self.payload)

    def update(self, **kwargs) -> None:
        self.client.updated.append(kwargs)
        if self.client.raise_on_update:
            raise RuntimeError("Langfuse update unavailable")


class FakeLangfuse:
    def __init__(self) -> None:
        self.calls = []
        self.ended = []
        self.updated = []
        self.raise_on_update = False

    def start_observation(self, **kwargs):
        self.calls.append(kwargs)
        return FakeObservation(self, kwargs)


class CoachingObservabilityTest(unittest.TestCase):
    def test_active_trace_keeps_only_pseudonymous_identity(self):
        context, token = activate_coaching_trace("trace-identity")
        try:
            set_active_coaching_identity(
                user_key="hashed-user", session_key="hashed-session"
            )
            self.assertEqual(context.user_key, "hashed-user")
            self.assertEqual(context.session_key, "hashed-session")
        finally:
            reset_coaching_trace(token)

    def test_pseudonymizes_identity_only_with_configured_salt(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(observation_identity("user-1"))

        with patch.dict(
            os.environ,
            {"COACHING_OBSERVATION_SALT": "test-salt-at-least-16-characters"},
            clear=True,
        ):
            first = observation_identity("user-1")
            second = observation_identity("user-1")

        self.assertEqual(first, second)
        self.assertNotEqual(first, "user-1")
        self.assertEqual(len(first or ""), 24)

    def test_langfuse_metadata_contains_versions_metrics_and_no_content(self):
        client = FakeLangfuse()
        sink = LangfuseCoachingObservationSink(client)

        sink.record(
            CoachingObservation(
                user_key="hashed-user",
                session_key="hashed-session",
                model="mock-v1",
                prompt_version="prompt-v1",
                skill_version="skill-v1",
                status="needs_more_info",
                latency_ms=12.5,
                cost_usd=0.0,
                gap_count=2,
            )
        )

        call = client.calls[0]
        self.assertEqual(call["name"], "coaching.analyze")
        self.assertEqual(call["metadata"]["prompt_version"], "prompt-v1")
        self.assertEqual(call["metadata"]["skill_version"], "skill-v1")
        self.assertEqual(call["metadata"]["latency_ms"], 12.5)
        serialized = str(call).lower()
        for forbidden in ("access_token", "transcript", "source_url", "quote"):
            self.assertNotIn(forbidden, serialized)

    def test_failure_observation_is_recorded_as_error_without_content(self):
        client = FakeLangfuse()
        sink = LangfuseCoachingObservationSink(client)

        sink.record(
            CoachingObservation(
                trace_id="trace-failure",
                user_key="hashed-user",
                session_key="hashed-session",
                model="google/gemini-3.5-flash-lite",
                prompt_version="coaching-output-v4.1",
                skill_version="interview-coach-v5",
                status="failed",
                latency_ms=321.0,
                failure_state=FailureState.PROVIDER_ERROR,
            )
        )

        call = client.calls[-1]
        self.assertEqual(call["level"], "ERROR")
        self.assertEqual(call["metadata"]["failure_state"], "provider_error")
        self.assertEqual(call["output"]["status"], "failed")
        serialized = str(call).lower()
        for forbidden in ("transcript", "source_url", "quote", "access_token"):
            self.assertNotIn(forbidden, serialized)

    def test_records_redacted_generation_and_validation_under_same_trace(self):
        client = FakeLangfuse()
        managed_prompt = object()
        sink = LangfuseCoachingObservationSink(
            client, managed_prompt=managed_prompt
        )

        sink.record_generation(
            CoachingGenerationObservation(
                trace_id="trace-1",
                model="provider/model",
                prompt_version="prompt-v1",
                skill_version="skill-v1",
                contract_attempt=2,
                transport_attempt=1,
                repair_prompt=True,
                status_code=200,
                outcome="success",
                latency_ms=18.0,
                input_tokens=100,
                output_tokens=40,
                cost_usd=0.01,
                output_is_json_object=True,
            )
        )
        sink.record_validation(
            CoachingValidationObservation(
                trace_id="trace-1",
                prompt_version="prompt-v1",
                skill_version="skill-v1",
                contract_attempt=2,
                valid=True,
                error_count=0,
                latency_ms=1.5,
            )
        )

        generation = client.calls[0]
        validation = client.calls[1]
        self.assertEqual(generation["trace_context"]["trace_id"], "trace-1")
        self.assertEqual(validation["trace_context"]["trace_id"], "trace-1")
        self.assertEqual(generation["input"]["content_policy"], "redacted")
        self.assertEqual(generation["output"]["content_policy"], "redacted")
        self.assertEqual(generation["usage_details"], {"input": 100, "output": 40})
        self.assertEqual(generation["cost_details"], {"total": 0.01})
        self.assertIs(generation["prompt"], managed_prompt)
        self.assertTrue(validation["output"]["valid"])
        serialized = str({"generation": generation, "validation": validation})
        self.assertNotIn("실제 답변", serialized)
        self.assertNotIn("owner-token", serialized)
        self.assertEqual(len(client.ended), 2)

    def test_starts_generation_before_provider_result_and_updates_same_observation(self):
        client = FakeLangfuse()
        sink = LangfuseCoachingObservationSink(client)
        pending = CoachingGenerationObservation(
            trace_id="trace-duration",
            generation_id="generation-duration",
            model="provider/model",
            prompt_version="prompt-v1",
            skill_version="skill-v1",
            contract_attempt=1,
            transport_attempt=1,
            outcome="pending",
            latency_ms=0.0,
        )

        sink.start_generation(pending)
        sink.record_generation(
            pending.model_copy(
                update={
                    "outcome": "success",
                    "latency_ms": 2500.0,
                    "input_tokens": 100,
                    "output_tokens": 40,
                    "cost_usd": 0.01,
                    "output_is_json_object": True,
                }
            )
        )

        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["metadata"]["outcome"], "pending")
        self.assertEqual(len(client.updated), 1)
        self.assertEqual(client.updated[0]["metadata"]["outcome"], "success")
        self.assertEqual(client.updated[0]["usage_details"], {"input": 100, "output": 40})
        self.assertEqual(len(client.ended), 1)

    def test_ends_started_generation_when_update_fails(self):
        client = FakeLangfuse()
        client.raise_on_update = True
        sink = LangfuseCoachingObservationSink(client)
        observation = CoachingGenerationObservation(
            trace_id="trace-update-error",
            generation_id="generation-update-error",
            model="provider/model",
            prompt_version="prompt-v1",
            skill_version="skill-v1",
            contract_attempt=1,
            transport_attempt=1,
            outcome="pending",
            latency_ms=0.0,
        )

        sink.start_generation(observation)
        with self.assertRaisesRegex(RuntimeError, "update unavailable"):
            sink.record_generation(observation.model_copy(update={"outcome": "success"}))

        self.assertEqual(len(client.ended), 1)

    def test_e2e_verifier_requires_mock_mode_and_exact_token(self):
        environment = {
            "COACHING_E2E_ENABLED": "true",
            "COACHING_E2E_TOKEN": "compose-e2e-token",
            "COACHING_MOCK_ENABLED": "true",
        }
        with patch.dict(os.environ, environment, clear=True):
            verifier = build_access_token_verifier_from_env()

        self.assertIsInstance(verifier, DevelopmentAccessTokenVerifier)
        self.assertEqual(
            verifier.verify_access_token("compose-e2e-token"),
            "compose-e2e-user",
        )

        environment["COACHING_MOCK_ENABLED"] = "false"
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaises(AuthConfigurationError):
                build_access_token_verifier_from_env()


if __name__ == "__main__":
    unittest.main()
