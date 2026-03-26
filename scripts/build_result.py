#!/usr/bin/env python3
"""Build a normalized result.json from collected experiment artifacts."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_utc(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def fmt_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_metrics(project: dict, summary: dict, lines: list[str]) -> dict:
    metric_parse = project.get("metric_parse", {})
    primary_metric = project.get("metric", "val_bpb")
    secondary_metrics = project.get("secondary_metrics", [])
    all_metrics = [primary_metric] + secondary_metrics

    parsed: dict[str, float] = {}
    for metric_name in all_metrics:
        mconf = metric_parse.get(metric_name, {})
        value = None

        sjk = mconf.get("summary_json_key", "")
        if sjk and isinstance(summary, dict):
            obj = summary
            for part in sjk.split("."):
                if isinstance(obj, dict):
                    obj = obj.get(part)
                else:
                    obj = None
                    break
            if obj is not None:
                try:
                    value = float(obj)
                except (TypeError, ValueError):
                    pass

        if value is None:
            regex = mconf.get("log_regex")
            if regex:
                for line in reversed(lines):
                    match = re.search(regex, line)
                    if match:
                        value = float(match.group(1))
                        break

        if value is not None:
            parsed[metric_name] = value

    return parsed


def parse_steps(project: dict, summary: dict, lines: list[str]) -> int:
    step_parse = project.get("step_parse", {})
    steps_completed = 0

    sjk = step_parse.get("summary_json_key", "")
    if sjk and isinstance(summary, dict):
        obj = summary
        for part in sjk.split("."):
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = None
                break
        if obj is not None:
            try:
                steps_completed = int(obj)
            except (TypeError, ValueError):
                pass

    if steps_completed == 0:
        regex = step_parse.get("log_regex", r"\bstep[:=]\s*([0-9]+)")
        for line in reversed(lines):
            match = re.search(regex, line)
            if match:
                steps_completed = int(match.group(1))
                break

    if steps_completed == 0:
        fallback = step_parse.get("log_regex_fallback", "")
        if fallback:
            for line in reversed(lines):
                match = re.search(fallback, line)
                if match:
                    steps_completed = int(match.group(1))
                    break

    return steps_completed


def parse_train_time_seconds(lines: list[str]) -> float | None:
    for line in reversed(lines):
        match = re.search(r"\btrain_time:(\d+)ms\b", line)
        if match:
            return int(match.group(1)) / 1000.0
    return None


def load_runtime_meta(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return load_json(path)
    except (OSError, json.JSONDecodeError):
        return {}


def runtime_from_log_mtime(log_path: Path, dispatched_at: datetime | None) -> tuple[int | None, str | None]:
    if dispatched_at is None or not log_path.exists():
        return None, None
    finished_at = datetime.fromtimestamp(log_path.stat().st_mtime, timezone.utc)
    delta = (finished_at - dispatched_at).total_seconds()
    if delta < 0:
        return None, None
    return int(round(delta)), fmt_utc(finished_at)


def choose_runtime(
    runtime_meta: dict,
    log_path: Path,
    dispatched_at: datetime | None,
    collected_at: datetime,
    train_time_seconds: float | None,
) -> tuple[int | None, str | None, str | None, str | None, int | None]:
    runtime_seconds = runtime_meta.get("runtime_seconds")
    exit_code = runtime_meta.get("exit_code")
    started_at = runtime_meta.get("started_at")
    finished_at = runtime_meta.get("finished_at")
    if isinstance(runtime_seconds, (int, float)) and runtime_seconds >= 0:
        return int(runtime_seconds), "remote_wrapper", started_at, finished_at, exit_code if isinstance(exit_code, int) else None

    mtime_runtime, mtime_finished_at = runtime_from_log_mtime(log_path, dispatched_at)
    if mtime_runtime is not None:
        return mtime_runtime, "log_mtime", started_at, mtime_finished_at, exit_code if isinstance(exit_code, int) else None

    if train_time_seconds is not None:
        return int(math.ceil(train_time_seconds)), "log_train_time_fallback", started_at, None, exit_code if isinstance(exit_code, int) else None

    if dispatched_at is not None:
        return int((collected_at - dispatched_at).total_seconds()), "collection_fallback", started_at, fmt_utc(collected_at), exit_code if isinstance(exit_code, int) else None

    return None, None, started_at, finished_at, exit_code if isinstance(exit_code, int) else None


def estimate_tracking(expected_seconds: object, runtime_seconds: int | None) -> dict:
    try:
        expected = int(expected_seconds) if expected_seconds not in (None, "") else None
    except (TypeError, ValueError):
        expected = None

    if expected is None or expected <= 0 or runtime_seconds is None or runtime_seconds < 0:
        return {
            "estimate_error_seconds": None,
            "estimate_error_pct": None,
            "estimate_ratio": None,
            "within_estimate_band_5pct": None,
        }

    error_seconds = runtime_seconds - expected
    error_pct = round((error_seconds / expected) * 100.0, 2)
    ratio = round(runtime_seconds / expected, 4)
    return {
        "estimate_error_seconds": error_seconds,
        "estimate_error_pct": error_pct,
        "estimate_ratio": ratio,
        "within_estimate_band_5pct": abs(error_pct) <= 5.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot_dir")
    parser.add_argument("project_json")
    parser.add_argument("gpu")
    parser.add_argument("log_path")
    args = parser.parse_args()

    snapshot_dir = Path(args.snapshot_dir)
    project = load_json(Path(args.project_json))
    log_path = Path(args.log_path)
    text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    summary_local = snapshot_dir / "results" / "summary.json"
    summary: dict = {}
    if summary_local.exists():
        try:
            summary = load_json(summary_local)
        except (OSError, json.JSONDecodeError):
            summary = {}

    parsed_metrics = parse_metrics(project, summary, lines)
    steps_completed = parse_steps(project, summary, lines)
    train_time_seconds = parse_train_time_seconds(lines)

    meta_path = snapshot_dir / "meta.json"
    meta = load_json(meta_path) if meta_path.exists() else {}
    expected_seconds = meta.get("expected_duration_seconds")

    dispatched_at_str = None
    dispatched_at = None
    dispatched_at_path = snapshot_dir / "dispatched_at"
    if dispatched_at_path.exists():
        dispatched_at_str = dispatched_at_path.read_text(encoding="utf-8").strip()
        dispatched_at = parse_utc(dispatched_at_str)

    collected_at = datetime.now(timezone.utc)
    collected_at_str = fmt_utc(collected_at)

    runtime_meta = load_runtime_meta(snapshot_dir / "results" / "runtime.json")
    runtime_seconds, runtime_source, process_started_at, process_finished_at, process_exit_code = choose_runtime(
        runtime_meta,
        log_path,
        dispatched_at,
        collected_at,
        train_time_seconds,
    )

    collection_lag_seconds = None
    finished_at_dt = parse_utc(process_finished_at)
    if finished_at_dt is not None:
        collection_lag_seconds = int((collected_at - finished_at_dt).total_seconds())

    overhead_seconds = None
    if runtime_seconds is not None and train_time_seconds is not None:
        overhead_seconds = max(runtime_seconds - train_time_seconds, 0.0)

    result = {
        "steps_completed": steps_completed,
        "gpu": args.gpu,
        "project": project.get("name"),
        "log_source": str(log_path.name),
        "dispatched_at": dispatched_at_str,
        "collected_at": collected_at_str,
        "runtime_seconds": runtime_seconds,
        "runtime_source": runtime_source,
        "duration_seconds": runtime_seconds,
        "train_time_seconds": train_time_seconds,
        "process_started_at": process_started_at,
        "process_finished_at": process_finished_at,
        "process_exit_code": process_exit_code,
        "collection_lag_seconds": collection_lag_seconds,
        "overhead_seconds": overhead_seconds,
        "expected_duration_seconds": expected_seconds,
        "log_tail": "\n".join(lines[-20:]),
    }
    result.update(parsed_metrics)
    result.update(estimate_tracking(expected_seconds, runtime_seconds))

    (snapshot_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "log_tail"}, indent=2))
    primary_metric = project.get("metric", "val_bpb")
    print("HAS_METRIC=" + str(primary_metric in parsed_metrics), file=sys.stderr)


if __name__ == "__main__":
    main()
