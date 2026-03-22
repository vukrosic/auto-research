"""Auth routes — magic link login + API key auth."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.database import get_db
from api.models import User

router = APIRouter()


class LoginRequest(BaseModel):
    email: str


class LoginResponse(BaseModel):
    message: str


@router.post("/login", response_model=LoginResponse)
def request_login(req: LoginRequest, db: Session = Depends(get_db)):
    """Send magic link to email. Creates account if new."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account found. Join via Skool first.")
    # TODO: Generate magic link token, send email
    return LoginResponse(message="Check your email for login link")


@router.get("/me")
def get_me(db: Session = Depends(get_db)):
    """Get current user info. TODO: extract user from JWT."""
    # Placeholder — needs JWT middleware
    return {"message": "implement JWT auth"}
