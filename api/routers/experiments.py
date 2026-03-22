"""Experiment routes — submit, list, cancel, monitor."""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.database import get_db
from api.models import Experiment, User
from api.routers.auth import get_current_user

router = APIRouter()


class ExperimentCreate(BaseModel):
    name: str
    template: str = "parameter_golf"
    stage: str = "explore"  # explore, validate, full
    config_overrides: dict = {}
    steps: int = 500
    competition_id: int | None = None


@router.post("/")
def submit_experiment(exp: ExperimentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Submit a new experiment to the queue."""
    # TODO: check user tier limits, check concurrent limit
    experiment = Experiment(
        user_id=current_user.id,
        name=exp.name,
        template=exp.template,
        stage=exp.stage,
        config_overrides=json.dumps(exp.config_overrides),
        steps=exp.steps,
        competition_id=exp.competition_id,
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return {"id": experiment.id, "status": "queued"}


@router.get("/")
def list_experiments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List user's experiments. Admins see all; others see only their own."""
    query = db.query(Experiment)
    if current_user.tier != "admin":
        query = query.filter(Experiment.user_id == current_user.id)
    experiments = query.order_by(Experiment.queued_at.desc()).limit(50).all()
    return experiments


@router.delete("/{experiment_id}")
def cancel_experiment(experiment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Cancel a queued or running experiment."""
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if exp.user_id != current_user.id and current_user.tier != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to cancel this experiment")
    if exp.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Cannot cancel finished experiment")
    exp.status = "cancelled"
    # TODO: if running, SSH kill the process
    db.commit()
    return {"status": "cancelled"}
