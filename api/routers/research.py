"""Read-only research routes backed by the repo adapter."""
from fastapi import APIRouter, HTTPException

from api.adapters.repo_adapter import call_repo_adapter

router = APIRouter()

VALID_TYPES = {"explorations", "hypotheses", "findings"}


@router.get("/")
def list_all():
    return call_repo_adapter("research", "list")


@router.get("/template/{doc_type}")
def get_template(doc_type: str):
    raise HTTPException(status_code=405, detail="Templates are controlled in the research repo")


@router.get("/{doc_type}")
def list_by_type(doc_type: str):
    if doc_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type: {doc_type}")
    payload = call_repo_adapter("research", "list")
    return payload.get(doc_type, [])


@router.get("/{doc_type}/{slug}")
def get_doc(doc_type: str, slug: str):
    if doc_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type: {doc_type}")
    return call_repo_adapter("research", "get", doc_type, slug)


@router.put("/{doc_type}/{slug}")
def update_doc(doc_type: str, slug: str):
    raise HTTPException(status_code=405, detail="Edit research documents in the research repo")


@router.post("/{doc_type}")
def create_doc(doc_type: str):
    raise HTTPException(status_code=405, detail="Create research documents in the research repo")


@router.delete("/{doc_type}/{slug}")
def delete_doc(doc_type: str, slug: str):
    raise HTTPException(status_code=405, detail="Delete research documents in the research repo")
