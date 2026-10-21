#!/usr/bin/env python3
"""Shared state and system helpers for detached overnight jobs."""

from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "overnight_jobs.json"
RUN_ROOT = PROJECT_ROOT / "artifacts" / "overnight"
SESSION_PREFIX = "p23-overnight-"
JOB_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_jobs() -> dict[str, dict[str, Any]]:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("overnight job config must be a JSON object")
    for name, spec in data.items():
        if not JOB_RE.fullmatch(name):
            raise ValueError(f"invalid job name: {name!r}")
        argv = spec.get("argv")
        if not isinstance(argv, list) or not argv or not all(
            isinstance(value, str) and value for value in argv
        ):
            raise ValueError(f"{name}: argv must be a non-empty string list")
    return data


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def session_name(job: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", job)
    return SESSION_PREFIX + safe


def tmux_available() -> str:
    value = shutil.which("tmux")
    if not value:
        raise RuntimeError("tmux is not installed")
    return value


def tmux_has_session(name: str) -> bool:
    tmux = tmux_available()
    result = subprocess.run(
        [tmux, "has-session", "-t", name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def latest_run_dir(job: str) -> Path | None:
    pointer = RUN_ROOT / job / "latest_run.txt"
    if not pointer.is_file():
        return None
    run_id = pointer.read_text(encoding="utf-8").strip()
    if not run_id:
        return None
    path = (RUN_ROOT / job / run_id).resolve()
    expected = (RUN_ROOT / job).resolve()
    if expected not in path.parents:
        raise RuntimeError(f"invalid latest run pointer for {job}")
    return path


def gpu_snapshot() -> dict[str, Any] | None:
    nvidia_smi = shutil.which("nvidia-smi") or "/usr/lib/wsl/lib/nvidia-smi"
    if not Path(nvidia_smi).exists():
        return None
    result = subprocess.run(
        [
            nvidia_smi,
            "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if result.returncode != 0:
        return {"error": result.stderr.strip()}
    line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    parts = [item.strip() for item in line.split(",")]
    if len(parts) != 5:
        return {"raw": line}
    return {
        "utilization_percent": parts[0],
        "memory_used_mib": parts[1],
        "memory_total_mib": parts[2],
        "temperature_c": parts[3],
        "power_w": parts[4],
    }


def windows_sleep_status() -> dict[str, Any] | None:
    exe = Path("/mnt/c/Windows/System32/powercfg.exe")
    if not exe.is_file():
        return None
    result = subprocess.run(
        [str(exe), "/query", "SCHEME_CURRENT", "SUB_SLEEP", "STANDBYIDLE"],
        capture_output=True,
        timeout=10,
        check=False,
    )
    text = ""
    for encoding in ("utf-8", "cp949", "utf-16le"):
        try:
            candidate = result.stdout.decode(encoding)
        except UnicodeDecodeError:
            continue
        if candidate.strip():
            text = candidate
            break
    ac = re.search(
        r"(?:현재\s+)?AC[^\r\n]*0x([0-9a-fA-F]{8})", text, re.IGNORECASE
    )
    dc = re.search(
        r"(?:현재\s+)?DC[^\r\n]*0x([0-9a-fA-F]{8})", text, re.IGNORECASE
    )
    status: dict[str, Any] = {"returncode": result.returncode}
    if ac:
        status["ac_sleep_seconds"] = int(ac.group(1), 16)
    if dc:
        status["dc_sleep_seconds"] = int(dc.group(1), 16)
    if not ac and not dc:
        status["raw_tail"] = text[-1200:]
    return status


def cmd_doctor() -> int:
    usage = shutil.disk_usage(PROJECT_ROOT)
    report = {
        "tmux": shutil.which("tmux"),
        "project_root": str(PROJECT_ROOT),
        "disk_free_gib": round(usage.free / (1024**3), 2),
        "gpu": gpu_snapshot(),
        "windows_sleep": windows_sleep_status(),
        "jobs_config": str(CONFIG_PATH),
        "run_root": str(RUN_ROOT),
    }
    sleep = report.get("windows_sleep") or {}
    if isinstance(sleep, dict) and sleep.get("ac_sleep_seconds") not in (None, 0):
        report["warning"] = (
            "Windows AC sleep is enabled; disable sleep before overnight jobs."
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_list() -> int:
    jobs = load_jobs()
    rows = []
    for name, spec in jobs.items():
        rows.append(
            {
                "job": name,
                "description": spec.get("description", ""),
                "gpu": bool(spec.get("gpu")),
                "network": bool(spec.get("network")),
                "resume_safe": bool(spec.get("resume_safe")),
                "argv": spec["argv"],
            }
        )
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0