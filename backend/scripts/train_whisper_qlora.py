#!/usr/bin/env python3
"""Train a fresh Whisper-medium QLoRA candidate on the reconstructed STT dataset.

This is intentionally a new experiment run. It does not claim to resume the
historical LoRA lineage whose adapter weights are missing.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any

import torch
from peft import (
    LoraConfig,
    PeftModel,
    get_peft_model,
    prepare_model_for_kbit_training,
)
from transformers import (
    BitsAndBytesConfig,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    WhisperForConditionalGeneration,
    WhisperProcessor,
)
from stt_train_support import (
    LazyWhisperDataset,
    WhisperDataCollator,
    check_audio_exists,
    normalized_metrics,
    project_path,
    read_manifest,
    resolve_resume,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "stt" / "finetune_retrain_5070ti.json"


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("training config must be a JSON object")
    return data


def parse_args() -> argparse.Namespace:
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    known, _ = pre.parse_known_args()
    config_path = project_path(known.config)
    defaults = load_config(config_path)

    parser = argparse.ArgumentParser(
        description="Fresh Whisper-medium QLoRA training for the Malhaebom STT experiment."
    )
    parser.add_argument("--config", type=Path, default=config_path)
    parser.add_argument("--dataset-root", default=defaults.get("dataset_root"))
    parser.add_argument("--train-manifest", default=defaults.get("train_manifest"))
    parser.add_argument("--validation-manifest", default=defaults.get("validation_manifest"))
    parser.add_argument("--output-dir", default=defaults.get("output_dir"))
    parser.add_argument("--model", default=defaults.get("model", "openai/whisper-medium"))
    parser.add_argument(
        "--init-adapter",
        default=defaults.get("init_adapter"),
        help=(
            "Optional PEFT adapter used as the trainable starting weight for a "
            "new experiment. Optimizer state is fresh unless --resume finds a "
            "checkpoint in this experiment output directory."
        ),
    )
    parser.add_argument("--epochs", type=float, default=defaults.get("epochs", 2.0))
    parser.add_argument("--batch-size", type=int, default=defaults.get("batch_size", 1))
    parser.add_argument(
        "--eval-batch-size",
        type=int,
        default=defaults.get("eval_batch_size", defaults.get("batch_size", 1)),
    )
    parser.add_argument("--grad-accum", type=int, default=defaults.get("grad_accum", 32))
    parser.add_argument(
        "--learning-rate", type=float, default=defaults.get("learning_rate", 1e-4)
    )
    parser.add_argument(
        "--warmup-ratio", type=float, default=defaults.get("warmup_ratio", 0.05)
    )
    parser.add_argument("--save-steps", type=int, default=defaults.get("save_steps", 500))
    parser.add_argument("--eval-steps", type=int, default=defaults.get("eval_steps", 500))
    parser.add_argument(
        "--save-total-limit", type=int, default=defaults.get("save_total_limit", 2)
    )
    parser.add_argument("--max-steps", type=int, default=defaults.get("max_steps", -1))
    parser.add_argument(
        "--max-train-samples", type=int, default=defaults.get("max_train_samples")
    )
    parser.add_argument(
        "--max-validation-samples",
        type=int,
        default=defaults.get("max_validation_samples"),
    )
    parser.add_argument("--seed", type=int, default=defaults.get("seed", 42))
    parser.add_argument(
        "--resume",
        default=defaults.get("resume", "auto"),
        metavar="{auto,none,PATH}",
        help="Resume only this new experiment run. Historical missing adapters are not valid.",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate paths/sample counts/CUDA and exit before loading the model.",
    )
    return parser.parse_args()



def main() -> int:
    args = parse_args()
    random.seed(args.seed)
    torch.manual_seed(args.seed)

    dataset_root = project_path(args.dataset_root)
    train_manifest = project_path(args.train_manifest, base=dataset_root)
    validation_manifest = project_path(args.validation_manifest, base=dataset_root)
    output_dir = project_path(args.output_dir)
    init_adapter = (
        project_path(args.init_adapter) if args.init_adapter else None
    )
    if init_adapter is not None:
        required_adapter = init_adapter / "adapter_model.safetensors"
        if not required_adapter.is_file():
            raise FileNotFoundError(
                f"init adapter weight not found: {required_adapter}"
            )

    train_rows = read_manifest(train_manifest, args.max_train_samples)
    validation_rows = read_manifest(
        validation_manifest, args.max_validation_samples
    )
    check_audio_exists(train_rows, dataset_root)
    check_audio_exists(validation_rows, dataset_root)

    effective_batch = args.batch_size * args.grad_accum
    steps_per_epoch = math.ceil(len(train_rows) / effective_batch)
    expected_steps = (
        args.max_steps
        if args.max_steps and args.max_steps > 0
        else math.ceil(steps_per_epoch * args.epochs)
    )
    warmup_steps = math.ceil(expected_steps * args.warmup_ratio)
    summary = {
        "config": str(project_path(args.config)),
        "dataset_root": str(dataset_root),
        "train_manifest": str(train_manifest),
        "validation_manifest": str(validation_manifest),
        "train_samples": len(train_rows),
        "validation_samples": len(validation_rows),
        "model": args.model,
        "init_adapter": str(init_adapter) if init_adapter else None,
        "output_dir": str(output_dir),
        "batch_size": args.batch_size,
        "eval_batch_size": args.eval_batch_size,
        "grad_accum": args.grad_accum,
        "effective_batch": effective_batch,
        "epochs": args.epochs,
        "max_steps": args.max_steps,
        "expected_optimizer_steps": expected_steps,
        "warmup_steps": warmup_steps,
        "cuda_available": torch.cuda.is_available(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "bf16_supported": (
            torch.cuda.is_available() and torch.cuda.is_bf16_supported()
        ),
        "seed": args.seed,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is required for QLoRA training")
    if args.preflight_only:
        print("STT QLoRA training preflight PASSED")
        return 0

    torch.cuda.reset_peak_memory_stats()
    compute_dtype = (
        torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    )
    processor = WhisperProcessor.from_pretrained(
        args.model, language="Korean", task="transcribe"
    )
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )
    model = WhisperForConditionalGeneration.from_pretrained(
        args.model,
        quantization_config=quantization_config,
        device_map={"": 0},
    )
    model.config.use_cache = False
    model.generation_config.language = "korean"
    model.generation_config.task = "transcribe"
    model.generation_config.forced_decoder_ids = None

    model = prepare_model_for_kbit_training(model)
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable()
    if init_adapter is not None:
        model = PeftModel.from_pretrained(
            model,
            init_adapter,
            is_trainable=True,
        )
        print(f"initialized trainable adapter from: {init_adapter}", flush=True)
    else:
        model = get_peft_model(
            model,
            LoraConfig(
                r=16,
                lora_alpha=32,
                lora_dropout=0.05,
                bias="none",
                target_modules=["q_proj", "v_proj"],
            ),
        )
    model.print_trainable_parameters()

    train_dataset = LazyWhisperDataset(train_rows, dataset_root, processor)
    validation_dataset = LazyWhisperDataset(
        validation_rows, dataset_root, processor
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    resume_checkpoint = resolve_resume(output_dir, args.resume)
    print(
        (
            f"resume checkpoint: {resume_checkpoint}"
            if resume_checkpoint
            else (
                f"resume checkpoint: none (new run from adapter {init_adapter})"
                if init_adapter
                else "resume checkpoint: none (fresh QLoRA run)"
            )
        ),
        flush=True,
    )

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.eval_batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.learning_rate,
        warmup_steps=warmup_steps,
        optim="adamw_torch",
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        gradient_checkpointing=True,
        fp16=compute_dtype == torch.float16,
        bf16=compute_dtype == torch.bfloat16,
        eval_strategy="steps",
        eval_steps=args.eval_steps,
        save_strategy="steps",
        save_steps=args.save_steps,
        save_total_limit=args.save_total_limit,
        save_only_model=False,
        logging_steps=25 if args.max_steps < 0 else 1,
        predict_with_generate=True,
        generation_max_length=128,
        generation_num_beams=1,
        load_best_model_at_end=True,
        metric_for_best_model="cer",
        greater_is_better=False,
        report_to="tensorboard",
        remove_unused_columns=False,
        dataloader_num_workers=0,
        seed=args.seed,
        data_seed=args.seed,
    )

    trainer = Seq2SeqTrainer(
        args=training_args,
        model=model,
        train_dataset=train_dataset,
        eval_dataset=validation_dataset,
        data_collator=WhisperDataCollator(
            processor=processor,
            decoder_start_token_id=model.config.decoder_start_token_id,
        ),
        compute_metrics=lambda pred: normalized_metrics(
            processor, pred.predictions, pred.label_ids
        ),
        processing_class=processor.feature_extractor,
    )
    trainer.train(resume_from_checkpoint=resume_checkpoint)

    final_dir = output_dir / "best_adapter"
    trainer.save_model(str(final_dir))
    processor.save_pretrained(str(final_dir))
    peak_allocated_gib = torch.cuda.max_memory_allocated() / (1024**3)
    peak_reserved_gib = torch.cuda.max_memory_reserved() / (1024**3)
    print(
        json.dumps(
            {
                "peak_cuda_allocated_gib": round(peak_allocated_gib, 3),
                "peak_cuda_reserved_gib": round(peak_reserved_gib, 3),
            },
            ensure_ascii=False,
        )
    )
    print(f"completed: {final_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
