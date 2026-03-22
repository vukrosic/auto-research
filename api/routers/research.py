"""Research routes — browse/edit explorations, hypotheses, findings.

Source of truth is markdown files in parameter-golf/research/.
No DB storage — we parse frontmatter directly from files.
"""
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.config import settings

router = APIRouter()

RESEARCH_ROOT = Path(settings.parameter_golf_path) / "research"
VALID_TYPES = {"explorations", "hypotheses", "findings"}


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML-ish frontmatter from markdown. Returns (meta, body)."""
    meta = {}
    body = text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if m:
        body = text[m.end():]
        for line in m.group(1).splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                val = val.strip().strip('"').strip("'")
                # Parse lists like [H001, H002]
                if val.startswith("[") and val.endswith("]"):
                    val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",") if v.strip()]
                meta[key.strip()] = val
    return meta, body


def _build_frontmatter(meta: dict) -> str:
    """Build frontmatter string from dict."""
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f'{k}: [{", ".join(v)}]')
        else:
            lines.append(f'{k}: "{v}"')
    lines.append("---\n")
    return "\n".join(lines)


def _list_docs(doc_type: str) -> list[dict]:
    """List all docs of a given type, sorted by filename."""
    folder = RESEARCH_ROOT / doc_type
    if not folder.exists():
        return []
    docs = []
    for f in sorted(folder.glob("*.md")):
        if f.name == "TEMPLATE.md":
            continue
        text = f.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        # Extract first heading as fallback title
        title = meta.get("title", "")
        if not title:
            hm = re.search(r"^#\s+(.+)", body, re.MULTILINE)
            title = hm.group(1) if hm else f.stem
        docs.append({
            "filename": f.name,
            "slug": f.stem,
            "type": doc_type,
            "title": title,
            "status": meta.get("status", ""),
            "date": meta.get("date", meta.get("created", "")),
            "meta": meta,
        })
    return docs


@router.get("/")
def list_all():
    """List all research documents across all types."""
    result = {}
    for t in VALID_TYPES:
        result[t] = _list_docs(t)
    return result


@router.get("/template/{doc_type}")
def get_template(doc_type: str):
    """Get the template for a document type."""
    if doc_type not in VALID_TYPES:
        raise HTTPException(400, f"Invalid type: {doc_type}")
    path = RESEARCH_ROOT / doc_type / "TEMPLATE.md"
    if not path.exists():
        raise HTTPException(404, "Template not found")
    return {"content": path.read_text(encoding="utf-8")}


@router.get("/{doc_type}")
def list_by_type(doc_type: str):
    """List documents of a specific type."""
    if doc_type not in VALID_TYPES:
        raise HTTPException(400, f"Invalid type: {doc_type}. Must be one of {VALID_TYPES}")
    return _list_docs(doc_type)


@router.get("/{doc_type}/{slug}")
def get_doc(doc_type: str, slug: str):
    """Get a single research document with full content."""
    if doc_type not in VALID_TYPES:
        raise HTTPException(400, f"Invalid type: {doc_type}")
    path = RESEARCH_ROOT / doc_type / f"{slug}.md"
    if not path.exists():
        raise HTTPException(404, f"Document not found: {doc_type}/{slug}")
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    title = meta.get("title", "")
    if not title:
        hm = re.search(r"^#\s+(.+)", body, re.MULTILINE)
        title = hm.group(1) if hm else slug
    return {
        "filename": path.name,
        "slug": slug,
        "type": doc_type,
        "title": title,
        "status": meta.get("status", ""),
        "meta": meta,
        "content": text,
        "body": body,
    }


class DocUpdate(BaseModel):
    content: str


@router.put("/{doc_type}/{slug}")
def update_doc(doc_type: str, slug: str, payload: DocUpdate):
    """Update a research document's full content."""
    if doc_type not in VALID_TYPES:
        raise HTTPException(400, f"Invalid type: {doc_type}")
    path = RESEARCH_ROOT / doc_type / f"{slug}.md"
    if not path.exists():
        raise HTTPException(404, f"Document not found: {doc_type}/{slug}")
    path.write_text(payload.content, encoding="utf-8")
    return {"ok": True, "slug": slug}


class DocCreate(BaseModel):
    filename: str
    content: str


@router.post("/{doc_type}")
def create_doc(doc_type: str, payload: DocCreate):
    """Create a new research document."""
    if doc_type not in VALID_TYPES:
        raise HTTPException(400, f"Invalid type: {doc_type}")
    folder = RESEARCH_ROOT / doc_type
    folder.mkdir(parents=True, exist_ok=True)
    # Sanitize filename
    fname = payload.filename
    if not fname.endswith(".md"):
        fname += ".md"
    fname = re.sub(r"[^a-zA-Z0-9_\-.]", "_", fname)
    path = folder / fname
    if path.exists():
        raise HTTPException(409, f"Document already exists: {fname}")
    path.write_text(payload.content, encoding="utf-8")
    slug = path.stem
    return {"ok": True, "slug": slug, "filename": fname}


@router.delete("/{doc_type}/{slug}")
def delete_doc(doc_type: str, slug: str):
    """Delete a research document."""
    if doc_type not in VALID_TYPES:
        raise HTTPException(400, f"Invalid type: {doc_type}")
    path = RESEARCH_ROOT / doc_type / f"{slug}.md"
    if not path.exists():
        raise HTTPException(404, f"Document not found: {doc_type}/{slug}")
    path.unlink()
    return {"ok": True}


@router.get("/templates/{doc_type}")
def get_template(doc_type: str):
    """Get the template for a document type."""
    if doc_type not in VALID_TYPES:
        raise HTTPException(400, f"Invalid type: {doc_type}")
    path = RESEARCH_ROOT / doc_type / "TEMPLATE.md"
    if not path.exists():
        raise HTTPException(404, "Template not found")
    return {"content": path.read_text(encoding="utf-8")}
