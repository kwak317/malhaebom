#!/usr/bin/env python3
"""Compare current Skill against exactly one candidate rule change under locked conditions."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

from app.services.coaching_prompt import prompt_sha256  # noqa: E402
from app.services.coaching_skill import load_skill_bundle  # noqa: E402
from evals.environment import load_evaluation_env, resolve_provider_credentials  # noqa: E402
from evals.run_model_comparison import (  # noqa: E402
    CandidateConfig,
    OpenAICompatibleRunner,
    build_system_prompt,
    load_dataset,
    run_comparison,
    write_report,
)

DEFAULT_SPEC = ROOT / "evals/skill_rule_candidates/off-topic-cav-independence-v1.json"


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_candidate_spec(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "candidate_id",
        "target_file",
        "target_section",
        "target_case",
        "target_criteria",
        "hypothesis",
        "old_rule",
        "new_rule",
        "locked",
    }
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"candidate spec missing keys: {', '.join(missing)}")
    if data["old_rule"] == data["new_rule"]:
        raise ValueError("old_rule and new_rule must differ")
    if not data["target_criteria"] or len(data["target_criteria"]) != len(
        set(data["target_criteria"])
    ):
        raise ValueError("target_criteria must be a non-empty unique list")
    return data


def build_rule_variants(spec: dict) -> tuple[object, str]:
    target = (ROOT / spec["target_file"]).resolve()
    bundle = load_skill_bundle(target)
    old_rule = spec["old_rule"]
    new_rule = spec["new_rule"]
    if bundle.rules_text.count(old_rule) != 1:
        raise ValueError("old_rule must occur exactly once in the assembled Skill bundle")
    if new_rule in bundle.rules_text:
        raise ValueError("new_rule is already present in the baseline Skill bundle")
    candidate_rules = bundle.rules_text.replace(old_rule, new_rule, 1)
    if candidate_rules.count(new_rule) != 1:
        raise ValueError("candidate rule replacement was not unique")
    return bundle, candidate_rules


def changed_lines(before: str, after: str) -> tuple[list[str], list[str]]:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    removed = [line for line in before_lines if line not in after_lines]
    added = [line for line in after_lines if line not in before_lines]
    return removed, added


def build_plan(spec: dict, bundle, candidate_rules: str, repeats: int, case_ids: list[str]) -> dict:
    locked = spec["locked"]
    prompt_version = locked["prompt_version"]
    baseline_prompt = build_system_prompt(
        bundle.rules_text, prompt_version, bundle.catalog.skill_version
    )
    candidate_prompt = build_system_prompt(
        candidate_rules, prompt_version, bundle.catalog.skill_version
    )
    removed, added = changed_lines(bundle.rules_text, candidate_rules)
    if removed != [spec["old_rule"]] or added != [spec["new_rule"]]:
        raise ValueError("candidate must change exactly one Skill rule line")
    return {
        "schema_version": 1,
        "candidate_id": spec["candidate_id"],
        "target_case": spec["target_case"],
        "target_criteria": spec["target_criteria"],
        "selected_cases": case_ids or ["ALL"],
        "hypothesis": spec["hypothesis"],
        "repeats": repeats,
        "single_variable_contract": {
            "changed": "one Skill rule line only",
            "old_rule": spec["old_rule"],
            "new_rule": spec["new_rule"],
            "unchanged": [
                "dataset",
                "prompt template/version",
                "model",
                "grader/policy",
                "Skill version metadata exposed to the model",
                "generation settings",
            ],
        },
        "locked": locked,
        "baseline": {
            "skill_version": bundle.catalog.skill_version,
            "criteria_version": bundle.catalog.criteria_version,
            "skill_bundle_sha256": bundle.sha256,
            "system_prompt_sha256": prompt_sha256(baseline_prompt),
        },
        "candidate": {
            "skill_version_metadata": bundle.catalog.skill_version,
            "criteria_version": bundle.catalog.criteria_version,
            "skill_rules_sha256": digest_text(candidate_rules),
            "system_prompt_sha256": prompt_sha256(candidate_prompt),
        },
    }


def evaluate_decision(report: dict, spec: dict) -> dict:
    target = spec["target_case"]
    target_criteria = spec["target_criteria"]
    labels = ("baseline", "candidate")
    rows = []
    target_hits: dict[str, int] = {}
    target_runs: dict[str, int] = {}
    target_hits_by_criterion: dict[str, dict[str, int]] = {}

    for label in labels:
        records = [
            item for item in report["attempts"]
            if item["candidate"] == label and item["case_id"] == target and item["score"]
        ]
        target_runs[label] = len(records)
        target_hits_by_criterion[label] = {
            criterion_id: sum(
                bool(
                    item["score"]["label_results"].get(
                        f"criterion:{criterion_id}"
                    )
                )
                for item in records
            )
            for criterion_id in target_criteria
        }
        target_hits[label] = sum(target_hits_by_criterion[label].values())
        summary = report["candidates"][label]
        rows.append(
            (
                label,
                summary["final_contract_rate"],
                summary["metrics"]["label_accuracy"],
                target_hits[label],
                target_runs[label],
            )
        )

    baseline = report["candidates"]["baseline"]
    candidate = report["candidates"]["candidate"]
    target_deltas = {
        criterion_id: (
            target_hits_by_criterion["candidate"][criterion_id]
            - target_hits_by_criterion["baseline"][criterion_id]
        )
        for criterion_id in target_criteria
    }
    improves_target = any(delta > 0 for delta in target_deltas.values())
    no_target_regression = all(delta >= 0 for delta in target_deltas.values())
    no_label_regression = (
        candidate["metrics"]["label_accuracy"] is not None
        and baseline["metrics"]["label_accuracy"] is not None
        and candidate["metrics"]["label_accuracy"] >= baseline["metrics"]["label_accuracy"]
    )
    no_contract_regression = candidate["final_contract_rate"] >= baseline["final_contract_rate"]

    if (
        improves_target
        and no_target_regression
        and no_label_regression
        and no_contract_regression
    ):
        recommendation = "KEEP_CANDIDATE_PENDING_HUMAN_REVIEW"
    elif not no_target_regression or not no_contract_regression:
        recommendation = "DISCARD_CANDIDATE"
    elif not improves_target:
        recommendation = "DISCARD_CANDIDATE"
    else:
        recommendation = "REVIEW"

    return {
        "recommendation": recommendation,
        "rows": rows,
        "target_hits": target_hits,
        "target_runs": target_runs,
        "target_hits_by_criterion": target_hits_by_criterion,
        "target_deltas_by_criterion": target_deltas,
        "no_target_regression": no_target_regression,
        "target_criteria": target_criteria,
    }


def write_decision_summary(report: dict, spec: dict, output_dir: Path) -> None:
    target = spec["target_case"]
    decision = evaluate_decision(report, spec)
    recommendation = decision["recommendation"]
    rows = decision["rows"]
    target_criteria = decision["target_criteria"]
    target_hits_by_criterion = decision["target_hits_by_criterion"]
    target_deltas_by_criterion = decision["target_deltas_by_criterion"]

    lines = [
        "# Single Skill Rule A/B decision summary",
        "",
        f"- candidate: `{spec['candidate_id']}`",
        f"- target case: `{target}`",
        f"- target criteria: `{', '.join(target_criteria)}`",
        f"- recommendation: **{recommendation}**",
        "- This recommendation is automatic; final KEEP/DISCARD requires a human review of target and regression cases.",
        "",
        "| variant | contract | label accuracy | target criterion hits | target runs |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for label, contract, accuracy, hits, runs in rows:
        lines.append(
            f"| {label} | {contract:.1%} | {accuracy:.1%} | {hits} | {runs} |"
        )
    lines.extend(
        [
            "",
            "## Target criterion hit detail",
            "",
            "| variant | criterion | correct runs |",
            "| --- | --- | ---: |",
        ]
    )
    for label in ("baseline", "candidate"):
        for criterion_id in target_criteria:
            lines.append(
                f"| {label} | {criterion_id} | "
                f"{target_hits_by_criterion[label][criterion_id]} |"
            )
    lines.extend(
        [
            "",
            "Target deltas (candidate - baseline): "
            + ", ".join(
                f"{criterion_id}={target_deltas_by_criterion[criterion_id]:+d}"
                for criterion_id in target_criteria
            ),
        ]
    )
    lines.extend(
        [
            "",
            "## Fixed decision policy",
            "",
            "- Candidate must improve at least one target criterion.",
            "- No target criterion may regress, even when total target hits increase.",
            "- Overall label accuracy must not decrease.",
            "- Final contract rate must not decrease.",
            "- Human review still checks the target case and any newly regressed case before final KEEP/DISCARD.",
            "",
        ]
    )
    (output_dir / "decision-summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.repeats < 1:
        parser.error("--repeats must be >= 1")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("existing non-empty output-dir is not overwritten")

    spec = load_candidate_spec(args.spec)
    bundle, candidate_rules = build_rule_variants(spec)
    cases = load_dataset(ROOT / spec["locked"]["dataset"])
    if args.case_id:
        requested = set(args.case_id)
        known = {case.id for case in cases}
        unknown = sorted(requested - known)
        if unknown:
            parser.error("unknown case-id: " + ", ".join(unknown))
        cases = [case for case in cases if case.id in requested]

    plan = build_plan(spec, bundle, candidate_rules, args.repeats, args.case_id)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "baseline.system.txt").write_text(
        build_system_prompt(
            bundle.rules_text,
            spec["locked"]["prompt_version"],
            bundle.catalog.skill_version,
        ),
        encoding="utf-8",
    )
    (args.output_dir / "candidate.system.txt").write_text(
        build_system_prompt(
            candidate_rules,
            spec["locked"]["prompt_version"],
            bundle.catalog.skill_version,
        ),
        encoding="utf-8",
    )

    if args.dry_run:
        print(args.output_dir / "plan.json")
        return

    load_evaluation_env()
    key, url = resolve_provider_credentials(require_openrouter=True)
    candidates = []
    for label, rules in (("baseline", bundle.rules_text), ("candidate", candidate_rules)):
        config = CandidateConfig(
            label=label,
            provider="openai",
            model=spec["locked"]["model"],
        )
        runner = OpenAICompatibleRunner(
            config,
            system_prompt=build_system_prompt(
                rules,
                spec["locked"]["prompt_version"],
                bundle.catalog.skill_version,
            ),
            api_key=key,
            base_url=url,
            timeout_seconds=spec["locked"]["timeout_seconds"],
            max_completion_tokens=spec["locked"]["max_completion_tokens"],
        )
        candidates.append((config, runner))

    report = run_comparison(
        cases,
        candidates,
        repeats=args.repeats,
        max_calls=spec["locked"]["max_calls"],
        configuration={
            "prompt_version": spec["locked"]["prompt_version"],
            "prompt_sha256": "per_candidate: see plan.json",
            "criteria_version": bundle.catalog.criteria_version,
            "skill_version": bundle.catalog.skill_version,
            "skill_bundle_sha256": "per_candidate: see plan.json",
            "generation_workflow": "single_skill_rule_ab_v1",
        },
    )
    write_report(report, args.output_dir)
    write_decision_summary(report, spec, args.output_dir)
    print(args.output_dir / "comparison.json")


if __name__ == "__main__":
    main()
