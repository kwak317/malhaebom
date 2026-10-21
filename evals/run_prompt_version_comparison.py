#!/usr/bin/env python3
"""동일 Skill에서 이전 영문 v4와 최신 영문 v5를 합성 30건으로 비교한다."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from app.services.coaching_prompt import prompt_sha256  # noqa: E402
from app.services.coaching_skill import load_skill_bundle  # noqa: E402
from evals.environment import load_evaluation_env, resolve_provider_credentials  # noqa: E402
from evals.run_model_comparison import (  # noqa: E402
    CandidateConfig, OpenAICompatibleRunner, build_system_prompt,
    load_dataset, run_comparison, write_report,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    out = parser.parse_args().output_dir
    if (out / "comparison.json").exists():
        parser.error("기존 결과를 덮어쓰지 않습니다. 새 output-dir를 지정하세요.")
    out.mkdir(parents=True, exist_ok=True)
    cases = load_dataset(ROOT / "evals/dataset.v2.jsonl")
    skill = load_skill_bundle(ROOT / "skills/interview-coach/SKILL.md")
    load_evaluation_env()
    key, url = resolve_provider_credentials(require_openrouter=True)
    candidates = []
    provenance = {}
    for label, version in [
        ("before_v4", "coaching-user-supplied-v4-verification"),
        ("latest_v5", "coaching-v5-skill-owned"),
    ]:
        config = CandidateConfig(label, "openai", "google/gemini-3.5-flash-lite")
        prompt = build_system_prompt(skill.rules_text, version, skill.catalog.skill_version)
        (out / f"{label}.system.txt").write_text(prompt, encoding="utf-8")
        runner = OpenAICompatibleRunner(
            config, system_prompt=prompt, api_key=key, base_url=url,
            timeout_seconds=45, max_completion_tokens=2048,
        )
        candidates.append((config, runner))
        provenance[label] = {
            "prompt_version": version, "prompt_sha256": prompt_sha256(prompt),
            "skill_version": skill.catalog.skill_version,
            "skill_bundle_sha256": skill.sha256,
        }
    (out / "plan.json").write_text(json.dumps({
        "candidates": provenance, "repeats": 1, "max_calls": 2,
        "order": "all before_v4, then all latest_v5", "synthetic": True,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    report = run_comparison(cases, candidates, repeats=1, max_calls=2, configuration={
        "prompt_version": "per_candidate: see candidate_provenance",
        "prompt_sha256": "per_candidate: see candidate_provenance",
        "criteria_version": skill.catalog.criteria_version,
        "skill_version": skill.catalog.skill_version,
        "skill_bundle_sha256": skill.sha256,
        "generation_workflow": "single_generation_v1",
    })
    report["candidate_provenance"] = provenance
    print(write_report(report, out), flush=True)


if __name__ == "__main__":
    main()
