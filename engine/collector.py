"""Result collector — polls GPUs for progress and completed experiments."""
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models import Experiment, GPU
from api.routers.fleet import is_local_gpu, ssh_exec
from engine.sync import find_result_path, read_result_json

logger = logging.getLogger(__name__)

POLL_INTERVAL = 5  # seconds


def _read_progress_from_files(gpu: GPU, exp: Experiment) -> tuple[int | None, float | None]:
    repo_path = Path(gpu.repo_path)
    result_summary = find_result_path(exp.name)
    if result_summary:
        summary = read_result_json(result_summary)
        if summary:
            last_eval = summary.get("last_eval") or {}
            step = last_eval.get("step")
            val_bpb = last_eval.get("val_bpb")
            if isinstance(step, int):
                return step, val_bpb

    snapshot_paths = list((repo_path / "results").glob(f"**/{exp.name}/snapshot_in_progress.json"))
    for snapshot_path in snapshot_paths:
        snapshot = read_result_json(snapshot_path)
        if snapshot:
            step = snapshot.get("last_step_reached")
            curve = snapshot.get("curve") or []
            val_bpb = curve[-1].get("val_bpb") if curve else None
            if isinstance(step, int):
                return step, val_bpb

    log_path = Path(f"/tmp/{exp.name}.log")
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-50:]
        for line in reversed(lines):
            if "step:" in line:
                try:
                    token = line.split("step:", 1)[1].split("/", 1)[0]
                    return int(token), exp.val_bpb
                except (ValueError, IndexError):
                    continue
    return None, None


def check_experiment(db: Session, exp: Experiment) -> None:
    """Check a single running experiment: is it done? If so, collect results."""
    gpu = db.query(GPU).filter(GPU.name == exp.gpu_name).first()
    if not gpu:
        logger.warning(f"GPU {exp.gpu_name} not found for experiment {exp.name}")
        return

    if is_local_gpu(gpu):
        pid_path = Path(f"/tmp/{exp.name}.pid")
        pid = None
        if pid_path.exists():
            try:
                pid = int(pid_path.read_text().strip())
            except ValueError:
                pid = None
        if pid is not None and Path(f"/proc/{pid}").exists():
            step, val_bpb = _read_progress_from_files(gpu, exp)
            if step is not None:
                exp.current_step = step
            if val_bpb is not None:
                exp.val_bpb = val_bpb
            gpu.current_step = exp.current_step
            db.commit()
            return
        returncode, output = 0, "done"
    else:
        returncode, output = ssh_exec(gpu, "pgrep -f train_gpt || echo 'done'", timeout=10)
    if returncode != 0:
        # SSH failed — GPU might be offline, don't mark as failed yet
        logger.warning(f"SSH to {gpu.name} failed for {exp.name}")
        return

    is_running = output.strip() != "done"

    if is_running:
        step, val_bpb = _read_progress_from_files(gpu, exp)
        if step is not None:
            exp.current_step = step
            gpu.current_step = step
        if val_bpb is not None:
            exp.val_bpb = val_bpb
        db.commit()
        return

    # Training done — collect results
    logger.info(f"Experiment {exp.name} finished on {gpu.name}, collecting results")

    found_path = find_result_path(exp.name)
    output = ""
    if found_path:
        try:
            output = found_path.read_text(encoding="utf-8")
        except OSError:
            output = ""
    elif not is_local_gpu(gpu):
        result_paths = [
            f"{gpu.repo_path}/results/explore/{exp.name}/summary.json",
            f"{gpu.repo_path}/results/validate/{exp.name}/summary.json",
            f"{gpu.repo_path}/results/full/{exp.name}/summary.json",
            f"{gpu.repo_path}/results/misc/{exp.name}/summary.json",
            f"{gpu.repo_path}/results/{exp.name}/summary.json",
        ]
        find_cmd = " || ".join(f"(test -f {p} && echo {p})" for p in result_paths)
        _, path_output = ssh_exec(gpu, find_cmd, timeout=10)
        found_raw = path_output.strip().split("\n")[0].strip() if path_output.strip() else ""
        found_path = Path(found_raw) if found_raw else None
        cat_cmd = " || ".join(f"cat {p} 2>/dev/null" for p in result_paths)
        returncode, output = ssh_exec(gpu, cat_cmd, timeout=15)
        if returncode != 0:
            output = ""

    if output.strip():
        try:
            summary = json.loads(output.strip())
            final_quant = summary.get("final_quant_eval", {})
            last_eval = summary.get("last_eval", {})

            exp.val_bpb = final_quant.get("val_bpb") or last_eval.get("val_bpb")
            exp.current_step = last_eval.get("step", exp.steps)
            exp.status = "completed"
            exp.completed_at = datetime.now(timezone.utc)
            if found_path:
                exp.result_path = str(found_path)

            gpu.status = "idle"
            gpu.current_experiment = None
            gpu.current_step = None
            local_pid = Path(f"/tmp/{exp.name}.pid")
            if local_pid.exists():
                local_pid.unlink()
            db.commit()
            logger.info(f"Collected {exp.name}: val_bpb={exp.val_bpb}")
            return
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse results for {exp.name}: {e}")

    # No results found — check if it failed
    if is_local_gpu(gpu):
        log_path = Path(f"/tmp/{exp.name}.log")
        err_output = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-5:]) if log_path.exists() else ""
    else:
        _, err_output = ssh_exec(
            gpu,
            f"tail -5 /tmp/{exp.name}.log 2>/dev/null",
            timeout=10,
        )
    logger.warning(f"No results for {exp.name}. Log tail: {err_output.strip()}")
    exp.status = "failed"
    exp.completed_at = datetime.now(timezone.utc)
    gpu.status = "idle"
    gpu.current_experiment = None
    gpu.current_step = None
    local_pid = Path(f"/tmp/{exp.name}.pid")
    if local_pid.exists():
        local_pid.unlink()
    db.commit()


async def collector_loop():
    """Main collector loop. Call this as a background task."""
    logger.info("Result collector started")
    while True:
        try:
            db = SessionLocal()
            try:
                running = db.query(Experiment).filter(Experiment.status == "running").all()
                for exp in running:
                    check_experiment(db, exp)
            finally:
                db.close()
        except Exception:
            logger.exception("Collector error")

        await asyncio.sleep(POLL_INTERVAL)
