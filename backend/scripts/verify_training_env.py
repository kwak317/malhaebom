from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

TARGETS = {
    "stt-runtime": {
        "packages": ["faster-whisper", "ctranslate2"],
        "imports": ["faster_whisper", "ctranslate2"],
        "needs_torch": False,
    },
    "stt-train": {
        "packages": [
            "torch",
            "torchaudio",
            "transformers",
            "peft",
            "bitsandbytes",
            "datasets",
            "accelerate",
            "evaluate",
            "jiwer",
            "tensorboard",
            "soundfile",
        ],
        "imports": [
            "torch",
            "transformers",
            "peft",
            "bitsandbytes",
            "datasets",
            "accelerate",
            "evaluate",
            "jiwer",
            "soundfile",
        ],
        "needs_torch": True,
    },
    "tts-runtime": {
        "packages": [
            "torch",
            "torchaudio",
            "qwen-tts",
            "faster-qwen3-tts",
            "fastapi",
            "uvicorn",
            "numpy",
        ],
        "imports": [
            "torch",
            "qwen_tts",
            "faster_qwen3_tts",
            "fastapi",
            "uvicorn",
            "numpy",
        ],
        "needs_torch": True,
    },
    "tts-train": {
        "packages": [
            "torch",
            "torchaudio",
            "qwen-tts",
            "faster-qwen3-tts",
            "fastapi",
            "uvicorn",
            "numpy",
            "transformers",
            "accelerate",
            "datasets",
            "tensorboard",
            "soundfile",
            "flash-attn",
        ],
        "imports": [
            "torch",
            "qwen_tts",
            "faster_qwen3_tts",
            "fastapi",
            "uvicorn",
            "numpy",
            "transformers",
            "accelerate",
            "datasets",
            "soundfile",
            "flash_attn",
        ],
        "needs_torch": True,
    },
}


def package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def infer_target() -> str | None:
    name = Path(sys.prefix).name
    return name if name in TARGETS else None


def import_status(module_name: str) -> str:
    try:
        importlib.import_module(module_name)
        return "ok"
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def torch_info() -> dict[str, object]:
    try:
        import torch

        return {
            "version": torch.__version__,
            "compiled_cuda": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "device_count": torch.cuda.device_count(),
            "device_0": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "bf16_supported": torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False,
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def ctranslate2_info() -> dict[str, object]:
    try:
        import ctranslate2

        return {
            "version": package_version("ctranslate2"),
            "cuda_device_count": ctranslate2.get_cuda_device_count(),
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify an isolated STT/TTS model environment.")
    parser.add_argument("--target", choices=tuple(TARGETS), help="Override target inference from sys.prefix.")
    parser.add_argument(
        "--require-cuda",
        action="store_true",
        help="Fail when the selected environment cannot access CUDA.",
    )
    args = parser.parse_args()

    target = args.target or infer_target()
    if target is None:
        raise SystemExit(
            "Could not infer target from sys.prefix. Activate one of "
            ".venvs/stt-runtime, .venvs/stt-train, .venvs/tts-runtime, "
            "or .venvs/tts-train, "
            "or pass --target."
        )

    spec = TARGETS[target]
    versions = {name: package_version(name) for name in spec["packages"]}
    imports = {name: import_status(name) for name in spec["imports"]}

    torch_state = torch_info() if spec["needs_torch"] else None
    ct2 = ctranslate2_info() if target == "stt-runtime" else None
    flash_attn_smoke: dict[str, object] | None = None
    if target == "tts-train":
        try:
            import torch as torch_module
            from flash_attn import flash_attn_func

            q = torch_module.randn(
                1, 32, 4, 64, device="cuda", dtype=torch_module.bfloat16
            )
            k = torch_module.randn_like(q)
            v = torch_module.randn_like(q)
            out = flash_attn_func(q, k, v, dropout_p=0.0, causal=False)
            flash_attn_smoke = {
                "ok": True,
                "shape": list(out.shape),
                "dtype": str(out.dtype),
            }
        except Exception as exc:
            flash_attn_smoke = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    missing_packages = [name for name, value in versions.items() if value is None]
    failed_imports = [name for name, value in imports.items() if value != "ok"]
    pip_check = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True,
        text=True,
        check=False,
    )

    if target == "stt-runtime":
        cuda_available = bool(ct2 and ct2.get("cuda_device_count", 0))
    else:
        cuda_available = bool(
            torch_state and torch_state.get("cuda_available", False)
        )

    ok = (
        not missing_packages
        and not failed_imports
        and pip_check.returncode == 0
        and (cuda_available or not args.require_cuda)
        and (target != "tts-train" or bool(flash_attn_smoke and flash_attn_smoke["ok"]))
    )

    result = {
        "ok": ok,
        "target": target,
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "prefix": sys.prefix,
        "versions": versions,
        "imports": imports,
        "torch_cuda": torch_state,
        "ctranslate2": ct2,
        "flash_attn_smoke": flash_attn_smoke,
        "missing_packages": missing_packages,
        "failed_imports": failed_imports,
        "pip_check": {
            "ok": pip_check.returncode == 0,
            "output": (pip_check.stdout or pip_check.stderr).strip(),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
