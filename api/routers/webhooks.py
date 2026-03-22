"""Webhook routes — Skool payment sync, GPU callbacks."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import User

router = APIRouter()


@router.post("/skool")
async def skool_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Skool membership events.

    When a user pays on Skool:
    1. Create platform account (or update tier)
    2. Trigger onboarding agent for new users
    3. Send welcome email with magic link

    Zero manual intervention.
    """
    payload = await request.json()
    # TODO: Verify Skool webhook signature
    # TODO: Parse event type (new_member, tier_change, cancellation)
    # TODO: Create/update user, trigger onboarding
    return {"status": "received"}


@router.post("/gpu-callback")
async def gpu_callback(request: Request, db: Session = Depends(get_db)):
    """Callback from GPU when experiment completes.

    Called by run_experiment.sh on the GPU via curl when training finishes.
    Updates experiment status, collects results, notifies user.
    """
    payload = await request.json()
    # TODO: Update experiment status, pull results, notify user
    return {"status": "received"}
