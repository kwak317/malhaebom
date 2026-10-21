"""Validate prepared speech-emotion audio and manifest contracts."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import soundfile as sf


LABELS = {"기쁨", "당황", "분노", "불안", "슬픔"}
SPLITS = {"train", "validation", "test"}
REQUIRED_COLUMNS = {"file", "label", "source_label", "split"}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--expected-count", type=int)
    return parser.parse_args()


def main():
    args = parse_args()
    manifest_path = args.data_root / "manifest.csv"
    audio_root = args.data_root / "audio"
    with manifest_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing_columns:
            raise SystemExit(f"manifest 필수 열 누락: {sorted(missing_columns)}")
        rows = list(reader)

    errors = []
    seen_files = set()
    label_counts = Counter()
    split_counts = Counter()
    for row in rows:
        filename = row["file"]
        if filename in seen_files:
            errors.append(f"중복 파일: {filename}")
        seen_files.add(filename)
        if row["label"] not in LABELS:
            errors.append(f"라벨 오류: {filename} -> {row['label']}")
        if row["split"] not in SPLITS:
            errors.append(f"split 오류: {filename} -> {row['split']}")
        path = audio_root / filename
        if not path.is_file():
            errors.append(f"파일 없음: {path}")
            continue
        try:
            info = sf.info(path)
            if info.samplerate != 16000 or info.channels != 1:
                errors.append(
                    f"형식 오류: {filename} ({info.samplerate} Hz, {info.channels} ch)"
                )
            if info.frames == 0:
                errors.append(f"빈 파일: {filename}")
        except Exception as exc:
            errors.append(f"읽기 오류: {filename} ({exc})")
        label_counts[row["label"]] += 1
        split_counts[row["split"]] += 1

    if args.expected_count is not None and len(rows) != args.expected_count:
        errors.append(f"예상 개수 {args.expected_count}, 실제 {len(rows)}")
    if set(split_counts) != SPLITS:
        errors.append(f"필수 split 부족: {dict(split_counts)}")

    summary = {
        "total": len(rows),
        "labels": dict(label_counts),
        "splits": dict(split_counts),
        "errors": len(errors),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if errors:
        print("\n".join(f"- {error}" for error in errors[:50]))
        raise SystemExit(1)
    print("데이터 계약 검증 통과")


if __name__ == "__main__":
    main()
