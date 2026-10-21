#!/usr/bin/env python3
"""Aggregate completed Final Four blind scores after joining the private mapping."""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.build_final_four_semantic_review import SCORE_FIELDS


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-csv", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mapping_data = json.loads(args.mapping.read_text(encoding="utf-8"))["mapping"]
    mapping = {(item["case_id"], item["anonymous_id"]): item["model_id"] for item in mapping_data}
    rows = list(csv.DictReader(args.review_csv.open(encoding="utf-8-sig")))
    output = {}
    for scope, selected in (("core_15", [row for row in rows if row["core_15"] == "Y"]),
                            ("all_30", rows)):
        grouped = defaultdict(list)
        for row in selected:
            values = [row[field].strip() for field in SCORE_FIELDS]
            if not any(values):
                continue
            if not all(values):
                raise ValueError(f"부분 점수 입력은 허용하지 않습니다: {row['case_id']} {row['anonymous_id']}")
            numbers = [float(value) for value in values]
            if any(value < 1 or value > 5 for value in numbers):
                raise ValueError("semantic 점수는 1~5여야 합니다")
            grouped[mapping[(row["case_id"], row["anonymous_id"])]].append(numbers)
        output[scope] = {}
        for model, items in grouped.items():
            output[scope][model] = {"reviewed_responses": len(items)}
            output[scope][model].update({field: sum(item[index] for item in items) / len(items)
                                         for index, field in enumerate(SCORE_FIELDS)})
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
