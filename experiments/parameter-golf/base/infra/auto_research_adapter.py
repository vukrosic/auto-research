#!/usr/bin/env python3
"""Thin JSON adapter for external shells such as auto-research."""

from __future__ import annotations

import json
import re
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_ROOT = ROOT / "research"
SPECS_ROOT = ROOT / "experiments" / "specs"
RESULTS_ROOT = ROOT / "results"
QUEUE_FILE = ROOT / "queues" / "active.txt"
VALID_DOC_TYPES = ("explorations", "hypotheses", "findings")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def parse_frontmatter(text: str) -> tuple[dict, str]:
    meta: dict[str, object] = {}
    body = text
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if match:
        body = text[match.end():]
        for line in match.group(1).splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            value = value.strip().strip('"').strip("'")
            if value.startswith("[") and value.endswith("]"):
                value = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",") if v.strip()]
            meta[key.strip()] = value
    return meta, body


def classify_stage(steps: int) -> str:
    if steps <= 800:
        return "explore"
    if steps <= 5000:
        return "validate"
    return "full"


def infer_lane(name: str, *, payload: dict | None = None, result_dir: Path | None = None) -> str | None:
    if isinstance(payload, dict):
        lane = payload.get("lane")
        if isinstance(lane, str) and lane.strip():
            return lane.strip()
    if name.startswith("micro_nano_") or name.startswith("micro_micro_"):
        return "micro_explore"
    if result_dir is not None and result_dir.parent.name == "micro_explore":
        return "micro_explore"
    return None


def read_progress_from_log(name: str) -> tuple[int | None, float | None]:
    log_path = Path(f"/tmp/{name}.log")
    if not log_path.exists():
        return None, None
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
    except OSError:
        return None, None

    current_step = None
    val_bpb = None
    for line in reversed(lines):
        if current_step is None and "step:" in line:
            match = re.search(r"step:(\d+)/(\d+)", line)
            if match:
                current_step = int(match.group(1))
        if val_bpb is None:
            match = re.search(r"val_bpb:([0-9.]+)", line)
            if match:
                val_bpb = float(match.group(1))
        if current_step is not None and val_bpb is not None:
            break
    return current_step, val_bpb


def find_result_dir(name: str) -> Path | None:
    direct = RESULTS_ROOT / name
    if (direct / "summary.json").exists():
        return direct
    for summary in RESULTS_ROOT.glob(f"**/{name}/summary.json"):
        return summary.parent
    return None


def running_runs() -> list[dict]:
    runs: list[dict] = []
    for pid_file in sorted(Path("/tmp").glob("*.pid")):
        name = pid_file.stem
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
        if not Path(f"/proc/{pid}").exists():
            continue
        if not Path(f"/tmp/{name}.log").exists() and find_result_dir(name) is None:
            continue

        current_step, val_bpb = read_progress_from_log(name)
        result_dir = find_result_dir(name)
        steps = 0
        completed_at = None
        if result_dir:
            summary = load_json(result_dir / "summary.json")
            if isinstance(summary, dict):
                last_eval = summary.get("last_eval") or {}
                steps = int(last_eval.get("max_steps") or last_eval.get("step") or 0)
                completed_at = summary.get("generated_at_utc")
        if steps == 0:
            log_path = Path(f"/tmp/{name}.log")
            if log_path.exists():
                try:
                    text = log_path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    text = ""
                match = re.search(r"iterations:(\d+)", text)
                if match:
                    steps = int(match.group(1))

        runs.append({
            "id": name,
            "name": name,
            "status": "running",
            "stage": classify_stage(steps or max(current_step or 0, 1)),
            "lane": infer_lane(name),
            "steps": steps,
            "current_step": current_step or 0,
            "val_bpb": val_bpb,
            "queued_at": None,
            "started_at": None,
            "completed_at": completed_at,
            "gpu_name": "local",
            "config_overrides": {},
            "readonly": True,
        })
    return runs


def queued_runs() -> list[dict]:
    if not QUEUE_FILE.exists():
        return []
    runs: list[dict] = []
    try:
        lines = QUEUE_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = shlex.split(line)
        if len(parts) < 2:
            continue
        name = parts[0]
        try:
            steps = int(parts[1])
        except ValueError:
            continue
        overrides = {}
        for part in parts[2:]:
            if "=" in part:
                key, value = part.split("=", 1)
                overrides[key] = value
        runs.append({
            "id": name,
            "name": name,
            "status": "queued",
            "stage": classify_stage(steps),
            "lane": infer_lane(name),
            "steps": steps,
            "current_step": 0,
            "val_bpb": None,
            "queued_at": QUEUE_FILE.stat().st_mtime,
            "started_at": None,
            "completed_at": None,
            "gpu_name": None,
            "config_overrides": overrides,
            "readonly": True,
        })
    return runs


def completed_runs() -> list[dict]:
    runs: list[dict] = []
    for summary_path in sorted(RESULTS_ROOT.glob("**/summary.json")):
        summary = load_json(summary_path)
        if not isinstance(summary, dict):
            continue
        name = summary_path.parent.name
        last_eval = summary.get("last_eval") or {}
        final_quant = summary.get("final_quant_eval") or {}
        steps = int(last_eval.get("max_steps") or last_eval.get("step") or 0)
        stage = classify_stage(steps)
        if summary_path.parent.parent != RESULTS_ROOT:
            stage = summary_path.parent.parent.name if summary_path.parent.parent.name in {"explore", "validate", "full", "misc"} else stage
        metadata = load_json(summary_path.parent / "metadata.json")
        config = metadata.get("config", {}) if isinstance(metadata, dict) else {}
        runs.append({
            "id": name,
            "name": name,
            "status": "completed",
            "stage": stage,
            "lane": infer_lane(name, result_dir=summary_path.parent),
            "steps": steps,
            "current_step": int(last_eval.get("step") or steps),
            "val_bpb": final_quant.get("val_bpb") or last_eval.get("val_bpb"),
            "queued_at": None,
            "started_at": None,
            "completed_at": summary.get("generated_at_utc") or datetime.fromtimestamp(summary_path.stat().st_mtime, tz=timezone.utc).isoformat(),
            "gpu_name": "local",
            "config_overrides": config,
            "readonly": True,
        })
    return runs


def list_runs() -> list[dict]:
    merged: dict[str, tuple[int, dict]] = {}
    for priority, items in ((3, running_runs()), (2, queued_runs()), (1, completed_runs())):
        for item in items:
            current = merged.get(item["name"])
            if current is None or priority > current[0]:
                merged[item["name"]] = (priority, item)

    runs = [payload for _, payload in merged.values()]
    runs.sort(
        key=lambda item: item.get("completed_at") or item.get("started_at") or item.get("queued_at") or item["name"],
        reverse=True,
    )
    return runs


def list_docs() -> dict[str, list[dict]]:
    payload: dict[str, list[dict]] = {}
    for doc_type in VALID_DOC_TYPES:
        folder = RESEARCH_ROOT / doc_type
        docs = []
        if folder.exists():
            for path in sorted(folder.glob("*.md")):
                if path.name == "TEMPLATE.md":
                    continue
                text = path.read_text(encoding="utf-8")
                meta, body = parse_frontmatter(text)
                title = str(meta.get("title", "")).strip()
                if not title:
                    match = re.search(r"^#\s+(.+)", body, re.MULTILINE)
                    title = match.group(1) if match else path.stem
                docs.append({
                    "filename": path.name,
                    "slug": path.stem,
                    "type": doc_type,
                    "title": title,
                    "status": meta.get("status", ""),
                    "date": meta.get("date", meta.get("created", "")),
                    "meta": meta,
                    "readonly": True,
                })
        payload[doc_type] = docs
    return payload


def get_doc(doc_type: str, slug: str) -> dict:
    path = RESEARCH_ROOT / doc_type / f"{slug}.md"
    if not path.exists():
        raise FileNotFoundError(f"document not found: {doc_type}/{slug}")
    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    title = str(meta.get("title", "")).strip()
    if not title:
        match = re.search(r"^#\s+(.+)", body, re.MULTILINE)
        title = match.group(1) if match else slug
    return {
        "filename": path.name,
        "slug": slug,
        "type": doc_type,
        "title": title,
        "status": meta.get("status", ""),
        "meta": meta,
        "content": text,
        "body": body,
        "readonly": True,
    }


def list_specs() -> list[dict]:
    latest_by_name = {run["name"]: run for run in list_runs()}
    specs: list[dict] = []
    if not SPECS_ROOT.exists():
        return specs
    for path in sorted(SPECS_ROOT.glob("*.json")):
        payload = load_json(path)
        if not isinstance(payload, dict) or path.name == "TEMPLATE.json":
            continue
        slug = str(payload.get("spec_id", path.stem))
        specs.append({
            "id": slug,
            "slug": slug,
            "name": payload.get("name", slug),
            "spec_type": payload.get("spec_type", "exploration"),
            "template": payload.get("template", "repo"),
            "stage": payload.get("stage", classify_stage(int(payload.get("steps", 0) or 0))),
            "lane": infer_lane(slug, payload=payload),
            "runner_profile": payload.get("runner_profile"),
            "baseline_spec_id": payload.get("baseline_spec_id"),
            "steps": int(payload.get("steps", 0) or 0),
            "config_overrides": payload.get("config_overrides", {}),
            "promotion_policy": payload.get("promotion_policy"),
            "promotion_max": payload.get("promotion_max"),
            "promotion_margin_bpb": payload.get("promotion_margin_bpb"),
            "linked_docs": payload.get("linked_docs", []),
            "tags": payload.get("tags", []),
            "notes": payload.get("notes", ""),
            "desired_state": payload.get("desired_state", "draft"),
            "source_path": str(path),
            "origin": "repo",
            "updated_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
            "last_synced_at": None,
            "content": json.dumps(payload, indent=2, sort_keys=True),
            "latest_run": latest_by_name.get(slug),
            "readonly": True,
        })
    return specs


def get_spec(slug: str) -> dict:
    path = SPECS_ROOT / f"{slug}.json"
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise FileNotFoundError(f"spec not found: {slug}")
    latest_by_name = {run["name"]: run for run in list_runs()}
    return {
        "id": slug,
        "slug": slug,
        "name": payload.get("name", slug),
        "spec_type": payload.get("spec_type", "exploration"),
        "template": payload.get("template", "repo"),
        "stage": payload.get("stage", classify_stage(int(payload.get("steps", 0) or 0))),
        "lane": infer_lane(slug, payload=payload),
        "runner_profile": payload.get("runner_profile"),
        "baseline_spec_id": payload.get("baseline_spec_id"),
        "steps": int(payload.get("steps", 0) or 0),
        "config_overrides": payload.get("config_overrides", {}),
        "promotion_policy": payload.get("promotion_policy"),
        "promotion_max": payload.get("promotion_max"),
        "promotion_margin_bpb": payload.get("promotion_margin_bpb"),
        "linked_docs": payload.get("linked_docs", []),
        "tags": payload.get("tags", []),
        "notes": payload.get("notes", ""),
        "desired_state": payload.get("desired_state", "draft"),
        "source_path": str(path),
        "origin": "repo",
        "updated_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
        "last_synced_at": None,
        "content": json.dumps(payload, indent=2, sort_keys=True),
        "latest_run": latest_by_name.get(slug),
        "readonly": True,
    }


def emit(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        emit({"error": "usage: auto_research_adapter.py <research|specs|runs> ...", "generated_at": utcnow()})
        return 1

    area = argv[1]
    try:
        if area == "research" and len(argv) >= 3 and argv[2] == "list":
            emit(list_docs())
            return 0
        if area == "research" and len(argv) == 5 and argv[2] == "get":
            emit(get_doc(argv[3], argv[4]))
            return 0
        if area == "specs" and len(argv) >= 3 and argv[2] == "list":
            emit(list_specs())
            return 0
        if area == "specs" and len(argv) == 4 and argv[2] == "get":
            emit(get_spec(argv[3]))
            return 0
        if area == "runs" and len(argv) >= 3 and argv[2] == "list":
            emit(list_runs())
            return 0
    except FileNotFoundError as exc:
        emit({"error": str(exc), "generated_at": utcnow()})
        return 2

    emit({"error": f"unknown command: {' '.join(argv[1:])}", "generated_at": utcnow()})
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
