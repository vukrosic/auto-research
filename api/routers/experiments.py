"""Experiment routes — submit, list, cancel, monitor."""
import json
import os
import signal
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.config import settings
from api.adapters.repo_adapter import call_repo_adapter
from api.database import get_db
from api.models import Experiment, GPU, User
from api.routers.auth import get_current_user
from api.routers.fleet import ensure_local_gpu, is_local_gpu, ssh_exec
from engine.sync import export_queue_file
from engine.scheduler import dispatch_experiment
from engine.collector import check_experiment

router = APIRouter()

FAST_DEFAULT_OVERRIDES = {
    "NUM_LAYERS": 2,
    "MODEL_DIM": 128,
    "NUM_HEADS": 2,
    "NUM_KV_HEADS": 1,
    "MLP_MULT": 1,
    "TRAIN_BATCH_TOKENS": 131072,
    "VAL_BATCH_SIZE": 131072,
    "VAL_LOSS_EVERY": 50,
    "TRAIN_LOG_EVERY": 10,
}

STAGE_THRESHOLDS = [
    (800, "explore"),
    (5000, "validate"),
    (float("inf"), "full"),
]


def classify_stage(steps: int) -> str:
    for threshold, stage in STAGE_THRESHOLDS:
        if steps <= threshold:
            return stage
    return "full"


def merge_fast_profile(config: dict | None) -> dict:
    merged = dict(FAST_DEFAULT_OVERRIDES)
    if config:
        merged.update(config)
    return merged


def maybe_reset_usage(user: User, db: Session):
    """Reset usage counters if 30+ days since last reset."""
    now = datetime.now(timezone.utc)
    reset_at = user.usage_reset_at
    if reset_at and reset_at.tzinfo is None:
        reset_at = reset_at.replace(tzinfo=timezone.utc)
    if not reset_at or (now - reset_at) >= timedelta(days=30):
        user.explore_runs_used = 0
        user.validate_runs_used = 0
        user.full_runs_used = 0
        user.usage_reset_at = now
        db.flush()


def check_tier_limits(user: User, stage: str, db: Session):
    """Enforce monthly experiment limit. All stages allowed on all tiers — only total count differs."""
    limits = settings.tier_limits.get(user.tier, {})
    max_exp = limits.get("experiments", 0)

    # Unlimited tiers
    if max_exp == -1:
        return

    if max_exp == 0:
        raise HTTPException(status_code=403, detail="No experiment quota on this tier.")

    if user.explore_runs_used >= max_exp:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly limit reached ({user.explore_runs_used}/{max_exp}). Resets in {days_until_reset(user)} days.",
        )


def increment_usage(user: User, stage: str):
    """Increment the unified experiment counter."""
    user.explore_runs_used += 1


def days_until_reset(user: User) -> int:
    now = datetime.now(timezone.utc)
    reset_at = user.usage_reset_at
    if reset_at and reset_at.tzinfo is None:
        reset_at = reset_at.replace(tzinfo=timezone.utc)
    if not reset_at:
        return 30
    next_reset = reset_at + timedelta(days=30)
    return max(0, (next_reset - now).days)


class ExperimentCreate(BaseModel):
    name: str
    template: str = "parameter_golf"
    stage: str = "explore"  # ignored — auto-set from steps
    config_overrides: dict = {}
    steps: int = 500


@router.post("/")
def submit_experiment(exp: ExperimentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Submit a new experiment to the queue.

    Stage is auto-determined from steps: <=800 explore, <=5000 validate, >5000 full.
    Enforces tier limits on run count, stage access, and concurrency.
    """
    # Auto-set stage from steps
    stage = classify_stage(exp.steps)

    # Reset usage if 30+ days old
    maybe_reset_usage(current_user, db)

    # Enforce tier limits
    check_tier_limits(current_user, stage, db)

    experiment = Experiment(
        user_id=current_user.id,
        name=exp.name,
        template=exp.template,
        stage=stage,
        config_overrides=json.dumps(merge_fast_profile(exp.config_overrides)),
        steps=exp.steps,
    )
    db.add(experiment)

    # Increment usage counter
    increment_usage(current_user, stage)

    db.commit()
    db.refresh(experiment)

    # Sync queue file so parameter-golf CLI can also run queued experiments
    export_queue_file(db)

    return {"id": experiment.id, "status": "queued", "stage": stage}


@router.get("/")
def list_experiments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List experiments from the repo adapter, falling back to local DB state."""
    try:
        return call_repo_adapter("runs", "list")
    except HTTPException:
        query = db.query(Experiment)
        if current_user.tier != "admin":
            query = query.filter(Experiment.user_id == current_user.id)
        experiments = query.order_by(Experiment.queued_at.desc()).all()
        for exp in experiments:
            if exp.status == "running":
                check_experiment(db, exp)
        for exp in experiments:
            db.refresh(exp)
        return experiments


def _authorize(exp: Experiment, current_user: User) -> None:
    if exp.user_id != current_user.id and current_user.tier != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to control this experiment")


def _kill_running_experiment(db: Session, exp: Experiment) -> None:
    gpu = db.query(GPU).filter(GPU.name == exp.gpu_name).first() if exp.gpu_name else None
    if not gpu:
        return

    if is_local_gpu(gpu):
        pid_path = Path(f"/tmp/{exp.name}.pid")
        if pid_path.exists():
            try:
                pid = int(pid_path.read_text().strip())
                os.killpg(pid, signal.SIGTERM)
            except (ValueError, ProcessLookupError, PermissionError):
                pass
            pid_path.unlink(missing_ok=True)
    else:
        ssh_exec(gpu, f"test -f /tmp/{exp.name}.pid && kill $(cat /tmp/{exp.name}.pid) || pkill -f {exp.name} || true", timeout=10)

    gpu.status = "idle"
    gpu.current_experiment = None
    gpu.current_step = None


@router.post("/{experiment_id}/start")
def start_experiment(experiment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Run a queued experiment immediately on an idle GPU, preferring the local 3090."""
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    _authorize(exp, current_user)
    if exp.status != "queued":
        raise HTTPException(status_code=400, detail="Only queued experiments can be started")

    ensure_local_gpu(db)
    gpu = db.query(GPU).filter(GPU.host == "localhost").first()
    if not gpu or gpu.status not in ("idle", "online"):
        raise HTTPException(status_code=409, detail="Local GPU is busy")

    if not dispatch_experiment(db, exp, gpu):
        raise HTTPException(status_code=500, detail="Failed to start experiment")
    return {"status": "running", "gpu": gpu.name}


@router.post("/{experiment_id}/refresh")
def refresh_experiment(experiment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Refresh progress/result state for one experiment immediately."""
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    _authorize(exp, current_user)
    if exp.status == "running":
        check_experiment(db, exp)
        db.refresh(exp)
    return exp


@router.delete("/{experiment_id}")
def cancel_experiment(experiment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Cancel a queued or running experiment."""
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    _authorize(exp, current_user)
    if exp.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Cannot cancel finished experiment")
    if exp.status == "running":
        _kill_running_experiment(db, exp)
    exp.status = "cancelled"
    db.commit()
    return {"status": "cancelled"}
