"""Subprocess adapter for repo-owned research data."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from fastapi import HTTPException

from api.config import settings


def adapter_script() -> Path:
    return Path(settings.parameter_golf_path) / "infra" / "auto_research_adapter.py"


def call_repo_adapter(*args: str):
    script = adapter_script()
    if not script.exists():
        raise HTTPException(status_code=500, detail=f"Repo adapter not found: {script}")

    result = subprocess.run(
        ["python3", str(script), *args],
        capture_output=True,
        text=True,
        cwd=settings.parameter_golf_path,
        timeout=30,
    )

    output = result.stdout.strip() or result.stderr.strip()
    try:
        payload = json.loads(output) if output else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Invalid adapter JSON: {exc}") from exc

    if result.returncode != 0:
        raise HTTPException(status_code=404 if result.returncode == 2 else 502, detail=payload.get("error", "Repo adapter error"))

    return payload
