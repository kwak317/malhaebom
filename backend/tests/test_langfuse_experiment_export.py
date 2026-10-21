from __future__ import annotations

import sys
import unittest
from inspect import signature
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.export_langfuse_experiments import (
    build_plan,
    export_report,
    final_attempt_groups,
    scores_for_record,
    select_dataset_items,
)


def record(
    *,
    candidate="flash-lite",
    case_id="coach-normal-01",
    run=1,
    call=1,
    contract_valid=True,
):
    execution_id = f"{candidate}:{case_id}:{run}"
    return {
        "candidate": candidate,
        "case_id": case_id,
        "category": "normal",
        "run": run,
        "execution_id": execution_id,
        "attempt_id": f"{execution_id}:{call}",
        "call": call,
        "model": "google/gemini-3.5-flash-lite",
        "contract_valid": contract_valid,
        "accuracy": 0.8 if contract_valid else 0.0,
        "latency_ms": 1234.5,
        "cost_usd": 0.0012,
        "failure_state": None if contract_valid else "schema_violation",
        "validated_output": {"status": "ok"} if contract_valid else None,
        "parsed_output": {"broken": True},
        "raw_output": "{broken",
        "metrics": {
            "label_accuracy": 0.75 if contract_valid else None,
            "evidence_accuracy": 1.0 if contract_valid else None,
            "ids": {"accuracy": 1.0},
        },
        "semantic_evaluation": {
            "scores": {
                "reason": 2,
                "action": 1,
                "clarifying_question": None,
                "hallucination": 2,
            },
            "critical_failure": False,
            "automatic_policy_checks": {
                "question_presence": True,
                "action_targets": False,
            },
        },
    }


def report(attempts):
    return {
        "generated_at": "2026-09-22T12:34:56+00:00",
        "versions": {
            "dataset_version": ["v2"],
            "dataset_sha256": "dataset-hash",
            "grader": "grader-v1",
            "policy": "policy-v1",
        },
        "configuration": {
            "prompt_version": "coaching-output-v4.1",
            "prompt_sha256": "prompt-hash",
            "skill_version": "interview-coach-v4",
            "criteria_version": "problem-solving-v4-draft.3",
        },
        "model_configs": [
            {
                "label": "flash-lite",
                "model": "google/gemini-3.5-flash-lite",
            }
        ],
        "candidates": {
            "flash-lite": {
                "final_contract_rate": 1.0,
                "p50_ms": 1200.0,
                "p95_ms": 1800.0,
                "cost_usd": 0.01,
            }
        },
        "attempts": attempts,
    }


class FakeItem:
    def __init__(self, case_id, *, synthetic=True):
        self.metadata = {"case_id": case_id, "synthetic": synthetic}
        self.input = {"case_id": case_id}
        self.expected_output = {"status": "ok"}


class FakeNotFound(Exception):
    status_code = 404


class FakeClient:
    def __init__(self, items):
        self.dataset = SimpleNamespace(items=items)
        self.calls = []
        self.existing = set()
        self.flushed = False

    def get_dataset(self, name, fetch_items_page_size=100):
        self.dataset_name = name
        self.fetch_items_page_size = fetch_items_page_size
        return self.dataset

    def get_dataset_run(self, *, dataset_name, run_name):
        if run_name not in self.existing:
            raise FakeNotFound()
        return object()

    def run_experiment(self, **kwargs):
        item_results = []
        for item in kwargs["data"]:
            output = kwargs["task"](item=item)
            evaluations = kwargs["evaluators"][0](
                input=item.input,
                output=output,
                expected_output=item.expected_output,
                metadata=item.metadata,
            )
            item_results.append((item.metadata["case_id"], output, evaluations))
        self.calls.append((kwargs, item_results))
        return SimpleNamespace(
            dataset_run_id="dataset-run-1",
            dataset_run_url="https://langfuse.test/run/1",
        )

    def flush(self):
        self.flushed = True


class LangfuseExperimentExportTest(unittest.TestCase):
    def test_final_attempt_groups_keeps_last_retry_per_execution(self):
        first = record(call=1, contract_valid=False)
        second = record(call=2, contract_valid=True)
        groups = final_attempt_groups(report([first, second]))

        final = groups[("flash-lite", 1)]["coach-normal-01"]
        self.assertEqual(final["attempt_id"], "flash-lite:coach-normal-01:1:2")
        self.assertTrue(final["contract_valid"])

    def test_scores_include_quality_semantic_latency_and_cost(self):
        scores = {item["name"]: item["value"] for item in scores_for_record(record())}

        self.assertEqual(scores["contract_valid"], 1)
        self.assertEqual(scores["label_accuracy"], 0.75)
        self.assertEqual(scores["evidence_accuracy"], 1.0)
        self.assertEqual(scores["id_reference_accuracy"], 1.0)
        self.assertEqual(scores["semantic_reason"], 2)
        self.assertEqual(scores["critical_failure"], 0)
        self.assertEqual(scores["policy_question_presence"], 1)
        self.assertEqual(scores["policy_action_targets"], 0)
        self.assertEqual(scores["recorded_latency_ms"], 1234.5)
        self.assertEqual(scores["recorded_cost_usd"], 0.0012)

    def test_dataset_selection_rejects_non_synthetic_items(self):
        dataset = SimpleNamespace(
            items=[
                FakeItem("coach-normal-01"),
                FakeItem("coach-normal-02", synthetic=False),
            ]
        )
        with self.assertRaisesRegex(ValueError, "non-synthetic"):
            select_dataset_items(dataset, {"coach-normal-01"})

    def test_export_creates_dataset_linked_experiment_without_provider_call(self):
        attempts = [
            record(case_id="coach-normal-01"),
            record(case_id="coach-normal-02"),
        ]
        client = FakeClient(
            [FakeItem("coach-normal-01"), FakeItem("coach-normal-02")]
        )

        results = export_report(client, report(attempts))

        self.assertEqual(results[0]["status"], "created")
        self.assertEqual(results[0]["items"], 2)
        self.assertTrue(client.flushed)
        kwargs, item_results = client.calls[0]
        self.assertEqual(kwargs["name"], "malhaebom-model-comparison")
        self.assertEqual(kwargs["max_concurrency"], 1)
        self.assertEqual(kwargs["metadata"]["provider_recalled"], "false")
        self.assertEqual(kwargs["metadata"]["prompt_version"], "coaching-output-v4.1")
        self.assertEqual(kwargs["metadata"]["recorded_p50_ms"], "1234.5")
        self.assertEqual(kwargs["metadata"]["recorded_known_cost_usd"], "0.0024")
        self.assertEqual(item_results[0][1], {"status": "ok"})
        self.assertTrue(
            any(score["name"] == "contract_valid" for score in item_results[0][2])
        )

    def test_existing_deterministic_run_is_skipped(self):
        attempts = [record()]
        client = FakeClient([FakeItem("coach-normal-01")])
        plan = build_plan(
            report(attempts),
            run_prefix="malhaebom-comparison",
            candidates=None,
            runs=None,
        )
        self.assertEqual(
            plan[0]["run_name"],
            "malhaebom-comparison-flash-lite-r1-20260922T123456Z",
        )
        client.existing.add(plan[0]["run_name"])

        results = export_report(client, report(attempts))

        self.assertEqual(results[0]["status"], "existing")
        self.assertEqual(client.calls, [])

    def test_legacy_langfuse_client_fails_with_upgrade_message(self):
        legacy = SimpleNamespace(get_dataset=lambda *args, **kwargs: None)
        with self.assertRaisesRegex(RuntimeError, "langfuse>=4.7,<5"):
            export_report(legacy, report([record()]))

    def test_installed_langfuse_sdk_exposes_experiment_runner_contract(self):
        try:
            installed = version("langfuse")
            from langfuse import Langfuse
        except (ImportError, PackageNotFoundError):
            self.skipTest("Langfuse SDK is not installed in this Python runtime")
        if int(installed.split(".", 1)[0]) < 4:
            self.skipTest(f"stale local Langfuse SDK: {installed}")

        parameters = signature(Langfuse.run_experiment).parameters
        for name in (
            "name",
            "run_name",
            "description",
            "data",
            "task",
            "evaluators",
            "max_concurrency",
            "metadata",
        ):
            self.assertIn(name, parameters)


if __name__ == "__main__":
    unittest.main()
