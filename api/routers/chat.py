"""Chat routes — AI research assistant powered by Novita (mimo-v2-flash)."""
import time
from typing import Optional
from fastapi import APIRouter, Depends, Cookie
from sqlalchemy.orm import Session
from pydantic import BaseModel
from openai import OpenAI

from api.database import get_db
from api.config import settings
from api.models import ChatMessage, User

router = APIRouter()

# Novita pricing (per million tokens)
PRICE_INPUT = 0.10
PRICE_CACHE_READ = 0.02
PRICE_OUTPUT = 0.30

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.novita_api_key, base_url=settings.novita_base_url)
    return _client


def calc_cost(input_tokens: int, cache_read_tokens: int, output_tokens: int) -> float:
    non_cached = max(0, input_tokens - cache_read_tokens)
    return (
        non_cached * PRICE_INPUT / 1_000_000
        + cache_read_tokens * PRICE_CACHE_READ / 1_000_000
        + output_tokens * PRICE_OUTPUT / 1_000_000
    )


SYSTEM_PROMPT = """You are an AI research assistant for the Auto-Research platform — a tool for running ML experiments to find the best tiny language model architecture.

The platform runs parameter-golf experiments: training 16MB language models scored by bits-per-byte (val_bpb, lower = better).

You help users:
- Understand their experiment results and what the val_bpb numbers mean
- Suggest next experiments to try (architecture changes, hyperparameter ideas)
- Explain ML concepts simply (attention heads, MLP multipliers, learning rate schedules, etc.)
- Troubleshoot issues with their experiment setup
- Decide which tier or experiments to run next

Key facts:
- Experiments have 3 stages: explore (500 steps, ~28 min), validate (2000-4000 steps), full (13780 steps, ~12.7 hr)
- val_bpb < 1.2244 beats the current baseline — that's the competition target
- Users submit config overrides (NUM_LAYERS, MODEL_DIM, NUM_HEADS, MLP_MULT, etc.)
- The platform handles GPU scheduling automatically

Be concise, practical, and encouraging. Format responses with markdown where helpful."""


def get_optional_user(session: Optional[str] = Cookie(None), db: Session = Depends(get_db)) -> Optional[User]:
    if not session:
        return None
    return db.query(User).filter(User.api_key == session).first()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []  # [{role: "user"|"assistant", content: "..."}] — client-side fallback


@router.post("/")
async def chat(req: ChatRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    """Chat with the AI research assistant."""
    client = get_client()

    # Build message list from DB history (if authenticated) or client-provided history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if user:
        db_history = (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == user.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(20)
            .all()
        )
        for msg in reversed(db_history):
            messages.append({"role": msg.role, "content": msg.content})
    else:
        for msg in req.history[-10:]:
            if msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": req.message})

    # Save user message to DB
    if user:
        db.add(ChatMessage(user_id=user.id, role="user", content=req.message))
        db.commit()

    t0 = time.time()
    response = client.chat.completions.create(
        model=settings.chat_model,
        messages=messages,
        max_tokens=1024,
        temperature=0.7,
    )
    latency_ms = int((time.time() - t0) * 1000)

    reply = response.choices[0].message.content

    # Extract usage
    usage = response.usage
    input_tokens = getattr(usage, "prompt_tokens", 0) or 0
    output_tokens = getattr(usage, "completion_tokens", 0) or 0
    # Try to get cached tokens from prompt_tokens_details
    cache_read_tokens = 0
    details = getattr(usage, "prompt_tokens_details", None)
    if details:
        cache_read_tokens = getattr(details, "cached_tokens", 0) or 0

    cost = calc_cost(input_tokens, cache_read_tokens, output_tokens)

    # Save assistant message to DB
    if user:
        db.add(ChatMessage(
            user_id=user.id,
            role="assistant",
            content=reply,
            input_tokens=input_tokens,
            cache_read_tokens=cache_read_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
        ))
        db.commit()

    result = {"response": reply}
    # Always include usage — frontend decides whether to display it based on user tier
    result["usage"] = {
        "input_tokens": input_tokens,
        "cache_read_tokens": cache_read_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 8),
        "latency_ms": latency_ms,
    }
    return result


@router.get("/history")
def get_history(db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    """Get chat history for the current user."""
    if not user:
        return []
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "input_tokens": m.input_tokens,
            "cache_read_tokens": m.cache_read_tokens,
            "output_tokens": m.output_tokens,
            "cost_usd": m.cost_usd,
            "latency_ms": m.latency_ms,
            "created_at": str(m.created_at),
        }
        for m in msgs
    ]


@router.delete("/history")
def clear_history(db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    """Clear chat history for the current user."""
    if not user:
        return {"error": "Not authenticated"}
    db.query(ChatMessage).filter(ChatMessage.user_id == user.id).delete()
    db.commit()
    return {"status": "cleared"}


@router.get("/stats")
def chat_stats(db: Session = Depends(get_db)):
    """Admin: per-user chat cost summary."""
    from sqlalchemy import func
    rows = (
        db.query(
            ChatMessage.user_id,
            func.count(ChatMessage.id).label("messages"),
            func.sum(ChatMessage.input_tokens).label("total_input"),
            func.sum(ChatMessage.cache_read_tokens).label("total_cache"),
            func.sum(ChatMessage.output_tokens).label("total_output"),
            func.sum(ChatMessage.cost_usd).label("total_cost"),
        )
        .filter(ChatMessage.role == "assistant")
        .group_by(ChatMessage.user_id)
        .all()
    )
    users = {u.id: u.email for u in db.query(User).all()}
    return [
        {
            "user_id": r.user_id,
            "email": users.get(r.user_id, "?"),
            "messages": r.messages,
            "total_input_tokens": r.total_input or 0,
            "total_cache_tokens": r.total_cache or 0,
            "total_output_tokens": r.total_output or 0,
            "total_cost_usd": round(r.total_cost or 0, 6),
        }
        for r in rows
    ]
