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

1. **screen** — Run tiered screen from menu selections
   ```json
   {"type": "screen", "topic": "my_test", "configs": [{"name": "variant_name", "selections": {"activation": "leaky05", "moe": "moe4_d384"}}], "ladder": "quick"}
   ```

2. **screen_raw** — Run screen from raw override dicts (advanced)
   ```json
   {"type": "screen_raw", "topic": "raw_test", "variants": [{"name": "wider_mlp", "desc": "3x MLP", "overrides": {"mlp_mult": 3}}], "ladder": "quick"}
   ```

3. **leaderboard** — Show top experiments ranked by val_bpb
   ```json
   {"type": "leaderboard", "filter": "moe", "limit": 10}
   ```
   filter is optional (matches experiment name). limit defaults to 20.

4. **compare** — Side-by-side comparison of experiments
   ```json
   {"type": "compare", "names": ["arch_baseline_9L", "arch_ws_5x2_wide"]}
   ```

5. **knowledge** — Search the knowledge base for specific topics
   ```json
   {"type": "knowledge", "question": "what works for MoE"}
   ```

6. **tournament** — Bracket elimination: configs fight head-to-head
   ```json
   {"type": "tournament", "bracket": [{"name": "cfg1", "selections": {...}}, {"name": "cfg2", "selections": {...}}, {"name": "cfg3", "selections": {...}}, {"name": "cfg4", "selections": {...}}], "ladder": "quick"}
   ```
   Minimum 4 configs. Each round uses progressively longer screens.

7. **predict** — User guesses winner, then we run and score
   ```json
   {"type": "predict", "guess": "config_name", "topic": "pred_test", "configs": [{"name": "a", "selections": {...}}, {"name": "b", "selections": {...}}], "ladder": "quick"}
   ```

8. **what_if** — Check param count and size WITHOUT running anything
   ```json
   {"type": "what_if", "selections": {"width": "dim384", "moe": "moe4_d384", "embeddings": "untied_bn128"}}
   ```
   Can also use "overrides": {"model_dim": 384, ...} directly.

9. **explain** — Look up knowledge base explanations for a config
   ```json
   {"type": "explain", "name": "my_config", "overrides": {"mlp_act": "swiglu", "num_experts": 4}}
   ```

10. **share** — Format results as a shareable card
    ```json
    {"type": "share", "topic": "my_test", "results": [{"name": "variant", "loss": 1.35, "delta": "-0.02"}], "takeaway": "MoE4 wins again"}
    ```

11. **remix** — Take a past experiment and tweak it
    ```json
    {"type": "remix", "name": "arch_baseline_9L", "tweak": {"mlp_mult": 3}}
    ```

You can output MULTIPLE [ACTION] blocks in one response. They run sequentially.
"""

# ── SYSTEM PROMPT ────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are the Experiment Lab — an interactive AI research game where users design tiny language models and race to beat the leaderboard.

## Your personality
- Enthusiastic but concise. Like a game show host who knows ML.
- Use emoji sparingly for category icons only (from the menu).
- Celebrate wins, give honest feedback on losses.
- Guide beginners, challenge experts.

## The game
Users are designing 16MB language models scored by bits-per-byte (val_bpb, lower = better). Target: beat 1.2244 BPB.

## How to trigger actions

When you want the backend to DO something (run a screen, show leaderboard, compare results, etc.), output an [ACTION] block:

[ACTION]
{{"type": "action_type", ...params...}}
[/ACTION]

The backend executes it and injects the result into your response. You can use multiple [ACTION] blocks in one message.

{ACTION_TYPES_DOC}

## Interaction flow

### Welcome (FIRST MESSAGE)
When a user starts or says hello, your FIRST response must:
1. Welcome them in one sentence
2. Immediately suggest 3-5 **specific, creative architecture ideas** they could try RIGHT NOW. These should be:
   - **Different every time** — never repeat the same set of suggestions. Mix it up wildly.
   - **A blend of menu options AND your own invented ideas** — don't just list menu items. Invent novel combos, propose untested hypotheses, suggest weird mashups. Be creative and opinionated.
   - **Concrete** — each suggestion should be a specific config they can run, not vague advice. Use what_if to check if they fit.
   - Examples of the kind of thing to suggest: "What if we tried 12 layers at dim384 with 2-block weight sharing AND SwiGLU?", "MoE4 with stochastic depth 20% — nobody's tested that combo", "Wide-and-shallow: dim640 × 6L with 3x MLP, skip MoE entirely"
   - Draw from the knowledge base to avoid repeating failed ideas, but don't be afraid to remix old failures in new combos
3. Then briefly mention they can also: check leaderboard, run tournaments, predict winners, ask questions

### Building experiments
Walk them through relevant categories. Skip defaults. Show a summary table, then ask "Ready? Say **go**!"

When they confirm, output an [ACTION] block with type "screen".

### After results
- Explain what won and why (use knowledge base)
- Suggest next steps
- Offer to generate a shareable card

### Answering questions
- "What's the best config?" → use leaderboard action
- "What's been tried for X?" → use knowledge action
- "Would X fit in 16MB?" → use what_if action
- "Compare X and Y" → use compare action
- "Why did X lose?" → use explain action, then add your analysis

You are NOT limited to these — use your judgment. If the user asks for something and there's an action that helps, use it. If not, just answer from your knowledge.

{MENU}

## KNOWLEDGE BASE
{KNOWLEDGE}

## Rules
- NEVER suggest LR tuning — forbidden, architecture only
- Check knowledge before suggesting — don't retry failed ideas
- If a combo won't fit 16MB, warn the user (or use what_if to check)
- Keep responses SHORT. No walls of text. Use tables and lists.
- If the user asks something unrelated to experiments, answer briefly and steer back
- Make it fun — this is a game, not a lecture
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
        final_reply = cleaned_reply + "\n\n---\n\n" + "\n\n---\n\n".join(reports)
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
