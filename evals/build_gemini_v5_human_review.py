#!/usr/bin/env python3
"""Build local human-review materials for Gemini v5 automatic mismatches."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from evals.coaching_dataset import load_dataset
from evals.semantic_grader import SEMANTIC_RUBRIC


def _is_mismatch(attempt: dict[str, Any]) -> bool:
    if attempt.get("contract_valid") is not True:
        return False
    metrics = attempt.get("metrics")
    if not isinstance(metrics, dict):
        return False
    values = (metrics.get("label_accuracy"), metrics.get("evidence_accuracy"))
    return any(isinstance(value, (int, float)) and value < 1.0 for value in values)


def _empty_review() -> dict[str, Any]:
    return {
        "reviewer": "",
        "rationale": "",
        "scores": {},
        "critical_failure": None,
        "critical_failure_reasons": [],
    }


def _json(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def build_review_pack(
    report: dict[str, Any],
    *,
    candidate: str,
    cases: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, dict[str, Any]], str]:
    attempts = report.get("attempts")
    if not isinstance(attempts, list):
        raise ValueError("comparison report에 attempts 배열이 필요합니다")
    candidate_attempts = [item for item in attempts if item.get("candidate") == candidate]
    if not candidate_attempts:
        raise ValueError(f"candidate를 찾을 수 없습니다: {candidate}")
    selected = sorted((item for item in candidate_attempts if _is_mismatch(item)), key=lambda item: str(item["attempt_id"]))
    ids = [str(item["attempt_id"]) for item in selected]
    if len(ids) != len(set(ids)):
        raise ValueError("검토 대상 attempt_id가 중복되었습니다")

    template = {attempt_id: _empty_review() for attempt_id in ids}
    lines = [
        "# Gemini v5 자동 불일치 사람 검토",
        "",
        f"- 후보: `{candidate}`",
        f"- 검토 대상: {len(selected)}건",
        "- 원본 응답과 이 문서는 로컬 평가 산출물로만 보관하며 Git에 커밋하지 않습니다.",
        "- `semantic-reviews.template.json`에서 reviewer, rationale, scores, critical_failure를 채우세요.",
        "",
        "## 점수 기준",
        "",
    ]
    for name, labels in SEMANTIC_RUBRIC.items():
        lines.append(f"### {name}")
        for score, meaning in labels.items():
            lines.append(f"- {score}: {meaning}")
        lines.append("")

    for attempt in selected:
        case_id = str(attempt["case_id"])
        case = (cases or {}).get(case_id)
        metrics = attempt.get("metrics", {})
        lines.extend([
            f"## {case_id}",
            "",
            f"- attempt ID: `{attempt['attempt_id']}`",
            f"- 자동 label/evidence: {metrics.get('label_accuracy')} / {metrics.get('evidence_accuracy')}",
            f"- 모델 label: `{_json(attempt.get('labels'))}`",
            "",
        ])
        if case:
            lines.extend([
                "### 평가 입력",
                "",
                "```json",
                _json({"question": case["question"], "context": case["context"], "expected": case["expected"]}),
                "```",
                "",
            ])
        lines.extend([
            "### 모델 출력",
            "",
            "```json",
            _json(attempt.get("validated_output") or attempt.get("parsed_output") or attempt.get("raw_output")),
            "```",
            "",
        ])
    return template, "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="comparison.json 경로")
    parser.add_argument("--candidate", default="gemini")
    parser.add_argument("--dataset", type=Path, default=ROOT / "evals" / "dataset.v2.jsonl")
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    cases = {case.id: case.model_dump(mode="json") for case in load_dataset(args.dataset)}
    template, markdown = build_review_pack(report, candidate=args.candidate, cases=cases)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "semantic-reviews.template.json").write_text(
        json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "REVIEW.md").write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
