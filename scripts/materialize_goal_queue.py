#!/usr/bin/env python3
"""Create queued goal experiments on demand from goal queue specs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOALS = ROOT / "goals"
EXPERIMENTS = ROOT / "experiments"
NEW_EXPERIMENT = ROOT / "scripts" / "new_experiment.sh"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def utcnow() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def snapshot_dir(project: str, name: str) -> Path:
    return EXPERIMENTS / project / "snapshots" / name


def resolve_entry_baseline(entry: dict, project: str) -> float | None:
    if entry.get("baseline_metric") is not None:
        try:
            return float(entry["baseline_metric"])
        except (TypeError, ValueError):
            return None

    source_name = entry.get("baseline_source_experiment")
    if not isinstance(source_name, str) or not source_name:
        return None

    result_path = snapshot_dir(project, source_name) / "result.json"
    if not result_path.exists():
        return None

    result = load_json(result_path)
    for key in ("decision_metric_value", "val_bpb", "avg_loss_last_30_mean"):
        value = result.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def update_meta(goal_name: str, project: str, name: str, entry: dict) -> bool:
    meta_path = snapshot_dir(project, name) / "meta.json"
    if not meta_path.exists():
        return False
    meta = load_json(meta_path)
    meta["goal"] = goal_name
    meta["project"] = project
    meta["owner"] = "goal_queue"

    baseline_metric = resolve_entry_baseline(entry, project)
    if baseline_metric is not None:
        meta["baseline_metric"] = baseline_metric

    for field in (
        "hypothesis",
        "stage",
        "steps",
        "promotion_threshold",
        "expected_duration_seconds",
        "changes_summary",
        "allow_promotion",
    ):
        if entry.get(field) is not None:
            meta[field] = entry[field]

    if entry.get("env_overrides") is not None:
        meta["env_overrides"] = entry["env_overrides"]

    write_json(meta_path, meta)
    return True


def materialize(goal_name: str, limit: int) -> list[str]:
    goal_path = GOALS / goal_name / "goal.json"
    queue_path = GOALS / goal_name / "queue.json"
    if not goal_path.exists():
        raise FileNotFoundError(f"Missing goal config: {goal_path}")
    if not queue_path.exists():
        raise FileNotFoundError(f"Missing goal queue: {queue_path}")

    goal = load_json(goal_path)
    queue = load_json(queue_path)
    project = goal["project"]
    created: list[str] = []
    changed = False

    for entry in queue.get("entries", []):
        state = str(entry.get("dispatch_state") or entry.get("state") or "queued")
        name = entry.get("experiment")
        if state not in {"queued", "pending", "ready", "retry"}:
            continue
        if not isinstance(name, str) or not name:
            continue
        if entry.get("baseline_metric") is None and entry.get("baseline_source_experiment"):
            if resolve_entry_baseline(entry, project) is None:
                continue
        snap = snapshot_dir(project, name)
        if snap.exists():
            update_meta(goal_name, project, name, entry)
            continue

        env = os.environ.copy()
        env["AUTORESEARCH_GOAL"] = goal_name
        subprocess.run(
            ["bash", str(NEW_EXPERIMENT), project, name],
            cwd=str(ROOT),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        update_meta(goal_name, project, name, entry)
        entry["materialized_at"] = utcnow()
        created.append(name)
        changed = True
        if len(created) >= limit:
            break

    if changed:
        queue["updated_at"] = utcnow()
        write_json(queue_path, queue)

    return created


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("goal")
    parser.add_argument("--limit", type=int, default=1, help="Number of missing queued experiments to create")
    args = parser.parse_args()

    created = materialize(args.goal, args.limit)
    if created:
        print("\n".join(created))
    else:
        print("no changes")


if __name__ == "__main__":
    main()
