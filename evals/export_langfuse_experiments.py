#!/usr/bin/env python3
"""Import existing model-comparison results into Langfuse Experiments without provider calls."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DATASET_NAME = "malhaebom-coaching-eval-v2"
DEFAULT_EXPERIMENT_NAME = "malhaebom-model-comparison"
DEFAULT_RUN_PREFIX = "malhaebom-comparison"


def load_report(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("comparison report must be a JSON object")
    attempts = report.get("attempts")
    if not isinstance(attempts, list) or not attempts:
        raise ValueError("comparison report has no attempts")
    return report


def final_attempt_groups(
    report: dict[str, Any],
    *,
    candidates: set[str] | None = None,
    runs: set[int] | None = None,
) -> dict[tuple[str, int], dict[str, dict[str, Any]]]:
    """Keep only the final call for each candidate/case/repeat execution."""

    final_by_execution: dict[str, dict[str, Any]] = {}
    for record in report["attempts"]:
        if not isinstance(record, dict):
            raise ValueError("attempt record must be an object")
        candidate = str(record.get("candidate", "")).strip()
        case_id = str(record.get("case_id", "")).strip()
        execution_id = str(record.get("execution_id", "")).strip()
        run = record.get("run")
        if not candidate or not case_id or not execution_id or type(run) is not int:
            raise ValueError("attempt record is missing candidate/case_id/execution_id/run")
        if candidates is not None and candidate not in candidates:
            continue
        if runs is not None and run not in runs:
            continue
        final_by_execution[execution_id] = record

    grouped: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for record in final_by_execution.values():
        key = (record["candidate"], record["run"])
        case_id = record["case_id"]
        if case_id in grouped[key]:
            raise ValueError(f"duplicate final case in {key}: {case_id}")
        grouped[key][case_id] = record
    if not grouped:
        raise ValueError("no attempts matched the requested candidate/run filters")
    return dict(grouped)


def _dataset_case_id(item: Any) -> str:
    metadata = getattr(item, "metadata", None)
    if metadata is None and isinstance(item, dict):
        metadata = item.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Langfuse dataset item is missing metadata")
    case_id = metadata.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise ValueError("Langfuse dataset item is missing metadata.case_id")
    if metadata.get("synthetic") is not True:
        raise ValueError(f"refusing non-synthetic Langfuse dataset item: {case_id}")
    return case_id


def select_dataset_items(dataset: Any, case_ids: set[str]) -> list[Any]:
    items = list(getattr(dataset, "items", []))
    by_case: dict[str, Any] = {}
    for item in items:
        case_id = _dataset_case_id(item)
        if case_id in by_case:
            raise ValueError(f"duplicate Langfuse dataset case_id: {case_id}")
        by_case[case_id] = item
    missing = sorted(case_ids - set(by_case))
    if missing:
        raise ValueError("Langfuse dataset is missing case IDs: " + ", ".join(missing))
    return [item for item in items if _dataset_case_id(item) in case_ids]


def _record_output(record: dict[str, Any]) -> Any:
    for key in ("validated_output", "parsed_output", "raw_output"):
        value = record.get(key)
        if value is not None:
            return value
    return {
        "contract_valid": bool(record.get("contract_valid")),
        "failure_state": record.get("failure_state"),
    }


def _metric_score(name: str, value: Any, record: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(value, bool):
        numeric = int(value)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric = value
    else:
        return None
    return {
        "name": name,
        "value": numeric,
        "comment": f"Imported from {record['attempt_id']} (no provider re-call)",
        "metadata": {
            "attempt_id": record["attempt_id"],
            "source": "model-comparison-report",
        },
    }


def scores_for_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    metrics = record.get("metrics") if isinstance(record.get("metrics"), dict) else {}
    ids = metrics.get("ids") if isinstance(metrics.get("ids"), dict) else {}
    semantic = (
        record.get("semantic_evaluation")
        if isinstance(record.get("semantic_evaluation"), dict)
        else {}
    )

    pairs: list[tuple[str, Any]] = [
        ("contract_valid", bool(record.get("contract_valid"))),
        ("rule_accuracy", record.get("accuracy")),
        ("label_accuracy", metrics.get("label_accuracy")),
        ("evidence_accuracy", metrics.get("evidence_accuracy")),
        ("id_reference_accuracy", ids.get("accuracy")),
        ("recorded_latency_ms", record.get("latency_ms")),
        ("recorded_cost_usd", record.get("cost_usd")),
    ]

    semantic_scores = semantic.get("scores")
    if isinstance(semantic_scores, dict):
        for name in ("reason", "action", "clarifying_question", "hallucination"):
            pairs.append((f"semantic_{name}", semantic_scores.get(name)))

    critical_failure = semantic.get("critical_failure")
    if isinstance(critical_failure, bool):
        pairs.append(("critical_failure", critical_failure))

    policy_checks = semantic.get("automatic_policy_checks")
    if isinstance(policy_checks, dict):
        for name in ("question_presence", "action_targets"):
            value = policy_checks.get(name)
            if isinstance(value, bool):
                pairs.append((f"policy_{name}", value))

    return [
        score
        for name, value in pairs
        if (score := _metric_score(name, value, record)) is not None
    ]


def _case_id_from_metadata(metadata: Any) -> str:
    if not isinstance(metadata, dict):
        raise ValueError("experiment item metadata must be an object")
    case_id = metadata.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise ValueError("experiment item metadata.case_id is required")
    return case_id


def make_task(records_by_case: dict[str, dict[str, Any]]):
    def task(*, item, **kwargs):
        del kwargs
        metadata = getattr(item, "metadata", None)
        if metadata is None and isinstance(item, dict):
            metadata = item.get("metadata")
        case_id = _case_id_from_metadata(metadata)
        return _record_output(records_by_case[case_id])

    return task


def make_evaluator(records_by_case: dict[str, dict[str, Any]]):
    def evaluator(*, metadata, **kwargs):
        del kwargs
        case_id = _case_id_from_metadata(metadata)
        return scores_for_record(records_by_case[case_id])

    return evaluator


def _slug(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z._-]+", "-", value).strip("-")
    return value or "candidate"


def build_run_name(
    report: dict[str, Any],
    candidate: str,
    run: int,
    *,
    run_prefix: str = DEFAULT_RUN_PREFIX,
) -> str:
    generated_at = str(report.get("generated_at", "unknown"))
    try:
        parsed = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        timestamp = parsed.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    except ValueError:
        timestamp = re.sub(r"[^0-9TZ]+", "", generated_at) or "unknown"
    return f"{_slug(run_prefix)}-{_slug(candidate)}-r{run}-{timestamp}"


def _run_exists(client: Any, dataset_name: str, run_name: str) -> bool:
    get_run = getattr(client, "get_dataset_run", None)
    if not callable(get_run):
        return False
    try:
        get_run(dataset_name=dataset_name, run_name=run_name)
    except Exception as error:
        if getattr(error, "status_code", None) == 404:
            return False
        raise
    return True


def _experiment_metadata(
    report: dict[str, Any],
    candidate: str,
    run: int,
    records_by_case: dict[str, dict[str, Any]],
) -> dict[str, str]:
    versions = report.get("versions") if isinstance(report.get("versions"), dict) else {}
    configuration = (
        report.get("configuration")
        if isinstance(report.get("configuration"), dict)
        else {}
    )
    configs = report.get("model_configs") if isinstance(report.get("model_configs"), list) else []
    model = next(
        (
            str(item.get("model"))
            for item in configs
            if isinstance(item, dict) and item.get("label") == candidate
        ),
        candidate,
    )
    records = list(records_by_case.values())
    latencies = sorted(
        float(item["latency_ms"])
        for item in records
        if isinstance(item.get("latency_ms"), (int, float))
    )
    known_costs = [
        float(item["cost_usd"])
        for item in records
        if isinstance(item.get("cost_usd"), (int, float))
    ]
    contract_rate = (
        sum(bool(item.get("contract_valid")) for item in records) / len(records)
        if records
        else None
    )

    def percentile(values: list[float], quantile: float) -> float | None:
        if not values:
            return None
        return values[max(0, math.ceil(len(values) * quantile) - 1)]

    values = {
        "source": "model-comparison-report",
        "provider_recalled": "false",
        "candidate": candidate,
        "model": model,
        "repeat": str(run),
        "prompt_version": configuration.get("prompt_version"),
        "prompt_sha256": configuration.get("prompt_sha256"),
        "skill_version": configuration.get("skill_version"),
        "criteria_version": configuration.get("criteria_version"),
        "dataset_version": versions.get("dataset_version"),
        "dataset_sha256": versions.get("dataset_sha256"),
        "grader_version": versions.get("grader"),
        "policy_version": versions.get("policy"),
        "recorded_contract_rate": contract_rate,
        "recorded_p50_ms": percentile(latencies, 0.50),
        "recorded_p95_ms": percentile(latencies, 0.95),
        "recorded_known_cost_usd": sum(known_costs),
        "recorded_unknown_cost_calls": sum(
            item.get("cost_usd") is None for item in records
        ),
    }
    return {
        key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
        for key, value in values.items()
        if value is not None
    }


def export_report(
    client: Any,
    report: dict[str, Any],
    *,
    dataset_name: str = DEFAULT_DATASET_NAME,
    experiment_name: str = DEFAULT_EXPERIMENT_NAME,
    run_prefix: str = DEFAULT_RUN_PREFIX,
    candidates: set[str] | None = None,
    runs: set[int] | None = None,
) -> list[dict[str, Any]]:
    groups = final_attempt_groups(report, candidates=candidates, runs=runs)
    run_experiment = getattr(client, "run_experiment", None)
    if not callable(run_experiment):
        raise RuntimeError(
            "Langfuse Python SDK v4 experiment runner가 필요합니다. "
            "backend/requirements.txt의 langfuse>=4.7,<5 환경을 사용하세요."
        )
    dataset = client.get_dataset(dataset_name, fetch_items_page_size=100)
    results: list[dict[str, Any]] = []

    for (candidate, run), records_by_case in sorted(groups.items()):
        run_name = build_run_name(report, candidate, run, run_prefix=run_prefix)
        if _run_exists(client, dataset_name, run_name):
            results.append(
                {
                    "candidate": candidate,
                    "run": run,
                    "run_name": run_name,
                    "status": "existing",
                }
            )
            continue

        selected_items = select_dataset_items(dataset, set(records_by_case))
        result = run_experiment(
            name=experiment_name,
            run_name=run_name,
            description=(
                "Imported from an existing 말해봄 model-comparison report. "
                "This experiment does not call the model provider again; latency/cost "
                "scores are the recorded values from the original evaluation."
            ),
            data=selected_items,
            task=make_task(records_by_case),
            evaluators=[make_evaluator(records_by_case)],
            max_concurrency=1,
            metadata=_experiment_metadata(report, candidate, run, records_by_case),
        )
        results.append(
            {
                "candidate": candidate,
                "run": run,
                "run_name": run_name,
                "status": "created",
                "items": len(selected_items),
                "dataset_run_id": getattr(result, "dataset_run_id", None),
                "dataset_run_url": getattr(result, "dataset_run_url", None),
            }
        )

    flush = getattr(client, "flush", None)
    if callable(flush):
        flush()
    return results


def build_plan(
    report: dict[str, Any],
    *,
    run_prefix: str,
    candidates: set[str] | None,
    runs: set[int] | None,
) -> list[dict[str, Any]]:
    groups = final_attempt_groups(report, candidates=candidates, runs=runs)
    return [
        {
            "candidate": candidate,
            "run": run,
            "cases": len(records),
            "run_name": build_run_name(report, candidate, run, run_prefix=run_prefix),
        }
        for (candidate, run), records in sorted(groups.items())
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--dataset-name", default=DEFAULT_DATASET_NAME)
    parser.add_argument("--experiment-name", default=DEFAULT_EXPERIMENT_NAME)
    parser.add_argument("--run-prefix", default=DEFAULT_RUN_PREFIX)
    parser.add_argument("--candidate", action="append")
    parser.add_argument("--run", action="append", type=int)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    report = load_report(args.report)
    candidates = set(args.candidate) if args.candidate else None
    runs = set(args.run) if args.run else None
    plan = build_plan(
        report,
        run_prefix=args.run_prefix,
        candidates=candidates,
        runs=runs,
    )
    if not args.apply:
        print(
            json.dumps(
                {
                    "mode": "dry-run",
                    "dataset_name": args.dataset_name,
                    "experiment_name": args.experiment_name,
                    "runs": plan,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    from evals.environment import load_evaluation_env
    from evals.sync_langfuse_assets import create_client_from_env

    load_evaluation_env()
    client = create_client_from_env()
    try:
        auth_check = getattr(client, "auth_check", None)
        if callable(auth_check) and not auth_check():
            raise RuntimeError("Langfuse 인증에 실패했습니다.")
        results = export_report(
            client,
            report,
            dataset_name=args.dataset_name,
            experiment_name=args.experiment_name,
            run_prefix=args.run_prefix,
            candidates=candidates,
            runs=runs,
        )
        print(
            json.dumps(
                {
                    "mode": "apply",
                    "dataset_name": args.dataset_name,
                    "experiment_name": args.experiment_name,
                    "runs": results,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    finally:
        shutdown = getattr(client, "shutdown", None)
        if callable(shutdown):
            shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
