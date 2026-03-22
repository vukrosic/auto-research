"""Auth routes — simple token-based auth for MVP."""
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from api.database import get_db
from api.models import User

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    api_key: str


@router.post("/login")
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Login with email + API key. Sets a session cookie."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account found. Join via Skool first.")
    if user.api_key != req.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    # Set session cookie (simple — just the API key)
    response.set_cookie(key="session", value=user.api_key, httponly=True, max_age=60*60*24*30)
    return {
        "id": user.id, "email": user.email, "name": user.name,
        "tier": user.tier,
    }


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("session")
    return {"status": "logged out"}


@router.get("/me")
def get_me(session: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    """Get current logged-in user."""
    if not session:
        raise HTTPException(status_code=401, detail="Not logged in")
    user = db.query(User).filter(User.api_key == session).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")

    return {
        "id": user.id, "email": user.email, "name": user.name,
        "tier": user.tier, "api_key": user.api_key,
        "explore_used": user.explore_runs_used,
        "validate_used": user.validate_runs_used,
        "full_used": user.full_runs_used,
        "usage_reset_at": str(user.usage_reset_at),
        "created_at": str(user.created_at),
        "is_active": user.is_active,
    }


def get_current_user(session: Optional[str] = Cookie(None), db: Session = Depends(get_db)) -> User:
    """Dependency to get current user from session cookie."""
    if not session:
        raise HTTPException(status_code=401, detail="Not logged in")
    user = db.query(User).filter(User.api_key == session).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")
    return user
