#!/usr/bin/env python3
"""Run the autonomous lab loop for a goal until its deadline, then write a report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from goal_timing import goal_effective_report_due, utcnow


ROOT = Path(__file__).resolve().parents[1]
GOALS = ROOT / "goals"
EXPERIMENTS = ROOT / "experiments"
PYTHON = sys.executable


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def project_has_running_experiment(project: str) -> bool:
    snap_root = EXPERIMENTS / project / "snapshots"
    if not snap_root.exists():
        return False
    for snapshot in snap_root.iterdir():
        if not snapshot.is_dir():
            continue
        status_path = snapshot / "status"
        if status_path.exists() and status_path.read_text(encoding="utf-8").strip() == "running":
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("goal")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()

    goal_path = GOALS / args.goal / "goal.json"
    goal = load_json(goal_path)
    project = goal["project"]

    goal["watchdog_started_at"] = goal.get("watchdog_started_at") or utcnow()
    write_json(goal_path, goal)
    label = goal.get("report_due_at") or goal.get("deadline_at") or goal.get("training_deadline_at") or "pending first dispatch"
    print(f"[{utcnow()}] watchdog started for {args.goal} until {label}", flush=True)

    while True:
        goal = load_json(goal_path)
        report_due = goal_effective_report_due(goal)
        if report_due is not None and datetime.now(timezone.utc) >= report_due:
            break
        materialize = subprocess.run(
            [PYTHON, str(ROOT / "scripts" / "materialize_goal_queue.py"), args.goal, "--limit", "1"],
            cwd=str(ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
        message = (materialize.stdout or materialize.stderr or "no materialization output").strip()
        print(f"[{utcnow()}] materialize: {message}", flush=True)

        cycle = subprocess.run(
            [PYTHON, str(ROOT / "scripts" / "autonomous_lab.py"), "cycle"],
            cwd=str(ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
        message = (cycle.stdout or cycle.stderr or "no changes").strip()
        print(f"[{utcnow()}] cycle: {message}", flush=True)

        goal = load_json(goal_path)
        goal["last_cycle_at"] = utcnow()
        write_json(goal_path, goal)

        goal = load_json(goal_path)
        report_due = goal_effective_report_due(goal)
        if report_due is None:
            time.sleep(args.interval)
            continue
        remaining = (report_due - datetime.now(timezone.utc)).total_seconds()
        if remaining <= 0:
            break
        time.sleep(min(args.interval, max(1, int(remaining))))

    final_cycle = subprocess.run(
        [PYTHON, str(ROOT / "scripts" / "autonomous_lab.py"), "cycle"],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    print(f"[{utcnow()}] final cycle: {(final_cycle.stdout or final_cycle.stderr or 'no changes').strip()}", flush=True)
    report = subprocess.run(
        [PYTHON, str(ROOT / "scripts" / "generate_goal_report.py"), args.goal],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    print(f"[{utcnow()}] report: {(report.stdout or report.stderr or 'no report output').strip()}", flush=True)


if __name__ == "__main__":
    main()
