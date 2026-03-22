"""Import existing parameter-golf results into the platform DB.

Walks results/*/summary.json + metadata.json and creates Experiment records
for the admin user. Run once to seed the platform with historical data.
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from api.config import settings
from api.database import SessionLocal
from api.models import User, Experiment

logger = logging.getLogger(__name__)

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


def parse_result_dir(result_dir: Path) -> dict | None:
    """Parse a single result directory into experiment data."""
    summary_path = result_dir / "summary.json"
    metadata_path = result_dir / "metadata.json"

    if not summary_path.exists():
        return None

    try:
        summary = json.loads(summary_path.read_text())
    except (json.JSONDecodeError, OSError):
        logger.warning(f"Failed to parse {summary_path}")
        return None

    # Extract fields from summary
    run_id = summary.get("run_id", result_dir.name)
    last_eval = summary.get("last_eval") or {}
    final_quant = summary.get("final_quant_eval") or {}
    steps = last_eval.get("max_steps") or last_eval.get("step") or 0
    val_bpb = final_quant.get("val_bpb") or last_eval.get("val_bpb")
    generated_at = summary.get("generated_at_utc")

    # Parse metadata for config overrides and hardware info
    config_overrides = {}
    gpu_hardware = None
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text())
            config_overrides = metadata.get("config", {})
            hw = metadata.get("hardware", {}).get("gpu", {})
            gpu_hardware = hw.get("name")
        except (json.JSONDecodeError, OSError):
            pass

    # Parse completion timestamp
    completed_at = None
    if generated_at:
        try:
            completed_at = datetime.fromisoformat(generated_at)
        except ValueError:
            pass

    return {
        "name": run_id,
        "steps": steps,
        "stage": classify_stage(steps),
        "val_bpb": val_bpb,
        "config_overrides": json.dumps(config_overrides),
        "completed_at": completed_at,
        "gpu_hardware": gpu_hardware,
        "model_bytes": summary.get("int8_zlib_total_submission_bytes"),
    }


def import_results(dry_run: bool = False) -> dict:
    """Import all results from parameter-golf into the DB.

    Returns summary of what was imported.
    """
    results_root = Path(settings.parameter_golf_path) / "results"
    if not results_root.exists():
        return {"error": f"Results dir not found: {results_root}"}

    db = SessionLocal()
    try:
        # Get or create admin user
        admin = db.query(User).filter(User.tier == "admin").first()
        if not admin:
            admin = User(
                email="vuk@auto-research.ai",
                name="Vuk Rosic",
                tier="admin",
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            logger.info(f"Created admin user: {admin.email}")

        # Get existing experiment names to avoid duplicates
        existing = {e.name for e in db.query(Experiment.name).all()}

        # Walk all result directories (both organized subdirs and top-level)
        imported = 0
        skipped = 0
        errors = 0
        results_by_stage = {"explore": 0, "validate": 0, "full": 0}

        for result_dir in sorted(results_root.iterdir()):
            if not result_dir.is_dir():
                continue

            # Check organized subdirectories (explore/, validate/, full/, misc/)
            if result_dir.name in ("explore", "validate", "full", "misc"):
                for sub_dir in sorted(result_dir.iterdir()):
                    if not sub_dir.is_dir():
                        continue
                    if sub_dir.name in existing:
                        skipped += 1
                        continue
                    data = parse_result_dir(sub_dir)
                    if data is None:
                        errors += 1
                        continue
                    if not dry_run:
                        exp = Experiment(
                            user_id=admin.id,
                            name=data["name"],
                            template="parameter_golf",
                            stage=data["stage"],
                            config_overrides=data["config_overrides"],
                            steps=data["steps"],
                            status="completed",
                            val_bpb=data["val_bpb"],
                            completed_at=data["completed_at"],
                        )
                        db.add(exp)
                        existing.add(data["name"])
                    imported += 1
                    results_by_stage[data["stage"]] = results_by_stage.get(data["stage"], 0) + 1
                continue

            # Top-level result directories
            if result_dir.name in existing:
                skipped += 1
                continue
            data = parse_result_dir(result_dir)
            if data is None:
                errors += 1
                continue
            if not dry_run:
                exp = Experiment(
                    user_id=admin.id,
                    name=data["name"],
                    template="parameter_golf",
                    stage=data["stage"],
                    config_overrides=data["config_overrides"],
                    steps=data["steps"],
                    status="completed",
                    val_bpb=data["val_bpb"],
                    completed_at=data["completed_at"],
                )
                db.add(exp)
                existing.add(data["name"])
            imported += 1
            results_by_stage[data["stage"]] = results_by_stage.get(data["stage"], 0) + 1

        if not dry_run:
            db.commit()

        return {
            "imported": imported,
            "skipped_existing": skipped,
            "errors": errors,
            "by_stage": results_by_stage,
            "dry_run": dry_run,
        }
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    dry = "--dry-run" in sys.argv
    result = import_results(dry_run=dry)
    print(json.dumps(result, indent=2))
