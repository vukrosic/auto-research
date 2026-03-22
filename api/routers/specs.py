"""Experiment spec routes — repo-backed experiment definitions with DB indexing."""
import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Experiment, ExperimentSpec, User
from api.routers.auth import get_current_user
from api.routers.experiments import check_tier_limits, classify_stage, increment_usage, maybe_reset_usage
from engine.sync import export_queue_file, export_spec_to_repo, sync_specs_to_db

router = APIRouter()


def _loads(text: str, default):
    try:
        return json.loads(text) if text else default
    except (json.JSONDecodeError, TypeError):
        return default


def _serialize_spec(spec: ExperimentSpec) -> dict:
    latest_run = (
        sorted(spec.experiments, key=lambda exp: exp.queued_at or 0, reverse=True)[0]
        if spec.experiments else None
    )
    payload = {
        "id": spec.id,
        "slug": spec.slug,
        "name": spec.name,
        "spec_type": spec.spec_type,
        "template": spec.template,
        "stage": spec.stage,
        "steps": spec.steps,
        "config_overrides": _loads(spec.config_overrides, {}),
        "linked_docs": _loads(spec.linked_docs, []),
        "tags": _loads(spec.tags, []),
        "notes": spec.notes or "",
        "desired_state": spec.desired_state,
        "source_path": spec.source_path,
        "origin": spec.origin,
        "updated_at": spec.updated_at,
        "last_synced_at": spec.last_synced_at,
        "content": json.dumps({
            "spec_id": spec.slug,
            "name": spec.name,
            "spec_type": spec.spec_type,
            "template": spec.template,
            "stage": spec.stage,
            "steps": spec.steps,
            "config_overrides": _loads(spec.config_overrides, {}),
            "linked_docs": _loads(spec.linked_docs, []),
            "tags": _loads(spec.tags, []),
            "notes": spec.notes or "",
            "desired_state": spec.desired_state,
        }, indent=2, sort_keys=True),
    }
    if latest_run:
        payload["latest_run"] = {
            "id": latest_run.id,
            "status": latest_run.status,
            "val_bpb": latest_run.val_bpb,
            "queued_at": latest_run.queued_at,
        }
    else:
        payload["latest_run"] = None
    return payload


def _validate_payload(content: str) -> dict:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"Invalid JSON: {exc}") from exc

    required = {"spec_id", "name", "spec_type", "template", "stage", "steps", "config_overrides", "linked_docs"}
    missing = sorted(required - set(payload))
    if missing:
        raise HTTPException(400, f"Missing required fields: {', '.join(missing)}")

    payload["spec_id"] = re.sub(r"[^a-zA-Z0-9_.-]", "_", str(payload["spec_id"]).strip())
    if not payload["spec_id"]:
        raise HTTPException(400, "spec_id is required")

    payload["steps"] = int(payload["steps"])
    payload["stage"] = classify_stage(payload["steps"])
    payload["config_overrides"] = payload.get("config_overrides", {})
    payload["linked_docs"] = payload.get("linked_docs", [])
    payload["tags"] = payload.get("tags", [])
    payload["notes"] = payload.get("notes", "")
    payload["desired_state"] = payload.get("desired_state", "draft")
    return payload


class SpecCreate(BaseModel):
    filename: str
    content: str


class SpecUpdate(BaseModel):
    content: str


@router.get("/")
def list_specs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sync_specs_to_db(db)
    query = db.query(ExperimentSpec)
    if current_user.tier != "admin":
        query = query.filter(
            (ExperimentSpec.user_id == current_user.id) | (ExperimentSpec.origin == "repo")
        )
    specs = query.order_by(ExperimentSpec.updated_at.desc()).all()
    return [_serialize_spec(spec) for spec in specs]


@router.get("/{spec_id}")
def get_spec(spec_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sync_specs_to_db(db)
    spec = db.query(ExperimentSpec).filter(ExperimentSpec.id == spec_id).first()
    if not spec:
        raise HTTPException(404, "Experiment spec not found")
    if current_user.tier != "admin" and spec.user_id != current_user.id and spec.origin != "repo":
        raise HTTPException(403, "Not authorized to view this spec")
    return _serialize_spec(spec)


@router.post("/")
def create_spec(payload: SpecCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    spec_payload = _validate_payload(payload.content)
    slug = Path(payload.filename).stem or spec_payload["spec_id"]
    slug = re.sub(r"[^a-zA-Z0-9_.-]", "_", slug)
    if slug != spec_payload["spec_id"]:
        raise HTTPException(400, "filename must match spec_id")
    existing = db.query(ExperimentSpec).filter(ExperimentSpec.slug == slug).first()
    if existing:
        raise HTTPException(409, "Experiment spec already exists")

    spec = ExperimentSpec(
        user_id=current_user.id,
        slug=slug,
        name=spec_payload["name"],
        spec_type=spec_payload["spec_type"],
        template=spec_payload["template"],
        stage=spec_payload["stage"],
        steps=spec_payload["steps"],
        config_overrides=json.dumps(spec_payload["config_overrides"], sort_keys=True),
        linked_docs=json.dumps(spec_payload["linked_docs"]),
        tags=json.dumps(spec_payload["tags"]),
        notes=spec_payload["notes"],
        desired_state=spec_payload["desired_state"],
        source_path="",
        origin="web",
    )
    db.add(spec)
    db.flush()
    spec.source_path = export_spec_to_repo(spec)
    db.commit()
    db.refresh(spec)
    return {"ok": True, "id": spec.id, "slug": spec.slug}


@router.put("/{spec_id}")
def update_spec(spec_id: int, payload: SpecUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    spec = db.query(ExperimentSpec).filter(ExperimentSpec.id == spec_id).first()
    if not spec:
        raise HTTPException(404, "Experiment spec not found")
    if current_user.tier != "admin" and spec.user_id != current_user.id:
        raise HTTPException(403, "Not authorized to edit this spec")

    spec_payload = _validate_payload(payload.content)
    if spec_payload["spec_id"] != spec.slug:
        raise HTTPException(400, "spec_id cannot be changed")

    spec.name = spec_payload["name"]
    spec.spec_type = spec_payload["spec_type"]
    spec.template = spec_payload["template"]
    spec.stage = spec_payload["stage"]
    spec.steps = spec_payload["steps"]
    spec.config_overrides = json.dumps(spec_payload["config_overrides"], sort_keys=True)
    spec.linked_docs = json.dumps(spec_payload["linked_docs"])
    spec.tags = json.dumps(spec_payload["tags"])
    spec.notes = spec_payload["notes"]
    spec.desired_state = spec_payload["desired_state"]
    if not spec.source_path:
        spec.source_path = str(Path("/root/parameter-golf/experiments/specs") / f"{spec.slug}.json")
    export_spec_to_repo(spec)
    db.commit()
    return {"ok": True}


@router.post("/{spec_id}/queue")
def queue_spec(spec_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    spec = db.query(ExperimentSpec).filter(ExperimentSpec.id == spec_id).first()
    if not spec:
        raise HTTPException(404, "Experiment spec not found")
    if current_user.tier != "admin" and spec.user_id != current_user.id and spec.origin != "repo":
        raise HTTPException(403, "Not authorized to queue this spec")

    stage = classify_stage(spec.steps)
    maybe_reset_usage(current_user, db)
    check_tier_limits(current_user, stage, db)

    experiment = Experiment(
        user_id=current_user.id,
        spec_id=spec.id,
        name=spec.slug,
        template=spec.template,
        stage=stage,
        config_overrides=spec.config_overrides,
        steps=spec.steps,
    )
    db.add(experiment)
    increment_usage(current_user, stage)

    spec.desired_state = "queued"
    export_spec_to_repo(spec)
    db.commit()
    db.refresh(experiment)
    export_queue_file(db)
    return {"ok": True, "experiment_id": experiment.id, "status": experiment.status}
