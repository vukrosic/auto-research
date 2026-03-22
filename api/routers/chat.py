"""Chat routes — AI research assistant powered by Novita (mimo-v2-flash).

When the user confirms an experiment, the chat AI outputs a [RUN_EXPERIMENT] JSON block.
The backend intercepts it, calls `claude -p` to generate a screen config, runs
`tiered_screen.py`, and appends the report to the chat response.
"""
import asyncio
import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Cookie
from sqlalchemy.orm import Session
from pydantic import BaseModel
from openai import OpenAI

from api.database import get_db
from api.config import settings
from api.models import ChatMessage, User

router = APIRouter()

PRICE_INPUT = 0.10
PRICE_CACHE_READ = 0.02
PRICE_OUTPUT = 0.30

PG_ROOT = Path(settings.parameter_golf_path)
SCREENS_DIR = PG_ROOT / "screens"
RESULTS_DIR = PG_ROOT / "results"

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


# ── Knowledge summary injected into every chat ──────────────────────────
def _load_knowledge_summary() -> str:
    """Read KNOWLEDGE.md and return a condensed version for the system prompt."""
    path = PG_ROOT / "KNOWLEDGE.md"
    if not path.exists():
        return ""
    text = path.read_text()
    # Truncate to ~3000 chars to stay within cheap model context
    if len(text) > 3000:
        text = text[:3000] + "\n... (truncated)"
    return text


KNOWLEDGE = _load_knowledge_summary()

# ── Valid override keys (from tiered_screen.py FULL dict) ────────────────
VALID_OVERRIDES = [
    "num_layers", "model_dim", "num_heads", "num_kv_heads", "mlp_mult",
    "tie_embeddings", "tied_embed_init_std", "logit_softcap", "rope_base",
    "qk_gain_init", "attnres_mode", "mlp_act", "act_power", "act_gate_floor",
    "embed_bottleneck", "num_unique_blocks", "num_cycles", "conv_kernel",
    "num_experts", "resid_scale_init", "stoch_depth_rate", "highway_net",
    "skip_weight_init",
]

SYSTEM_PROMPT = f"""You are an AI research assistant for the Auto-Research platform. You help users design and run ML architecture experiments on tiny language models (16MB, scored by val_bpb — lower is better).

## Your job
1. Suggest experiment ideas when asked
2. Discuss what's been tried and what worked/failed (see KNOWLEDGE below)
3. When the user wants to run an experiment, collect details then output a [RUN_EXPERIMENT] block
4. Explain results in plain English

## How experiments work
The platform uses tiered screening: run many variants cheaply (1-2 steps), eliminate losers, scale survivors. Each experiment is a set of config overrides compared against a baseline.

Valid override keys: {', '.join(VALID_OVERRIDES)}

Common values:
- mlp_act: "relu2", "swiglu", "leaky_relu2_05", "abs2", "selu2"
- attnres_mode: "none", "value_residual"
- num_experts: 0 (no MoE), 2, 3, 4
- embed_bottleneck: 0 (none), 64, 128, 256
- num_unique_blocks: 0 (all unique), or N for weight-sharing (N blocks repeated)
- num_cycles: 1 (no repeat), 2+ (cycle through blocks)

## When the user confirms they want to run an experiment
Output EXACTLY this JSON block (the backend will intercept it):

[RUN_EXPERIMENT]
{{
  "topic": "short_snake_case_topic",
  "why": "One sentence: why these variants were chosen",
  "variants": [
    {{"name": "variant_name", "desc": "What it tests", "overrides": {{"key": "value"}}}},
    ...
  ],
  "ladder": "quick"
}}
[/RUN_EXPERIMENT]

Rules:
- Always include 2-6 variants (not counting baseline — baseline is added automatically)
- "ladder" is "quick" (seconds, default), "standard" (minutes), or "thorough" (longer)
- Variant names must be short snake_case
- Each variant needs exactly one clear hypothesis
- Do NOT include a baseline variant — it's automatic

## Before suggesting experiments, check KNOWLEDGE for:
- Already tried and failed approaches (don't waste runs)
- What's proven to work (build on it)
- The 16MB submission limit (reject configs that won't fit)

## KNOWLEDGE BASE (what we know so far)
{KNOWLEDGE}

## Important
- Be concise and practical
- If an idea was already tried and failed, say so and suggest alternatives
- If unsure whether something fits in 16MB, say so
- Don't suggest LR tuning — it's forbidden, architecture changes only
- When the user says "run it" or "let's try it", output the [RUN_EXPERIMENT] block
"""


def get_optional_user(session: Optional[str] = Cookie(None), db: Session = Depends(get_db)) -> Optional[User]:
    if not session:
        return None
    return db.query(User).filter(User.api_key == session).first()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


# ── Experiment execution ─────────────────────────────────────────────────
RUN_EXP_PATTERN = re.compile(
    r"\[RUN_EXPERIMENT\]\s*(\{.*?\})\s*\[/RUN_EXPERIMENT\]",
    re.DOTALL,
)


def _generate_screen_config(topic: str, why: str, variants: list[dict]) -> Path:
    """Write a screen config .py file directly (no claude -p needed for this)."""
    screen_id = f"chat_{topic}_{uuid.uuid4().hex[:6]}"
    screen_path = SCREENS_DIR / f"{screen_id}.py"

    lines = [
        f'WHY = {json.dumps(why)}',
        "",
        "CONFIGS = [",
        '    ("baseline", "Control — no changes.", {}),',
    ]
    for v in variants:
        name = re.sub(r"[^a-z0-9_]", "_", v["name"].lower())[:32]
        desc = v.get("desc", v["name"])
        overrides = {k: v2 for k, v2 in v.get("overrides", {}).items() if k in VALID_OVERRIDES}
        lines.append(f"    ({json.dumps(name)}, {json.dumps(desc)}, {json.dumps(overrides)}),")
    lines.append("]")

    screen_path.write_text("\n".join(lines) + "\n")
    return screen_path


def _run_screen(screen_path: Path, ladder: str = "quick") -> str:
    """Run tiered_screen.py and return the report contents."""
    result = subprocess.run(
        ["python3", "infra/tiered_screen.py", "--screen", str(screen_path), "--ladder", ladder],
        capture_output=True, text=True, timeout=300,
        cwd=str(PG_ROOT),
    )
    # Find the report file
    topic = screen_path.stem
    import glob as gl
    reports = sorted(gl.glob(str(RESULTS_DIR / f"tiered_screen_{topic}_*.md")))
    if reports:
        return Path(reports[-1]).read_text()
    # Fallback: return stdout
    output = result.stdout
    if result.returncode != 0:
        output += f"\n\nSTDERR:\n{result.stderr[-500:]}" if result.stderr else ""
    return output or "Screen completed but no report found."


def _maybe_run_experiment(ai_reply: str) -> tuple[str, Optional[str]]:
    """Check if AI reply contains a [RUN_EXPERIMENT] block. If so, run it.

    Returns (cleaned_reply, report_or_none).
    """
    match = RUN_EXP_PATTERN.search(ai_reply)
    if not match:
        return ai_reply, None

    try:
        exp = json.loads(match.group(1))
    except json.JSONDecodeError:
        return ai_reply, None

    topic = exp.get("topic", "experiment")
    why = exp.get("why", "")
    variants = exp.get("variants", [])
    ladder = exp.get("ladder", "quick")

    if not variants:
        return ai_reply, None

    # Generate screen config
    screen_path = _generate_screen_config(topic, why, variants)

    # Run the screen
    report = _run_screen(screen_path, ladder)

    # Clean the [RUN_EXPERIMENT] block from the reply and append status
    cleaned = RUN_EXP_PATTERN.sub("", ai_reply).strip()

    return cleaned, report


@router.post("/")
async def chat(req: ChatRequest, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    """Chat with the AI research assistant. Auto-runs experiments when triggered."""
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
        model=settings.chat_model,
        messages=messages,
        max_tokens=1024,
        temperature=0.7,
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

    # Check if the AI wants to run an experiment
    cleaned_reply, report = _maybe_run_experiment(reply)

    if report:
        final_reply = cleaned_reply + f"\n\n---\n**Screen running...**\n\n```\n{report}\n```"
    else:
        final_reply = reply

    if user:
        db.add(ChatMessage(
            user_id=user.id,
            role="assistant",
            content=final_reply,
            input_tokens=input_tokens,
            cache_read_tokens=cache_read_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
        ))
        db.commit()

    result = {"response": final_reply}
    result["usage"] = {
        "input_tokens": input_tokens,
        "cache_read_tokens": cache_read_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 8),
        "latency_ms": latency_ms,
    }
    if report:
        result["experiment_ran"] = True
    return result


@router.get("/history")
def get_history(db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
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
