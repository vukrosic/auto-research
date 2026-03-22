"""Experiment routes — submit, list, cancel, monitor."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.database import get_db
from api.models import Experiment

router = APIRouter()


class ExperimentCreate(BaseModel):
    name: str
    template: str = "parameter_golf"
    stage: str = "explore"  # explore, validate, full
    config_overrides: dict = {}
    steps: int = 500
    competition_id: int | None = None


@router.post("/")
def submit_experiment(exp: ExperimentCreate, db: Session = Depends(get_db)):
    """Submit a new experiment to the queue."""
    # TODO: check user tier limits, check concurrent limit
    experiment = Experiment(
        user_id=1,  # TODO: from JWT
        name=exp.name,
        template=exp.template,
        stage=exp.stage,
        config_overrides=str(exp.config_overrides),
        steps=exp.steps,
        competition_id=exp.competition_id,
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return {"id": experiment.id, "status": "queued"}


@router.get("/")
def list_experiments(db: Session = Depends(get_db)):
    """List user's experiments."""
    # TODO: filter by user from JWT
    experiments = db.query(Experiment).order_by(Experiment.queued_at.desc()).limit(50).all()
    return experiments


@router.delete("/{experiment_id}")
def cancel_experiment(experiment_id: int, db: Session = Depends(get_db)):
    """Cancel a queued or running experiment."""
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if exp.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Cannot cancel finished experiment")
    exp.status = "cancelled"
    # TODO: if running, SSH kill the process
    db.commit()
    return {"status": "cancelled"}
