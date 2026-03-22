"""Chat routes — generic action router for interactive experiment builder.

The model outputs [ACTION]{...}[/ACTION] JSON blocks. The backend dispatches
to the right handler and injects results into the response. Adding a new
feature = adding a handler in actions.py + one line in the system prompt.
"""
import json
import re
import time
from typing import Optional

from fastapi import APIRouter, Depends, Cookie
from sqlalchemy.orm import Session
from pydantic import BaseModel
from openai import OpenAI

from api.database import get_db
from api.config import settings
from api.models import ChatMessage, User
from api.experiment_menu import (
    CATEGORIES, PRESETS, build_menu_summary,
)
from api.actions import ACTION_HANDLERS, dispatch_action

router = APIRouter()

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


def _load_knowledge_summary() -> str:
    from pathlib import Path
    path = Path(settings.parameter_golf_path) / "KNOWLEDGE.md"
    if not path.exists():
        return ""
    text = path.read_text()
    if len(text) > 3000:
        text = text[:3000] + "\n... (truncated)"
    return text


KNOWLEDGE = _load_knowledge_summary()
MENU = build_menu_summary()

# Action types list for the system prompt
ACTION_TYPES_DOC = """
Available action types (use inside [ACTION]...[/ACTION] blocks):

1. **screen** — Run a head-to-head experiment screen (your main tool!)
   ```json
   {"type": "screen", "topic": "my_test", "configs": [{"name": "variant_name", "selections": {"activation": "leaky05", "moe": "moe4_d384"}}], "ladder": "quick"}
   ```
   Each config needs a name and selections from the menu categories. A baseline is auto-added.

2. **screen_raw** — Run screen with raw parameter overrides (for custom combos not in menu)
   ```json
   {"type": "screen_raw", "topic": "raw_test", "variants": [{"name": "wider_mlp", "desc": "3x MLP", "overrides": {"mlp_mult": 3}}], "ladder": "quick"}
   ```

3. **knowledge** — Search the knowledge base
   ```json
   {"type": "knowledge", "question": "what works for MoE"}
   ```
"""

# ── ANALYSIS PROMPT (second call after experiments run) ──────────────────
ANALYSIS_PROMPT = """You're a friendly, enthusiastic AI research buddy analyzing experiment results. Write a fun, insightful breakdown.

Your style:
- Use emojis naturally 🔥 🏆 😅 🧪 💡
- Talk like a smart friend — short sentences, excited energy
- Have opinions! "I called it!" or "Wow, didn't expect that"
- Be genuinely curious about what the results mean

Structure your response like this:
1. **Headline** — did it win or lose? How big was the effect? Set the mood with emoji
2. **What happened** — explain the results in plain English (2-3 sentences)
3. **Why** — your theory on why this worked or didn't (2-3 sentences)
4. **What's next** — suggest 2-3 follow-up ideas naturally: "This makes me want to try..."

Keep it to ~150 words. Punchy and insightful, not a wall of text. Don't include the raw data tables — the user already sees those. Just give the human interpretation."""

# ── SYSTEM PROMPT ────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are the Experiment Lab — a friendly AI research companion that helps people design tiny language models and test them instantly.

## Your personality
- Warm, encouraging, genuinely excited about ideas. You LOVE when people try weird stuff.
- Use emojis naturally — you're enthusiastic! 🔥 🧪 🎯 🧠 💡 🚀 ✨ etc.
- Talk like a smart friend, not a professor. Short sentences. Excited energy.
- Celebrate wins big. On losses, be supportive and curious — "interesting, that tells us something!"
- Have opinions! Say "I'd bet on this one" or "ooh that's spicy" or "honestly I'm not sure this beats baseline but let's find out"
- Be playful. This is fun, not homework.

## The game
We're designing 16MB language models scored by bits-per-byte (val_bpb, lower = better). The target to beat: **1.2244 BPB**.

We can test ideas INSTANTLY by running quick screens — head-to-head battles between configs. Results come back in seconds. It's like a lab where experiments are free!

## How you run experiments

When you want to test something, output an [ACTION] block (the user never sees this, they just see results):

[ACTION]
{{"type": "screen", "topic": "my_test", "configs": [{{"name": "variant_name", "selections": {{"activation": "leaky05"}}}}], "ladder": "quick"}}
[/ACTION]

{ACTION_TYPES_DOC}

## Conversation flow

### WELCOME (first message or after clear)
When a user starts fresh, give them a warm welcome and immediately suggest **10 specific experiment ideas** they can try. These MUST be:

- **Different every time** — randomize! Never give the same list twice.
- **Creative and opinionated** — don't just list menu items. Invent wild combos, untested mashups, bold hypotheses. Mix proven winners with speculative shots.
- **Numbered 1-10** so they can just say a number
- **Each idea in 1-2 lines max** with a fun name and a quick "why it might work"
- **Mix of safe bets and wild cards** — some should be "this probably wins" and some should be "this is a long shot but imagine if..."

Use the knowledge base to know what's already been tried. Remix old ideas in new combos. Be creative!

End with something like "Pick a number, describe your own idea, or just tell me what you're curious about! 🧪"

### When the user picks an idea or describes one
1. Show them what you're about to test in a quick summary (1-3 lines)
2. Ask ONE question if something is genuinely ambiguous — otherwise just confirm: "Love it, running this now! 🚀"
3. If the user says "just run it" or "go" or "sure" or anything affirmative — run it immediately with a [ACTION] block. Don't ask more questions.

### After results come back
This is the most important part! Write a **fun, insightful analysis**:

- Start with the headline: did it win or lose? By how much? Use emoji to set the mood 🏆 or 😅
- Explain WHY in plain English — what does this result tell us about how these models learn?
- Connect it to what we know from past experiments (use knowledge base internally)
- Give your honest take — "This confirms that..." or "Surprising! I expected..." or "This is a clue that..."
- End with 2-3 natural next ideas: "This makes me want to try..." or "The obvious follow-up is..."
- Keep the whole analysis to ~150 words. Insightful and punchy, not a wall of text.

### General conversation
- Answer questions naturally. If it's about experiments, draw from knowledge.
- If they ask what's been tried, search knowledge and give a helpful summary.
- Stay in character — you're their enthusiastic research buddy.

{MENU}

## KNOWLEDGE BASE (what's been tried before)
{KNOWLEDGE}

## Hard rules
- NEVER suggest learning rate tuning — architecture changes only
- Check knowledge before suggesting — don't recommend things that already failed (unless remixed in a genuinely new way)
- All configs must fit in 16MB — if something probably won't fit, say so
- Keep responses conversational and concise. NO walls of text.
"""


def get_optional_user(session: Optional[str] = Cookie(None), db: Session = Depends(get_db)) -> Optional[User]:
    if not session:
        return None
    return db.query(User).filter(User.api_key == session).first()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


# ── Action block parsing and dispatch ────────────────────────────────────
ACTION_PATTERN = re.compile(r"\[ACTION\]\s*(\{.*?\})\s*\[/ACTION\]", re.DOTALL)


def _process_actions(ai_reply: str) -> tuple[str, list[str]]:
    """Find all [ACTION] blocks, execute them, return cleaned reply + reports."""
    reports = []
    matches = list(ACTION_PATTERN.finditer(ai_reply))

    if not matches:
        return ai_reply, []

    for match in matches:
        try:
            data = json.loads(match.group(1))
            report = dispatch_action(data)
            reports.append(report)
        except json.JSONDecodeError as e:
            reports.append(f"Failed to parse action JSON: {e}")
        except Exception as e:
            reports.append(f"Action error: {e}")

    # Remove action blocks from reply
    cleaned = ACTION_PATTERN.sub("", ai_reply).strip()
    return cleaned, reports


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("/menu")
def get_menu():
    """Return experiment categories and presets for the frontend."""
    return {"categories": CATEGORIES, "presets": PRESETS}


@router.post("/")
async def chat(req: ChatRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    client = get_client()
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

    if user:
        db.add(ChatMessage(user_id=user.id, role="user", content=req.message))
        db.commit()

    t0 = time.time()
    response = client.chat.completions.create(
        model=settings.chat_model, messages=messages,
        max_tokens=2048, temperature=0.7,
    )
    latency_ms = int((time.time() - t0) * 1000)

    reply = response.choices[0].message.content
    usage = response.usage
    input_tokens = getattr(usage, "prompt_tokens", 0) or 0
    output_tokens = getattr(usage, "completion_tokens", 0) or 0
    cache_read_tokens = 0
    details = getattr(usage, "prompt_tokens_details", None)
    if details:
        cache_read_tokens = getattr(details, "cached_tokens", 0) or 0
    cost = calc_cost(input_tokens, cache_read_tokens, output_tokens)

    # Process action blocks
    cleaned_reply, reports = _process_actions(reply)

    if reports:
        # Second LLM call: have the model analyze the results with personality
        raw_results = "\n\n---\n\n".join(reports)
        analysis_messages = [
            {"role": "system", "content": ANALYSIS_PROMPT},
            {"role": "user", "content": f"Here's what the user asked for:\n{req.message}\n\nHere's what I was about to say:\n{cleaned_reply}\n\nHere are the experiment results:\n\n{raw_results}"},
        ]
        t1 = time.time()
        analysis_response = client.chat.completions.create(
            model=settings.chat_model, messages=analysis_messages,
            max_tokens=1024, temperature=0.7,
        )
        analysis_latency = int((time.time() - t1) * 1000)
        analysis = analysis_response.choices[0].message.content

        # Accumulate usage from both calls
        a_usage = analysis_response.usage
        input_tokens += getattr(a_usage, "prompt_tokens", 0) or 0
        output_tokens += getattr(a_usage, "completion_tokens", 0) or 0
        a_details = getattr(a_usage, "prompt_tokens_details", None)
        if a_details:
            cache_read_tokens += getattr(a_details, "cached_tokens", 0) or 0
        latency_ms += analysis_latency
        cost = calc_cost(input_tokens, cache_read_tokens, output_tokens)

        # Combine analysis + raw results (collapsed)
        final_reply = analysis + "\n\n<details><summary>📊 Raw results</summary>\n\n" + raw_results + "\n</details>"
    else:
        final_reply = reply

    if user:
        db.add(ChatMessage(
            user_id=user.id, role="assistant", content=final_reply,
            input_tokens=input_tokens, cache_read_tokens=cache_read_tokens,
            output_tokens=output_tokens, cost_usd=cost, latency_ms=latency_ms,
        ))
        db.commit()

    result = {"response": final_reply}
    result["usage"] = {
        "input_tokens": input_tokens, "cache_read_tokens": cache_read_tokens,
        "output_tokens": output_tokens, "cost_usd": round(cost, 8),
        "latency_ms": latency_ms,
    }
    if reports:
        result["actions_executed"] = len(reports)
    return result


@router.get("/history")
def get_history(db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    if not user:
        return []
    msgs = (
        db.query(ChatMessage).filter(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.asc()).limit(100).all()
    )
    return [
        {"id": m.id, "role": m.role, "content": m.content,
         "input_tokens": m.input_tokens, "cache_read_tokens": m.cache_read_tokens,
         "output_tokens": m.output_tokens, "cost_usd": m.cost_usd,
         "latency_ms": m.latency_ms, "created_at": str(m.created_at)}
        for m in msgs
    ]


@router.delete("/history")
def clear_history(db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    if not user:
        return {"error": "Not authenticated"}
    db.query(ChatMessage).filter(ChatMessage.user_id == user.id).delete()
    db.commit()
    return {"status": "cleared"}


@router.get("/stats")
def chat_stats(db: Session = Depends(get_db)):
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
        .group_by(ChatMessage.user_id).all()
    )
    users = {u.id: u.email for u in db.query(User).all()}
    return [
        {"user_id": r.user_id, "email": users.get(r.user_id, "?"),
         "messages": r.messages, "total_input_tokens": r.total_input or 0,
         "total_cache_tokens": r.total_cache or 0,
         "total_output_tokens": r.total_output or 0,
         "total_cost_usd": round(r.total_cost or 0, 6)}
        for r in rows
    ]


@router.get("/actions")
def list_actions():
    """List all available action types with descriptions."""
    return {
        "actions": list(ACTION_HANDLERS.keys()),
        "count": len(ACTION_HANDLERS),
    }
