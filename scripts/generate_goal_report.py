#!/usr/bin/env python3
"""Generate a deadline report for a goal-scoped research sprint."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from goal_timing import goal_effective_deadline, goal_effective_report_due


ROOT = Path(__file__).resolve().parents[1]
GOALS = ROOT / "goals"
EXPERIMENTS = ROOT / "experiments"
PROJECTS = ROOT / "projects"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fmt_delta(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.4f}"


def fmt_seconds(value: object) -> str:
    if value in (None, ""):
        return "—"
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return "—"
    minutes, rem = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{rem:02d}s"
    if minutes:
        return f"{minutes}m{rem:02d}s"
    return f"{rem}s"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("goal")
    args = parser.parse_args()

    goal_dir = GOALS / args.goal
    goal_path = goal_dir / "goal.json"
    queue_path = goal_dir / "queue.json"
    goal = load_json(goal_path)
    queue = load_json(queue_path)
    project = load_json(PROJECTS / f"{goal['project']}.json")
    metric_name = project.get("metric", "val_bpb")
    direction = project.get("metric_direction", "lower")

    report_rel = goal.get("report_path") or f"goals/{args.goal}/reports/{utcnow().replace(':', '-')}_report.md"
    report_path = ROOT / report_rel
    report_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    completed_candidates: list[dict] = []
    failure_count = 0

    for entry in queue.get("entries", []):
        name = entry["experiment"]
        snap = EXPERIMENTS / goal["project"] / "snapshots" / name
        meta = load_json(snap / "meta.json") if (snap / "meta.json").exists() else {}
        result = load_json(snap / "result.json") if (snap / "result.json").exists() else {}
        status = (snap / "status").read_text(encoding="utf-8").strip() if (snap / "status").exists() else "not_materialized"
        metric_value = result.get(metric_name)
        baseline = meta.get("baseline_metric", entry.get("baseline_metric"))
        improvement = None
        if metric_value is not None and baseline is not None:
            baseline = float(baseline)
            metric_value = float(metric_value)
            improvement = (baseline - metric_value) if direction == "lower" else (metric_value - baseline)

        row = {
            "name": name,
            "status": status,
            "metric_value": metric_value,
            "baseline": baseline,
            "improvement": improvement,
            "actual_runtime_seconds": result.get("runtime_seconds") or result.get("duration_seconds"),
            "runtime_source": result.get("runtime_source"),
            "predicted_runtime_seconds": result.get("expected_duration_seconds") or meta.get("expected_duration_seconds") or entry.get("expected_duration_seconds"),
            "estimate_error_pct": result.get("estimate_error_pct"),
            "role": entry.get("role", ""),
            "reason": entry.get("reason", ""),
        }
        rows.append(row)

        if status in {"failed"}:
            failure_count += 1
        if status in {"done", "rejected", "validated_winner", "stale_winner", "promoted"} and row["role"] == "candidate" and improvement is not None:
            completed_candidates.append(row)

    completed_candidates.sort(key=lambda r: (r["improvement"] is None, -(r["improvement"] or -1e9)))

    summary_lines = []
    if completed_candidates:
        best = completed_candidates[0]
        if (best["improvement"] or 0.0) > 0:
            summary_lines.append(
                f"- Best candidate: `{best['name']}` with `{metric_name}={best['metric_value']:.4f}` "
                f"({fmt_delta(best['improvement'])} vs baseline)."
            )
        else:
            summary_lines.append("- No completed candidate beat the fast baseline.")
    else:
        summary_lines.append("- No completed candidate results were available by report time.")

    if failure_count:
        summary_lines.append(f"- Failures: {failure_count}. These runs still consumed deadline budget.")

    report = [
        f"# Goal Report — {goal.get('title', args.goal)}",
        "",
        "## Timing",
        "",
        f"- Goal start: `{goal.get('started_at')}`",
        f"- Training start: `{goal.get('training_started_at', 'not started')}`",
        f"- Dispatch deadline: `{(goal_effective_deadline(goal) or '').isoformat().replace('+00:00', 'Z') if goal_effective_deadline(goal) else 'none'}`",
        f"- Report due: `{(goal_effective_report_due(goal) or '').isoformat().replace('+00:00', 'Z') if goal_effective_report_due(goal) else 'none'}`",
        f"- Report generated: `{utcnow()}`",
        "",
        "## Summary",
        "",
    ]
    report.extend(summary_lines)
    report.extend(
        [
            "",
            "## Queue Status",
            "",
            "| Experiment | Role | Status | Metric | Delta vs baseline | Predicted | Actual | Error | Notes |",
            "|-----------|------|--------|--------|-------------------|-----------|--------|-------|-------|",
        ]
    )

    for row in rows:
        metric_str = f"{row['metric_value']:.4f}" if row["metric_value"] is not None else "—"
        error_str = "—"
        if row["estimate_error_pct"] is not None:
            error_str = f"{float(row['estimate_error_pct']):+.2f}%"
        report.append(
            f"| {row['name']} | {row['role'] or '—'} | {row['status']} | {metric_str} | {fmt_delta(row['improvement'])} | "
            f"{fmt_seconds(row['predicted_runtime_seconds'])} | {fmt_seconds(row['actual_runtime_seconds'])} | {error_str} | {row['reason']} |"
        )

    report.extend(
        [
            "",
            "## Findings",
            "",
        ]
    )
    if completed_candidates:
        for rank, row in enumerate(completed_candidates, 1):
            report.append(
                f"{rank}. `{row['name']}`: `{metric_name}={row['metric_value']:.4f}`, delta `{fmt_delta(row['improvement'])}` vs baseline."
            )
    else:
        report.append("1. No ranked candidate findings available yet.")

    report.extend(
        [
            "",
            "## Recommendation",
            "",
        ]
    )
    if completed_candidates and (completed_candidates[0]["improvement"] or 0.0) > 0:
        report.append(
            f"1. Continue with `{completed_candidates[0]['name']}` in the regular explore/validate lane if the same base is still current."
        )
        report.append("2. Keep the fast no-quant lane for triage before spending 45-minute explore runs.")
    else:
        report.append("1. Do not spend additional long explore runs on this exact batch until a stronger hypothesis set is prepared.")
        report.append("2. Keep the fast lane, but refresh the candidate list.")

    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")

    goal["report_generated_at"] = utcnow()
    goal["last_report_path"] = str(report_rel)
    report_due = goal_effective_report_due(goal)
    report_generated = datetime.fromisoformat(goal["report_generated_at"].replace("Z", "+00:00"))
    goal["status"] = "completed" if report_due and report_generated >= report_due else "report_generated"
    write_json(goal_path, goal)
    print(report_path)


if __name__ == "__main__":
    main()
