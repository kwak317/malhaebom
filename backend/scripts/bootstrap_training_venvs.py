from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import venv
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_ROOT = PROJECT_ROOT / ".venvs"
PYTORCH_INDEX = "https://download.pytorch.org/whl/cu128"
PYTORCH_VERSION = "2.8.0"
FLASH_ATTN_INDEX = "https://wheels.astral.sh/simple/cu128/"
FLASH_ATTN_VERSION = "2.8.3.post1+cu.12.8.torch.2.8"


@dataclass(frozen=True)
class ModelEnvSpec:
    key: str
    directory: Path
    requirements: Path
    c2c_profile: str
    needs_torch: bool
    reference_python: str | None = None


SPECS = {
    "stt-runtime": ModelEnvSpec(
        key="stt-runtime",
        directory=ENV_ROOT / "stt-runtime",
        requirements=PROJECT_ROOT / "backend/requirements-stt-runtime.txt",
        c2c_profile="proj2-3-stt-runtime",
        needs_torch=False,
    ),
    "stt-train": ModelEnvSpec(
        key="stt-train",
        directory=ENV_ROOT / "stt-train",
        requirements=PROJECT_ROOT / "backend/requirements-stt-training.txt",
        c2c_profile="proj2-3-stt-train",
        needs_torch=True,
    ),
    "tts-runtime": ModelEnvSpec(
        key="tts-runtime",
        directory=ENV_ROOT / "tts-runtime",
        requirements=PROJECT_ROOT / "backend/requirements-tts-runtime.txt",
        c2c_profile="proj2-3-tts-runtime",
        needs_torch=True,
        reference_python="3.12.13",
    ),
    "tts-train": ModelEnvSpec(
        key="tts-train",
        directory=ENV_ROOT / "tts-train",
        requirements=PROJECT_ROOT / "backend/requirements-tts-training.txt",
        c2c_profile="proj2-3-tts-train",
        needs_torch=True,
    ),
}


def run(*args: str) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=PROJECT_ROOT, check=True)


def ensure_python_version(spec: ModelEnvSpec) -> None:
    if sys.version_info[:2] != (3, 12):
        raise SystemExit(
            f"Python 3.12 is required; current interpreter is {sys.version.split()[0]}"
        )
    if spec.reference_python and sys.version.split()[0] != spec.reference_python:
        print(
            f"NOTE: {spec.key} handoff was recorded with Python "
            f"{spec.reference_python}; creating a compatible 3.12 environment "
            f"with {sys.version.split()[0]}.",
            flush=True,
        )


def env_python(env_dir: Path) -> Path:
    if os.name == "nt":
        return env_dir / "Scripts" / "python.exe"
    return env_dir / "bin" / "python"


def has_working_pip(python: Path) -> bool:
    if not python.exists():
        return False
    return (
        subprocess.run(
            [str(python), "-m", "pip", "--version"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def create_env(spec: ModelEnvSpec) -> Path:
    ensure_python_version(spec)
    python = env_python(spec.directory)
    if python.exists():
        if has_working_pip(python):
            print(f"Reusing existing {spec.directory}")
            return python
        print(f"Removing incomplete {spec.directory} (pip is unavailable)")
        shutil.rmtree(spec.directory)

    spec.directory.parent.mkdir(parents=True, exist_ok=True)
    uv = shutil.which("uv")
    if uv:
        run(uv, "venv", "--python", "3.12", str(spec.directory))
    else:
        virtualenv = shutil.which("virtualenv")
        if virtualenv:
            run(virtualenv, "--python", sys.executable, str(spec.directory))
        else:
            ensurepip_ok = (
                subprocess.run(
                    [sys.executable, "-m", "ensurepip", "--version"],
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                ).returncode
                == 0
            )
            if not ensurepip_ok:
                raise SystemExit(
                    "Python 3.12 is installed, but ensurepip/python3.12-venv is missing. "
                    "On Ubuntu/WSL install it with: sudo apt install python3.12-venv."
                )
            venv.EnvBuilder(with_pip=True, symlinks=os.name != "nt").create(spec.directory)

    python = env_python(spec.directory)
    if not has_working_pip(python):
        raise SystemExit(f"Created {spec.directory}, but pip is unavailable")
    return python


def install_pytorch(python: Path) -> None:
    run(
        str(python),
        "-m",
        "pip",
        "install",
        f"torch=={PYTORCH_VERSION}",
        f"torchaudio=={PYTORCH_VERSION}",
        "--index-url",
        PYTORCH_INDEX,
    )


def install_flash_attn(python: Path) -> None:
    run(
        str(python),
        "-m",
        "pip",
        "install",
        f"flash-attn=={FLASH_ATTN_VERSION}",
        "--extra-index-url",
        FLASH_ATTN_INDEX,
    )


def install_env(spec: ModelEnvSpec) -> Path:
    python = create_env(spec)
    run(str(python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")
    if spec.needs_torch:
        install_pytorch(python)
    run(
        str(python),
        "-m",
        "pip",
        "install",
        "-r",
        str(spec.requirements.relative_to(PROJECT_ROOT)),
    )
    if spec.key == "tts-train":
        install_flash_attn(python)
    run(str(python), "-m", "pip", "check")
    return python


def selected_specs(target: str) -> list[ModelEnvSpec]:
    if target == "all":
        return list(SPECS.values())
    return [SPECS[target]]


def print_summary(specs: list[ModelEnvSpec]) -> None:
    print("\nModel environments:")
    profile_paths: dict[str, str] = {}
    for spec in specs:
        python = env_python(spec.directory)
        activate = spec.directory / ("Scripts/activate" if os.name == "nt" else "bin/activate")
        print(f"- {spec.key}: {spec.directory}")
        print(f"  python: {python}")
        if os.name != "nt":
            print(f"  activate: source {activate.relative_to(PROJECT_ROOT)}")
        profile_paths[spec.c2c_profile] = str(python)

    print("\nc2c runtime profile entries:")
    print(json.dumps(profile_paths, ensure_ascii=False, separators=(",", ":")))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create isolated Python 3.12 environments for the transferred STT "
            "runtime, STT QLoRA training, and Qwen3-TTS runtime."
        )
    )
    parser.add_argument(
        "--target",
        choices=(*SPECS.keys(), "all"),
        help="Environment to create/install.",
    )
    parser.add_argument(
        "--create-only",
        action="store_true",
        help="Create the selected venv(s) without installing dependencies.",
    )
    args = parser.parse_args()

    if args.target is None:
        parser.print_help()
        return

    specs = selected_specs(args.target)
    for spec in specs:
        if args.create_only:
            create_env(spec)
        else:
            install_env(spec)

    print_summary(specs)


if __name__ == "__main__":
    main()
