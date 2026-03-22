"""Results routes — view, compare, export."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Experiment

router = APIRouter()


@router.get("/{experiment_id}")
def get_result(experiment_id: int, db: Session = Depends(get_db)):
    """Get detailed results for an experiment."""
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        return {"error": "Not found"}
    return exp


@router.get("/compare/{id1}/{id2}")
def compare_results(id1: int, id2: int, db: Session = Depends(get_db)):
    """Compare two experiments side by side."""
    e1 = db.query(Experiment).filter(Experiment.id == id1).first()
    e2 = db.query(Experiment).filter(Experiment.id == id2).first()
    if not e1 or not e2:
        return {"error": "Experiment not found"}
    return {
        "experiments": [
            {"id": e1.id, "name": e1.name, "val_bpb": e1.val_bpb, "config": e1.config_overrides},
            {"id": e2.id, "name": e2.name, "val_bpb": e2.val_bpb, "config": e2.config_overrides},
        ]
    }
