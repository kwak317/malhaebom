"""Run an isolated one-epoch speech-emotion pilot experiment."""

import argparse
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
import torch
from sklearn.metrics import accuracy_score, f1_score
from torch.utils.data import DataLoader, Dataset

from model_loader import LABELS, MODEL_NAME, load_model


REQUIRED_COLUMNS = {"file", "label", "split"}
ALLOWED_SPLITS = {"train", "validation", "test"}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--base-model", default=MODEL_NAME)
    parser.add_argument("--confirm-data-use", action="store_true")
    parser.add_argument("--epochs", type=int, default=1, choices=[1])
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--gradient-accumulation", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_and_validate_manifest(data_root):
    manifest_path = data_root / "manifest.csv"
    audio_dir = data_root / "audio"
    manifest = pd.read_csv(manifest_path)
    missing_columns = REQUIRED_COLUMNS - set(manifest.columns)
    if missing_columns:
        raise ValueError(f"manifest 필수 열 누락: {sorted(missing_columns)}")
    if not set(manifest["label"]).issubset(LABELS):
        raise ValueError("지원하지 않는 감정 라벨이 있습니다.")
    if not ALLOWED_SPLITS.issubset(set(manifest["split"])):
        raise ValueError("train, validation, test split이 모두 필요합니다.")
    if len(manifest) != 5000:
        raise ValueError(f"파일럿 manifest는 5,000행이어야 합니다: {len(manifest)}")

    for row in manifest.itertuples(index=False):
        audio_path = audio_dir / row.file
        if not audio_path.is_file():
            raise FileNotFoundError(audio_path)
        info = sf.info(audio_path)
        if info.samplerate != 16000 or info.channels != 1:
            raise ValueError(f"16 kHz mono가 아닙니다: {audio_path}")
    return manifest, audio_dir


class EmotionDataset(Dataset):
    def __init__(self, rows, audio_dir, processor, label2id):
        self.rows = rows.reset_index(drop=True)
        self.audio_dir = audio_dir
        self.processor = processor
        self.label2id = label2id

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows.iloc[index]
        audio, sample_rate = sf.read(self.audio_dir / row["file"], dtype="float32")
        values = self.processor(audio, sampling_rate=sample_rate).input_values[0]
        return {
            "input_values": torch.tensor(values),
            "labels": torch.tensor(self.label2id[row["label"]], dtype=torch.long),
        }


class EmotionCollator:
    def __init__(self, processor):
        self.processor = processor

    def __call__(self, features):
        labels = torch.stack([feature["labels"] for feature in features])
        inputs = [{"input_values": feature["input_values"]} for feature in features]
        batch = self.processor.pad(inputs, padding=True, return_tensors="pt")
        batch["labels"] = labels
        return batch


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    predictions, targets, losses = [], [], []
    for batch in loader:
        batch = {key: value.to(device) for key, value in batch.items()}
        output = model(**batch)
        losses.append(output["loss"].item())
        predictions.extend(output["logits"].argmax(dim=-1).cpu().tolist())
        targets.extend(batch["labels"].cpu().tolist())
    return {
        "loss": float(np.mean(losses)),
        "accuracy": accuracy_score(targets, predictions),
        "macro_f1": f1_score(targets, predictions, average="macro", zero_division=0),
    }


def main():
    args = parse_args()
    if not args.confirm_data_use:
        raise SystemExit("데이터 이용 승인 확인 후 --confirm-data-use를 지정하세요.")
    if args.output_dir.exists():
        raise SystemExit(f"출력 경로가 이미 존재합니다: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    set_seed(args.seed)

    manifest, audio_dir = load_and_validate_manifest(args.data_root)
    processor, model = load_model(args.base_model)
    label2id = {label: index for index, label in model.config.id2label.items()}
    collator = EmotionCollator(processor)
    datasets = {
        split: EmotionDataset(
            manifest[manifest["split"] == split], audio_dir, processor, label2id
        )
        for split in ALLOWED_SPLITS
    }
    loaders = {
        split: DataLoader(
            dataset,
            batch_size=args.batch_size,
            shuffle=split == "train",
            collate_fn=collator,
        )
        for split, dataset in datasets.items()
    }

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    smoke_batch = next(iter(loaders["validation"]))
    smoke_batch = {key: value.to(device) for key, value in smoke_batch.items()}
    with torch.no_grad():
        assert model(**smoke_batch)["logits"].shape[-1] == len(LABELS)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    model.train()
    optimizer.zero_grad(set_to_none=True)
    running_loss = 0.0
    for step, batch in enumerate(loaders["train"], start=1):
        batch = {key: value.to(device) for key, value in batch.items()}
        with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
            loss = model(**batch)["loss"] / args.gradient_accumulation
        scaler.scale(loss).backward()
        running_loss += loss.item() * args.gradient_accumulation
        if step % args.gradient_accumulation == 0 or step == len(loaders["train"]):
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad(set_to_none=True)

    train_metrics = {
        "epoch": 1,
        "steps": len(loaders["train"]),
        "mean_batch_loss": running_loss / len(loaders["train"]),
        "base_model": args.base_model,
    }
    validation_metrics = evaluate(model, loaders["validation"], device)
    final_dir = args.output_dir / "final"
    model.save_pretrained(final_dir)
    processor.save_pretrained(final_dir)
    (args.output_dir / "train_metrics.json").write_text(
        json.dumps(train_metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output_dir / "validation_metrics.json").write_text(
        json.dumps(validation_metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(validation_metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
