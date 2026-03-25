#!/usr/bin/env python3
"""Autonomous control loop for the markdown-defined research lab."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "experiments"
SNAPSHOTS = EXPERIMENTS / "snapshots"
BASE = EXPERIMENTS / "base"
CURRENT_BEST = EXPERIMENTS / "current_best.json"
BASE_ID_FILE = EXPERIMENTS / "base_id.txt"
STATE = ROOT / "state"
PROJECTS = ROOT / "projects"
LOCK_FILE = ROOT / ".cycle.lock"


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def snapshot_dirs() -> list[Path]:
    if not SNAPSHOTS.exists():
        return []
    return sorted([p for p in SNAPSHOTS.iterdir() if p.is_dir()])


def current_best() -> dict:
    return load_json(CURRENT_BEST)


def metric_key(best: dict, result: dict | None = None) -> str:
    if result and result.get("val_bpb_quant") is not None and best.get("val_bpb_quant") is not None:
        return "val_bpb_quant"
    if best.get("val_bpb_quant") is not None and (result is None or result.get("val_bpb_quant") is not None):
        return "val_bpb_quant"
    return "val_bpb"


def current_base_id() -> str:
    if BASE_ID_FILE.exists():
        value = BASE_ID_FILE.read_text(encoding="utf-8").strip()
        if value:
            return value
    best = current_best()
    base_id = f"base::{best.get('experiment_name', 'unknown')}::{best.get('promoted_at', 'unknown')}"
    write_text(BASE_ID_FILE, base_id + "\n")
    return base_id


def primary_project_name() -> str:
    project_files = sorted(PROJECTS.glob("*.json"))
    if not project_files:
        return "unknown"
    return load_json(project_files[0]).get("name", project_files[0].stem)


def read_status(snapshot: Path) -> str:
    status_file = snapshot / "status"
    if not status_file.exists():
        return "missing"
    return status_file.read_text(encoding="utf-8").strip() or "missing"


def write_status(snapshot: Path, status: str) -> None:
    write_text(snapshot / "status", status + "\n")


def check_running_experiments() -> list[str]:
    events: list[str] = []
    for snapshot in snapshot_dirs():
        if read_status(snapshot) != "running":
            continue
        name = snapshot.name
        proc = run(["bash", str(ROOT / "scripts" / "check_experiment.sh"), name], check=False)
        output = (proc.stdout or "").strip()
        first = output.splitlines()[0].strip() if output else ""
        if first == "done":
            run(["bash", str(ROOT / "scripts" / "collect_result.sh"), name], check=False)
            events.append(f"collected {name}")
        elif first == "failed":
            write_status(snapshot, "failed")
            failure = {"failure_mode": "remote_run_failed", "checked_at": utcnow(), "check_output": output}
            write_json(snapshot / "result.json", failure)
            events.append(f"failed {name}")
    return events


@dataclass
class Decision:
    status: str
    reason: str
    metric_key: str | None = None
    metric_value: float | None = None
    baseline: float | None = None
    threshold: float | None = None


def adjudicate_snapshot(snapshot: Path, best: dict, base_id: str) -> Decision:
    meta_path = snapshot / "meta.json"
    result_path = snapshot / "result.json"
    if not meta_path.exists():
        return Decision("failed", "missing meta.json")
    if not result_path.exists():
        return Decision("failed", "missing result.json")

    meta = load_json(meta_path)
    result = load_json(result_path)
    for field in ("name", "hypothesis", "parent_base", "stage", "steps", "baseline_metric", "promotion_threshold"):
        if meta.get(field) in (None, ""):
            return Decision("failed", f"missing required meta field: {field}")

    mkey = metric_key(best, result)
    value = result.get(mkey)
    if value is None:
        return Decision("failed", f"missing primary metric: {mkey}")

    baseline = float(meta["baseline_metric"])
    threshold = float(meta["promotion_threshold"])
    if value < baseline - threshold:
        if meta["parent_base"] == base_id:
            return Decision("validated_winner", f"{mkey} improved from {baseline:.4f} to {value:.4f} beyond threshold {threshold:.4f}", mkey, float(value), baseline, threshold)
        return Decision("stale_winner", f"{mkey} beat stale baseline; parent_base={meta['parent_base']} current_base={base_id}", mkey, float(value), baseline, threshold)
    return Decision("rejected", f"{mkey}={value:.4f} did not beat baseline {baseline:.4f} by threshold {threshold:.4f}", mkey, float(value), baseline, threshold)


def adjudicate_done_experiments() -> list[str]:
    events: list[str] = []
    best = current_best()
    base_id = current_base_id()
    for snapshot in snapshot_dirs():
        if read_status(snapshot) != "done":
            continue
        decision = adjudicate_snapshot(snapshot, best, base_id)
        write_status(snapshot, decision.status)
        result = load_json(snapshot / "result.json") if (snapshot / "result.json").exists() else {}
        result["adjudicated_at"] = utcnow()
        result["decision"] = decision.status
        result["decision_reason"] = decision.reason
        if decision.metric_key:
            result["decision_metric"] = decision.metric_key
            result["decision_metric_value"] = decision.metric_value
            result["decision_baseline"] = decision.baseline
            result["decision_threshold"] = decision.threshold
        write_json(snapshot / "result.json", result)
        events.append(f"{decision.status} {snapshot.name}")
    return events


def promote_best_validated_winner() -> list[str]:
    winners: list[tuple[float, Path, dict, dict, str]] = []
    best = current_best()
    base_id = current_base_id()
    for snapshot in snapshot_dirs():
        if read_status(snapshot) != "validated_winner":
            continue
        meta_path = snapshot / "meta.json"
        result_path = snapshot / "result.json"
        if not meta_path.exists() or not result_path.exists():
            continue
        meta = load_json(meta_path)
        result = load_json(result_path)
        if meta.get("parent_base") != base_id:
            write_status(snapshot, "stale_winner")
            continue
        mkey = metric_key(best, result)
        value = result.get(mkey)
        if value is None:
            continue
        winners.append((float(value), snapshot, meta, result, mkey))

    if not winners:
        return []

    winners.sort(key=lambda item: item[0])
    value, snapshot, meta, result, mkey = winners[0]
    previous = current_best()
    old_base_id = current_base_id()
    backup = EXPERIMENTS / f"base_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    if BASE.exists():
        shutil.move(str(BASE), str(backup))
    shutil.copytree(snapshot / "code", BASE)

    new_best = {
        "experiment_name": snapshot.name,
        "val_bpb": result.get("val_bpb"),
        "val_bpb_quant": result.get("val_bpb_quant"),
        "promoted_at": utcnow(),
        "hypothesis": meta.get("hypothesis", ""),
        "parent_base": meta.get("parent_base"),
        "promotion_metric": mkey,
        "stage_baselines": {},  # must recalibrate after promotion
    }
    write_json(CURRENT_BEST, new_best)
    new_base_id = f"base::{snapshot.name}::{new_best['promoted_at']}"
    write_text(BASE_ID_FILE, new_base_id + "\n")
    write_status(snapshot, "promoted")

    promotion_record = {
        "promoted_at": new_best["promoted_at"],
        "previous_frontier": previous.get("experiment_name"),
        "previous_base_id": old_base_id,
        "new_base_id": new_base_id,
        "promotion_metric": mkey,
        "metric_value": value,
        "metric_delta": float(previous.get(mkey) or previous.get("val_bpb") or 0.0) - value,
        "validation_basis": "validated_winner on current base",
    }
    write_json(snapshot / "promotion.json", promotion_record)
    return [f"promoted {snapshot.name} via {mkey}={value:.4f}"]


def busy_gpus() -> set[str]:
    """Return the set of GPU names that currently have a running experiment."""
    busy: set[str] = set()
    for snapshot in snapshot_dirs():
        if read_status(snapshot) != "running":
            continue
        gpu_file = snapshot / "gpu"
        if gpu_file.exists():
            busy.add(gpu_file.read_text(encoding="utf-8").strip())
    return busy


def all_gpu_names() -> list[str]:
    """Read GPU names from the project config, falling back to a hardcoded default."""
    project_files = sorted(PROJECTS.glob("*.json"))
    if project_files:
        project = load_json(project_files[0])
        gpus = project.get("gpus", [])
        if gpus:
            return gpus
    return ["novita-rtx3090"]


def snapshot_created_at(snapshot: Path) -> str:
    """Return created_at from meta.json, or a fallback that sorts last."""
    meta_path = snapshot / "meta.json"
    if not meta_path.exists():
        return "9999-12-31T23:59:59Z"
    try:
        meta = load_json(meta_path)
        created = meta.get("created_at", "")
        if not created or not isinstance(created, str):
            return "9999-12-31T23:59:59Z"
        # Basic sanity: must start with a year
        if not created[:4].isdigit():
            return "9999-12-31T23:59:59Z"
        return created
    except (json.JSONDecodeError, OSError):
        return "9999-12-31T23:59:59Z"


def pending_queue() -> list[Path]:
    """Return pending snapshots ordered by created_at (oldest first)."""
    pending = [s for s in snapshot_dirs() if read_status(s) == "pending"]
    pending.sort(key=snapshot_created_at)
    return pending


def dispatch_pending() -> list[str]:
    available = set(all_gpu_names()) - busy_gpus()
    if not available:
        return []
    queue = pending_queue()
    if not queue:
        return []
    events: list[str] = []
    for snapshot in queue:
        if not available:
            break
        gpu = sorted(available)[0]
        proc = run(["bash", str(ROOT / "scripts" / "dispatch.sh"), snapshot.name, gpu], check=False)
        if proc.returncode == 0:
            events.append(f"dispatched {snapshot.name} → {gpu}")
            available.discard(gpu)
        else:
            events.append(f"dispatch_failed {snapshot.name}: {(proc.stderr or proc.stdout).strip()}")
    return events


def reconcile_state() -> None:
    STATE.mkdir(exist_ok=True)
    best = current_best()
    mkey = metric_key(best)
    best_value = best.get(mkey)
    frontier = "\n".join(
        [
            "# Frontier",
            "",
            "> **Derived view.** Canonical frontier record is `experiments/current_best.json`. Regenerate this file from that record at session open.",
            "",
            "## Current Best",
            "",
            f"- Project: `{primary_project_name()}`",
            f"- Experiment: `{best.get('experiment_name', 'unknown')}`",
            f"- Metric: `{mkey}`",
            f"- Value: `{best_value}`",
            f"- Promoted at: `{best.get('promoted_at', 'unknown')}`",
            f"- Reason believed best: {best.get('hypothesis', 'not recorded')}",
            "",
        ]
    )
    write_text(STATE / "FRONTIER.md", frontier + "\n")

    running_lines = ["# Active Runs", "", "> **Derived view.** Canonical run status lives in `experiments/snapshots/*/status`. Regenerate this file from snapshot records at session open.", "", "## Running", ""]
    running = []
    for snapshot in snapshot_dirs():
        if read_status(snapshot) != "running":
            continue
        line = f"- `{snapshot.name}`"
        meta_path = snapshot / "meta.json"
        if meta_path.exists():
            meta = load_json(meta_path)
            stage = meta.get("stage", "unknown")
            gpu = (snapshot / "gpu").read_text(encoding="utf-8").strip() if (snapshot / "gpu").exists() else "unassigned"
            line = f"- `{snapshot.name}` — stage `{stage}`, gpu `{gpu}`"
        running.append(line)
    running_lines.extend(running or ["None recorded yet."])
    # Show pending queue in created_at order
    queue = pending_queue()
    running_lines.extend(["", "## Pending Queue (ordered by created_at)", ""])
    pending_items = []
    for i, snapshot in enumerate(queue, 1):
        line = f"{i}. `{snapshot.name}`"
        meta_path = snapshot / "meta.json"
        if meta_path.exists():
            meta = load_json(meta_path)
            stage = meta.get("stage", "unknown")
            created = meta.get("created_at", "unknown")
            line = f"{i}. `{snapshot.name}` — stage `{stage}`, created `{created}`"
        pending_items.append(line)
    running_lines.extend(pending_items or ["(empty)"])
    write_text(STATE / "ACTIVE_RUNS.md", "\n".join(running_lines).rstrip() + "\n")

    queue_lines = ["# Adjudication Queue", "", "> **Derived view.** This queue is all experiments with `status=done` in their snapshot records. Regenerate at session open.", "", "## Ready For Review", ""]
    done_items = []
    for snapshot in snapshot_dirs():
        if read_status(snapshot) != "done":
            continue
        line = f"- `{snapshot.name}`"
        result_path = snapshot / "result.json"
        if result_path.exists():
            result = load_json(result_path)
            value = result.get("val_bpb_quant")
            if value is None:
                value = result.get("val_bpb")
            if value is not None:
                line += f" — result `{value}`"
        done_items.append(line)
    queue_lines.extend(done_items or ["None recorded yet.", ""])
    write_text(STATE / "ADJUDICATION_QUEUE.md", "\n".join(queue_lines).rstrip() + "\n")


def _cycle_unlocked() -> list[str]:
    events: list[str] = []
    events.extend(check_running_experiments())
    events.extend(adjudicate_done_experiments())
    events.extend(promote_best_validated_winner())
    events.extend(dispatch_pending())
    reconcile_state()
    return events


def cycle() -> list[str]:
    """Run one cycle with an exclusive file lock to prevent concurrent dispatchers."""
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("Another cycle is already running (lock held). Skipping.", file=sys.stderr)
        lock_fd.close()
        return []
    try:
        return _cycle_unlocked()
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


def loop_forever(interval: int) -> None:
    while True:
        events = cycle()
        stamp = utcnow()
        summary = ", ".join(events) if events else "no changes"
        print(f"[{stamp}] {summary}", flush=True)
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["cycle", "reconcile", "loop"])
    parser.add_argument("--interval", type=int, default=300, help="Loop sleep interval in seconds")
    args = parser.parse_args()

    if args.command == "reconcile":
        reconcile_state()
        return
    if args.command == "cycle":
        events = cycle()
        print("\n".join(events) if events else "no changes")
        return
    loop_forever(args.interval)


if __name__ == "__main__":
    main()
