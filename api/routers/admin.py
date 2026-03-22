"""Admin routes — Vuk's one-click management."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.database import get_db
from api.models import User, Competition, GPU, Experiment, SupportTicket
from api.config import settings

router = APIRouter()


class UserCreate(BaseModel):
    email: str
    name: str = ""
    tier: str = "starter"


class UserUpdate(BaseModel):
    tier: str | None = None
    name: str | None = None
    is_active: bool | None = None
    reset_usage: bool = False


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
    """Manually provision a user (after Skool payment)."""
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        existing.tier = user.tier
        if user.name:
            existing.name = user.name
        db.commit()
        return {"action": "updated", "id": existing.id, "email": user.email, "tier": user.tier, "api_key": existing.api_key}

    new_user = User(email=user.email, name=user.name, tier=user.tier)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"action": "created", "id": new_user.id, "email": new_user.email, "tier": new_user.tier, "api_key": new_user.api_key}


@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    """List all users with usage stats."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        exp_count = db.query(Experiment).filter(Experiment.user_id == u.id).count()
        completed = db.query(Experiment).filter(Experiment.user_id == u.id, Experiment.status == "completed").count()
        best = db.query(Experiment).filter(
            Experiment.user_id == u.id, Experiment.val_bpb.isnot(None)
        ).order_by(Experiment.val_bpb.asc()).first()

        limits = settings.tier_limits.get(u.tier, {})
        result.append({
            "id": u.id, "email": u.email, "name": u.name, "tier": u.tier,
            "api_key": u.api_key, "is_active": u.is_active,
            "explore_used": u.explore_runs_used,
            "explore_limit": limits.get("explore", 0),
            "validate_used": u.validate_runs_used,
            "validate_limit": limits.get("validate", 0),
            "full_used": u.full_runs_used,
            "full_limit": limits.get("full", 0),
            "total_experiments": exp_count,
            "completed_experiments": completed,
            "best_bpb": best.val_bpb if best else None,
            "created": str(u.created_at),
            # Estimated social media posts: 1 per 50 completed experiments
            "est_social_posts": completed // 50,
        })
    return result


@router.put("/users/{user_id}")
def update_user(user_id: int, update: UserUpdate, db: Session = Depends(get_db)):
    """Update user tier, status, or reset usage."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}

    if update.tier is not None:
        user.tier = update.tier
    if update.name is not None:
        user.name = update.name
    if update.is_active is not None:
        user.is_active = update.is_active
    if update.reset_usage:
        user.explore_runs_used = 0
        user.validate_runs_used = 0
        user.full_runs_used = 0

    db.commit()
    return {"id": user.id, "email": user.email, "tier": user.tier, "is_active": user.is_active}


@router.post("/competitions")
def create_competition(comp: CompetitionCreate, db: Session = Depends(get_db)):
    """Create a new competition."""
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
    """Full admin overview."""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active).count()
    total_experiments = db.query(Experiment).count()
    running = db.query(Experiment).filter(Experiment.status == "running").count()
    queued = db.query(Experiment).filter(Experiment.status == "queued").count()
    completed = db.query(Experiment).filter(Experiment.status == "completed").count()
    gpus_online = db.query(GPU).filter(GPU.status != "offline", GPU.status != "unknown").count()
    gpus_total = db.query(GPU).count()
    tickets_open = db.query(SupportTicket).filter(SupportTicket.needs_human == True).count()

    # Revenue estimate by tier
    tier_counts = {}
    tier_prices = {"starter": 9, "researcher": 29, "pro": 79, "admin": 0}
    for u in db.query(User).filter(User.is_active, User.tier != "admin").all():
        tier_counts[u.tier] = tier_counts.get(u.tier, 0) + 1
    mrr = sum(tier_prices.get(t, 0) * c for t, c in tier_counts.items())

    # Social media posts estimate (1 per 50 completed experiments)
    est_posts = completed // 50

    return {
        "total_users": total_users,
        "active_users": active_users,
        "tier_breakdown": tier_counts,
        "mrr": mrr,
        "total_experiments": total_experiments,
        "running": running,
        "queued": queued,
        "completed": completed,
        "gpus_online": gpus_online,
        "gpus_total": gpus_total,
        "tickets_open": tickets_open,
        "est_social_posts": est_posts,
    }


@router.get("/db")
def view_database(db: Session = Depends(get_db)):
    """View all database contents. For debugging."""
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
