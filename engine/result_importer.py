"""Import existing parameter-golf results into the platform DB.

Thin wrapper around engine.sync.sync_results_to_db for backwards compatibility.
"""
import json
import logging

from api.database import SessionLocal
from engine.sync import sync_results_to_db

logger = logging.getLogger(__name__)


def import_results(dry_run: bool = False) -> dict:
    """Import all results from parameter-golf into the DB."""
    if dry_run:
        return {"dry_run": True, "note": "dry_run no longer supported, use sync_results_to_db directly"}

    db = SessionLocal()
    try:
        return sync_results_to_db(db)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = import_results()
    print(json.dumps(result, indent=2))
