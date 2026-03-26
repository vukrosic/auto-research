#!/usr/bin/env python3
"""Validate an experiment snapshot before dispatch.

Preflight is the hard gate before compute allocation:
- validate snapshot + project config
- validate goal constraints and deadline fit
- validate project-specific config invariants
- derive/update expected duration from measured runs when possible
- optionally validate remote GPU readiness

Writes snapshot-local preflight.json so queue/state views can surface blockers.
"""

from __future__ import annotations

import argparse
import json
import math
import shlex
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from goal_timing import goal_effective_deadline, goal_remaining_dispatch_budget_seconds

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "projects"
EXPERIMENTS = ROOT / "experiments"
GOALS = ROOT / "goals"
GPU_CONFIG = ROOT / "scripts" / "gpu_config.sh"


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def snapshot_dir(project: str, name: str) -> Path:
    return EXPERIMENTS / project / "snapshots" / name


def read_status(path: Path) -> str:
    status_path = path / "status"
    if not status_path.exists():
        return "missing"
    return status_path.read_text(encoding="utf-8").strip() or "missing"


def load_project(project: str) -> dict:
    path = PROJECTS / f"{project}.json"
    if not path.exists():
        raise FileNotFoundError(f"missing project config: {path}")
    return load_json(path)


def load_goal(goal_name: str) -> dict:
    path = GOALS / goal_name / "goal.json"
    if not path.exists():
        raise FileNotFoundError(f"missing goal config: {path}")
    goal = load_json(path)
    goal.setdefault("name", goal_name)
    return goal


def load_queue_entry(goal_name: str, experiment: str) -> dict | None:
    path = GOALS / goal_name / "queue.json"
    if not path.exists():
        return None
    queue = load_json(path)
    for entry in queue.get("entries", []):
        if entry.get("experiment") == experiment:
            return entry
    return None


def update_goal_queue_entry(goal_name: str, experiment: str, updates: dict) -> None:
    path = GOALS / goal_name / "queue.json"
    if not path.exists():
        return
    queue = load_json(path)
    changed = False
    for entry in queue.get("entries", []):
        if entry.get("experiment") != experiment:
            continue
        for key, value in updates.items():
            if entry.get(key) != value:
                entry[key] = value
                changed = True
        break
    if changed:
        queue["updated_at"] = utcnow()
        write_json(path, queue)


def update_goal_queue_expectation(goal_name: str, experiment: str, expectation: dict) -> None:
    update_goal_queue_entry(goal_name, experiment, expectation)


def add_check(checks: list[dict], name: str, ok: bool, message: str, *, level: str = "error", data: dict | None = None) -> None:
    checks.append(
        {
            "name": name,
            "status": "pass" if ok else "fail",
            "level": level,
            "message": message,
            "data": data or {},
        }
    )


def env_value(meta: dict, key: str, default: object | None = None) -> object | None:
    env = meta.get("env_overrides") or {}
    return env.get(key, default)


def int_or_none(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def float_or_none(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def completed_references(project: str, current_name: str) -> list[dict]:
    refs: list[dict] = []
    root = EXPERIMENTS / project / "snapshots"
    if not root.exists():
        return refs
    terminal_statuses = {
        "done",
        "rejected",
        "validated_winner",
        "stale_winner",
        "promoted",
        "rollback_invalidated",
    }
    for snap in sorted(root.iterdir()):
        if not snap.is_dir() or snap.name == current_name:
            continue
        if read_status(snap) not in terminal_statuses:
            continue
        meta_path = snap / "meta.json"
        result_path = snap / "result.json"
        if not meta_path.exists() or not result_path.exists():
            continue
        try:
            meta = load_json(meta_path)
            result = load_json(result_path)
        except (OSError, json.JSONDecodeError):
            continue
        steps = int_or_none(meta.get("steps"))
        duration = int_or_none(result.get("runtime_seconds"))
        if duration is None or duration <= 0:
            train_time_seconds = float_or_none(result.get("train_time_seconds"))
            if train_time_seconds is not None and train_time_seconds > 0:
                duration = int(math.ceil(train_time_seconds))
        if duration is None or duration <= 0:
            duration = int_or_none(result.get("duration_seconds"))
        runtime_source = result.get("runtime_source")
        if not steps or steps <= 0 or not duration or duration <= 0:
            continue
        refs.append(
            {
                "name": snap.name,
                "goal": meta.get("goal"),
                "stage": meta.get("stage"),
                "steps": steps,
                "duration_seconds": duration,
                "runtime_source": runtime_source,
                "env_overrides": meta.get("env_overrides") or {},
            }
        )
    return refs


ARCH_KEYS = {
    "NUM_LAYERS",
    "MODEL_DIM",
    "NUM_HEADS",
    "NUM_KV_HEADS",
    "MLP_MULT",
    "NUM_EXPERTS",
    "ATTNRES_MODE",
    "MLP_ACT",
    "QAT_START_FRAC",
}

TIMING_KEYS = {
    "SKIP_QUANT_EVAL",
    "SKIP_EXPORT_ARTIFACTS",
    "VAL_MAX_SEQS",
    "VAL_LOSS_EVERY",
    "VAL_BATCH_SIZE",
    "TRAIN_SEQ_LEN",
    "TRAIN_BATCH_TOKENS",
    "WARMUP_STEPS",
    "HARD_TIMEOUT_SECONDS",
    "MAX_WALLCLOCK_SECONDS",
}


def normalized_env(meta: dict, preflight_cfg: dict) -> dict:
    env = dict(preflight_cfg.get("env_defaults") or {})
    env.update(meta.get("env_overrides") or {})
    return env


def timing_signature(meta: dict, preflight_cfg: dict) -> tuple[tuple[str, str], ...]:
    env = normalized_env(meta, preflight_cfg)
    keys = preflight_cfg.get("timing_signature_keys") or []
    signature = []
    for key in keys:
        value = env.get(key)
        if value is None:
            continue
        signature.append((str(key), str(value)))
    return tuple(signature)


def adjusted_reference_duration(ref: dict, preflight_cfg: dict) -> int:
    duration = int_or_none(ref.get("duration_seconds")) or 0
    runtime_source = ref.get("runtime_source")
    padding_map = preflight_cfg.get("runtime_source_padding_seconds") or {}
    padding = int_or_none(padding_map.get(runtime_source, 0)) or 0
    return duration + max(padding, 0)


def similarity_score(target_meta: dict, ref: dict, preflight_cfg: dict) -> int:
    score = 0
    if target_meta.get("goal") and target_meta.get("goal") == ref.get("goal"):
        score += 8
    if target_meta.get("stage") and target_meta.get("stage") == ref.get("stage"):
        score += 4
    target_steps = int_or_none(target_meta.get("steps"))
    if target_steps and target_steps == ref.get("steps"):
        score += 4

    target_env = normalized_env(target_meta, preflight_cfg)
    ref_env = dict(preflight_cfg.get("env_defaults") or {})
    ref_env.update(ref.get("env_overrides") or {})
    relevant_keys = sorted(ARCH_KEYS | TIMING_KEYS)
    for key in relevant_keys:
        target_value = target_env.get(key)
        ref_value = ref_env.get(key)
        if target_value is None and ref_value is None:
            continue
        if str(target_value) == str(ref_value):
            score += 2
        else:
            score -= 2
    return score


def derive_duration_estimate(meta: dict, refs: list[dict], preflight_cfg: dict) -> dict | None:
    target_steps = int_or_none(meta.get("steps"))
    if not target_steps or target_steps <= 0:
        return None

    scored = []
    target_signature = timing_signature(meta, preflight_cfg)
    for ref in refs:
        score = similarity_score(meta, ref, preflight_cfg)
        if score <= 0:
            continue
        enriched = dict(ref)
        enriched["score"] = score
        enriched["timing_signature"] = timing_signature(ref, preflight_cfg)
        scored.append(enriched)
    if not scored:
        return None

    same_signature = [item for item in scored if item["timing_signature"] == target_signature]
    using_same_signature = bool(same_signature)
    if using_same_signature:
        scored = same_signature

    scored.sort(key=lambda item: (-item["score"], item["name"]))
    same_steps = [item for item in scored if item["steps"] == target_steps]

    if same_steps:
        top = same_steps[:10]
        durations = [adjusted_reference_duration(item, preflight_cfg) for item in top]
        expected = int(math.ceil(statistics.median(durations)))
        source = "empirical_median_same_steps"
        reference_mode = "same_signature_same_steps" if using_same_signature else "cross_signature_same_steps"
        samples = len(top)
    else:
        top = scored[:10]
        durations = [adjusted_reference_duration(item, preflight_cfg) / item["steps"] * target_steps for item in top]
        expected = int(math.ceil(statistics.median(durations)))
        source = "empirical_median_per_step"
        reference_mode = "same_signature_per_step" if using_same_signature else "cross_signature_per_step"
        samples = len(top)

    return {
        "expected_duration_seconds": expected,
        "expected_duration_source": source,
        "expected_duration_reference_mode": reference_mode,
        "expected_duration_samples": samples,
        "reference_experiments": [item["name"] for item in top],
    }


def sync_meta_expectation(meta_path: Path, meta: dict, estimate: dict) -> bool:
    changed = False
    for key, value in estimate.items():
        if meta.get(key) != value:
            meta[key] = value
            changed = True
    if changed:
        meta["expected_duration_updated_at"] = utcnow()
        write_json(meta_path, meta)
    return changed


def supports_snapshot_feature(snap: Path, requirements: list[dict]) -> tuple[bool, str]:
    for requirement in requirements:
        rel_path = requirement.get("path")
        pattern = requirement.get("pattern")
        if not rel_path or not pattern:
            continue
        target = snap / "code" / rel_path
        if not target.exists():
            return False, f"missing snapshot code file {target.relative_to(snap)}"
        text = target.read_text(encoding="utf-8", errors="replace")
        if pattern not in text:
            return False, f"snapshot code missing pattern {pattern!r} in {target.relative_to(snap)}"
    return True, "snapshot code supports requested env feature"


def remote_ready(gpu: str, remote_dir: str) -> tuple[bool, str]:
    remote_parent = str(Path(remote_dir).parent)
    remote_cmd = (
        "command -v python3 >/dev/null "
        "&& command -v nvidia-smi >/dev/null "
        f"&& (test -d {shlex.quote(remote_dir)} || test -d {shlex.quote(remote_parent)})"
    )
    shell_cmd = (
        f"source {shlex.quote(str(GPU_CONFIG))} "
        f"&& gpu_ssh {shlex.quote(gpu)} {shlex.quote(remote_cmd)}"
    )
    proc = subprocess.run(
        ["bash", "-lc", shell_cmd],
        text=True,
        capture_output=True,
        timeout=20,
    )
    if proc.returncode == 0:
        return True, f"remote ready on {gpu}"
    output = (proc.stderr or proc.stdout or "").strip()
    if output:
        return False, output
    return False, f"remote readiness check failed for {gpu}"


def build_preflight(project_name: str, experiment: str, gpu: str | None, sync_expected: bool) -> dict:
    checked_at = utcnow()
    snap = snapshot_dir(project_name, experiment)
    checks: list[dict] = []

    payload: dict[str, object] = {
        "checked_at": checked_at,
        "project": project_name,
        "experiment": experiment,
        "gpu": gpu,
    }

    if not snap.exists():
        payload.update(
            {
                "status": "fail",
                "dispatch_ready": False,
                "summary": f"missing snapshot {snap}",
                "checks": [
                    {
                        "name": "snapshot_exists",
                        "status": "fail",
                        "level": "error",
                        "message": f"missing snapshot {snap}",
                        "data": {},
                    }
                ],
            }
        )
        return payload

    meta_path = snap / "meta.json"
    if not meta_path.exists():
        payload.update(
            {
                "status": "fail",
                "dispatch_ready": False,
                "summary": f"missing meta.json for {experiment}",
                "checks": [
                    {
                        "name": "meta_exists",
                        "status": "fail",
                        "level": "error",
                        "message": f"missing {meta_path}",
                        "data": {},
                    }
                ],
            }
        )
        return payload

    meta = load_json(meta_path)
    project = load_project(project_name)
    goal_name = meta.get("goal")
    goal = load_goal(goal_name) if isinstance(goal_name, str) and goal_name else None
    queue_entry = load_queue_entry(goal_name, experiment) if goal_name else None
    queue_role = queue_entry.get("role") if isinstance(queue_entry, dict) else None
    status = read_status(snap)

    payload["goal"] = goal_name
    payload["snapshot_status"] = status

    add_check(checks, "snapshot_exists", True, f"snapshot present: {snap}")
    add_check(checks, "code_exists", (snap / "code").is_dir(), "snapshot code directory present" if (snap / "code").is_dir() else "missing snapshot code directory")
    add_check(
        checks,
        "status_dispatchable",
        status != "running",
        f"snapshot status is {status}",
        data={"status": status},
    )

    preflight_cfg = project.get("preflight") or {}
    required_meta_fields = preflight_cfg.get(
        "required_meta_fields",
        ["name", "project", "parent_base", "stage", "steps", "baseline_metric", "promotion_threshold", "expected_duration_seconds"],
    )
    missing_meta = [field for field in required_meta_fields if meta.get(field) in (None, "")]
    add_check(
        checks,
        "required_meta_fields",
        not missing_meta,
        "required meta fields present" if not missing_meta else f"missing meta fields: {', '.join(missing_meta)}",
        data={"missing": missing_meta},
    )

    add_check(
        checks,
        "project_match",
        meta.get("project") == project_name,
        f"meta project={meta.get('project')}",
        data={"meta_project": meta.get("project")},
    )

    stage = meta.get("stage")
    add_check(
        checks,
        "stage_known",
        isinstance(stage, str) and stage in (project.get("stages") or {}),
        f"stage={stage}",
        data={"stage": stage},
    )

    steps = int_or_none(meta.get("steps"))
    add_check(
        checks,
        "steps_positive",
        steps is not None and steps > 0,
        f"steps={steps}",
        data={"steps": steps},
    )

    baseline_metric = float_or_none(meta.get("baseline_metric"))
    add_check(
        checks,
        "baseline_metric_present",
        baseline_metric is not None,
        f"baseline_metric={baseline_metric}",
    )

    threshold = float_or_none(meta.get("promotion_threshold"))
    add_check(
        checks,
        "promotion_threshold_present",
        threshold is not None,
        f"promotion_threshold={threshold}",
    )

    env = meta.get("env_overrides") or {}
    feature_contracts = ((preflight_cfg.get("snapshot_code_contracts") or {}).get("env_features") or {})

    for env_key, requirements in feature_contracts.items():
        if env_key not in env:
            continue
        ok, message = supports_snapshot_feature(snap, requirements)
        add_check(
            checks,
            f"snapshot_feature_{env_key.lower()}",
            ok,
            f"{env_key}: {message}",
            data={"env_key": env_key, "requirements": requirements},
        )

    for index, rule in enumerate(preflight_cfg.get("divisibility_checks", []), start=1):
        numerator_key = rule.get("numerator_env")
        denominator_key = rule.get("denominator_env")
        numerator = int_or_none(env.get(numerator_key, rule.get("default_numerator")))
        denominator = int_or_none(env.get(denominator_key, rule.get("default_denominator")))
        ok = numerator is not None and denominator is not None and denominator > 0 and numerator % denominator == 0
        message = rule.get("message") or f"{numerator_key} must be divisible by {denominator_key}"
        add_check(
            checks,
            f"divisibility_{index}",
            ok,
            f"{message} ({numerator_key}={numerator}, {denominator_key}={denominator})",
            data={"numerator": numerator, "denominator": denominator},
        )

    effective_expected = int_or_none(meta.get("expected_duration_seconds"))
    estimate = derive_duration_estimate(meta, completed_references(project_name, experiment), preflight_cfg)
    tolerance = 0.05
    if goal:
        tolerance = float_or_none(goal.get("deadline_tolerance_ratio")) or tolerance

    expectation_synced = False
    if estimate is not None:
        payload["recommended_expected_duration_seconds"] = estimate["expected_duration_seconds"]
        payload["expected_duration_source"] = estimate["expected_duration_source"]
        payload["expected_duration_reference_mode"] = estimate["expected_duration_reference_mode"]
        payload["expected_duration_samples"] = estimate["expected_duration_samples"]
        payload["reference_experiments"] = estimate["reference_experiments"]
        should_sync_from_estimate = estimate["expected_duration_reference_mode"].startswith("same_signature")
        if sync_expected and should_sync_from_estimate and estimate["expected_duration_seconds"] > 0:
            current_expected = int_or_none(meta.get("expected_duration_seconds"))
            if current_expected is None or current_expected <= 0:
                sync_needed = True
            else:
                sync_needed = abs(estimate["expected_duration_seconds"] - current_expected) / current_expected > tolerance
            if sync_needed:
                expectation_synced = sync_meta_expectation(meta_path, meta, estimate)
                effective_expected = estimate["expected_duration_seconds"]
                if goal_name:
                    update_goal_queue_expectation(
                        goal_name,
                        experiment,
                        {
                            "expected_duration_seconds": estimate["expected_duration_seconds"],
                            "expected_duration_source": estimate["expected_duration_source"],
                            "expected_duration_samples": estimate["expected_duration_samples"],
                            "expected_duration_updated_at": utcnow(),
                        },
                    )
        if effective_expected is None:
            effective_expected = estimate["expected_duration_seconds"]

    payload["effective_expected_duration_seconds"] = effective_expected
    payload["expectation_synced"] = expectation_synced

    add_check(
        checks,
        "expected_duration_present",
        effective_expected is not None and effective_expected > 0,
        f"expected_duration_seconds={effective_expected}",
        data={"expected_duration_seconds": effective_expected},
    )

    if estimate is not None and effective_expected and estimate["expected_duration_reference_mode"].startswith("same_signature"):
        drift = abs(estimate["expected_duration_seconds"] - effective_expected) / effective_expected
        add_check(
            checks,
            "expected_duration_calibrated",
            drift <= tolerance,
            (
                f"expected duration aligned with measured runs "
                f"(expected={effective_expected}s empirical={estimate['expected_duration_seconds']}s)"
            ),
            data={
                "effective_expected_duration_seconds": effective_expected,
                "empirical_expected_duration_seconds": estimate["expected_duration_seconds"],
                "tolerance_ratio": tolerance,
            },
        )
    elif estimate is not None and queue_role == "baseline":
        add_check(
            checks,
            "expected_duration_probe_mode",
            True,
            (
                "no same-signature empirical timing exists yet; keeping the explicit baseline estimate "
                f"{effective_expected}s for the first runtime probe"
            ),
            level="warning",
        )

    if goal:
        add_check(
            checks,
            "goal_active",
            goal.get("status", "active") == "active",
            f"goal status={goal.get('status')}",
        )
        if queue_entry is not None:
            allowed_states = {"queued", "pending", "ready", "retry", "running", "completed"}
            dispatch_state = str(queue_entry.get("dispatch_state") or queue_entry.get("state") or "queued")
            add_check(
                checks,
                "goal_queue_entry_present",
                dispatch_state in allowed_states,
                f"goal queue state={dispatch_state}",
                data={"dispatch_state": dispatch_state},
            )

        constraints = goal.get("experiment_constraints") or {}
        max_wallclock = int_or_none(constraints.get("max_wallclock_seconds"))
        env_wallclock = int_or_none(env_value(meta, "MAX_WALLCLOCK_SECONDS"))
        if max_wallclock is not None:
            add_check(
                checks,
                "goal_max_wallclock",
                env_wallclock is not None and env_wallclock <= max_wallclock,
                f"MAX_WALLCLOCK_SECONDS={env_wallclock}, limit={max_wallclock}",
                data={"max_wallclock_seconds": env_wallclock, "limit": max_wallclock},
            )

        max_minutes = float_or_none(constraints.get("max_experiment_minutes"))
        if max_minutes is not None and effective_expected is not None:
            cap = int(math.floor(max_minutes * 60 * (1.0 + tolerance)))
            add_check(
                checks,
                "goal_max_duration",
                effective_expected <= cap,
                (
                    f"expected duration {effective_expected}s within cap {cap}s"
                    if effective_expected <= cap
                    else f"expected duration {effective_expected}s exceeds cap {cap}s"
                ),
                data={"effective_expected_duration_seconds": effective_expected, "cap_seconds": cap},
            )

        if constraints.get("skip_quant_eval") is True:
            add_check(
                checks,
                "goal_skip_quant_eval",
                str(env_value(meta, "SKIP_QUANT_EVAL", "0")) == "1",
                f"SKIP_QUANT_EVAL={env_value(meta, 'SKIP_QUANT_EVAL', '0')}",
            )

        if constraints.get("single_final_eval_only") is True and steps is not None:
            val_loss_every = int_or_none(env_value(meta, "VAL_LOSS_EVERY"))
            add_check(
                checks,
                "goal_single_final_eval_only",
                val_loss_every is not None and val_loss_every > steps,
                f"VAL_LOSS_EVERY={val_loss_every}, steps={steps}",
                data={"VAL_LOSS_EVERY": val_loss_every, "steps": steps},
            )

        max_val_seqs = int_or_none(constraints.get("max_validation_sequences"))
        if max_val_seqs is not None:
            val_max_seqs = int_or_none(env_value(meta, "VAL_MAX_SEQS"))
            add_check(
                checks,
                "goal_max_validation_sequences",
                val_max_seqs is not None and 0 < val_max_seqs <= max_val_seqs,
                f"VAL_MAX_SEQS={val_max_seqs}, limit={max_val_seqs}",
                data={"VAL_MAX_SEQS": val_max_seqs, "limit": max_val_seqs},
            )

        if constraints.get("skip_export_artifacts") is True:
            add_check(
                checks,
                "goal_skip_export_artifacts",
                str(env_value(meta, "SKIP_EXPORT_ARTIFACTS", "0")) == "1",
                f"SKIP_EXPORT_ARTIFACTS={env_value(meta, 'SKIP_EXPORT_ARTIFACTS', '0')}",
            )

        remaining = goal_remaining_dispatch_budget_seconds(goal)
        deadline = goal_effective_deadline(goal)
        if remaining is not None and effective_expected is not None:
            required = int(math.ceil(effective_expected * (1.0 + tolerance)))
            payload["remaining_deadline_seconds"] = remaining
            payload["required_dispatch_budget_seconds"] = required
            if deadline is not None:
                payload["effective_deadline_at"] = deadline.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            add_check(
                checks,
                "deadline_window",
                remaining >= required,
                f"remaining={remaining}s required={required}s",
                data={"remaining_seconds": remaining, "required_seconds": required},
            )

    if gpu:
        project_gpus = project.get("gpus") or []
        add_check(
            checks,
            "gpu_known",
            gpu in project_gpus,
            f"gpu={gpu}",
            data={"known_gpus": project_gpus},
        )
        remote_dir = ((project.get("gpu_remote_dirs") or {}).get(gpu))
        add_check(
            checks,
            "remote_dir_configured",
            isinstance(remote_dir, str) and bool(remote_dir),
            f"remote_dir={remote_dir}",
        )
        if isinstance(remote_dir, str) and remote_dir:
            ok, message = remote_ready(gpu, remote_dir)
            add_check(checks, "remote_ready", ok, message)

    errors = [check for check in checks if check["status"] == "fail" and check["level"] == "error"]
    status_label = "pass" if not errors else "fail"

    if not errors:
        summary = (
            f"preflight passed for {project_name}/{experiment}"
            + (f" on {gpu}" if gpu else "")
            + (
                f" with expected={effective_expected}s"
                if effective_expected is not None
                else ""
            )
        )
    else:
        summary = f"preflight blocked {project_name}/{experiment}: {errors[0]['name']} - {errors[0]['message']}"

    payload.update(
        {
            "status": status_label,
            "dispatch_ready": not errors,
            "summary": summary,
            "checks": checks,
        }
    )

    if goal_name:
        update_goal_queue_entry(
            goal_name,
            experiment,
            {
                "expected_duration_seconds": effective_expected,
                "preflight": {
                    "status": payload.get("status"),
                    "dispatch_ready": payload.get("dispatch_ready"),
                    "checked_at": payload.get("checked_at"),
                    "summary": payload.get("summary"),
                    "effective_expected_duration_seconds": payload.get("effective_expected_duration_seconds"),
                    "recommended_expected_duration_seconds": payload.get("recommended_expected_duration_seconds"),
                },
            },
        )

    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("experiment")
    parser.add_argument("--gpu")
    parser.add_argument("--write", action="store_true", help="Persist snapshot preflight.json")
    parser.add_argument(
        "--sync-expected",
        action="store_true",
        help="Update expected_duration_seconds from empirical references when drift exceeds tolerance",
    )
    args = parser.parse_args()

    payload = build_preflight(args.project, args.experiment, args.gpu, args.sync_expected)
    if args.write:
        write_json(snapshot_dir(args.project, args.experiment) / "preflight.json", payload)

    print(payload["summary"])
    if payload.get("dispatch_ready"):
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
