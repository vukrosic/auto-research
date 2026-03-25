#!/usr/bin/env python3
"""
Live GPU progress monitor.

Shows, per GPU:
- utilization / memory / temperature
- active training PID
- experiment name from run_experiment.sh ancestry
- latest parsed step/max_step
- latest val_bpb if available

Usage:
    python3 infra/gpu_progress_monitor.py
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"


@dataclass
class GPUProcess:
    gpu_index: int
    pid: int
    used_mem_mb: int


@dataclass
class GPUStat:
    index: int
    name: str
    utilization: int
    memory_used: int
    memory_total: int
    temperature: int


@dataclass
class ExperimentStatus:
    name: str
    max_steps: int
    step: int
    last_bpb: float | None
    log_path: Path | None


def run_cmd(args: list[str], timeout: int = 5) -> str:
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=True)
    return result.stdout


def get_gpu_stats() -> list[GPUStat]:
    out = run_cmd(
        [
            "nvidia-smi",
            "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu",
            "--format=csv,noheader,nounits",
        ]
    )
    stats: list[GPUStat] = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 6:
            continue
        stats.append(
            GPUStat(
                index=int(parts[0]),
                name=parts[1],
                utilization=int(parts[2]),
                memory_used=int(parts[3]),
                memory_total=int(parts[4]),
                temperature=int(parts[5]),
            )
        )
    return stats


def get_gpu_processes() -> dict[int, GPUProcess]:
    out = run_cmd(
        [
            "nvidia-smi",
            "--query-compute-apps=gpu_uuid,gpu_name,pid,used_memory",
            "--format=csv,noheader,nounits",
        ]
    )
    uuid_to_index = {}
    uuid_out = run_cmd(
        [
            "nvidia-smi",
            "--query-gpu=index,uuid",
            "--format=csv,noheader,nounits",
        ]
    )
    for line in uuid_out.strip().splitlines():
        idx, uuid = [x.strip() for x in line.split(",", 1)]
        uuid_to_index[uuid] = int(idx)

    procs: dict[int, GPUProcess] = {}
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            continue
        uuid, _gpu_name, pid, used_mem = parts
        if uuid not in uuid_to_index:
            continue
        gpu_index = uuid_to_index[uuid]
        procs[gpu_index] = GPUProcess(gpu_index=gpu_index, pid=int(pid), used_mem_mb=int(used_mem))
    return procs


def get_ps_table() -> dict[int, tuple[int, str]]:
    out = run_cmd(["ps", "-eo", "pid=,ppid=,args="], timeout=5)
    table: dict[int, tuple[int, str]] = {}
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"(\d+)\s+(\d+)\s+(.*)", line)
        if not m:
            continue
        table[int(m.group(1))] = (int(m.group(2)), m.group(3))
    return table


def experiment_name_from_pid(pid: int, ps_table: dict[int, tuple[int, str]]) -> str | None:
    current = pid
    while current in ps_table:
        ppid, args = ps_table[current]
        m = re.search(r"run_experiment\.sh\s+(\S+)\s+(\d+)", args)
        if m:
            return m.group(1)
        if ppid == 0 or ppid == current:
            break
        current = ppid
    return None


def parse_experiment_status(name: str) -> ExperimentStatus:
    candidates = [
        LOGS_DIR / f"{name}_parallel.log",
        LOGS_DIR / f"{name}.txt",
        ROOT / "results" / name / "train.log",
    ]
    log_path = next((p for p in candidates if p.exists()), None)
    if log_path is None:
        return ExperimentStatus(name=name, max_steps=0, step=0, last_bpb=None, log_path=None)

    step = 0
    max_steps = 0
    last_bpb = None
    with log_path.open() as f:
        for line in f:
            m = re.search(r"step:(\d+)/(\d+)", line)
            if m:
                step = int(m.group(1))
                max_steps = int(m.group(2))
            m = re.search(r"step:(\d+)/(\d+)\s+val_loss:[\d.]+\s+val_bpb:([\d.]+)", line)
            if m:
                last_bpb = float(m.group(3))

    return ExperimentStatus(
        name=name,
        max_steps=max_steps,
        step=step,
        last_bpb=last_bpb,
        log_path=log_path,
    )


def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def render(interval: int) -> None:
    stats = get_gpu_stats()
    gpu_procs = get_gpu_processes()
    ps_table = get_ps_table()

    clear_screen()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"GPU Progress Monitor  {now}")
    print(f"Refresh: {interval}s")
    print()
    print(
        f"{'GPU':<4} {'Util':>5} {'Mem':>13} {'Temp':>5} {'PID':>7} "
        f"{'Experiment':<32} {'Step':>11} {'Val BPB':>8}"
    )
    print("-" * 96)

    for gpu in stats:
        proc = gpu_procs.get(gpu.index)
        exp_name = "-"
        step_text = "-"
        bpb_text = "-"
        pid_text = "-"

        if proc:
            pid_text = str(proc.pid)
            exp_name = experiment_name_from_pid(proc.pid, ps_table) or "<unknown>"
            status = parse_experiment_status(exp_name) if exp_name != "<unknown>" else None
            if status and status.max_steps:
                step_text = f"{status.step}/{status.max_steps}"
                if status.last_bpb is not None:
                    bpb_text = f"{status.last_bpb:.4f}"

        mem_text = f"{gpu.memory_used:5d}/{gpu.memory_total:5d}"
        print(
            f"{gpu.index:<4} {gpu.utilization:>4}% {mem_text:>13} {gpu.temperature:>4}C {pid_text:>7} "
            f"{exp_name[:32]:<32} {step_text:>11} {bpb_text:>8}"
        )

    print()
    print("Ctrl+C to stop.")


def main() -> None:
    interval = 5
    if len(sys.argv) > 1:
        interval = int(sys.argv[1])

    try:
        run_cmd(["nvidia-smi", "--version"])
    except Exception:
        print("nvidia-smi not available")
        sys.exit(1)

    signal.signal(signal.SIGINT, lambda _sig, _frame: sys.exit(0))

    while True:
        try:
            render(interval)
        except Exception as exc:
            clear_screen()
            print(f"Monitor error: {exc}")
        time.sleep(interval)


if __name__ == "__main__":
    main()
