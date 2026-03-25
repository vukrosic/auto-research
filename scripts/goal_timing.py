#!/usr/bin/env python3
"""Shared goal timing helpers.

Supports two timing models:
- absolute calendar deadlines via deadline_at/report_due_at
- training-window deadlines that start when the first experiment is dispatched
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


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


def format_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def int_or_none(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def goal_training_window_seconds(goal: dict) -> int | None:
    return int_or_none(goal.get("training_window_seconds"))


def goal_training_window_anchor(goal: dict) -> str:
    anchor = goal.get("training_window_anchor")
    return anchor if isinstance(anchor, str) and anchor else "goal_started_at"


def goal_training_anchor_time(goal: dict) -> datetime | None:
    anchor = goal_training_window_anchor(goal)
    if anchor == "first_dispatch":
        return parse_utc(goal.get("training_started_at"))
    if anchor == "goal_started_at":
        return parse_utc(goal.get("started_at"))
    return parse_utc(goal.get(anchor))


def goal_training_deadline(goal: dict) -> datetime | None:
    stored = parse_utc(goal.get("training_deadline_at"))
    if stored is not None:
        return stored
    window_seconds = goal_training_window_seconds(goal)
    if window_seconds is None:
        return None
    anchor_time = goal_training_anchor_time(goal)
    if anchor_time is None:
        return None
    return anchor_time + timedelta(seconds=window_seconds)


def goal_effective_deadline(goal: dict) -> datetime | None:
    deadlines = [dt for dt in (parse_utc(goal.get("deadline_at")), goal_training_deadline(goal)) if dt is not None]
    if not deadlines:
        return None
    return min(deadlines)


def goal_effective_report_due(goal: dict) -> datetime | None:
    deadlines = [dt for dt in (parse_utc(goal.get("report_due_at")), goal_effective_deadline(goal)) if dt is not None]
    if not deadlines:
        return None
    return min(deadlines)


def goal_remaining_dispatch_budget_seconds(goal: dict, now: datetime | None = None) -> int | None:
    now = now or datetime.now(timezone.utc)
    deadline = goal_effective_report_due(goal)
    if deadline is not None:
        return int((deadline - now).total_seconds())

    window_seconds = goal_training_window_seconds(goal)
    if window_seconds is not None and goal_training_window_anchor(goal) == "first_dispatch":
        if parse_utc(goal.get("training_started_at")) is None:
            return window_seconds
    return None


def start_training_window(goal: dict, started_at: str | None = None) -> tuple[dict, bool]:
    window_seconds = goal_training_window_seconds(goal)
    anchor = goal_training_window_anchor(goal)
    if window_seconds is None or anchor != "first_dispatch":
        return goal, False
    if parse_utc(goal.get("training_started_at")) is not None:
        return goal, False

    started = parse_utc(started_at) if started_at else None
    if started is None:
        started = datetime.now(timezone.utc)
    started_str = format_utc(started)
    deadline = started + timedelta(seconds=window_seconds)
    deadline_str = format_utc(deadline)

    goal["training_started_at"] = started_str
    goal["training_deadline_at"] = deadline_str
    if goal.get("report_due_policy") == "training_deadline" and not goal.get("report_due_at"):
        goal["report_due_at"] = deadline_str
    return goal, True


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    start = sub.add_parser("start")
    start.add_argument("goal_json")
    start.add_argument("started_at", nargs="?")

    deadline_epoch = sub.add_parser("deadline-epoch")
    deadline_epoch.add_argument("goal_json")

    deadline_iso = sub.add_parser("deadline-iso")
    deadline_iso.add_argument("goal_json")

    report_epoch = sub.add_parser("report-epoch")
    report_epoch.add_argument("goal_json")

    report_iso = sub.add_parser("report-iso")
    report_iso.add_argument("goal_json")

    args = parser.parse_args()
    goal_path = Path(getattr(args, "goal_json"))
    goal = load_json(goal_path)

    if args.cmd == "start":
        goal, changed = start_training_window(goal, args.started_at)
        if changed:
            write_json(goal_path, goal)
        print(goal.get("training_deadline_at") or "none")
        return

    if args.cmd == "deadline-epoch":
        deadline = goal_effective_deadline(goal)
        print(int(deadline.timestamp()) if deadline is not None else "none")
        return

    if args.cmd == "deadline-iso":
        print(format_utc(goal_effective_deadline(goal)) or "none")
        return

    if args.cmd == "report-epoch":
        due = goal_effective_report_due(goal)
        print(int(due.timestamp()) if due is not None else "none")
        return

    if args.cmd == "report-iso":
        print(format_utc(goal_effective_report_due(goal)) or "none")
        return


if __name__ == "__main__":
    main()
