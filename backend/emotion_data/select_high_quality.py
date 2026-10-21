"""Select high-quality Korean speech-emotion samples without changing source data."""

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import soundfile as sf


LABELS = ("기쁨", "당황", "분노", "불안", "슬픔")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--confirm-data-use", action="store_true")
    parser.add_argument("--min-duration", type=float, default=1.5)
    parser.add_argument("--max-duration", type=float, default=12.0)
    return parser.parse_args()


def dbfs(value):
    return 20.0 * math.log10(max(float(value), 1e-8))


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def analyze(path, min_duration, max_duration):
    info = sf.info(path)
    if info.samplerate != 16000 or info.channels != 1:
        return None, "not_16khz_mono", ""
    duration = info.frames / info.samplerate
    if not min_duration <= duration <= max_duration:
        return None, "duration_out_of_range", ""

    audio, sample_rate = sf.read(path, dtype="float32")
    if sample_rate != 16000 or audio.size == 0:
        return None, "unreadable_or_empty", ""
    rms_dbfs = dbfs(np.sqrt(np.mean(np.square(audio))))
    clip_ratio = float(np.mean(np.abs(audio) >= 0.99))
    frame_size = 400
    frame_count = len(audio) // frame_size
    if frame_count == 0:
        return None, "too_short", ""
    frames = audio[: frame_count * frame_size].reshape(frame_count, frame_size)
    frame_dbfs = 20.0 * np.log10(
        np.maximum(np.sqrt(np.mean(np.square(frames), axis=1)), 1e-8)
    )
    active_ratio = float(np.mean(frame_dbfs > max(-45.0, rms_dbfs - 20.0)))

    reasons = []
    if rms_dbfs < -35.0:
        reasons.append("too_quiet")
    if rms_dbfs > -8.0:
        reasons.append("too_loud")
    if clip_ratio > 0.005:
        reasons.append("clipping")
    if active_ratio < 0.45:
        reasons.append("too_much_silence")
    if reasons:
        return None, ";".join(reasons), ""

    score = 100.0
    score -= min(abs(rms_dbfs + 20.0) * 1.5, 20.0)
    score -= min(abs(active_ratio - 0.80) * 25.0, 10.0)
    score -= min(clip_ratio * 1000.0, 10.0)
    score -= min(abs(duration - 4.5) * 1.5, 10.0)
    return {
        "duration_sec": round(duration, 4),
        "rms_dbfs": round(rms_dbfs, 2),
        "clip_ratio": round(clip_ratio, 6),
        "active_ratio": round(active_ratio, 4),
        "quality_score": round(score, 3),
    }, "", fingerprint(path)


def main():
    args = parse_args()
    if not args.confirm_data_use:
        raise SystemExit("데이터 이용 범위를 확인한 뒤 --confirm-data-use를 지정하세요.")
    if args.output_dir.exists():
        raise SystemExit(f"출력 폴더가 이미 존재합니다: {args.output_dir}")
    manifest_path = args.data_root / "manifest.csv"
    audio_dir = args.data_root / "audio"
    if not manifest_path.is_file() or not audio_dir.is_dir():
        raise SystemExit("data-root에는 manifest.csv와 audio 폴더가 필요합니다.")

    with manifest_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or not {"file", "label", "split"}.issubset(rows[0]):
        raise SystemExit("manifest에는 file,label,split 열이 필요합니다.")
    if not set(row["label"] for row in rows).issubset(LABELS):
        raise SystemExit("허용되지 않은 라벨이 있습니다.")

    args.output_dir.mkdir(parents=True)
    candidates, rejected, hashes = [], [], {}
    for index, row in enumerate(rows, start=1):
        result = dict(row)
        try:
            metrics, reason, digest = analyze(
                audio_dir / row["file"], args.min_duration, args.max_duration
            )
        except Exception as error:
            metrics, reason, digest = None, f"read_error:{type(error).__name__}", ""
        if metrics is None:
            result.update({"status": "rejected", "reason": reason})
            rejected.append(result)
        elif digest in hashes:
            result.update({**metrics, "status": "rejected", "reason": "duplicate_audio"})
            rejected.append(result)
        else:
            hashes[digest] = row["file"]
            result.update({**metrics, "status": "candidate", "reason": ""})
            candidates.append(result)
        if index % 500 == 0 or index == len(rows):
            print(f"분석 진행률: {index}/{len(rows)} ({index / len(rows):.1%})")

    by_label = defaultdict(list)
    for row in candidates:
        by_label[row["label"]].append(row)
    if set(by_label) != set(LABELS):
        raise SystemExit("모든 감정 라벨의 후보가 필요합니다.")
    for label_rows in by_label.values():
        label_rows.sort(key=lambda row: (-float(row["quality_score"]), row["file"]))
    balanced_count = min(len(by_label[label]) for label in LABELS)
    balanced = [row for label in LABELS for row in by_label[label][:balanced_count]]
    balanced.sort(key=lambda row: (row["label"], row["file"]))

    fields = [
        "file", "label", "source_label", "split", "duration_sec", "rms_dbfs",
        "clip_ratio", "active_ratio", "quality_score", "status", "reason",
    ]
    for name, output_rows in (
        ("quality_candidates.csv", candidates),
        ("rejected_samples.csv", rejected),
        ("balanced_high_quality_manifest.csv", balanced),
    ):
        with (args.output_dir / name).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(output_rows)

    summary = {
        "source_total": len(rows),
        "candidates": len(candidates),
        "rejected": len(rejected),
        "balanced_per_label": balanced_count,
        "balanced_total": len(balanced),
        "candidate_counts": dict(Counter(row["label"] for row in candidates)),
        "rejection_reasons": dict(Counter(row["reason"] for row in rejected)),
    }
    (args.output_dir / "selection_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
