"""Sync layer between auto-research DB and parameter-golf files.

auto-research DB owns: users, GPU creds, scheduling state
parameter-golf files own: experiment results, queue format, research docs

This module bridges the two so either system works standalone.
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from api.config import settings
from api.database import Base, SessionLocal, engine
from api.models import GPU, Experiment, ExperimentSpec, User

logger = logging.getLogger(__name__)

PG_PATH = Path(settings.parameter_golf_path)
CREDS_FILE = PG_PATH / "infra" / "gpu_creds.sh"
RESULTS_DIR = PG_PATH / "results"
QUEUE_FILE = PG_PATH / "queues" / "active.txt"
SPECS_DIR = PG_PATH / "experiments" / "specs"

STAGE_BY_STEPS = [
    (800, "explore"),
    (5000, "validate"),
    (float("inf"), "full"),
]


def classify_stage(steps: int) -> str:
    for threshold, stage in STAGE_BY_STEPS:
        if steps <= threshold:
            return stage
    return "full"


# ---------------------------------------------------------------------------
# GPU creds: DB → gpu_creds.sh
# ---------------------------------------------------------------------------

def sync_creds_to_file(db: Session) -> str:
    """Generate infra/gpu_creds.sh from the DB so parameter-golf CLI works standalone.

    Returns the path written to.
    """
    gpus = db.query(GPU).order_by(GPU.added_at.asc()).all()
    if not gpus:
        logger.info("No GPUs in DB, skipping creds sync")
        return ""

    # Use the host from the first GPU (they share a proxy)
    host = gpus[0].host

    lines = [
        "# GPU credentials — auto-generated from auto-research DB",
        "# DO NOT EDIT MANUALLY — changes will be overwritten on next GPU add/remove",
        f'HOST="{host}"',
    ]
    for g in gpus:
        lines.append(f"GPU_{g.name}_PORT={g.port}")
        lines.append(f'GPU_{g.name}_PASS="{g.password}"')
        if g.hourly_rate:
            lines.append(f"GPU_{g.name}_RATE={g.hourly_rate:.2f}")

    content = "\n".join(lines) + "\n"

    # Only write if parameter-golf exists
    if CREDS_FILE.parent.exists():
        CREDS_FILE.write_text(content)
        logger.info(f"Synced {len(gpus)} GPUs to {CREDS_FILE}")
        return str(CREDS_FILE)
    else:
        logger.warning(f"parameter-golf infra dir not found at {CREDS_FILE.parent}")
        return ""


# ---------------------------------------------------------------------------
# Results: parameter-golf files → DB index
# ---------------------------------------------------------------------------

def find_result_path(name: str) -> Path | None:
    """Find the result directory for an experiment by name."""
    # Check organized subdirs first, then top-level
    for subdir in ("explore", "validate", "full", "misc"):
        p = RESULTS_DIR / subdir / name / "summary.json"
        if p.exists():
            return p
    # Top-level
    p = RESULTS_DIR / name / "summary.json"
    if p.exists():
        return p
    return None


def read_result_json(path: Path) -> dict | None:
    """Read and parse a summary.json file."""
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _utcnow():
    return datetime.now(timezone.utc)


def _ensure_spec_tables() -> None:
    inspector = inspect(engine)
    if "experiment_specs" not in inspector.get_table_names():
        Base.metadata.create_all(bind=engine)


def _json_loads(text: str, default):
    try:
        return json.loads(text) if text else default
    except (json.JSONDecodeError, TypeError):
        return default


def _spec_payload_from_file(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None

    required = {"spec_id", "name", "spec_type", "template", "stage", "steps", "config_overrides", "linked_docs"}
    if not required.issubset(payload):
        return None
    return payload


def _spec_to_manifest(spec: ExperimentSpec) -> dict:
    return {
        "spec_id": spec.slug,
        "name": spec.name,
        "spec_type": spec.spec_type,
        "template": spec.template,
        "stage": spec.stage,
        "steps": spec.steps,
        "config_overrides": _json_loads(spec.config_overrides, {}),
        "linked_docs": _json_loads(spec.linked_docs, []),
        "tags": _json_loads(spec.tags, []),
        "notes": spec.notes or "",
        "desired_state": spec.desired_state,
    }


def _spec_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def export_spec_to_repo(spec: ExperimentSpec) -> str:
    """Write an experiment spec row to parameter-golf/experiments/specs."""
    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    payload = _spec_to_manifest(spec)
    path = SPECS_DIR / f"{spec.slug}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    spec.source_path = str(path)
    spec.content_hash = _spec_hash(payload)
    spec.last_synced_at = _utcnow()
    return str(path)


def sync_specs_to_db(db: Session) -> dict:
    """Index repo-backed experiment specs into the DB and keep file paths current."""
    _ensure_spec_tables()
    if not SPECS_DIR.exists():
        return {"indexed": 0, "updated": 0, "skipped": 0}

    admin = db.query(User).filter(User.tier == "admin").first()
    if not admin:
        admin = User(email="admin@auto-research.local", name="Admin", tier="admin")
        db.add(admin)
        db.flush()

    by_slug = {s.slug: s for s in db.query(ExperimentSpec).all()}
    stats = {"indexed": 0, "updated": 0, "skipped": 0}

    for path in sorted(SPECS_DIR.glob("*.json")):
        payload = _spec_payload_from_file(path)
        if not payload:
            stats["skipped"] += 1
            continue

        slug = payload["spec_id"]
        digest = _spec_hash(payload)
        spec = by_slug.get(slug)
        if spec and spec.content_hash == digest and spec.source_path == str(path):
            spec.last_synced_at = _utcnow()
            stats["skipped"] += 1
            continue

        if not spec:
            spec = ExperimentSpec(
                user_id=admin.id,
                slug=slug,
                source_path=str(path),
                origin="repo",
            )
            db.add(spec)
            by_slug[slug] = spec
            stats["indexed"] += 1
        else:
            stats["updated"] += 1

        spec.name = payload["name"]
        spec.spec_type = payload["spec_type"]
        spec.template = payload["template"]
        spec.stage = payload["stage"]
        spec.steps = int(payload["steps"])
        spec.config_overrides = json.dumps(payload.get("config_overrides", {}), sort_keys=True)
        spec.linked_docs = json.dumps(payload.get("linked_docs", []))
        spec.tags = json.dumps(payload.get("tags", []))
        spec.notes = payload.get("notes", "")
        spec.desired_state = payload.get("desired_state", "draft")
        spec.content_hash = digest
        spec.source_path = str(path)
        spec.last_synced_at = _utcnow()

    db.commit()
    return stats


def sync_results_to_db(db: Session) -> dict:
    """Scan parameter-golf/results/ and index new results into the DB.

    - Existing experiments get their result_path and val_bpb updated
    - New result dirs (from CLI runs) get indexed as admin experiments
    """
    if not RESULTS_DIR.exists():
        return {"error": f"Results dir not found: {RESULTS_DIR}"}

    # Get admin user for attributing CLI-originated experiments
    admin = db.query(User).filter(User.tier == "admin").first()
    if not admin:
        admin = User(email="admin@auto-research.local", name="Admin", tier="admin")
        db.add(admin)
        db.flush()

    # Index of existing experiment names → Experiment objects
    existing = {e.name: e for e in db.query(Experiment).all()}
    spec_by_slug = {s.slug: s for s in db.query(ExperimentSpec).all()}

    stats = {"updated": 0, "indexed": 0, "skipped": 0}

    def process_dir(result_dir: Path):
        name = result_dir.name
        summary_path = result_dir / "summary.json"
        if not summary_path.exists():
            return

        summary = read_result_json(summary_path)
        if not summary:
            return

        last_eval = summary.get("last_eval") or {}
        final_quant = summary.get("final_quant_eval") or {}
        val_bpb = final_quant.get("val_bpb") or last_eval.get("val_bpb")
        steps = last_eval.get("max_steps") or last_eval.get("step") or 0
        result_path_str = str(summary_path)

        if name in existing:
            exp = existing[name]
            # Update result_path and val_bpb if missing or changed
            changed = False
            if exp.spec_id is None and name in spec_by_slug:
                exp.spec_id = spec_by_slug[name].id
                changed = True
            if exp.result_path != result_path_str:
                exp.result_path = result_path_str
                changed = True
            if val_bpb and (exp.val_bpb is None or abs((exp.val_bpb or 0) - val_bpb) > 1e-8):
                exp.val_bpb = val_bpb
                changed = True
            if changed:
                stats["updated"] += 1
            else:
                stats["skipped"] += 1
        else:
            # New result from CLI — index it
            metadata_path = result_dir / "metadata.json"
            config = {}
            if metadata_path.exists():
                meta = read_result_json(metadata_path)
                if meta:
                    config = meta.get("config", {})

            generated_at = summary.get("generated_at_utc")
            completed_at = None
            if generated_at:
                try:
                    from datetime import datetime
                    completed_at = datetime.fromisoformat(generated_at)
                except ValueError:
                    pass

            exp = Experiment(
                user_id=admin.id,
                spec_id=spec_by_slug.get(name).id if name in spec_by_slug else None,
                name=name,
                template="parameter_golf",
                stage=classify_stage(steps),
                config_overrides=json.dumps(config),
                steps=steps,
                status="completed",
                val_bpb=val_bpb,
                result_path=result_path_str,
                completed_at=completed_at,
            )
            db.add(exp)
            existing[name] = exp
            stats["indexed"] += 1

    # Walk organized subdirs
    for subdir in ("explore", "validate", "full", "misc"):
        subdir_path = RESULTS_DIR / subdir
        if subdir_path.is_dir():
            for d in sorted(subdir_path.iterdir()):
                if d.is_dir():
                    process_dir(d)

    # Walk top-level dirs (skip the organized subdirs)
    for d in sorted(RESULTS_DIR.iterdir()):
        if d.is_dir() and d.name not in ("explore", "validate", "full", "misc"):
            process_dir(d)

    db.commit()
    return stats


# ---------------------------------------------------------------------------
# Queue: DB → parameter-golf queues/active.txt
# ---------------------------------------------------------------------------

def export_queue_file(db: Session) -> str:
    """Write queued experiments to parameter-golf's active.txt format.

    Format: <name> <steps> [ENV=val ...]
    This lets parameter-golf's run_queue.sh work without auto-research running.
    """
    queued = (
        db.query(Experiment)
        .filter(Experiment.status == "queued")
        .order_by(Experiment.queued_at.asc())
        .all()
    )

    lines = ["# Auto-generated from auto-research DB — do not edit manually"]
    for exp in queued:
        parts = [exp.name, str(exp.steps)]
        try:
            config = json.loads(exp.config_overrides) if exp.config_overrides else {}
            for k, v in config.items():
                parts.append(f"{k}={v}")
        except (json.JSONDecodeError, TypeError):
            pass
        lines.append(" ".join(parts))

    content = "\n".join(lines) + "\n"

    if QUEUE_FILE.parent.exists():
        QUEUE_FILE.write_text(content)
        logger.info(f"Exported {len(queued)} queued experiments to {QUEUE_FILE}")
        return str(QUEUE_FILE)

    return ""


# ---------------------------------------------------------------------------
# Import GPU creds from existing gpu_creds.sh → DB (one-time bootstrap)
# ---------------------------------------------------------------------------

def import_creds_from_file(db: Session) -> dict:
    """Parse existing gpu_creds.sh and import GPUs into DB.

    Use this when connecting auto-research to an existing parameter-golf setup.
    """
    if not CREDS_FILE.exists():
        return {"error": f"Creds file not found: {CREDS_FILE}"}

    content = CREDS_FILE.read_text()
    host = ""
    gpus_data: dict[str, dict] = {}

    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        if line.startswith("HOST="):
            host = line.split("=", 1)[1].strip('"').strip("'")
            continue

        # Parse GPU_<NAME>_PORT=, GPU_<NAME>_PASS=, GPU_<NAME>_RATE=
        if line.startswith("GPU_"):
            # e.g. GPU_ARCH1_PORT=47763
            rest = line[4:]  # ARCH1_PORT=47763
            # Find the last _ before = to split name from field
            eq_pos = rest.index("=")
            key_part = rest[:eq_pos]  # ARCH1_PORT
            value = rest[eq_pos + 1:].strip('"').strip("'")

            # Split into name and field (PORT, PASS, RATE)
            for suffix in ("_PORT", "_PASS", "_RATE"):
                if key_part.endswith(suffix):
                    name = key_part[: -len(suffix)]
                    field = suffix[1:].lower()  # port, pass, rate
                    gpus_data.setdefault(name, {})
                    gpus_data[name][field] = value
                    break

    imported = 0
    skipped = 0
    for name, data in gpus_data.items():
        existing = db.query(GPU).filter(GPU.name == name).first()
        if existing:
            skipped += 1
            continue

        gpu = GPU(
            name=name,
            host=host,
            port=int(data.get("port", 22)),
            user="root",
            password=data.get("pass", ""),
            hourly_rate=float(data.get("rate", 0)),
            repo_path="/root/parameter-golf",
        )
        db.add(gpu)
        imported += 1

    db.commit()
    return {"imported": imported, "skipped": skipped, "host": host}
