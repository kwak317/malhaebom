"""Prepare a private Korean speech-emotion dataset without overwriting data."""

import argparse
import csv
import json
import random
import zipfile
from collections import defaultdict
from pathlib import Path

import soundfile as sf
from scipy.signal import resample_poly


LABEL_MAP = {
    "happiness": "기쁨",
    "surprise": "당황",
    "anger": "분노",
    "angry": "분노",
    "fear": "불안",
    "sad": "슬픔",
    "sadness": "슬픔",
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--csv-encoding", default="cp949")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--confirm-data-use", action="store_true")
    return parser.parse_args()


def read_labels(source_dir, encoding):
    records = {}
    for csv_path in sorted(source_dir.glob("*.csv")):
        with csv_path.open(encoding=encoding, newline="") as handle:
            for row in csv.reader(handle):
                if not row or row[0].strip().lower() == "wav_id":
                    continue
                if len(row) < 3:
                    raise ValueError(f"CSV 열이 부족합니다: {csv_path}")
                raw_label = row[2].strip().lower()
                if raw_label in LABEL_MAP:
                    wav_id = row[0].strip()
                    records[wav_id] = {
                        "file": f"{wav_id}.wav",
                        "label": LABEL_MAP[raw_label],
                        "source_label": raw_label,
                    }
    return records


def assign_stratified_splits(records, seed):
    by_label = defaultdict(list)
    for record in records:
        by_label[record["label"]].append(record)
    rng = random.Random(seed)
    for label_records in by_label.values():
        label_records.sort(key=lambda item: item["file"])
        rng.shuffle(label_records)
        total = len(label_records)
        validation_start = int(total * 0.8)
        test_start = int(total * 0.9)
        for index, record in enumerate(label_records):
            record["split"] = (
                "train"
                if index < validation_start
                else "validation"
                if index < test_start
                else "test"
            )


def convert_audio(source, destination):
    audio, sample_rate = sf.read(source, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sample_rate != 16000:
        audio = resample_poly(audio, 16000, sample_rate)
    if audio.size == 0:
        raise ValueError(f"빈 WAV입니다: {source}")
    sf.write(destination, audio, 16000, subtype="PCM_16")


def main():
    args = parse_args()
    if not args.confirm_data_use:
        raise SystemExit("데이터 이용 범위를 확인한 뒤 --confirm-data-use를 지정하세요.")
    if args.output_dir.exists():
        raise SystemExit(f"출력 디렉터리가 이미 존재합니다: {args.output_dir}")

    records = read_labels(args.source_dir, args.csv_encoding)
    if not records:
        raise SystemExit("허용된 라벨의 CSV 행을 찾지 못했습니다.")
    args.output_dir.mkdir(parents=True)
    audio_dir = args.output_dir / "audio"
    audio_dir.mkdir()

    found = set()
    duplicate_names = set()
    for zip_path in sorted(args.source_dir.glob("*.zip")):
        with zipfile.ZipFile(zip_path) as archive:
            for member in archive.infolist():
                filename = Path(member.filename).name
                if not filename.lower().endswith(".wav"):
                    continue
                wav_id = Path(filename).stem
                if wav_id not in records:
                    continue
                if wav_id in found:
                    duplicate_names.add(filename)
                    continue
                with archive.open(member) as source:
                    convert_audio(source, audio_dir / filename)
                found.add(wav_id)

    usable = [record for wav_id, record in records.items() if wav_id in found]
    assign_stratified_splits(usable, args.seed)
    usable.sort(key=lambda item: item["file"])
    with (args.output_dir / "manifest.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["file", "label", "source_label", "split"]
        )
        writer.writeheader()
        writer.writerows(usable)

    missing = sorted(set(records) - found)
    summary = {
        "seed": args.seed,
        "labeled_rows": len(records),
        "usable_audio": len(usable),
        "missing_audio": len(missing),
        "duplicate_wav_names": len(duplicate_names),
        "excluded_source_labels": ["disgust", "neutral"],
        "label_map": LABEL_MAP,
    }
    (args.output_dir / "preparation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not usable:
        raise SystemExit("사용 가능한 WAV가 없습니다.")


if __name__ == "__main__":
    main()
