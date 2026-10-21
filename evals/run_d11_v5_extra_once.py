#!/usr/bin/env python3
"""Run at most ONE additional provider call for each of two failed D11 v5 cases.

Invoke twice, with existing outcome files kept intact; do not repeat an in-flight
call after a tool timeout without checking provider billing first.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from app.services.coaching_prompt import prompt_sha256
from app.services.coaching_skill import load_skill_bundle
from evals.coaching_dataset import load_dataset
from evals.environment import load_evaluation_env, resolve_provider_credentials
from evals.run_model_comparison import CandidateConfig, OpenAICompatibleRunner, build_system_prompt, run_comparison

OUT = ROOT / "local-results/d11-injection-ab-20261008"
DATASET = ROOT / "evals/d11_injection_candidates.jsonl"
REVIEW = ROOT / "local-results/d11-human-review-2026-10-07/human-review.user-filled.json"
MODEL = "google/gemini-3.5-flash-lite"
PROMPT = "coaching-v5-skill-owned"
CASES = ((4, "d11-injection-02"), (5, "d11-injection-03"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path: Path, obj: dict) -> None:
    temp = path.with_suffix(".writing")
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def main() -> int:
    cases = {c.id: c for c in load_dataset(DATASET)}
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    if manifest["case_sha256"] != sha(DATASET) or manifest["human_review_sha256"] != sha(REVIEW):
        raise ValueError("Frozen input or human review changed")
    if manifest["model"] != MODEL or manifest["max_completion_tokens"] != 4096:
        raise ValueError("Model or generation setting changed")
    skill = load_skill_bundle(ROOT / "skills/interview-coach/SKILL.md")
    system = build_system_prompt(skill.rules_text, PROMPT, skill.catalog.skill_version)
    v5 = manifest["prompt_versions"]["after_v5"]
    if v5["prompt_sha256"] != prompt_sha256(system) or v5["skill_bundle_sha256"] != skill.sha256:
        raise ValueError("Prompt or Skill changed since first experiment")

    for index, case_id in CASES:
        original = json.loads((OUT / f"retry-{index:02d}.json").read_text(encoding="utf-8"))
        if original["case"] != case_id or original["attempt"]["contract_valid"]:
            raise ValueError(f"Previous result not a failure: {case_id}")
        target = OUT / f"extra-retry-{index:02d}.json"
        inflight = OUT / f"inflight-extra-retry-{index:02d}.json"
        if target.exists():
            continue
        if inflight.exists():
            print(f"BLOCKED: previous attempt may have been charged: {case_id}", flush=True)
            return 2
        load_evaluation_env()
        key, url = resolve_provider_credentials(require_openrouter=True)
        cfg = CandidateConfig("after_v5", "openai", MODEL)
        runner = OpenAICompatibleRunner(
            cfg, system_prompt=system, api_key=key, base_url=url,
            timeout_seconds=20, max_completion_tokens=4096,
        )
        atomic(inflight, {
            "case_id": case_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "rule": "Do not repeat this call without auditing provider billing",
        })
        print(f"ONE additional real call: after_v5 {case_id}", flush=True)
        report = run_comparison([cases[case_id]], [(cfg, runner)], repeats=1, max_calls=1)
        attempt = report["attempts"][0]
        atomic(target, {
            "case_id": case_id,
            "prompt": PROMPT,
            "retry_number": 2,
            "attempt": attempt,
            "candidate_summary": report["candidates"]["after_v5"],
        })
        inflight.unlink()
        print(json.dumps({
            "case_id": case_id,
            "contract_valid": attempt["contract_valid"],
            "failure_state": attempt.get("failure_state"),
            "failure_reason": attempt.get("failure_reason"),
            "latency_ms": attempt["latency_ms"],
            "cost_usd": attempt.get("cost_usd"),
            "labels": (attempt.get("score") or {}).get("label_results"),
            "saved": str(target.relative_to(ROOT)),
        }, ensure_ascii=False), flush=True)
        return 0
    print("COMPLETE: both one-off extra retries already recorded, no new call", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
