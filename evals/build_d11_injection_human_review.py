#!/usr/bin/env python3
"""Create an offline, non-authoritative D11 injection-case human review packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _load_candidates(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != 3 or len({row.get("id") for row in rows}) != 3:
        raise ValueError("Expected exactly three unique D11 injection candidates")
    for row in rows:
        provenance = str(row.get("annotation_provenance", ""))
        if "independent_human_authored_input_pending" not in provenance:
            raise ValueError(f"Candidate lacks pending-human-review provenance: {row.get('id')}")
    return rows


def build_packet(candidates_path: Path) -> dict[str, Any]:
    candidates = _load_candidates(candidates_path)
    reviews = [
        {
            "case_id": candidate["id"],
            "reviewer": "",
            "reviewed_at": "",
            "input_disposition": "",
            "independent_rationale": "",
            "final_expected": None,
            "approved": None,
        }
        for candidate in candidates
    ]
    return {
        "status": "AWAITING_INDEPENDENT_HUMAN_REVIEW",
        "source": str(candidates_path.relative_to(ROOT)).replace("\\", "/"),
        "official_dataset_update_allowed": False,
        "reviews": reviews,
        "candidates": candidates,
    }


def write_packet(packet: dict[str, Any], output_dir: Path) -> None:
    target = output_dir.resolve()
    local_results = (ROOT / "local-results").resolve()
    if not target.is_relative_to(local_results):
        raise ValueError("Output must be inside Git-ignored local-results/")
    target.mkdir(parents=True, exist_ok=False)
    template = {key: value for key, value in packet.items() if key != "candidates"}
    (target / "human-review.template.json").write_text(
        json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# D11 신규 인젝션 사람 검토 패킷",
        "",
        "- 이 패킷은 사람 검토 준비용이며, 공식 평가셋 또는 유료 평가 실행을 생성하지 않습니다.",
        "- 검토자는 각 case의 입력을 직접 작성·수정하거나 독립적으로 확인하고, 이유와 최종 판정을 작성해야 합니다.",
        "- `approved=true`만으로는 부족합니다. reviewer, reviewed_at, input_disposition, independent_rationale, final_expected를 모두 채운 뒤 팀이 별도 승격을 결정합니다.",
        "",
        "## 후보 원문과 제안 판정",
        "",
    ]
    for candidate in packet["candidates"]:
        lines.extend(
            [
                f"## {candidate['id']}",
                "",
                "```json",
                json.dumps(candidate, ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )
    (target / "REVIEW.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "local-results" / "d11-injection-review-20261008",
        help="검토 패킷 위치 (기본: local-results/d11-injection-review-20261008)",
    )
    parser.add_argument(
        "--candidates",
        type=Path,
        default=ROOT / "evals" / "d11_injection_candidates.jsonl",
    )
    args = parser.parse_args()
    target = args.output_dir.resolve()
    if target.exists():
        parser.error("Output directory already exists; choose a new directory")
    try:
        write_packet(build_packet(args.candidates), target)
    except ValueError as error:
        parser.error(str(error))
    print("D11 human review packet written:", target.relative_to(ROOT))
    print("Provider calls: 0; official dataset update: NOT AUTHORIZED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
