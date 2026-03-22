"""Admin routes — Vuk's one-click management."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.database import get_db
from api.models import User, Competition

router = APIRouter()


class UserCreate(BaseModel):
    email: str
    name: str = ""
    tier: str = "starter"


class CompetitionCreate(BaseModel):
    name: str
    description: str = ""
    template: str = "parameter_golf"
    metric: str = "val_bpb"
    max_steps: int = 13780
    prize_description: str = ""
    sponsor: str = ""


@router.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Manually provision a user (fallback if Skool webhook isn't set up)."""
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        existing.tier = user.tier
        db.commit()
        return {"action": "updated", "email": user.email, "tier": user.tier}

    new_user = User(email=user.email, name=user.name, tier=user.tier)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"action": "created", "email": new_user.email, "api_key": new_user.api_key}


@router.post("/competitions")
def create_competition(comp: CompetitionCreate, db: Session = Depends(get_db)):
    """Create a new competition (or approve AI-proposed one)."""
    competition = Competition(
        name=comp.name,
        description=comp.description,
        template=comp.template,
        metric=comp.metric,
        max_steps=comp.max_steps,
        prize_description=comp.prize_description,
        sponsor=comp.sponsor,
    )
    db.add(competition)
    db.commit()
    db.refresh(competition)
    return {"id": competition.id, "name": competition.name}


@router.get("/dashboard")
def admin_dashboard(db: Session = Depends(get_db)):
    """One-screen overview for Vuk. Glance at this once/day max."""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active).count()
    # TODO: active experiments, GPU utilization, revenue estimate, flagged issues
    return {
        "total_users": total_users,
        "active_users": active_users,
        "flagged_issues": 0,  # TODO: from support tickets
        "gpu_utilization": "TODO",
        "monthly_revenue_estimate": "TODO",
    }
