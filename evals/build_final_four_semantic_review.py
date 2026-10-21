#!/usr/bin/env python3
"""Build a deterministic 30-case blind review CSV and private model mapping."""

import argparse
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.run_openrouter_final_four import MODEL_IDS, ROOT

SCORE_FIELDS = (
    "intent_score_1_5", "evidence_score_1_5", "needed_score_1_5",
    "coaching_usefulness_score_1_5", "grounding_score_1_5",
    "service_ready_score_1_5",
)
SHUFFLE_SEED_ID = "malhaebom-final-four-blind-v1"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT / "evals/dataset.v2.jsonl")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line]
    if len(cases) != 30:
        raise ValueError("blind review는 고정 30건 dataset만 허용합니다")
    core = {case["id"] for case in cases if case["expected"].get("semantic") is not None}
    if len(core) != 15:
        raise ValueError("semantic annotation 핵심 case는 15건이어야 합니다")
    records = {}
    for model in MODEL_IDS:
        slug = model.replace("/", "__")
        for path in sorted((args.results_dir / "records" / slug).glob("*.json")):
            item = json.loads(path.read_text(encoding="utf-8"))
            records[(model, item["case_id"])] = item["final"]
    if len(records) != 120:
        raise ValueError(f"Final Four 결과는 120건이어야 합니다: {len(records)}")
    rng = random.Random(SHUFFLE_SEED_ID)
    rows, mapping = [], []
    for case in cases:
        shuffled = list(MODEL_IDS)
        rng.shuffle(shuffled)
        context = case["context"]
        source = {"question": case["question"], "requirement_ids": context["requirement_ids"],
                  "active_criterion_ids": context["active_criterion_ids"],
                  "answer_segments": context["answer_segments"]}
        for anonymous_id, model in zip("ABCD", shuffled):
            record = records[(model, case["id"])]
            raw = record.get("raw_output")
            row = {"case_id": case["id"], "core_15": "Y" if case["id"] in core else "N",
                   "anonymous_id": anonymous_id,
                   "source_context_json": json.dumps(source, ensure_ascii=False, separators=(",", ":")),
                   "response_json": raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False),
                   **{field: "" for field in SCORE_FIELDS}, "comment": ""}
            rows.append(row)
            mapping.append({"case_id": case["id"], "anonymous_id": anonymous_id,
                            "model_id": model, "attempt_id": record["attempt_id"]})
    fields = list(rows[0])
    with (args.results_dir / "semantic-blind-review.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (args.results_dir / "semantic-blind-mapping.json").write_text(json.dumps({
        "warning": "Keep separate from reviewers until scoring is complete.",
        "shuffle_seed_id": SHUFFLE_SEED_ID, "mapping": mapping,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
