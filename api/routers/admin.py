"""Admin routes — management dashboard and sync operations."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.database import get_db
from api.models import User, GPU, Experiment, SupportTicket
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
    }


@router.post("/sync-results")
def sync_results(db: Session = Depends(get_db)):
    """Sync parameter-golf result files into the DB index.

    Indexes new results from CLI runs and updates existing result_paths.
    """
    from engine.sync import sync_results_to_db
    return sync_results_to_db(db)


@router.post("/import-creds")
def import_creds(db: Session = Depends(get_db)):
    """Import GPUs from existing gpu_creds.sh into the DB.

    One-time bootstrap when connecting to an existing parameter-golf setup.
    """
    from engine.sync import import_creds_from_file
    return import_creds_from_file(db)


@router.post("/sync-creds")
def sync_creds(db: Session = Depends(get_db)):
    """Write gpu_creds.sh from DB so parameter-golf CLI works standalone."""
    from engine.sync import sync_creds_to_file
    path = sync_creds_to_file(db)
    return {"written_to": path}


@router.get("/db")
def view_database(db: Session = Depends(get_db)):
    """View all database contents. For debugging."""
    users = db.query(User).all()
    experiments = db.query(Experiment).all()
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
             "gpu_util": g.gpu_utilization, "gpu_temp": g.gpu_temp, "hourly_rate": g.hourly_rate,
             "repo_path": g.repo_path, "last_seen": str(g.last_seen), "added": str(g.added_at)}
            for g in gpus
        ],
        "experiments": [
            {"id": e.id, "user_id": e.user_id, "name": e.name, "template": e.template,
             "stage": e.stage, "status": e.status, "steps": e.steps,
             "current_step": e.current_step, "val_bpb": e.val_bpb,
             "gpu": e.gpu_name, "result_path": e.result_path, "config": e.config_overrides}
            for e in experiments
        ],
        "support_tickets": [
            {"id": t.id, "user_id": t.user_id, "message": t.message,
             "resolved_by_ai": t.resolved_by_ai, "needs_human": t.needs_human}
            for t in tickets
        ],
    }
