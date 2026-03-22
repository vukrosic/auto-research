"""Results routes — view, compare, export.

Result data lives in parameter-golf's JSON files (source of truth).
The DB caches val_bpb and result_path for fast queries.
"""
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Experiment
from engine.sync import find_result_path, read_result_json

router = APIRouter()


def _load_full_result(exp: Experiment) -> dict:
    """Load full result data from the JSON file, falling back to DB fields."""
    base = {
        "id": exp.id,
        "name": exp.name,
        "stage": exp.stage,
        "steps": exp.steps,
        "status": exp.status,
        "val_bpb": exp.val_bpb,
        "gpu_name": exp.gpu_name,
        "config_overrides": exp.config_overrides,
        "queued_at": str(exp.queued_at) if exp.queued_at else None,
        "started_at": str(exp.started_at) if exp.started_at else None,
        "completed_at": str(exp.completed_at) if exp.completed_at else None,
    }

    # Try to load full result from file
    summary_path = None
    if exp.result_path:
        p = Path(exp.result_path)
        if p.exists():
            summary_path = p
    if not summary_path:
        summary_path = find_result_path(exp.name)

    if summary_path:
        summary = read_result_json(summary_path)
        if summary:
            base["summary"] = summary

        # Also load metadata if available
        metadata_path = summary_path.parent / "metadata.json"
        if metadata_path.exists():
            metadata = read_result_json(metadata_path)
            if metadata:
                base["metadata"] = metadata

    return base


@router.get("/{experiment_id}")
def get_result(experiment_id: int, db: Session = Depends(get_db)):
    """Get detailed results for an experiment, including full JSON from files."""
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return _load_full_result(exp)


@router.get("/compare/{id1}/{id2}")
def compare_results(id1: int, id2: int, db: Session = Depends(get_db)):
    """Compare two experiments side by side with full result data."""
    e1 = db.query(Experiment).filter(Experiment.id == id1).first()
    e2 = db.query(Experiment).filter(Experiment.id == id2).first()
    if not e1 or not e2:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"experiments": [_load_full_result(e1), _load_full_result(e2)]}


@router.get("/by-name/{name}")
def get_result_by_name(name: str, db: Session = Depends(get_db)):
    """Get experiment result by name. Checks DB first, then files."""
    exp = db.query(Experiment).filter(Experiment.name == name).first()
    if exp:
        return _load_full_result(exp)

    # Not in DB — check if result exists on disk
    summary_path = find_result_path(name)
    if not summary_path:
        raise HTTPException(status_code=404, detail="Result not found")

    summary = read_result_json(summary_path)
    metadata_path = summary_path.parent / "metadata.json"
    metadata = read_result_json(metadata_path) if metadata_path.exists() else None

    return {
        "name": name,
        "status": "completed",
        "source": "files_only",
        "summary": summary,
        "metadata": metadata,
    }
