#!/usr/bin/env python3
"""Run registered long jobs safely in detached tmux sessions.

State and logs are written below artifacts/overnight/, which is gitignored.
Commands are read from configs/overnight_jobs.json and are never executed
through shell=True.
"""

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

from overnight_support import (
    PROJECT_ROOT,
    RUN_ROOT,
    atomic_json,
    cmd_doctor,
    cmd_list,
    gpu_snapshot,
    latest_run_dir,
    load_jobs,
    now_iso,
    pid_alive,
    read_json,
    session_name,
    tmux_available,
    tmux_has_session,
)

_CURRENT_CHILD: subprocess.Popen[bytes] | None = None




def cmd_start(job: str) -> int:
    jobs = load_jobs()
    if job not in jobs:
        raise SystemExit(f"unknown job: {job}")
    session = session_name(job)
    if tmux_has_session(session):
        raise SystemExit(
            f"job already has a live tmux session: {job} ({session})"
        )

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = RUN_ROOT / job / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (RUN_ROOT / job / "latest_run.txt").write_text(
        run_id + "\n", encoding="utf-8"
    )
    spec = jobs[job]
    state = {
        "job": job,
        "run_id": run_id,
        "session": session,
        "status": "starting",
        "description": spec.get("description", ""),
        "argv": spec["argv"],
        "gpu": bool(spec.get("gpu")),
        "network": bool(spec.get("network")),
        "resume_safe": bool(spec.get("resume_safe")),
        "created_at": now_iso(),
        "project_root": str(PROJECT_ROOT),
        "log_path": str(run_dir / "run.log"),
    }
    atomic_json(run_dir / "state.json", state)

    tmux = tmux_available()
    worker_argv = [
        sys.executable,
        str(Path(__file__).resolve()),
        "_worker",
        job,
        str(run_dir),
    ]
    command = shlex.join(worker_argv)
    result = subprocess.run(
        [tmux, "new-session", "-d", "-s", session, "-c", str(PROJECT_ROOT), command],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        state.update(
            {
                "status": "start_failed",
                "ended_at": now_iso(),
                "error": result.stderr.strip(),
            }
        )
        atomic_json(run_dir / "state.json", state)
        raise SystemExit(result.stderr.strip() or "tmux start failed")

    time.sleep(0.25)
    current = read_json(run_dir / "state.json")
    print(
        json.dumps(
            {
                "job": job,
                "run_id": run_id,
                "status": current.get("status"),
                "session": session,
                "log": str(run_dir / "run.log"),
                "attach": f"tmux attach -t {session}",
                "follow_log": f"tail -f {shlex.quote(str(run_dir / 'run.log'))}",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def state_with_liveness(job: str) -> dict[str, Any]:
    run_dir = latest_run_dir(job)
    if run_dir is None:
        return {"job": job, "status": "never_run"}
    state_path = run_dir / "state.json"
    state = read_json(state_path)
    session = str(state.get("session") or session_name(job))
    child_pid = state.get("child_pid")
    live = pid_alive(child_pid if isinstance(child_pid, int) else None)
    tmux_live = tmux_has_session(session)
    result = {
        **state,
        "run_dir": str(run_dir),
        "tmux_live": tmux_live,
        "child_live": live,
    }
    if state.get("status") in {"starting", "running"} and not tmux_live and not live:
        result["status_observed"] = "stale_or_crashed"
    elif live and not tmux_live:
        result["status_observed"] = "running_without_tmux"
    elif live or tmux_live:
        result["status_observed"] = "running"
    else:
        result["status_observed"] = state.get("status")
    if state.get("gpu"):
        result["gpu_snapshot"] = gpu_snapshot()
    return result


def cmd_status(job: str | None) -> int:
    jobs = load_jobs()
    names = [job] if job else list(jobs)
    for name in names:
        if name not in jobs:
            raise SystemExit(f"unknown job: {name}")
    payload = [state_with_liveness(name) for name in names]
    print(json.dumps(payload[0] if job else payload, ensure_ascii=False, indent=2))
    return 0


def cmd_logs(job: str, lines: int) -> int:
    if job not in load_jobs():
        raise SystemExit(f"unknown job: {job}")
    run_dir = latest_run_dir(job)
    if run_dir is None:
        raise SystemExit(f"job has never run: {job}")
    log_path = run_dir / "run.log"
    if not log_path.is_file():
        print(f"log not created yet: {log_path}")
        return 0
    with log_path.open(encoding="utf-8", errors="replace") as handle:
        tail = deque(handle, maxlen=lines)
    print("".join(tail), end="")
    return 0


def terminate_group(pid: int, timeout: float = 10.0) -> None:
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not pid_alive(pid):
            return
        time.sleep(0.2)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def cmd_stop(job: str) -> int:
    if job not in load_jobs():
        raise SystemExit(f"unknown job: {job}")
    run_dir = latest_run_dir(job)
    if run_dir is None:
        raise SystemExit(f"job has never run: {job}")
    state_path = run_dir / "state.json"
    state = read_json(state_path)
    child_pid = state.get("child_pid")
    if isinstance(child_pid, int) and pid_alive(child_pid):
        terminate_group(child_pid)
    session = str(state.get("session") or session_name(job))
    if tmux_has_session(session):
        subprocess.run(
            [tmux_available(), "kill-session", "-t", session],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    state.update(
        {
            "status": "stopped",
            "ended_at": now_iso(),
            "stopped_by": "overnight_job.py stop",
        }
    )
    atomic_json(state_path, state)
    print(json.dumps({"job": job, "status": "stopped"}, ensure_ascii=False))
    return 0


def _forward_signal(signum: int, _frame: Any) -> None:
    global _CURRENT_CHILD
    if _CURRENT_CHILD is not None and _CURRENT_CHILD.poll() is None:
        try:
            os.killpg(os.getpgid(_CURRENT_CHILD.pid), signum)
        except ProcessLookupError:
            pass
    raise SystemExit(128 + signum)


def cmd_worker(job: str, run_dir_text: str) -> int:
    global _CURRENT_CHILD
    jobs = load_jobs()
    if job not in jobs:
        raise SystemExit(f"unknown job: {job}")
    run_dir = Path(run_dir_text).resolve()
    job_root = (RUN_ROOT / job).resolve()
    if job_root not in run_dir.parents:
        raise SystemExit("worker run directory is outside the job run root")

    state_path = run_dir / "state.json"
    state = read_json(state_path)
    state.update({"status": "running", "started_at": now_iso(), "worker_pid": os.getpid()})
    atomic_json(state_path, state)

    signal.signal(signal.SIGTERM, _forward_signal)
    signal.signal(signal.SIGINT, _forward_signal)
    argv = jobs[job]["argv"]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    log_path = run_dir / "run.log"

    exit_code = 1
    worker_error: str | None = None
    with log_path.open("ab", buffering=0) as log:
        header = (
            f"=== {now_iso()} START {job} ===\n"
            f"cwd={PROJECT_ROOT}\n"
            f"argv={shlex.join(argv)}\n"
        ).encode()
        log.write(header)
        sys.stdout.buffer.write(header)
        sys.stdout.buffer.flush()
        try:
            _CURRENT_CHILD = subprocess.Popen(
                argv,
                cwd=PROJECT_ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            state.update({"child_pid": _CURRENT_CHILD.pid, "child_pgid": _CURRENT_CHILD.pid})
            atomic_json(state_path, state)
            assert _CURRENT_CHILD.stdout is not None
            while True:
                chunk = _CURRENT_CHILD.stdout.read(8192)
                if not chunk:
                    break
                log.write(chunk)
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
            exit_code = _CURRENT_CHILD.wait()
        except Exception as exc:
            worker_error = f"{type(exc).__name__}: {exc}"
            message = f"\nworker exception: {type(exc).__name__}: {exc}\n".encode()
            log.write(message)
            sys.stdout.buffer.write(message)
            sys.stdout.buffer.flush()
        finally:
            end = f"\n=== {now_iso()} END exit_code={exit_code} ===\n".encode()
            log.write(end)
            sys.stdout.buffer.write(end)
            sys.stdout.buffer.flush()

    state = read_json(state_path)
    state.update(
        {
            "status": "completed" if exit_code == 0 else "failed",
            "exit_code": exit_code,
            "ended_at": now_iso(),
        }
    )
    if worker_error is not None:
        state["error"] = worker_error
    atomic_json(state_path, state)
    return exit_code


def cmd_self_test_worker() -> int:
    for index in range(1, 4):
        print(f"overnight self-test tick {index}/3", flush=True)
        time.sleep(0.5)
    print("overnight self-test PASS", flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor")
    sub.add_parser("list")

    start = sub.add_parser("start")
    start.add_argument("job")

    status = sub.add_parser("status")
    status.add_argument("job", nargs="?")

    logs = sub.add_parser("logs")
    logs.add_argument("job")
    logs.add_argument("--lines", type=int, default=80)

    stop = sub.add_parser("stop")
    stop.add_argument("job")

    worker = sub.add_parser("_worker")
    worker.add_argument("job")
    worker.add_argument("run_dir")

    sub.add_parser("_self-test-worker")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "doctor":
        return cmd_doctor()
    if args.command == "list":
        return cmd_list()
    if args.command == "start":
        return cmd_start(args.job)
    if args.command == "status":
        return cmd_status(args.job)
    if args.command == "logs":
        return cmd_logs(args.job, args.lines)
    if args.command == "stop":
        return cmd_stop(args.job)
    if args.command == "_worker":
        return cmd_worker(args.job, args.run_dir)
    if args.command == "_self-test-worker":
        return cmd_self_test_worker()
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
