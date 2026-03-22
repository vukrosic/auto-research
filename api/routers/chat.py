"""Chat routes — AI research assistant + support."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.database import get_db

router = APIRouter()


class ChatMessage(BaseModel):
    message: str
    context: str = "research"  # research, support, onboarding


@router.post("/")
async def chat(msg: ChatMessage, db: Session = Depends(get_db)):
    """Chat with AI research assistant.

    Handles three contexts:
    - research: Suggest experiments, explain results, propose next steps
    - support: Answer platform questions, troubleshoot issues
    - onboarding: Guide new users through first experiment

    All handled by AI. Zero human involvement.
    """
    # TODO: Call Claude API with appropriate system prompt per context
    # Include user's experiment history, tier, current results as context
    return {
        "response": "AI chat coming soon — will handle research advice, support, and onboarding",
        "context": msg.context,
    }
