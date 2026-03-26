#!/usr/bin/env python3
"""Regenerate state/ACTIVE_RUNS.md from snapshot records.
Run at session open to get an accurate live picture."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

AUTORESEARCH = Path(__file__).parent.parent
EXPERIMENTS = AUTORESEARCH / "experiments"
OUT = AUTORESEARCH / "state" / "ACTIVE_RUNS.md"
TIMING_LOG = AUTORESEARCH / "state" / "timing_log.md"


def read_json(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def read_file(path):
    try:
        return path.read_text().strip()
    except Exception:
        return None


def fmt_duration(seconds):
    if seconds is None:
        return "?"
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m"
    elif m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def expected_finish(dispatched_at_str, expected_seconds):
    if not dispatched_at_str or not expected_seconds:
        return "?"
    try:
        dt = datetime.strptime(dispatched_at_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        from datetime import timedelta
        finish = dt + timedelta(seconds=expected_seconds)
        return finish.strftime("%Y-%m-%dT%H:%MZ")
    except Exception:
        return "?"


def check_progress(name, gpu):
    """SSH to GPU and get last log line."""
    try:
        from subprocess import check_output, STDOUT
        log = f"/tmp/autoresearch_{name}.log"
        # Try to read GPU creds from script
        result = subprocess.run(
            ["bash", "-c", f"source {AUTORESEARCH}/scripts/gpu_config.sh && gpu_ssh {gpu} 'tail -1 {log} 2>/dev/null'"],
            capture_output=True, text=True, timeout=10
        )
        line = result.stdout.strip()
        return line if line else "?"
    except Exception:
        return "?"


now = datetime.now(timezone.utc)
now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

running = []
pending = []
recently_done = []

for project_dir in sorted(EXPERIMENTS.iterdir()):
    snapshots_dir = project_dir / "snapshots"
    if not snapshots_dir.is_dir():
        continue
    project_name = project_dir.name
    for snap_dir in sorted(snapshots_dir.iterdir()):
        if not snap_dir.is_dir():
            continue
        name = snap_dir.name
        status = read_file(snap_dir / "status") or "unknown"
        meta = read_json(snap_dir / "meta.json")
        result = read_json(snap_dir / "result.json")
        gpu = read_file(snap_dir / "gpu") or meta.get("gpu") or "?"
        dispatched_at = read_file(snap_dir / "dispatched_at")
        stage = meta.get("stage", "?")
        steps = meta.get("steps", "?")
        expected_s = meta.get("expected_duration_seconds")
        created_at = meta.get("created_at", "")
        actual_s = result.get("runtime_seconds") or result.get("duration_seconds")

        if status == "running":
            finish = expected_finish(dispatched_at, expected_s)
            running.append({
                "project": project_name,
                "name": name,
                "gpu": gpu,
                "stage": stage,
                "steps": steps,
                "dispatched_at": (dispatched_at or "?")[:16],
                "expected_finish": finish,
                "expected_s": expected_s,
            })

        elif status == "pending":
            pending.append({
                "project": project_name,
                "name": name,
                "stage": stage,
                "steps": steps,
                "expected_s": expected_s,
                "created_at": created_at,
            })

        elif status in ("done", "failed", "rejected", "validated_winner", "promoted"):
            collected_at = result.get("collected_at", "")
            if collected_at:
                recently_done.append({
                    "project": project_name,
                    "name": name,
                    "status": status,
                    "finished": collected_at[:16],
                    "actual_s": actual_s,
                    "predicted_s": result.get("expected_duration_seconds") or expected_s,
                    "val_bpb": result.get("val_bpb", "?"),
                    "estimate_error_pct": result.get("estimate_error_pct"),
                    "collected_at": collected_at,
                })

# Sort recently_done by collected_at desc, take 5
recently_done.sort(key=lambda x: x.get("collected_at", ""), reverse=True)
recently_done = recently_done[:5]

# Sort pending by created_at
pending_real = [p for p in pending if p is not None]
pending_real.sort(key=lambda x: x.get("created_at", ""))

# Estimate queue start times
last_finish_offset = 0
if running:
    # Rough: assume current run finishes in expected_s from now
    r = running[0]
    if r.get("expected_s"):
        last_finish_offset = int(r["expected_s"])

lines = [
    "# Active Runs",
    "",
    "> **Live dashboard.** Auto-updated by `dispatch.sh` and `collect_result.sh`.",
    "> Regenerate manually: `python3 scripts/refresh_active_runs.py`",
    "",
    f"**Last updated**: {now_str}",
    "",
    "---",
    "",
    "## Currently Running",
    "",
]

if running:
    lines += [
        "| Project | Experiment | GPU | Stage | Steps | Dispatched | Expected Finish | Expected Duration |",
        "|---------|------------|-----|-------|-------|-----------|----------------|-----------------|",
    ]
    for r in running:
        lines.append(
            f"| {r['project']} | {r['name']} | {r['gpu']} | {r['stage']} | {r['steps']} | "
            f"{r['dispatched_at']} | {r['expected_finish']} | {fmt_duration(r['expected_s'])} |"
        )
else:
    lines.append("*(nothing running)*")

lines += ["", "## Queue (pending, dispatch order)", ""]

if pending_real:
    lines += [
        "| # | Project | Experiment | Stage | Steps | Est. Duration |",
        "|---|---------|------------|-------|-------|--------------|",
    ]
    for i, p in enumerate(pending_real, 1):
        lines.append(
            f"| {i} | {p['project']} | {p['name']} | {p['stage']} | {p['steps']} | {fmt_duration(p['expected_s'])} |"
        )
    total_pending_s = sum(p.get("expected_s") or 0 for p in pending_real)
    lines.append("")
    lines.append(f"**Total queued**: {len(pending_real)} experiments, ~{fmt_duration(total_pending_s)}")
else:
    lines.append("*(queue empty — generate new experiments)*")

lines += ["", "## Recently Finished (last 5)", ""]

if recently_done:
    lines += [
        "| Project | Experiment | Status | Finished | Actual | Predicted | Ratio | Error | val_bpb |",
        "|---------|------------|--------|---------|--------|-----------|-------|-------|---------|",
    ]
    for r in recently_done:
        actual = r.get("actual_s")
        predicted = r.get("predicted_s")
        ratio = f"{actual/predicted:.2f}x" if actual and predicted else "?"
        error = r.get("estimate_error_pct")
        error_str = f"{float(error):+.2f}%" if error is not None else "?"
        lines.append(
            f"| {r['project']} | {r['name']} | {r['status']} | {r['finished']} | "
            f"{fmt_duration(actual)} | {fmt_duration(predicted)} | {ratio} | {error_str} | {r['val_bpb']} |"
        )
else:
    lines.append("*(none yet)*")

lines += ["", "## Issues / Flags", "", "*(none — update manually when issues arise)*"]

OUT.write_text("\n".join(lines) + "\n")
print(f"Refreshed {OUT}")
print(f"  Running: {len(running)}, Pending: {len(pending_real)}, Recently done: {len(recently_done)}")
