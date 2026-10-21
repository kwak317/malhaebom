#!/usr/bin/env python3
"""Discover diverse OpenRouter models, preflight them, then evaluate PASS models."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for entry in (ROOT, BACKEND):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from app.services.coaching_skill import load_skill_bundle  # noqa: E402
from evals.coaching_dataset import load_dataset  # noqa: E402
from evals.environment import load_evaluation_env, resolve_provider_credentials  # noqa: E402
from evals.evaluation_records import (  # noqa: E402
    GRADER_VERSION,
    POLICY_VERSION,
    REQUEST_SETTINGS,
)
from evals.run_model_comparison import (  # noqa: E402
    CandidateConfig,
    OpenAICompatibleRunner,
    build_system_prompt,
    run_comparison,
)


TARGET_DEVELOPERS = (
    "openai", "anthropic", "google", "meta-llama", "qwen", "deepseek",
    "mistralai", "cohere", "x-ai", "microsoft", "nvidia",
)
DEVELOPER_ALIASES = {
    "meta": "meta-llama", "meta-llama": "meta-llama", "mistral": "mistralai",
    "mistralai": "mistralai", "xai": "x-ai", "x-ai": "x-ai",
}
ROUTER_SUFFIXES = (":free", ":nitro", ":extended", ":thinking", ":online")
PREFLIGHT_CASE_NUMBERS = (1, 16, 23)
RETRYABLE = {"TIMEOUT", "RATE_LIMITED", "API_ERROR"}


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def safe_http_json(url: str, key: str, timeout: float = 30) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Do not persist response bodies: providers may echo request context.
        raise RuntimeError(f"model discovery HTTP {error.code}") from None


def discover_models(base_url: str, key: str) -> tuple[list[dict[str, Any]], str]:
    errors = []
    for suffix in ("/models/user", "/models"):
        try:
            payload = safe_http_json(base_url.rstrip("/") + suffix, key)
            data = payload.get("data")
            if isinstance(data, list):
                return data, suffix
            errors.append(f"{suffix}: invalid response")
        except RuntimeError as error:
            errors.append(str(error))
    raise RuntimeError("; ".join(errors))


def developer_for(model_id: str) -> str:
    raw = model_id.split("/", 1)[0].lower().lstrip("~")
    return DEVELOPER_ALIASES.get(raw, raw)


def per_million(raw: Any) -> float | None:
    try:
        return float(raw) * 1_000_000
    except (TypeError, ValueError):
        return None


def sanitize_model(model: dict[str, Any]) -> dict[str, Any]:
    architecture = model.get("architecture") or {}
    pricing = model.get("pricing") or {}
    model_id = str(model.get("id") or "")
    return {
        "model_id": model_id,
        "canonical_slug": model.get("canonical_slug"),
        "name": model.get("name"),
        "developer": developer_for(model_id),
        "created": model.get("created"),
        "expiration_date": model.get("expiration_date"),
        "context_length": model.get("context_length"),
        "input_modalities": architecture.get("input_modalities") or [],
        "output_modalities": architecture.get("output_modalities") or [],
        "modality": architecture.get("modality"),
        "supported_parameters": model.get("supported_parameters") or [],
        "input_usd_per_million": per_million(pricing.get("prompt")),
        "output_usd_per_million": per_million(pricing.get("completion")),
        "request_usd": float(pricing.get("request") or 0),
    }


def exclusion_reason(model: dict[str, Any]) -> str | None:
    model_id = model["model_id"]
    if not model_id or "/" not in model_id:
        return "INVALID_MODEL_ID"
    if "text" not in model["input_modalities"] or model["output_modalities"] != ["text"]:
        return "NON_TEXT_CHAT_MODEL"
    if "response_format" not in model["supported_parameters"]:
        return "NO_STRUCTURED_OUTPUT"
    if model_id.endswith(ROUTER_SUFFIXES) or model_id.endswith(":batch") or model_id.startswith("openrouter/"):
        return "ALIAS_OR_ROUTER"
    if "safeguard" in model_id or model_id.endswith("/relace-search"):
        return "SPECIALIZED_NON_CHAT"
    return None


def select_candidates(
    eligible: list[dict[str, Any]], *, max_models: int, per_developer: int,
    max_output_price: float,
) -> list[dict[str, Any]]:
    affordable = [
        model for model in eligible
        if model["output_usd_per_million"] is not None
        and model["output_usd_per_million"] <= max_output_price
    ]
    by_developer: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for model in affordable:
        by_developer[model["developer"]].append(model)
    for models in by_developer.values():
        models.sort(key=lambda item: (
            -(item.get("created") or 0),
            item["output_usd_per_million"], item["model_id"],
        ))

    selected: list[dict[str, Any]] = []
    ordered_developers = [*TARGET_DEVELOPERS]
    ordered_developers.extend(sorted(set(by_developer) - set(ordered_developers)))
    # Round-robin maximizes developer diversity before adding second variants.
    for rank in range(per_developer):
        for developer in ordered_developers:
            choices = by_developer.get(developer, [])
            if rank < len(choices) and len(selected) < max_models:
                selected.append(choices[rank])
    return selected


def failure_classification(record: dict[str, Any]) -> tuple[str, str | None]:
    if record.get("contract_valid"):
        return "PASS", None
    state = record.get("failure_state")
    status = record.get("http_status")
    if state in {"schema_violation", "validator_violation"}:
        return "CONTRACT_VIOLATION", state
    if state == "timeout" or status == 408:
        return "TIMEOUT", "timeout"
    if state == "rate_limited" or status == 429:
        return "RATE_LIMITED", "rate_limited"
    if status in {401, 402, 403}:
        return "POLICY_RESTRICTED", f"HTTP_{status}"
    if status == 404:
        return "MODEL_UNAVAILABLE", "HTTP_404"
    return "API_ERROR", f"HTTP_{status}" if status else (state or "provider_error")


class RecordedRunner(OpenAICompatibleRunner):
    def generate(self, case):
        try:
            return super().generate(case)
        except Exception as error:
            self.last_record["http_status"] = getattr(error, "status_code", None)
            self.last_record["error_type"] = type(error).__name__
            raise


def run_one(
    model: dict[str, Any], case, *, key: str, base_url: str, prompt: str,
    configuration: dict[str, str], timeout: float,
) -> dict[str, Any]:
    config = CandidateConfig(model["model_id"], "openai", model["model_id"])
    runner = RecordedRunner(
        config, system_prompt=prompt, api_key=key, base_url=base_url,
        timeout_seconds=timeout,
    )
    try:
        report = run_comparison([case], [(config, runner)], configuration=configuration)
        record = report["attempts"][0]
    finally:
        runner.client.close()
    classification, reason = failure_classification(record)
    record["classification"] = classification
    record["safe_failure_reason"] = reason
    record["developer"] = model["developer"]
    return record


def run_with_retry(path: Path, model: dict[str, Any], case, args, runtime) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    attempts = []
    for retry in range(args.retries + 1):
        record = run_one(model, case, **runtime)
        record["retry_index"] = retry
        attempts.append(record)
        if record["classification"] not in RETRYABLE or retry == args.retries:
            break
        time.sleep(args.backoff_seconds * (2 ** retry))
    result = {"model": model, "case_id": case.id, "calls": attempts, "final": attempts[-1]}
    atomic_json(path, result)
    return result


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    return values[max(0, math.ceil(len(values) * quantile) - 1)]


def summarize_model(model: dict[str, Any], preflight: list[dict[str, Any]], full: list[dict[str, Any]]) -> dict[str, Any]:
    preflight_final = [item["final"] for item in preflight]
    preflight_statuses = [item["classification"] for item in preflight_final]
    preflight_result = "PASS" if preflight_statuses and set(preflight_statuses) == {"PASS"} else next(
        (status for status in preflight_statuses if status != "PASS"), "NOT_RUN"
    )
    all_calls = [call for item in [*preflight, *full] for call in item["calls"]]
    full_final = [item["final"] for item in full]
    failures = Counter(item["classification"] for item in full_final if item["classification"] != "PASS")
    providers = sorted({str(item.get("provider")) for item in [*preflight_final, *full_final] if item.get("provider")})
    semantic_values = [item.get("semantic_evaluation") for item in full_final]
    semantic_reviewed = sum(bool(value and value.get("human_review")) for value in semantic_values)
    return {
        "model_id": model["model_id"], "developer": model["developer"],
        "providers": providers, "preflight_result": preflight_result,
        "preflight_cases": len(preflight_final), "full_evaluation_performed": bool(full),
        "success_count": sum(item["classification"] == "PASS" for item in full_final),
        "total_count": len(full_final),
        "contract_violation_count": failures.get("CONTRACT_VIOLATION", 0),
        "semantic_reviewed": semantic_reviewed,
        "semantic_result": None,
        "latency_p50_ms": percentile([item["latency_ms"] for item in full_final], .5),
        "latency_p95_ms": percentile([item["latency_ms"] for item in full_final], .95),
        "input_tokens": sum((item.get("input_tokens") or 0) for item in all_calls),
        "output_tokens": sum((item.get("output_tokens") or 0) for item in all_calls),
        "known_cost_usd": sum((item.get("cost_usd") or 0) for item in all_calls),
        "unknown_cost_calls": sum(item.get("cost_usd") is None for item in all_calls),
        "failure_counts": dict(sorted(failures.items())),
        "failure_reasons": sorted({item.get("safe_failure_reason") for item in [*preflight_final, *full_final]
                                   if item.get("safe_failure_reason")}),
    }


def write_reports(output: Path, discovery: dict[str, Any], summaries: list[dict[str, Any]]) -> None:
    total_cost = sum(item["known_cost_usd"] for item in summaries)
    result = {
        "generated_at": datetime.now(UTC).isoformat(),
        "discovered_count": discovery["discovered_count"],
        "eligible_count": discovery["eligible_count"],
        "selected_count": len(summaries),
        "preflight_pass_count": sum(item["preflight_result"] == "PASS" for item in summaries),
        "full_completed_count": sum(item["total_count"] == 30 for item in summaries),
        "known_cost_usd": total_cost,
        "unknown_cost_calls": sum(item["unknown_cost_calls"] for item in summaries),
        "developer_distribution": dict(sorted(Counter(item["developer"] for item in summaries).items())),
        "models": summaries,
    }
    atomic_json(output / "summary.json", result)
    fields = list(summaries[0]) if summaries else []
    with (output / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in summaries:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                             for key, value in item.items()})
    lines = [
        "# OpenRouter 모델 다양성 평가", "",
        f"- 발견: {result['discovered_count']}개; eligible: {result['eligible_count']}개; 선택: {result['selected_count']}개",
        f"- Preflight PASS: {result['preflight_pass_count']}개; 30건 완료: {result['full_completed_count']}개",
        f"- 알려진 비용: ${total_cost:.6f}; 비용 미확인 호출: {result['unknown_cost_calls']}개", "",
        "| Developer | Model | Preflight | Full | Success | Contract violations | p50 ms | p95 ms | Tokens in/out | Cost USD | Failure |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in summaries:
        lines.append(
            f"| {item['developer']} | `{item['model_id']}` | {item['preflight_result']} | {item['total_count']} | "
            f"{item['success_count']} | {item['contract_violation_count']} | {item['latency_p50_ms'] or ''} | "
            f"{item['latency_p95_ms'] or ''} | {item['input_tokens']}/{item['output_tokens']} | "
            f"{item['known_cost_usd']:.6f} | {', '.join(item['failure_reasons'])} |"
        )
    (output / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
