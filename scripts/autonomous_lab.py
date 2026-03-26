#!/usr/bin/env python3
"""Autonomous control loop for the markdown-defined research lab.

Multi-project aware: all operations are scoped to a project. The project
is resolved from experiment meta.json or passed explicitly.
"""

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

from goal_timing import goal_effective_deadline, goal_remaining_dispatch_budget_seconds


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "experiments"
STATE = ROOT / "state"
PROJECTS = ROOT / "projects"
GOALS = ROOT / "goals"
LOCK_FILE = ROOT / ".cycle.lock"


# ── Helpers ──────────────────────────────────────────────────────────────────


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


# ── Project helpers ──────────────────────────────────────────────────────────


def all_project_names() -> list[str]:
    """Return names of all configured projects."""
    return sorted([p.stem for p in PROJECTS.glob("*.json")])


def load_project(name: str) -> dict:
    """Load a project config by name."""
    path = PROJECTS / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"No project config: {path}")
    return load_json(path)


def project_enabled(name: str) -> bool:
    """Whether a project is enabled for automatic dispatch."""
    try:
        project = load_project(name)
    except FileNotFoundError:
        return False
    return bool(project.get("enabled", True))


def project_experiments_dir(project: str) -> Path:
    return EXPERIMENTS / project


def project_snapshots_dir(project: str) -> Path:
    return project_experiments_dir(project) / "snapshots"


def project_base_dir(project: str) -> Path:
    return project_experiments_dir(project) / "base"


def project_current_best_path(project: str) -> Path:
    return project_experiments_dir(project) / "current_best.json"


def project_base_id_path(project: str) -> Path:
    return project_experiments_dir(project) / "base_id.txt"


# ── Goal helpers ─────────────────────────────────────────────────────────────


def goal_dir(name: str) -> Path:
    return GOALS / name


def goal_config_path(name: str) -> Path:
    return goal_dir(name) / "goal.json"


def goal_queue_path(name: str) -> Path:
    return goal_dir(name) / "queue.json"


def all_goal_names() -> list[str]:
    return sorted([p.parent.name for p in GOALS.glob("*/goal.json")])


def load_goal(name: str) -> dict:
    path = goal_config_path(name)
    if not path.exists():
        raise FileNotFoundError(f"No goal config: {path}")
    goal = load_json(path)
    goal.setdefault("name", name)
    return goal


def goal_dispatch_priority(goal: dict) -> int:
    try:
        return int(goal.get("dispatch_priority", 0))
    except (TypeError, ValueError):
        return 0


def goal_started_at(goal: dict) -> str:
    started = goal.get("started_at")
    return started if isinstance(started, str) else ""


def goal_accepts_dispatch(goal: dict) -> bool:
    if goal.get("status", "active") != "active":
        return False
    deadline = goal_effective_deadline(goal)
    if deadline and goal.get("stop_dispatch_at_deadline", True):
        return datetime.now(timezone.utc) < deadline
    return True


def goal_deadline_tolerance(goal: dict) -> float:
    try:
        return float(goal.get("deadline_tolerance_ratio", 0.05))
    except (TypeError, ValueError):
        return 0.05


def goals_for_project(project: str) -> list[dict]:
    results: list[dict] = []
    for name in all_goal_names():
        try:
            goal = load_goal(name)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            continue
        if goal.get("project") != project:
            continue
        if not goal_queue_path(name).exists():
            continue
        results.append(goal)
    results.sort(key=lambda g: (-goal_dispatch_priority(g), goal_started_at(g), g.get("name", "")))
    return results


# ── Snapshot helpers ─────────────────────────────────────────────────────────


def snapshot_dirs(project: str) -> list[Path]:
    sdir = project_snapshots_dir(project)
    if not sdir.exists():
        return []
    return sorted([p for p in sdir.iterdir() if p.is_dir()])


def all_snapshot_dirs() -> list[tuple[str, Path]]:
    """Return (project, snapshot_path) for all projects."""
    results = []
    for proj in all_project_names():
        for snap in snapshot_dirs(proj):
            results.append((proj, snap))
    return results


def current_best(project: str) -> dict:
    return load_json(project_current_best_path(project))


def project_metric(project: str) -> str:
    """Return the primary metric name for a project."""
    try:
        proj = load_project(project)
        return proj.get("metric", "val_bpb")
    except FileNotFoundError:
        return "val_bpb"


def metric_key(project: str, best: dict, result: dict | None = None) -> str:
    """Determine which metric key to use for comparison.

    Prefers the project's secondary metric (e.g. val_bpb_quant) if both
    the baseline and the result have it, otherwise falls back to primary.
    """
    try:
        proj = load_project(project)
    except FileNotFoundError:
        proj = {}
    primary = proj.get("metric", "val_bpb")
    secondary = proj.get("secondary_metrics", [])

    # If there's a secondary metric and both sides have it, prefer it.
    # Skip placeholder/sentinel values used by no-quant fast lanes.
    for sm in secondary:
        sm_value = result.get(sm) if result else None
        if sm_value in (None, 8, 8.0, "8", "8.0"):
            continue
        if result and sm_value is not None and best.get(sm) is not None:
            return sm

    # Fall back to primary
    if best.get(primary) is not None:
        return primary

    # Legacy fallback
    if result and result.get("val_bpb_quant") is not None and best.get("val_bpb_quant") is not None:
        return "val_bpb_quant"
    return "val_bpb"


def current_base_id(project: str) -> str:
    bid_path = project_base_id_path(project)
    if bid_path.exists():
        value = bid_path.read_text(encoding="utf-8").strip()
        if value:
            return value
    best = current_best(project)
    base_id = f"base::{best.get('experiment_name', 'unknown')}::{best.get('promoted_at', 'unknown')}"
    write_text(bid_path, base_id + "\n")
    return base_id


def read_status(snapshot: Path) -> str:
    status_file = snapshot / "status"
    if not status_file.exists():
        return "missing"
    return status_file.read_text(encoding="utf-8").strip() or "missing"


def write_status(snapshot: Path, status: str) -> None:
    write_text(snapshot / "status", status + "\n")


def snapshot_project(snapshot: Path) -> str:
    """Resolve which project a snapshot belongs to, from meta.json or path."""
    meta_path = snapshot / "meta.json"
    if meta_path.exists():
        try:
            meta = load_json(meta_path)
            proj = meta.get("project")
            if proj:
                return proj
        except (json.JSONDecodeError, OSError):
            pass
    # Fallback: infer from directory structure (experiments/<project>/snapshots/<name>)
    try:
        return snapshot.parent.parent.name
    except Exception:
        return "unknown"


def snapshot_goal(snapshot: Path) -> str | None:
    meta_path = snapshot / "meta.json"
    if not meta_path.exists():
        return None
    try:
        meta = load_json(meta_path)
    except (json.JSONDecodeError, OSError):
        return None
    goal = meta.get("goal")
    return goal if isinstance(goal, str) and goal else None


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
        if not created[:4].isdigit():
            return "9999-12-31T23:59:59Z"
        return created
    except (json.JSONDecodeError, OSError):
        return "9999-12-31T23:59:59Z"


def snapshot_meta(snapshot: Path) -> dict:
    meta_path = snapshot / "meta.json"
    if not meta_path.exists():
        return {}
    try:
        return load_json(meta_path)
    except (json.JSONDecodeError, OSError):
        return {}


def snapshot_expected_duration(snapshot: Path) -> int | None:
    meta = snapshot_meta(snapshot)
    try:
        value = meta.get("expected_duration_seconds")
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def goal_dispatch_window_ok(snapshot: Path) -> tuple[bool, str | None]:
    goal_name = snapshot_goal(snapshot)
    if not goal_name:
        return True, None
    try:
        goal = load_goal(goal_name)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return True, None

    remaining = goal_remaining_dispatch_budget_seconds(goal)
    if remaining is None:
        return True, None

    expected = snapshot_expected_duration(snapshot)
    if expected is None or expected <= 0:
        return True, None

    tolerance = goal_deadline_tolerance(goal)
    required = int(expected * (1.0 + tolerance))
    if remaining >= required:
        return True, None
    return (
        False,
        f"deadline_blocked {snapshot.name}: remaining={remaining}s required={required}s "
        f"(expected={expected}s tolerance={tolerance:.0%})",
    )


def reconcile_goal_queue(goal_name: str) -> None:
    queue_path = goal_queue_path(goal_name)
    if not queue_path.exists():
        return

    goal = load_goal(goal_name)
    queue = load_json(queue_path)
    queue.setdefault("goal", goal_name)
    queue.setdefault("project", goal.get("project"))

    changed = False
    project = queue.get("project")
    for entry in queue.get("entries", []):
        name = entry.get("experiment")
        if not isinstance(name, str) or not name or not isinstance(project, str) or not project:
            continue

        snapshot = project_snapshots_dir(project) / name
        updates: dict[str, object] = {}
        if snapshot.exists():
            status = read_status(snapshot)
            updates["snapshot_status"] = status
            if status == "pending":
                updates["dispatch_state"] = "queued"
            elif status == "running":
                updates["dispatch_state"] = "running"
            elif status in {
                "done",
                "failed",
                "rejected",
                "stale_winner",
                "validated_winner",
                "promoted",
                "rollback_invalidated",
            }:
                updates["dispatch_state"] = "completed"
            meta_path = snapshot / "meta.json"
            result_path = snapshot / "result.json"
            if meta_path.exists():
                meta = load_json(meta_path)
                if meta.get("goal"):
                    updates["goal"] = meta.get("goal")
                updates["stage"] = meta.get("stage")
                updates["created_at"] = meta.get("created_at")
                updates["expected_duration_seconds"] = meta.get("expected_duration_seconds")
            if (snapshot / "dispatched_at").exists():
                updates["dispatched_at"] = (snapshot / "dispatched_at").read_text(encoding="utf-8").strip()
            preflight_path = snapshot / "preflight.json"
            if preflight_path.exists():
                preflight = load_json(preflight_path)
                updates["preflight"] = {
                    "status": preflight.get("status"),
                    "dispatch_ready": preflight.get("dispatch_ready"),
                    "checked_at": preflight.get("checked_at"),
                    "summary": preflight.get("summary"),
                    "effective_expected_duration_seconds": preflight.get("effective_expected_duration_seconds"),
                    "recommended_expected_duration_seconds": preflight.get("recommended_expected_duration_seconds"),
                }
            if result_path.exists():
                result = load_json(result_path)
                metric_name = project_metric(project)
                metric_value = result.get(metric_name)
                if metric_value is not None:
                    updates["metric"] = {"name": metric_name, "value": metric_value}
                updates["collected_at"] = result.get("collected_at")
                updates["duration_seconds"] = result.get("runtime_seconds") or result.get("duration_seconds")
                updates["runtime_source"] = result.get("runtime_source")
                updates["train_time_seconds"] = result.get("train_time_seconds")
                updates["estimate_error_pct"] = result.get("estimate_error_pct")
                updates["within_estimate_band_5pct"] = result.get("within_estimate_band_5pct")
        for key, value in updates.items():
            if entry.get(key) != value:
                entry[key] = value
                changed = True

    if changed:
        queue["updated_at"] = utcnow()
        write_json(queue_path, queue)


def reconcile_goal_queues() -> None:
    for goal_name in all_goal_names():
        reconcile_goal_queue(goal_name)


# ── Core operations ──────────────────────────────────────────────────────────


def check_running_experiments(project: str) -> list[str]:
    events: list[str] = []
    for snapshot in snapshot_dirs(project):
        if read_status(snapshot) != "running":
            continue
        name = snapshot.name
        proc = run(["bash", str(ROOT / "scripts" / "check_experiment.sh"), project, name], check=False)
        output = (proc.stdout or "").strip()
        first = output.splitlines()[0].strip() if output else ""
        if first == "done":
            run(["bash", str(ROOT / "scripts" / "collect_result.sh"), project, name], check=False)
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


def adjudicate_snapshot(project: str, snapshot: Path, best: dict, base_id: str) -> Decision:
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

    mkey = metric_key(project, best, result)
    value = result.get(mkey)
    if value is None:
        return Decision("failed", f"missing primary metric: {mkey}")

    baseline = float(meta["baseline_metric"])
    threshold = float(meta["promotion_threshold"])

    # Determine direction from project config
    try:
        proj = load_project(project)
        direction = proj.get("metric_direction", "lower")
    except FileNotFoundError:
        direction = "lower"

    if direction == "lower":
        beats = value < baseline - threshold
    else:
        beats = value > baseline + threshold

    if beats:
        if meta["parent_base"] == base_id:
            return Decision("validated_winner", f"{mkey} improved from {baseline:.4f} to {value:.4f} beyond threshold {threshold:.4f}", mkey, float(value), baseline, threshold)
        return Decision("stale_winner", f"{mkey} beat stale baseline; parent_base={meta['parent_base']} current_base={base_id}", mkey, float(value), baseline, threshold)
    return Decision("rejected", f"{mkey}={value:.4f} did not beat baseline {baseline:.4f} by threshold {threshold:.4f}", mkey, float(value), baseline, threshold)


def adjudicate_done_experiments(project: str) -> list[str]:
    events: list[str] = []
    best = current_best(project)
    base_id = current_base_id(project)
    for snapshot in snapshot_dirs(project):
        if read_status(snapshot) != "done":
            continue
        decision = adjudicate_snapshot(project, snapshot, best, base_id)
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


def promote_best_validated_winner(project: str) -> list[str]:
    winners: list[tuple[float, Path, dict, dict, str]] = []
    best = current_best(project)
    base_id = current_base_id(project)

    try:
        proj = load_project(project)
        direction = proj.get("metric_direction", "lower")
    except FileNotFoundError:
        direction = "lower"

    for snapshot in snapshot_dirs(project):
        if read_status(snapshot) != "validated_winner":
            continue
        meta_path = snapshot / "meta.json"
        result_path = snapshot / "result.json"
        if not meta_path.exists() or not result_path.exists():
            continue
        meta = load_json(meta_path)
        result = load_json(result_path)
        if meta.get("allow_promotion", True) is False:
            continue
        if meta.get("parent_base") != base_id:
            write_status(snapshot, "stale_winner")
            continue
        mkey = metric_key(project, best, result)
        value = result.get(mkey)
        if value is None:
            continue
        winners.append((float(value), snapshot, meta, result, mkey))

    if not winners:
        return []

    # Sort: best first (lowest for "lower", highest for "higher")
    winners.sort(key=lambda item: item[0], reverse=(direction == "higher"))

    value, snapshot, meta, result, mkey = winners[0]
    previous = current_best(project)
    old_base_id = current_base_id(project)
    base = project_base_dir(project)
    backup = project_experiments_dir(project) / f"base_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    if base.exists():
        shutil.move(str(base), str(backup))
    shutil.copytree(snapshot / "code", base)

    primary = project_metric(project)
    try:
        proj = load_project(project)
        secondary = proj.get("secondary_metrics", [])
    except FileNotFoundError:
        secondary = []

    new_best: dict = {
        "experiment_name": snapshot.name,
        "promoted_at": utcnow(),
        "hypothesis": meta.get("hypothesis", ""),
        "parent_base": meta.get("parent_base"),
        "promotion_metric": mkey,
        "stage_baselines": {},  # must recalibrate after promotion
    }
    # Add primary and secondary metrics
    new_best[primary] = result.get(primary)
    for sm in secondary:
        if result.get(sm) is not None:
            new_best[sm] = result.get(sm)

    write_json(project_current_best_path(project), new_best)
    new_base_id = f"base::{snapshot.name}::{new_best['promoted_at']}"
    write_text(project_base_id_path(project), new_base_id + "\n")
    write_status(snapshot, "promoted")

    promotion_record = {
        "promoted_at": new_best["promoted_at"],
        "previous_frontier": previous.get("experiment_name"),
        "previous_base_id": old_base_id,
        "new_base_id": new_base_id,
        "promotion_metric": mkey,
        "metric_value": value,
        "metric_delta": (
            (float(previous.get(mkey) or previous.get(primary) or 0.0) - value)
            if direction == "lower"
            else (value - float(previous.get(mkey) or previous.get(primary) or 0.0))
        ),
        "validation_basis": "validated_winner on current base",
    }
    write_json(snapshot / "promotion.json", promotion_record)
    return [f"promoted {snapshot.name} via {mkey}={value:.4f}"]


def busy_gpus() -> set[str]:
    """Return the set of GPU names that currently have a running experiment (any project)."""
    busy: set[str] = set()
    for _proj, snapshot in all_snapshot_dirs():
        if read_status(snapshot) != "running":
            continue
        gpu_file = snapshot / "gpu"
        if gpu_file.exists():
            busy.add(gpu_file.read_text(encoding="utf-8").strip())
    return busy


def all_gpu_names(project: str) -> list[str]:
    """Read GPU names from the project config."""
    try:
        proj = load_project(project)
        gpus = proj.get("gpus", [])
        if gpus:
            return gpus
    except FileNotFoundError:
        pass
    return ["novita-rtx3090"]


def pending_queue(project: str) -> list[Path]:
    """Return pending snapshots, preferring explicit goal queues when present."""
    pending = [s for s in snapshot_dirs(project) if read_status(s) == "pending"]
    if not pending:
        return []

    pending_by_name = {s.name: s for s in pending}
    ordered: list[Path] = []
    used: set[str] = set()
    goal_controls_project_queue = False

    for goal in goals_for_project(project):
        if not goal_accepts_dispatch(goal):
            continue
        queue_path = goal_queue_path(goal["name"])
        try:
            queue = load_json(queue_path)
        except (json.JSONDecodeError, OSError):
            continue
        for entry in queue.get("entries", []):
            name = entry.get("experiment")
            dispatch_state = str(entry.get("dispatch_state") or entry.get("state") or "queued")
            if dispatch_state in {"queued", "pending", "ready", "retry", "running"}:
                goal_controls_project_queue = True
            if dispatch_state not in {"queued", "pending", "ready", "retry"}:
                continue
            if not isinstance(name, str) or name in used:
                continue
            snapshot = pending_by_name.get(name)
            if snapshot is None:
                continue
            ordered.append(snapshot)
            used.add(name)

    if goal_controls_project_queue:
        return ordered

    leftovers = [s for s in pending if s.name not in used]
    leftovers.sort(key=snapshot_created_at)
    return ordered + leftovers


def dispatch_pending(project: str) -> list[str]:
    available = set(all_gpu_names(project)) - busy_gpus()
    if not available:
        return []
    queue = pending_queue(project)
    if not queue:
        return []
    events: list[str] = []
    for snapshot in queue:
        if not available:
            break
        allowed, reason = goal_dispatch_window_ok(snapshot)
        if not allowed:
            events.append(reason or f"deadline_blocked {snapshot.name}")
            if snapshot_goal(snapshot):
                break
            continue
        gpu = sorted(available)[0]
        proc = run(["bash", str(ROOT / "scripts" / "dispatch.sh"), project, snapshot.name, gpu], check=False)
        if proc.returncode == 0:
            events.append(f"dispatched {snapshot.name} → {gpu}")
            available.discard(gpu)
        else:
            events.append(f"dispatch_failed {snapshot.name}: {(proc.stderr or proc.stdout).strip()}")
            if snapshot_goal(snapshot):
                break
    return events


def reconcile_state() -> None:
    """Regenerate state files from all projects."""
    STATE.mkdir(exist_ok=True)
    reconcile_goal_queues()

    all_frontiers = []
    all_running = []
    all_pending = []
    all_done = []

    for proj_name in all_project_names():
        pedir = project_experiments_dir(proj_name)
        if not pedir.exists():
            continue

        best = current_best(proj_name)
        mkey = metric_key(proj_name, best)
        best_value = best.get(mkey)
        all_frontiers.append(
            f"### {proj_name}\n"
            f"- Experiment: `{best.get('experiment_name', 'unknown')}`\n"
            f"- Metric: `{mkey}`\n"
            f"- Value: `{best_value}`\n"
            f"- Promoted at: `{best.get('promoted_at', 'unknown')}`\n"
            f"- Reason: {best.get('hypothesis', 'not recorded')}\n"
        )

        for snapshot in snapshot_dirs(proj_name):
            status = read_status(snapshot)
            if status == "running":
                line = f"- `{snapshot.name}` (project: {proj_name})"
                meta_path = snapshot / "meta.json"
                if meta_path.exists():
                    meta = load_json(meta_path)
                    stage = meta.get("stage", "unknown")
                    goal = meta.get("goal")
                    gpu = (snapshot / "gpu").read_text(encoding="utf-8").strip() if (snapshot / "gpu").exists() else "unassigned"
                    if goal:
                        line = f"- `{snapshot.name}` — project `{proj_name}`, goal `{goal}`, stage `{stage}`, gpu `{gpu}`"
                    else:
                        line = f"- `{snapshot.name}` — project `{proj_name}`, stage `{stage}`, gpu `{gpu}`"
                all_running.append(line)
            elif status == "done":
                line = f"- `{snapshot.name}` (project: {proj_name})"
                result_path = snapshot / "result.json"
                if result_path.exists():
                    result = load_json(result_path)
                    pm = project_metric(proj_name)
                    value = result.get(pm)
                    if value is not None:
                        line += f" — {pm}=`{value}`"
                all_done.append(line)

        queue = pending_queue(proj_name)
        for i, snapshot in enumerate(queue, 1):
            line = f"{i}. `{snapshot.name}` (project: {proj_name})"
            meta_path = snapshot / "meta.json"
            if meta_path.exists():
                meta = load_json(meta_path)
                stage = meta.get("stage", "unknown")
                created = meta.get("created_at", "unknown")
                goal = meta.get("goal")
                if goal:
                    line = f"{i}. `{snapshot.name}` — project `{proj_name}`, goal `{goal}`, stage `{stage}`, created `{created}`"
                else:
                    line = f"{i}. `{snapshot.name}` — project `{proj_name}`, stage `{stage}`, created `{created}`"
            preflight_path = snapshot / "preflight.json"
            if preflight_path.exists():
                try:
                    preflight = load_json(preflight_path)
                    if preflight.get("dispatch_ready") is False:
                        line += f", preflight `blocked`: {preflight.get('summary')}"
                except (json.JSONDecodeError, OSError):
                    pass
            all_pending.append(line)

    frontier = "\n".join(
        [
            "# Frontier",
            "",
            "> **Derived view.** Canonical frontier records are `experiments/<project>/current_best.json`. Regenerate at session open.",
            "",
            "## Current Best",
            "",
        ] + all_frontiers
    )
    write_text(STATE / "FRONTIER.md", frontier + "\n")

    running_lines = [
        "# Active Runs", "",
        "> **Derived view.** Canonical run status lives in `experiments/<project>/snapshots/*/status`.", "",
        "## Running", "",
    ]
    running_lines.extend(all_running or ["None recorded yet."])
    running_lines.extend(["", "## Pending Queue (ordered by created_at)", ""])
    running_lines.extend(all_pending or ["(empty)"])
    write_text(STATE / "ACTIVE_RUNS.md", "\n".join(running_lines).rstrip() + "\n")

    queue_lines = [
        "# Adjudication Queue", "",
        "> **Derived view.** All experiments with `status=done`.", "",
        "## Ready For Review", "",
    ]
    queue_lines.extend(all_done or ["None recorded yet.", ""])
    write_text(STATE / "ADJUDICATION_QUEUE.md", "\n".join(queue_lines).rstrip() + "\n")


# ── Cycle ────────────────────────────────────────────────────────────────────


def _cycle_unlocked() -> list[str]:
    events: list[str] = []
    for proj_name in all_project_names():
        pedir = project_experiments_dir(proj_name)
        if not pedir.exists():
            continue
        events.extend(check_running_experiments(proj_name))
        events.extend(adjudicate_done_experiments(proj_name))
        events.extend(promote_best_validated_winner(proj_name))
        if project_enabled(proj_name):
            events.extend(dispatch_pending(proj_name))
    reconcile_goal_queues()
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
