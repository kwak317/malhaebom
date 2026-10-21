#!/usr/bin/env python3
"""Score scripted STT predictions with raw and conservative spoken-form CER/WER."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

EQUIVALENCE_CLASSES = {
    "num_1233": ("1,233", "1233", "천이백삼십삼"),
    "num_2_5876": ("2.5876", "이점오팔칠육", "이 점 오 팔 칠 육"),
    "num_9_7740": ("9.7740", "구점칠칠사공", "구 점 칠 칠 사 공"),
    "num_2026": ("2026", "이천이십육", "이천 이십육"),
    "num_sep": ("9월 23일", "구월 이십삼일", "구월 이십삼 일"),
    "num_1030": ("10시 30분", "열시 삼십분", "열 시 삼십 분"),
    "num_1h20": ("1시간 20분", "한시간 이십분", "한 시간 이십 분"),
    "num_16gb": ("16기가바이트", "십육기가바이트", "십육 기가바이트"),
    "term_cer": ("CER", "씨이알", "씨에알"),
    "term_wer": ("WER", "더블유이알", "더블유에알"),
    "term_python": ("Python", "파이썬"),
    "term_react": ("React", "리액트"),
    "term_request": ("request", "리퀘스트"),
    "term_backend_server": ("backend server", "백엔드 서버"),
    "term_access_token": ("access token", "액세스 토큰"),
    "term_json_response": ("JSON response", "제이슨 리스폰스"),
    "term_ci": ("CI", "씨아이"),
    "term_cd": ("CD", "씨디"),
    "term_pr": ("PR", "피알"),
    "term_api": ("API", "에이피아이"),
    "term_db": ("DB", "디비"),
    "term_health_check": ("health check", "헬스 체크", "헬스체크"),
    "term_validation_set": ("validation set", "밸리데이션 셋", "밸리데이션셋"),
    "term_test_set": ("test set", "테스트 셋", "테스트셋"),
}


def normalize_raw(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def normalize_spoken_form(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    markers: dict[str, str] = {}
    replacements = []
    for index, (canonical, aliases) in enumerate(EQUIVALENCE_CLASSES.items()):
        marker = f"spokenformeq{index}token"
        markers[marker] = canonical
        for alias in aliases:
            replacements.append((alias, marker))
    replacements.sort(key=lambda item: len(item[0]), reverse=True)
    for alias, marker in replacements:
        text = re.sub(re.escape(alias), marker, text, flags=re.IGNORECASE)
    for marker, canonical in markers.items():
        text = text.replace(marker, canonical)
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.lower().split())


def edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for i, ref_token in enumerate(reference, start=1):
        current = [i]
        for j, hyp_token in enumerate(hypothesis, start=1):
            substitution = previous[j - 1] + (ref_token != hyp_token)
            insertion = current[j - 1] + 1
            deletion = previous[j] + 1
            current.append(min(substitution, insertion, deletion))
        previous = current
    return previous[-1]


def score_records(records: list[dict], *, spoken_form: bool) -> dict:
    normalizer = normalize_spoken_form if spoken_form else normalize_raw
    cer_edits = cer_units = wer_edits = wer_units = 0

    for record in records:
        reference = normalizer(record["reference"])
        prediction = normalizer(record["prediction"])
        ref_chars = list(reference.replace(" ", ""))
        hyp_chars = list(prediction.replace(" ", ""))
        ref_words = reference.split()
        hyp_words = prediction.split()

        cer_edits += edit_distance(ref_chars, hyp_chars)
        cer_units += len(ref_chars)
        wer_edits += edit_distance(ref_words, hyp_words)
        wer_units += len(ref_words)

    return {
        "cer_percent": 100 * cer_edits / cer_units if cer_units else 0.0,
        "wer_percent": 100 * wer_edits / wer_units if wer_units else 0.0,
        "cer_edits": cer_edits,
        "cer_units": cer_units,
        "wer_edits": wer_edits,
        "wer_units": wer_units,
        "utterances": len(records),
    }


def load_records(paths: list[Path]) -> list[dict]:
    records: list[dict] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"{path}: predictions payload must be a list")
        for row in payload:
            if not isinstance(row, dict) or "reference" not in row or "prediction" not in row:
                raise ValueError(f"{path}: invalid prediction row")
            records.append(row)
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--predictions",
        type=Path,
        action="append",
        required=True,
        help="One or more evaluate_stt_ct2 predictions.json files.",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = load_records(args.predictions)
    result = {
        "raw": score_records(records, spoken_form=False),
        "spoken_form_normalized": score_records(records, spoken_form=True),
        "normalization_policy": {
            "equivalence_classes": EQUIVALENCE_CLASSES,
            "note": (
                "Only clear notation/pronunciation equivalents are collapsed. "
                "Recognition errors such as 덕허/Docker, 웨알/WER, 피아리/PR remain errors."
            ),
        },
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
