"""Experiment scheduler — dispatches queued experiments to idle GPUs.

Runs as a background task in FastAPI. Polls every 30s for:
1. Queued experiments (ordered by tier priority, then queue time)
2. Idle GPUs
3. Matches them and dispatches via SSH.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import case
from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models import User, Experiment, GPU
from api.routers.fleet import ssh_exec

logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # seconds

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


def dispatch_experiment(db: Session, exp: Experiment, gpu: GPU) -> bool:
    """Dispatch a single experiment to a GPU. Returns True on success."""
    # Build command
    overrides = ""
    try:
        config = json.loads(exp.config_overrides) if exp.config_overrides else {}
        if config:
            # Filter out metadata keys (SEED, RUN_ID, etc. are set by the runner)
            env_keys = {"MATRIX_LR", "SCALAR_LR", "EMBED_LR", "NUM_LAYERS", "MODEL_DIM",
                        "NUM_HEADS", "NUM_KV_HEADS", "MLP_MULT", "WARMDOWN_ITERS",
                        "WARMUP_STEPS", "LOGIT_SOFTCAP", "QK_GAIN_INIT", "ROPE_BASE",
                        "MUON_MOMENTUM", "GRAD_CLIP_NORM", "TIED_EMBED_LR", "TIED_EMBED_INIT_STD"}
            overrides = " ".join(f"{k}={v}" for k, v in config.items() if k in env_keys)
    except (json.JSONDecodeError, TypeError):
        pass

    cmd = f"cd {gpu.repo_path} && {overrides} bash infra/run_experiment.sh {exp.name} {exp.steps}".strip()
    bg_cmd = f"nohup bash -c '{cmd}' > /tmp/{exp.name}.log 2>&1 &"

    logger.info(f"Dispatching {exp.name} ({exp.steps} steps) -> {gpu.name}")
    returncode, output = ssh_exec(gpu, bg_cmd, timeout=15)

    if returncode == 0:
        exp.status = "running"
        exp.gpu_name = gpu.name
        exp.started_at = datetime.now(timezone.utc)
        gpu.status = "training"
        gpu.current_experiment = exp.name
        gpu.current_step = 0
        db.commit()
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
                idle_gpus = get_idle_gpus(db)
                if not idle_gpus:
                    continue

                queued = get_queued_experiments(db)
                if not queued:
                    continue

                for exp, gpu in zip(queued, idle_gpus):
                    dispatch_experiment(db, exp, gpu)
            finally:
                db.close()
        except Exception:
            logger.exception("Scheduler error")

        await asyncio.sleep(POLL_INTERVAL)
