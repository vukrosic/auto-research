"""Read-only experiment spec routes backed by the repo adapter."""
from fastapi import APIRouter, HTTPException

from api.adapters.repo_adapter import call_repo_adapter

router = APIRouter()


@router.get("/")
def list_specs():
    return call_repo_adapter("specs", "list")


@router.get("/{spec_slug}")
def get_spec(spec_slug: str):
    return call_repo_adapter("specs", "get", spec_slug)


@router.post("/")
def create_spec():
    raise HTTPException(status_code=405, detail="Create specs in the research repo")


@router.put("/{spec_slug}")
def update_spec(spec_slug: str):
    raise HTTPException(status_code=405, detail="Edit specs in the research repo")


@router.post("/{spec_slug}/queue")
def queue_spec(spec_slug: str):
    raise HTTPException(status_code=405, detail="Queue runs from the research repo")
