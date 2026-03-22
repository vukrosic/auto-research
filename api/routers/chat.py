"""Chat routes — interactive experiment builder + AI research assistant.

Three experiment trigger types:
1. [BUILD_EXPERIMENT] — menu-based, model picks from pre-built options (most common)
2. [RUN_EXPERIMENT]   — raw config overrides (advanced users)
3. [DEEP_EXPERIMENT]  — code changes via Novita code generation (rare, expensive)
"""
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
from api.experiment_menu import (
    CATEGORIES, PRESETS, build_menu_summary,
    selections_to_overrides, selections_to_description, build_screen_from_selections,
)

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


def _load_knowledge_summary() -> str:
    path = PG_ROOT / "KNOWLEDGE.md"
    if not path.exists():
        return ""
    text = path.read_text()
    if len(text) > 3000:
        text = text[:3000] + "\n... (truncated)"
    return text


KNOWLEDGE = _load_knowledge_summary()
MENU = build_menu_summary()

VALID_OVERRIDES = [
    "num_layers", "model_dim", "num_heads", "num_kv_heads", "mlp_mult",
    "tie_embeddings", "tied_embed_init_std", "logit_softcap", "rope_base",
    "qk_gain_init", "attnres_mode", "mlp_act", "act_power", "act_gate_floor",
    "embed_bottleneck", "num_unique_blocks", "num_cycles", "conv_kernel",
    "num_experts", "resid_scale_init", "stoch_depth_rate", "highway_net",
    "skip_weight_init",
]

# ── SYSTEM PROMPT ────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are the Experiment Lab — an interactive AI research game where users design tiny language models and race to beat the leaderboard.

## Your personality
- Enthusiastic but concise. Like a game show host who knows ML.
- Use emoji sparingly for category icons only (from the menu).
- Celebrate wins, give honest feedback on losses.
- Guide beginners, challenge experts.

## The game
Users are designing 16MB language models scored by bits-per-byte (val_bpb, lower = better). Target: beat 1.2244 BPB.

The experiment pipeline:
1. **Design** — user picks options from the menu (you guide them)
2. **Screen** — quick 1-2 step test eliminates bad ideas (seconds)
3. **Results** — show what worked, what flopped, and why
4. **Iterate** — learn from results, try again

## How to interact

### Phase 1: Welcome & suggest
When a user starts, welcome them and show 2-3 interesting experiment ideas. Ask what direction interests them. Show the preset options if they want a quick start.

### Phase 2: Build the experiment
Walk them through choices category by category. For each category:
- Show the options as a numbered list
- Give your recommendation with brief reasoning
- Let them pick (they can say the number, name, or describe what they want)
- Move to next category

You DON'T need to go through every category. Skip categories the user hasn't mentioned — use defaults. Only show categories relevant to their idea.

### Phase 3: Confirm & run
Once selections are made, show a summary card like:

**Your Experiment:**
| Category | Choice | Why |
|----------|--------|-----|
| ⚡ Activation | leaky05 | Lets negative signal through |
| 🧠 MoE | 4 experts | Best scaling found |
...

Then ask: "Ready to run? Say **go** to start the screen!"

### Phase 4: Results & next steps
After results come back, explain them in plain English:
- What beat the baseline and by how much
- What flopped and a theory why
- Suggest what to try next
- Generate a shareable results card the user can post

## Triggering experiments

When the user confirms (says "go", "run it", "let's try", etc.), output EXACTLY this block:

[BUILD_EXPERIMENT]
{{
  "topic": "short_snake_case_name",
  "configs": [
    {{
      "name": "descriptive_name",
      "selections": {{
        "activation": "option_id",
        "width": "option_id",
        "depth": "option_id",
        ...only include categories where selection differs from default
      }}
    }}
  ],
  "ladder": "quick"
}}
[/BUILD_EXPERIMENT]

You can include 1-5 configs to test against baseline. Each config is a different combination.
If the user picked a preset, use its selections.
The baseline (all defaults) is added automatically — never include it.

For advanced users who want raw overrides, use [RUN_EXPERIMENT] instead (same format as before).

## Generating shareable results

After an experiment completes, generate a **postable results card** in this format:

```
🧪 Experiment: [topic]
🎯 Target: < 1.2244 BPB

Results:
[emoji] variant_name: loss [delta vs baseline]
...

💡 Takeaway: [one sentence insight]

🔬 Built with Auto-Research — design ML experiments in chat
```

{MENU}

## KNOWLEDGE BASE
{KNOWLEDGE}

## Rules
- NEVER suggest LR tuning — forbidden, architecture only
- Check knowledge before suggesting — don't retry failed ideas
- If a combo won't fit 16MB, warn the user
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


# ── Pattern matching for experiment triggers ─────────────────────────────
BUILD_EXP_PATTERN = re.compile(
    r"\[BUILD_EXPERIMENT\]\s*(\{.*?\})\s*\[/BUILD_EXPERIMENT\]", re.DOTALL)
RUN_EXP_PATTERN = re.compile(
    r"\[RUN_EXPERIMENT\]\s*(\{.*?\})\s*\[/RUN_EXPERIMENT\]", re.DOTALL)
DEEP_EXP_PATTERN = re.compile(
    r"\[DEEP_EXPERIMENT\]\s*(\{.*?\})\s*\[/DEEP_EXPERIMENT\]", re.DOTALL)


# ── Screen config generation ────────────────────────────────────────────
def _write_screen_file(topic: str, content: str) -> Path:
    screen_id = f"chat_{topic}_{uuid.uuid4().hex[:6]}"
    screen_path = SCREENS_DIR / f"{screen_id}.py"
    screen_path.write_text(content)
    return screen_path


def _run_screen(screen_path: Path, ladder: str = "quick") -> str:
    result = subprocess.run(
        ["python3", "infra/tiered_screen.py", "--screen", str(screen_path), "--ladder", ladder],
        capture_output=True, text=True, timeout=300, cwd=str(PG_ROOT),
    )
    import glob as gl
    topic = screen_path.stem
    reports = sorted(gl.glob(str(RESULTS_DIR / f"tiered_screen_{topic}_*.md")))
    if reports:
        return Path(reports[-1]).read_text()
    output = result.stdout
    if result.returncode != 0:
        output += f"\n\nSTDERR:\n{result.stderr[-500:]}" if result.stderr else ""
    return output or "Screen completed but no report found."


def _handle_build_experiment(data: dict) -> Optional[str]:
    """Handle [BUILD_EXPERIMENT] — menu-based config assembly."""
    topic = data.get("topic", "experiment")
    configs = data.get("configs", [])
    ladder = data.get("ladder", "quick")
    if not configs:
        return None

    content = build_screen_from_selections(topic, configs)
    screen_path = _write_screen_file(topic, content)
    return _run_screen(screen_path, ladder)


def _handle_run_experiment(data: dict) -> Optional[str]:
    """Handle [RUN_EXPERIMENT] — raw override configs."""
    topic = data.get("topic", "experiment")
    variants = data.get("variants", [])
    ladder = data.get("ladder", "quick")
    why = data.get("why", "")
    if not variants:
        return None

    lines = [f'WHY = {json.dumps(why)}', "", "CONFIGS = [",
             '    ("baseline", "Control — no changes.", {}),']
    for v in variants:
        name = re.sub(r"[^a-z0-9_]", "_", v["name"].lower())[:32]
        desc = v.get("desc", v["name"])
        overrides = {k: v2 for k, v2 in v.get("overrides", {}).items() if k in VALID_OVERRIDES}
        lines.append(f"    ({json.dumps(name)}, {json.dumps(desc)}, {json.dumps(overrides)}),")
    lines.append("]")

    screen_path = _write_screen_file(topic, "\n".join(lines) + "\n")
    return _run_screen(screen_path, ladder)


def _handle_deep_experiment(data: dict) -> Optional[str]:
    """Handle [DEEP_EXPERIMENT] — code changes via Novita."""
    import shutil

    topic = data.get("topic", "experiment")
    description = data.get("description", "")
    env_var = data.get("env_var", "EXPERIMENT")
    test_values = data.get("test_values", [])
    ladder = data.get("ladder", "quick")

    if not description or not test_values:
        return None

    original = PG_ROOT / "train_gpt.py"
    backup = PG_ROOT / "train_gpt.py.backup"
    shutil.copy2(original, backup)

    try:
        client = get_client()
        full_code = original.read_text()

        response = client.chat.completions.create(
            model=settings.chat_model,
            messages=[{"role": "user", "content": f"""Modify this code to add: {description}

Control via env var `{env_var}`: when NOT set = original behavior, when set = activates change.
Output ONLY the complete modified Python file. No markdown, no fences, no explanation.

{full_code}"""}],
            max_tokens=16000, temperature=0.0,
        )

        new_code = response.choices[0].message.content
        if new_code.startswith("```"):
            lines = new_code.split("\n")
            if lines[0].startswith("```"): lines = lines[1:]
            if lines and lines[-1].strip() == "```": lines = lines[:-1]
            new_code = "\n".join(lines)

        if "class GPT" not in new_code or env_var not in new_code:
            return "Code generation failed — invalid output."

        original.write_text(new_code)

        diff_result = subprocess.run(
            ["diff", "-u", str(backup), str(original)],
            capture_output=True, text=True)
        diff_text = diff_result.stdout[:2000] if diff_result.stdout else "(no diff)"

        # Run each value manually
        ld = {"quick": 2, "standard": 6, "thorough": 20}
        steps = ld.get(ladder, 2)
        results = []
        env_clean = {k: v for k, v in os.environ.items() if k != env_var}

        for val in [None] + test_values:
            env = {**env_clean, **(({env_var: str(val)}) if val is not None else {})}
            label = re.sub(r"[^a-z0-9_]", "_", str(val).lower())[:32] if val else "baseline"
            r = subprocess.run(
                ["python3", "-c", _make_runner_script(steps, env_var, val)],
                capture_output=True, text=True, timeout=300,
                cwd=str(PG_ROOT), env=env)
            try:
                results.append(json.loads(r.stdout.strip().split('\n')[-1]))
            except (json.JSONDecodeError, IndexError):
                results.append({"name": label, "loss": 999, "error": (r.stderr or r.stdout)[-200:]})

        baseline_loss = results[0]["loss"] if results else 999
        rpt = [f"## Deep Experiment Results ({steps} steps)", "",
               f"**Env var:** `{env_var}`", "",
               "| Variant | Loss | Delta | Verdict |",
               "|---------|-----:|------:|---------|"]
        for r in sorted(results, key=lambda x: x.get("loss", 999)):
            loss, name = r.get("loss", 999), r.get("name", "?")
            delta = loss - baseline_loss
            verdict = "baseline" if name == "baseline" else ("better" if delta < -0.001 else "worse" if delta > 0.001 else "noise")
            rpt.append(f"| `{name}` | {loss:.4f} | {delta:+.4f} | {verdict} |")

        return f"**Code diff:**\n```diff\n{diff_text}\n```\n\n{chr(10).join(rpt)}"

    except Exception as e:
        return f"Deep experiment failed: {e}"
    finally:
        shutil.copy2(backup, original)
        backup.unlink(missing_ok=True)


def _make_runner_script(steps: int, env_var: str, val) -> str:
    env_line = f"os.environ['{env_var}'] = '{val}'" if val is not None else f"os.environ.pop('{env_var}', None)"
    name = re.sub(r"[^a-z0-9_]", "_", str(val).lower())[:32] if val is not None else "baseline"
    return f"""
import sys, os, json
{env_line}
sys.path.insert(0, '.')
import torch
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
torch.cuda.set_device(0)
import train_gpt as tg
torch.manual_seed(1337); torch.cuda.manual_seed_all(1337)
loader = tg.DistributedTokenLoader('./data/datasets/fineweb10B_sp1024/fineweb_train_*.bin', 0, 1, torch.device('cuda',0))
model = tg.GPT(vocab_size=1024, num_layers=9, model_dim=512, num_heads=8, num_kv_heads=4, mlp_mult=2, tie_embeddings=True, tied_embed_init_std=0.005, logit_softcap=30.0, rope_base=10000.0, qk_gain_init=1.5, attnres_mode='none', mlp_act='relu2', act_power=2.0, act_gate_floor=0.5, embed_bottleneck=0, num_unique_blocks=0, num_cycles=1, conv_kernel=0, num_experts=0, resid_scale_init=1.0, stoch_depth_rate=0.0, highway_net=False, skip_weight_init=1.0).to('cuda').bfloat16()
tg.restore_low_dim_params_to_fp32(model)
opt = torch.optim.Adam(model.parameters(), lr=0.04)
model.train()
losses = []
for _ in range({steps}):
    opt.zero_grad(set_to_none=True)
    sl = 0.0
    for _ in range(8):
        x, y = loader.next_batch(32768, 256, 8)
        with torch.autocast('cuda', torch.bfloat16):
            loss = model(x, y)
        (loss / 8).backward()
        sl += loss.item() / 8
    opt.step()
    losses.append(sl)
print(json.dumps({{'name': '{name}', 'loss': sum(losses)/len(losses)}}))
"""


# ── Dispatch experiment from AI reply ────────────────────────────────────
def _maybe_run_experiment(ai_reply: str) -> tuple[str, Optional[str]]:
    """Check AI reply for experiment blocks, run if found."""

    for pattern, handler in [
        (BUILD_EXP_PATTERN, _handle_build_experiment),
        (RUN_EXP_PATTERN, _handle_run_experiment),
        (DEEP_EXP_PATTERN, _handle_deep_experiment),
    ]:
        match = pattern.search(ai_reply)
        if match:
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
            report = handler(data)
            if report:
                cleaned = pattern.sub("", ai_reply).strip()
                return cleaned, report

    return ai_reply, None


# ── Endpoint: get menu ───────────────────────────────────────────────────
@router.get("/menu")
def get_menu():
    """Return experiment categories and presets for the frontend."""
    return {"categories": CATEGORIES, "presets": PRESETS}


# ── Endpoint: chat ───────────────────────────────────────────────────────
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

    # Check for experiment triggers
    cleaned_reply, report = _maybe_run_experiment(reply)

    if report:
        final_reply = cleaned_reply + f"\n\n---\n\n{report}"
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
    if report:
        result["experiment_ran"] = True
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
