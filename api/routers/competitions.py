"""Competition routes — browse, join, leaderboard."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Competition, Experiment

router = APIRouter()


@router.get("/")
def list_competitions(db: Session = Depends(get_db)):
    """List all competitions."""
    return db.query(Competition).order_by(Competition.created_at.desc()).all()


@router.get("/{competition_id}/leaderboard")
def get_leaderboard(competition_id: int, db: Session = Depends(get_db)):
    """Get competition leaderboard ranked by metric."""
    comp = db.query(Competition).filter(Competition.id == competition_id).first()
    if not comp:
        return {"error": "Competition not found"}

    experiments = (
        db.query(Experiment)
        .filter(Experiment.competition_id == competition_id, Experiment.status == "completed")
        .order_by(Experiment.val_bpb.asc())  # lower = better
        .all()
    )
    return {
        "competition": comp.name,
        "metric": comp.metric,
        "entries": [
            {"rank": i + 1, "user_id": e.user_id, "name": e.name, "val_bpb": e.val_bpb}
            for i, e in enumerate(experiments)
        ],
    }
