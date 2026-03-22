"""Admin routes — Vuk's one-click management."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.database import get_db
from api.models import User, Competition, GPU, Experiment, SupportTicket

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


@router.get("/db")
def view_database(db: Session = Depends(get_db)):
    """View all database contents. For debugging/admin."""
    users = db.query(User).all()
    experiments = db.query(Experiment).all()
    competitions = db.query(Competition).all()
    gpus = db.query(GPU).all()
    tickets = db.query(SupportTicket).all()

    return {
        "users": [
            {"id": u.id, "email": u.email, "name": u.name, "tier": u.tier,
             "api_key": u.api_key, "explore_used": u.explore_runs_used,
             "validate_used": u.validate_runs_used, "full_used": u.full_runs_used,
             "created": str(u.created_at)}
            for u in users
        ],
        "gpus": [
            {"id": g.id, "name": g.name, "host": g.host, "port": g.port,
             "user": g.user, "status": g.status, "current_experiment": g.current_experiment,
             "gpu_util": g.gpu_utilization, "gpu_temp": g.gpu_temp,
             "repo_path": g.repo_path, "last_seen": str(g.last_seen), "added": str(g.added_at)}
            for g in gpus
        ],
        "experiments": [
            {"id": e.id, "user_id": e.user_id, "name": e.name, "template": e.template,
             "stage": e.stage, "status": e.status, "steps": e.steps,
             "current_step": e.current_step, "val_bpb": e.val_bpb,
             "gpu": e.gpu_name, "config": e.config_overrides}
            for e in experiments
        ],
        "competitions": [
            {"id": c.id, "name": c.name, "status": c.status, "metric": c.metric,
             "sponsor": c.sponsor, "prize": c.prize_description}
            for c in competitions
        ],
        "support_tickets": [
            {"id": t.id, "user_id": t.user_id, "message": t.message,
             "resolved_by_ai": t.resolved_by_ai, "needs_human": t.needs_human}
            for t in tickets
        ],
    }
