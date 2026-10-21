#!/usr/bin/env python3
"""Run the fixed four-model comparison; network calls require --live."""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for entry in (ROOT, BACKEND):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from app.services.coaching_skill import load_skill_bundle  # noqa: E402
from evals.coaching_dataset import load_dataset  # noqa: E402
from evals.environment import load_evaluation_env, resolve_provider_credentials  # noqa: E402
from evals.evaluation_records import GRADER_VERSION, POLICY_VERSION, REQUEST_SETTINGS  # noqa: E402
from evals.openrouter_diversity import atomic_json, run_with_retry, summarize_model, write_reports  # noqa: E402
from evals.run_model_comparison import build_system_prompt  # noqa: E402

MODEL_IDS = (
    "google/gemini-3.5-flash-lite",
    "google/gemini-3.8-flash",
    "openai/gpt-5.6-luna",
    "openai/gpt-5.6-terra",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="실제 API 호출 허용")
    parser.add_argument("--catalog", type=Path, required=True,
                        help="diversity discovery.json (eligible metadata 포함)")
    parser.add_argument("--dataset", type=Path, default=ROOT / "evals/dataset.v2.jsonl")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=60)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--backoff-seconds", type=float, default=2)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--prompt-version", default="coaching-output-v3")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.live:
        print(json.dumps({"models": MODEL_IDS, "planned_unique_calls": 120,
                          "network_calls": False}, ensure_ascii=False))
        return 0
    if args.concurrency < 1 or args.retries < 0:
        raise ValueError("concurrency는 1 이상, retries는 0 이상이어야 합니다")
    load_evaluation_env()
    key, base_url = resolve_provider_credentials(require_openrouter=True)
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    by_id = {item["model_id"]: item for item in catalog["eligible"]}
    missing = sorted(set(MODEL_IDS) - set(by_id))
    if missing:
        raise ValueError("catalog에 없는 모델: " + ", ".join(missing))
    models = [by_id[model_id] for model_id in MODEL_IDS]
    cases = load_dataset(args.dataset)
    if len(cases) != 30:
        raise ValueError("Final Four는 고정 30건 dataset만 허용합니다")
    bundle = load_skill_bundle()
    prompt = build_system_prompt(bundle.rules_text, args.prompt_version, bundle.catalog.skill_version)
    configuration = {"prompt_version": args.prompt_version,
                     "skill_version": bundle.catalog.skill_version,
                     "criteria_version": bundle.catalog.criteria_version,
                     "skill_bundle_sha256": bundle.sha256}
    runtime = {"key": key, "base_url": base_url, "prompt": prompt,
               "configuration": configuration, "timeout": args.timeout_seconds}
    retry_args = SimpleNamespace(retries=args.retries, backoff_seconds=args.backoff_seconds)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(args.output_dir / "manifest.json", {
        "created_at": datetime.now(UTC).isoformat(), "models": list(MODEL_IDS),
        "cases": [case.id for case in cases], "planned_unique_calls": 120,
        "dataset": str(args.dataset),
        "request_settings": {**REQUEST_SETTINGS, "max_output": "model_default"},
        "configuration": configuration, "grader": GRADER_VERSION, "policy": POLICY_VERSION,
        "sdk_retries": 0, "orchestration_retries": args.retries,
        "timeout_seconds": args.timeout_seconds, "concurrency": args.concurrency,
        "semantic_evaluation": None,
    })
    jobs, results = {}, {model_id: [] for model_id in MODEL_IDS}
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for case in cases:
            for model in models:
                slug = model["model_id"].replace("/", "__")
                path = args.output_dir / "records" / slug / f"{case.id}.json"
                future = pool.submit(run_with_retry, path, model, case, retry_args, runtime)
                jobs[future] = model["model_id"]
        for future in as_completed(jobs):
            results[jobs[future]].append(future.result())
    summaries = [summarize_model(model, [], sorted(results[model["model_id"]],
                   key=lambda item: item["case_id"])) for model in models]
    write_reports(args.output_dir, {"discovered_count": 4, "eligible_count": 4,
                                    "selected": models}, summaries)
    atomic_json(args.output_dir / "run-summary.json", {
        "completed_at": datetime.now(UTC).isoformat(), "models": summaries,
        "known_cost_usd": sum(item["known_cost_usd"] for item in summaries),
        "unknown_cost_calls": sum(item["unknown_cost_calls"] for item in summaries),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
