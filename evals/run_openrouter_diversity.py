#!/usr/bin/env python3
"""Run OpenRouter diversity discovery, preflight, and full evaluation."""

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for entry in (ROOT, BACKEND):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from app.services.coaching_skill import load_skill_bundle
from evals.coaching_dataset import load_dataset
from evals.environment import load_evaluation_env, resolve_provider_credentials
from evals.evaluation_records import GRADER_VERSION, POLICY_VERSION, REQUEST_SETTINGS
from evals.openrouter_diversity import (
    PREFLIGHT_CASE_NUMBERS,
    atomic_json,
    discover_models,
    exclusion_reason,
    run_with_retry,
    sanitize_model,
    select_candidates,
    summarize_model,
    write_reports,
)
from evals.run_model_comparison import build_system_prompt

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "local-results" /
                        f"openrouter-diversity-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}")
    parser.add_argument("--stage", choices=("discover", "preflight", "full", "all"), default="discover")
    parser.add_argument("--max-models", type=int, default=30)
    parser.add_argument("--per-developer", type=int, default=2)
    parser.add_argument("--max-output-price", type=float, default=20.0,
                        help="USD per million output tokens")
    parser.add_argument("--model", action="append", default=[])
    parser.add_argument("--timeout-seconds", type=float, default=60)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--backoff-seconds", type=float, default=2)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--prompt-version", default="coaching-output-v3")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_evaluation_env()
    key, base_url = resolve_provider_credentials(require_openrouter=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    discovery_path = args.output_dir / "discovery.json"
    if discovery_path.exists():
        discovery = json.loads(discovery_path.read_text(encoding="utf-8"))
    else:
        raw_models, endpoint = discover_models(base_url, key)
        safe_models = [sanitize_model(item) for item in raw_models]
        eligible, excluded = [], []
        for model in safe_models:
            reason = exclusion_reason(model)
            (excluded if reason else eligible).append({**model, **({"exclusion_reason": reason} if reason else {})})
        selected = select_candidates(
            eligible, max_models=args.max_models, per_developer=args.per_developer,
            max_output_price=args.max_output_price,
        )
        selected_ids = {item["model_id"] for item in selected}
        for model_id in args.model:
            match = next((item for item in eligible if item["model_id"] == model_id), None)
            if match and model_id not in selected_ids:
                selected.append(match); selected_ids.add(model_id)
        discovery = {
            "discovered_at": datetime.now(UTC).isoformat(), "endpoint": endpoint,
            "discovered_count": len(safe_models), "eligible_count": len(eligible),
            "selection_policy": {"max_models": args.max_models, "per_developer": args.per_developer,
                                 "max_output_price_usd_per_million": args.max_output_price},
            "selected": selected, "eligible": eligible, "excluded": excluded,
        }
        atomic_json(discovery_path, discovery)
    if args.stage == "discover":
        print(json.dumps({"output": str(discovery_path), "discovered": discovery["discovered_count"],
                          "eligible": discovery["eligible_count"], "selected": len(discovery["selected"])}, ensure_ascii=False))
        return 0

    cases = load_dataset(ROOT / "evals" / "dataset.v2.jsonl")
    bundle = load_skill_bundle()
    prompt = build_system_prompt(bundle.rules_text, args.prompt_version, bundle.catalog.skill_version)
    configuration = {"prompt_version": args.prompt_version, "skill_version": bundle.catalog.skill_version,
                     "criteria_version": bundle.catalog.criteria_version, "skill_bundle_sha256": bundle.sha256}
    runtime = {"key": key, "base_url": base_url, "prompt": prompt, "configuration": configuration,
               "timeout": args.timeout_seconds}
    manifest_path = args.output_dir / "manifest.json"
    if not manifest_path.exists():
        atomic_json(manifest_path, {"created_at": datetime.now(UTC).isoformat(), "models": [m["model_id"] for m in discovery["selected"]],
                    "preflight_cases": list(PREFLIGHT_CASE_NUMBERS), "dataset_cases": len(cases),
                    "request_settings": REQUEST_SETTINGS, "prompt": configuration,
                    "grader": GRADER_VERSION, "policy": POLICY_VERSION, "sdk_retries": 0,
                    "orchestration_retries": args.retries, "backoff_seconds": args.backoff_seconds,
                    "timeout_seconds": args.timeout_seconds, "concurrency": args.concurrency})
    selected_cases = [case for case in cases if int(case.id.rsplit("-", 1)[-1]) in PREFLIGHT_CASE_NUMBERS]
    if args.concurrency < 1:
        raise ValueError("concurrency must be positive")

    def execute_jobs(models, selected_cases, directory):
        jobs = {}
        results = defaultdict(list)
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            # Interleave developers so one slow/rate-limited provider cannot occupy the queue head.
            for case in selected_cases:
                for model in models:
                    slug = model["model_id"].replace("/", "__").replace(":", "_")
                    path = args.output_dir / directory / slug / f"{case.id}.json"
                    future = pool.submit(run_with_retry, path, model, case, args, runtime)
                    jobs[future] = (model["model_id"], case.id)
            for future in as_completed(jobs):
                model_id, _ = jobs[future]
                results[model_id].append(future.result())
        for model_results in results.values():
            model_results.sort(key=lambda item: item["case_id"])
        return results

    selected_models = discovery["selected"]
    preflight_by_model = execute_jobs(selected_models, selected_cases, "preflight")
    passed_models = [model for model in selected_models if all(
        item["final"]["classification"] == "PASS"
        for item in preflight_by_model[model["model_id"]]
    )]
    full_by_model = {}
    if args.stage in {"full", "all"}:
        full_by_model = execute_jobs(passed_models, cases, "full")

    summaries = []
    for model in selected_models:
        preflight = preflight_by_model[model["model_id"]]
        full = full_by_model.get(model["model_id"], [])
        summaries.append(summarize_model(model, preflight, full))
        write_reports(args.output_dir, discovery, summaries)
        print(json.dumps({"model": model["model_id"], "preflight": summaries[-1]["preflight_result"],
                          "full": len(full), "cost": summaries[-1]["known_cost_usd"]}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
