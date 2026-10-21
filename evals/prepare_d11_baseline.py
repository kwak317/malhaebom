#!/usr/bin/env python3
"""Build a strictly offline D11 evaluation preflight manifest; no provider calls."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from app.services.coaching_prompt import (  # noqa: E402
    DEFAULT_COACHING_PROMPT_VERSION,
    prompt_sha256,
)
from app.services.coaching_skill import load_skill_bundle  # noqa: E402
from evals.run_model_comparison import build_system_prompt, load_dataset  # noqa: E402

SENTINELS = {
    "coach-failure-23": "지시문 삽입",
    "coach-failure-28": "JSON 위장 입력",
    "coach-failure-29": "도구 호출 지시",
}


def build_manifest() -> dict:
    dataset = ROOT / "evals" / "dataset.v2.jsonl"
    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    cases = load_dataset(dataset)
    ids = [case["id"] for case in rows]
    if len(rows) != 30 or len(set(ids)) != 30 or len(cases) != 30:
        raise ValueError("Expected exactly 30 unique validated dataset v2 cases")
    counts = Counter(case["category"] for case in rows)
    if counts != {"normal": 12, "boundary": 10, "failure": 8}:
        raise ValueError(f"Unexpected category counts: {dict(counts)}")
    by_id = {case["id"]: case for case in rows}
    for case_id, label in SENTINELS.items():
        if by_id.get(case_id, {}).get("note") != label:
            raise ValueError(f"Sentinel changed or missing: {case_id}")

    skill = load_skill_bundle(ROOT / "evals/candidates/main-before-production-sync-20261010/skills/interview-coach/SKILL.md")
    prompt_version = DEFAULT_COACHING_PROMPT_VERSION
    compiled = build_system_prompt(skill.rules_text, prompt_version, skill.catalog.skill_version)
    git_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              text=True, capture_output=True, check=True).stdout.strip()
    return {
        "status": "OFFLINE_PREFLIGHT_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": git_head,
        "dataset": {
            "path": "evals/dataset.v2.jsonl",
            "version": "v2",
            "sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
            "count": len(rows),
            "counts": dict(counts),
            "expected_labels": "user-approved single reviewer; not v5 output human review",
        },
        "proposed_local_candidate": {
            "model": "google/gemini-3.5-flash-lite",
            "prompt_version": prompt_version,
            "compiled_prompt_sha256": prompt_sha256(compiled),
            "skill_version": skill.catalog.skill_version,
            "skill_bundle_sha256": skill.sha256,
            "criteria_version": skill.catalog.criteria_version,
            "max_completion_tokens_proposal": 4096,
            "timeout_seconds_proposal": 60,
            "repeats_proposal": 2,
            "note": "Provisional; not evidence of production configuration or an executed D11 baseline.",
        },
        "existing_injection_regression_sentinels": [
            {"case_id": k, "scenario": v} for k, v in SENTINELS.items()
        ],
        "new_injection_cases_added": 0,
        "official_run_requirements": {
            "deployed_revision": None,
            "effective_model_and_provider_route": None,
            "effective_prompt_version_and_hash": None,
            "effective_skill_version_and_hash": None,
            "langfuse_environment_and_prompt_binding": None,
            "approved_generation_settings_and_repeat_count": None,
            "approved_usd_budget": None,
            "team_confirmed_new_injection_case_policy": None,
            "completed_v5_semantic_critical_review": None,
        },
        "paid_run_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    base = (ROOT / "local-results").resolve()
    target = args.output_dir.resolve()
    if not target.is_relative_to(base):
        parser.error("Output must be inside Git-ignored local-results/")
    if target.exists():
        parser.error("Output directory already exists; choose a new run directory")
    result = build_manifest()  # validate before creating any output
    target.mkdir(parents=True, exist_ok=False)
    path = target / "preflight.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Offline preflight written:", path.relative_to(ROOT.resolve()))
    print("Model calls: 0; production match: NOT VERIFIED; paid run: NOT AUTHORIZED")


if __name__ == "__main__":
    main()
