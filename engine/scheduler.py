"""Experiment scheduler — dispatches queued experiments to idle GPUs."""
import asyncio
import json
import logging
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import case
from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models import User, Experiment, GPU
from api.routers.fleet import ensure_local_gpu, is_local_gpu, ssh_exec

logger = logging.getLogger(__name__)

POLL_INTERVAL = 5  # seconds

# Tier priority: higher = dispatched first
TIER_PRIORITY = {"admin": 10, "pro": 3, "team": 3, "researcher": 2, "starter": 1}


def get_idle_gpus(db: Session) -> list[GPU]:
    return db.query(GPU).filter(GPU.status.in_(["idle", "online"])).all()


def get_queued_experiments(db: Session) -> list[Experiment]:
    """Get queued experiments ordered by tier priority (desc), then queue time (asc)."""
    priority_case = case(
        {tier: prio for tier, prio in TIER_PRIORITY.items()},
        value=User.tier,
        else_=0,
    )
    return (
        db.query(Experiment)
        .join(User)
        .filter(Experiment.status == "queued")
        .order_by(priority_case.desc(), Experiment.queued_at.asc())
        .all()
    )

def _build_overrides(exp: Experiment) -> str:
    overrides = ""
    try:
        config = json.loads(exp.config_overrides) if exp.config_overrides else {}
        if config:
            env_keys = {"MATRIX_LR", "SCALAR_LR", "EMBED_LR", "NUM_LAYERS", "MODEL_DIM",
                        "NUM_HEADS", "NUM_KV_HEADS", "MLP_MULT", "WARMDOWN_ITERS",
                        "WARMUP_STEPS", "LOGIT_SOFTCAP", "QK_GAIN_INIT", "ROPE_BASE",
                        "MUON_MOMENTUM", "GRAD_CLIP_NORM", "TIED_EMBED_LR", "TIED_EMBED_INIT_STD",
                        "MLP_ACT", "SEED"}
            overrides = " ".join(f"{k}={shlex.quote(str(v))}" for k, v in config.items() if k in env_keys)
    except (json.JSONDecodeError, TypeError):
        pass
    return overrides


def _set_running(db: Session, exp: Experiment, gpu: GPU) -> None:
    exp.status = "running"
    exp.gpu_name = gpu.name
    exp.started_at = datetime.now(timezone.utc)
    gpu.status = "training"
    gpu.current_experiment = exp.name
    gpu.current_step = 0
    db.commit()


def dispatch_local_experiment(db: Session, exp: Experiment, gpu: GPU) -> bool:
    overrides = _build_overrides(exp)
    command = f"cd {shlex.quote(gpu.repo_path)} && {overrides} bash infra/run_experiment.sh {shlex.quote(exp.name)} {exp.steps}"
    log_path = f"/tmp/{exp.name}.log"
    pid_path = f"/tmp/{exp.name}.pid"
    wrapped = f"{command} > {shlex.quote(log_path)} 2>&1"
    try:
        proc = subprocess.Popen(
            ["bash", "-lc", wrapped],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid,
            cwd=gpu.repo_path,
        )
    except OSError as exc:
        logger.error(f"Failed to dispatch local experiment {exp.name}: {exc}")
        return False

    Path(pid_path).write_text(str(proc.pid), encoding="utf-8")
    _set_running(db, exp, gpu)
    logger.info(f"Dispatched local experiment {exp.name} -> pid {proc.pid}")
    return True


def dispatch_experiment(db: Session, exp: Experiment, gpu: GPU) -> bool:
    """Dispatch a single experiment to a GPU. Returns True on success."""
    if is_local_gpu(gpu):
        return dispatch_local_experiment(db, exp, gpu)

    overrides = _build_overrides(exp)
    safe_name = shlex.quote(exp.name)
    cmd = f"cd {gpu.repo_path} && {overrides} bash infra/run_experiment.sh {safe_name} {exp.steps}".strip()
    bg_cmd = f"nohup bash -c '{cmd}' > /tmp/{safe_name}.log 2>&1 &"

    logger.info(f"Dispatching {exp.name} ({exp.steps} steps) -> {gpu.name}")
    returncode, output = ssh_exec(gpu, bg_cmd, timeout=15)

    if returncode == 0:
        _set_running(db, exp, gpu)
        logger.info(f"Dispatched {exp.name} -> {gpu.name}")
        return True
    else:
        logger.error(f"Failed to dispatch {exp.name} -> {gpu.name}: {output}")
        return False


async def scheduler_loop():
    """Main scheduler loop. Call this as a background task."""
    logger.info("Scheduler started")
    while True:
        try:
            db = SessionLocal()
            try:
                ensure_local_gpu(db)
                idle_gpus = get_idle_gpus(db)
                if idle_gpus:
                    queued = get_queued_experiments(db)
                    for exp, gpu in zip(queued, idle_gpus):
                        dispatch_experiment(db, exp, gpu)
            finally:
                db.close()
        except Exception:
            logger.exception("Scheduler error")

        await asyncio.sleep(POLL_INTERVAL)
