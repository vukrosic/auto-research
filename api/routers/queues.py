"""Queue routes — view/edit experiment queues and deploy to GPUs.

Source of truth is queue files in parameter-golf/queues/.
"""
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.config import settings

router = APIRouter()

QUEUES_ROOT = Path(settings.parameter_golf_path) / "queues"


def _parse_queue_line(line: str) -> dict | None:
    """Parse a queue line: <name> <steps> [ENV=val ...]"""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = line.split()
    if len(parts) < 2:
        return None
    name = parts[0]
    try:
        steps = int(parts[1])
    except ValueError:
        return None
    overrides = " ".join(parts[2:]) if len(parts) > 2 else ""
    return {"name": name, "steps": steps, "overrides": overrides}


def _read_queue(filename: str) -> list[dict]:
    """Read a queue file and return parsed entries."""
    path = QUEUES_ROOT / filename
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = _parse_queue_line(line)
        if entry:
            entries.append(entry)
    return entries


@router.get("/active")
def get_active_queue():
    """Get the current active queue."""
    entries = _read_queue("active.txt")
    raw = ""
    path = QUEUES_ROOT / "active.txt"
    if path.exists():
        raw = path.read_text(encoding="utf-8")
    return {"entries": entries, "raw": raw, "count": len(entries)}


class QueueUpdate(BaseModel):
    content: str


@router.put("/active")
def update_active_queue(payload: QueueUpdate):
    """Update the active queue file content."""
    path = QUEUES_ROOT / "active.txt"
    path.write_text(payload.content, encoding="utf-8")
    entries = _read_queue("active.txt")
    return {"ok": True, "count": len(entries)}


@router.get("/files")
def list_queue_files():
    """List all queue files (active + archive)."""
    files = []
    for f in sorted(QUEUES_ROOT.glob("*.txt")):
        entries = _read_queue(f.name)
        files.append({"filename": f.name, "count": len(entries), "active": f.name == "active.txt"})
    # Also list archive
    archive = QUEUES_ROOT / "archive"
    if archive.exists():
        for f in sorted(archive.glob("*.txt")):
            entries = []
            for line in f.read_text(encoding="utf-8").splitlines():
                entry = _parse_queue_line(line)
                if entry:
                    entries.append(entry)
            files.append({"filename": f"archive/{f.name}", "count": len(entries), "active": False})
    return files


@router.get("/file/{filename:path}")
def get_queue_file(filename: str):
    """Get contents of a specific queue file."""
    path = QUEUES_ROOT / filename
    if not path.exists():
        raise HTTPException(404, f"Queue file not found: {filename}")
    raw = path.read_text(encoding="utf-8")
    entries = []
    for line in raw.splitlines():
        entry = _parse_queue_line(line)
        if entry:
            entries.append(entry)
    return {"filename": filename, "entries": entries, "raw": raw}


@router.get("/plans")
def list_wave_plans():
    """List wave plan markdown files."""
    plans = []
    for f in sorted(QUEUES_ROOT.glob("*_plan.md")):
        text = f.read_text(encoding="utf-8")
        # Extract first heading as title
        title = f.stem
        hm = re.search(r"^#\s+(.+)", text, re.MULTILINE)
        if hm:
            title = hm.group(1)
        plans.append({"filename": f.name, "title": title})
    return plans


@router.get("/plan/{filename}")
def get_wave_plan(filename: str):
    """Get contents of a wave plan file."""
    path = QUEUES_ROOT / filename
    if not path.exists():
        raise HTTPException(404, f"Plan not found: {filename}")
    return {"filename": filename, "content": path.read_text(encoding="utf-8")}
