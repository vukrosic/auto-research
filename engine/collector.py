"""Result collector — polls GPUs for completed experiments and updates the DB.

Runs as a background task. Every 60s:
1. Finds experiments with status='running'
2. SSHes to their GPU to check if training is still active
3. If done, pulls summary.json and updates val_bpb in the DB
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models import Experiment, GPU
from api.routers.fleet import ssh_exec

logger = logging.getLogger(__name__)

POLL_INTERVAL = 60  # seconds


def check_experiment(db: Session, exp: Experiment) -> None:
    """Check a single running experiment: is it done? If so, collect results."""
    gpu = db.query(GPU).filter(GPU.name == exp.gpu_name).first()
    if not gpu:
        logger.warning(f"GPU {exp.gpu_name} not found for experiment {exp.name}")
        return

    # Check if training process is still running
    returncode, output = ssh_exec(gpu, "pgrep -f train_gpt || echo 'done'", timeout=10)
    if returncode != 0:
        # SSH failed — GPU might be offline, don't mark as failed yet
        logger.warning(f"SSH to {gpu.name} failed for {exp.name}")
        return

    is_running = output.strip() != "done"

    if is_running:
        # Still training — try to get current step from log
        _, log_output = ssh_exec(
            gpu,
            f"tail -20 /tmp/{exp.name}.log 2>/dev/null | grep -oP 'step \\K[0-9]+' | tail -1",
            timeout=10,
        )
        step_str = log_output.strip()
        if step_str.isdigit():
            exp.current_step = int(step_str)
            db.commit()
        return

    # Training done — collect results
    logger.info(f"Experiment {exp.name} finished on {gpu.name}, collecting results")

    # Determine result path — check organized dirs first, then top-level
    result_paths = [
        f"{gpu.repo_path}/results/explore/{exp.name}/summary.json",
        f"{gpu.repo_path}/results/validate/{exp.name}/summary.json",
        f"{gpu.repo_path}/results/full/{exp.name}/summary.json",
        f"{gpu.repo_path}/results/misc/{exp.name}/summary.json",
        f"{gpu.repo_path}/results/{exp.name}/summary.json",
    ]

    # Find which path exists and cat it
    find_cmd = " || ".join(f"(test -f {p} && echo {p})" for p in result_paths)
    _, path_output = ssh_exec(gpu, find_cmd, timeout=10)
    found_path = path_output.strip().split("\n")[0].strip() if path_output.strip() else ""

    cat_cmd = " || ".join(f"cat {p} 2>/dev/null" for p in result_paths)
    returncode, output = ssh_exec(gpu, cat_cmd, timeout=15)

    if returncode == 0 and output.strip():
        try:
            summary = json.loads(output.strip())
            final_quant = summary.get("final_quant_eval", {})
            last_eval = summary.get("last_eval", {})

            exp.val_bpb = final_quant.get("val_bpb") or last_eval.get("val_bpb")
            exp.current_step = last_eval.get("step", exp.steps)
            exp.status = "completed"
            exp.completed_at = datetime.now(timezone.utc)
            if found_path:
                exp.result_path = found_path

            gpu.status = "idle"
            gpu.current_experiment = None
            gpu.current_step = None
            db.commit()
            logger.info(f"Collected {exp.name}: val_bpb={exp.val_bpb}")
            return
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse results for {exp.name}: {e}")

    # No results found — check if it failed
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
