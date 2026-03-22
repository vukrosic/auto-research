"""Research pipeline: 12 screens → 5 scales → 2 full runs."""
import asyncio
import json
import re
import subprocess
import uuid
from pathlib import Path

import httpx

PG_ROOT = Path("/root/parameter-golf")
SCREENS_DIR = PG_ROOT / "screens"
API_BASE = "http://localhost:8000"

# Override the fast-profile defaults in the experiments API with full model config
FULL_MODEL = {
    "NUM_LAYERS": 9, "MODEL_DIM": 512, "NUM_HEADS": 8, "NUM_KV_HEADS": 4, "MLP_MULT": 2,
    "TRAIN_BATCH_TOKENS": 524288, "VAL_BATCH_SIZE": 524288,
    "VAL_LOSS_EVERY": 1000, "TRAIN_LOG_EVERY": 200,
}


# ── Planning ──────────────────────────────────────────────────────────────

async def plan_screens(topic: str, n: int) -> list[dict]:
    """Ask LLM to generate n screen configs for topic. Returns [{name, description, overrides}]."""
    from api.config import settings

    knowledge = ""
    k_path = PG_ROOT / "KNOWLEDGE.md"
    if k_path.exists():
        knowledge = k_path.read_text()[:2500]

    system = (
        "You are a ML research assistant for a 16MB language model competition (val_bpb, lower=better). "
        "Target: beat 1.2244 BPB.\n\n"
        f"KNOWLEDGE BASE:\n{knowledge}\n\n"
        "Rules: architecture/mechanism changes only, NO LR tuning. All models must fit in 16MB."
    )
    user_msg = (
        f"Generate {n} diverse experiment configs to screen for: {topic}\n\n"
        "Output ONLY a JSON array:\n"
        '[{"name": "snake_case", "description": "one line", "overrides": {"KEY": value}}, ...]\n\n'
        "Valid override keys: mlp_act, num_layers, model_dim, mlp_mult, num_kv_heads, "
        "tie_embeddings, logit_softcap, rope_base, attnres_mode, num_experts, embed_bottleneck, "
        "num_unique_blocks, conv_kernel, resid_scale_init, stoch_depth_rate, highway_net, skip_weight_init\n\n"
        "Be creative and diverse. Avoid repeating things already in the knowledge base."
    )

    def _call():
        from openai import OpenAI
        client = OpenAI(api_key=settings.novita_api_key, base_url=settings.novita_base_url)
        resp = client.chat.completions.create(
            model=settings.chat_model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
            max_tokens=2000, temperature=0.85,
        )
        return resp.choices[0].message.content

    text = await asyncio.to_thread(_call)

    try:
        m = re.search(r'\[.*\]', text, re.DOTALL)
        if m:
            return json.loads(m.group(0))[:n]
    except Exception:
        pass

    # Fallback configs if parsing fails
    return [{"name": f"variant_{i}", "description": f"Variant {i}", "overrides": {}} for i in range(n)]


# ── Screen runner ─────────────────────────────────────────────────────────

def _run_screen_sync(name: str, overrides: dict, description: str) -> tuple[float, str]:
    """Run a tiered screen (blocking). Returns (best_delta_vs_baseline, short_report)."""
    SCREENS_DIR.mkdir(parents=True, exist_ok=True)
    screen_id = f"dp_{name[:20]}_{uuid.uuid4().hex[:6]}"
    screen_path = SCREENS_DIR / f"{screen_id}.py"

    safe_name = re.sub(r"[^a-z0-9_]", "_", name.lower())[:32]
    content = (
        f'WHY = {json.dumps(description)}\n\n'
        f'CONFIGS = [\n'
        f'    ("baseline", "Control.", {"{}"} ),\n'
        f'    ({json.dumps(safe_name)}, {json.dumps(description)}, {json.dumps(overrides)}),\n'
        f']\n'
    )
    screen_path.write_text(content)

    result = subprocess.run(
        ["python3", "infra/tiered_screen.py", "--screen", str(screen_path), "--ladder", "quick"],
        capture_output=True, text=True, timeout=120, cwd=str(PG_ROOT),
    )

    report_text = ""
    for p in sorted(PG_ROOT.glob(f"results/tiered_screen_{screen_id}_*.md"), reverse=True):
        report_text = p.read_text()
        break
    if not report_text:
        report_text = result.stdout or result.stderr or "no output"

    screen_path.unlink(missing_ok=True)

    # Extract best delta (most negative number in a line containing the variant name)
    delta = 0.0
    for line in report_text.split("\n"):
        if safe_name in line or name.lower() in line.lower():
            m = re.search(r'([+-]\d+\.\d+)', line)
            if m:
                d = float(m.group(1))
                if d < delta:
                    delta = d

    return delta, report_text[:600]


async def run_screen(name: str, overrides: dict, description: str) -> tuple[float, str]:
    return await asyncio.to_thread(_run_screen_sync, name, overrides, description)


# ── GPU experiment submission & polling ───────────────────────────────────

async def submit_experiment(api_key: str, name: str, overrides: dict, steps: int) -> int | None:
    """Submit via experiments API. Returns experiment ID or None."""
    full_overrides = {**FULL_MODEL, **overrides}
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.post(
                f"{API_BASE}/experiments/",
                json={"name": name, "config_overrides": full_overrides, "steps": steps},
                cookies={"session": api_key},
            )
        if resp.status_code == 200:
            return resp.json().get("id")
        print(f"submit_experiment error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"submit_experiment exception: {e}")
    return None


async def refresh_experiment(api_key: str, exp_id: int) -> dict:
    """Refresh and return experiment status dict."""
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.post(
                f"{API_BASE}/experiments/{exp_id}/refresh",
                cookies={"session": api_key},
            )
        if resp.status_code == 200:
            d = resp.json()
            return {
                "id": exp_id,
                "name": d.get("name", f"exp_{exp_id}"),
                "status": d.get("status", "unknown"),
                "current_step": d.get("current_step") or 0,
                "steps": d.get("steps") or 0,
                "val_bpb": d.get("val_bpb"),
            }
    except Exception:
        pass
    return {"id": exp_id, "name": f"exp_{exp_id}", "status": "unknown", "current_step": 0, "steps": 0}


async def poll_experiments(api_key: str, exp_ids: list[int]) -> list[dict]:
    return await asyncio.gather(*[refresh_experiment(api_key, eid) for eid in exp_ids])


# ── Progress formatting ───────────────────────────────────────────────────

def _bar(done: int, total: int, width: int = 12) -> str:
    filled = int(width * done / max(total, 1))
    return "█" * filled + "░" * (width - filled)


def format_progress(job: dict, scale_exps: list | None = None, full_exps: list | None = None) -> str:
    topic = job.get("topic", "?")
    phase = job.get("phase", "screens")

    sd, st = job["screen_done"], job["screen_total"]
    sk, skt = job.get("scale_done", 0), job["scale_total"]
    fk, ft = job.get("full_done", 0), job["full_total"]

    lines = [f"🔬 **{topic}**\n```"]

    # Screens line
    bar = _bar(sd, st)
    lines.append(f"Screens  [{bar}] {sd}/{st}")

    # Scales
    if phase in ("scales", "full", "done", "error"):
        bar = _bar(sk, skt)
        lines.append(f"Scales   [{bar}] {sk}/{skt}")
        if scale_exps:
            for exp in scale_exps:
                if exp.get("val_bpb"):
                    info = f"bpb {exp['val_bpb']:.4f} ✓"
                elif exp["status"] == "running" and exp["steps"]:
                    info = f"{exp['current_step']}/{exp['steps']} steps"
                else:
                    info = exp["status"]
                lines.append(f"  {exp['name']}: {info}")
    else:
        lines.append(f"Scales   [{'░'*12}] 0/{skt}")

    # Full
    if phase in ("full", "done", "error"):
        bar = _bar(fk, ft)
        lines.append(f"Full     [{bar}] {fk}/{ft}")
        if full_exps:
            for exp in full_exps:
                if exp.get("val_bpb"):
                    info = f"bpb {exp['val_bpb']:.4f} ✓"
                elif exp["status"] == "running" and exp["steps"]:
                    info = f"{exp['current_step']}/{exp['steps']} steps"
                else:
                    info = exp["status"]
                lines.append(f"  {exp['name']}: {info}")
    else:
        lines.append(f"Full     [{'░'*12}] 0/{ft}")

    lines.append("```")
    return "\n".join(lines)


# ── Pipeline orchestrator ─────────────────────────────────────────────────

async def run_pipeline(job: dict, channel, api_key: str | None, prog_msg):
    """Orchestrate the full pipeline. Mutates job in place."""
    topic = job["topic"]

    try:
        # === PHASE 1: SCREENS ===
        job["phase"] = "screens"
        configs = await plan_screens(topic, n=job["screen_total"])

        screen_winners: list[tuple[float, str, dict]] = []  # (delta, name, overrides)

        for i, cfg in enumerate(configs):
            name = cfg.get("name", f"v{i}")
            overrides = cfg.get("overrides", {})
            desc = cfg.get("description", name)

            await prog_msg.edit(content=format_progress(job))

            delta, _ = await run_screen(name, overrides, desc)
            screen_winners.append((delta, name, overrides))
            job["screen_done"] = i + 1

        screen_winners.sort(key=lambda x: x[0])  # lowest delta first (best improvement)
        await prog_msg.edit(content=format_progress(job))

        if not api_key:
            await prog_msg.edit(content=format_progress(job) + "\n⚠️ No API key — skipping GPU stages.")
            job["phase"] = "done"
            return

        # === PHASE 2: SCALES ===
        job["phase"] = "scales"
        top_for_scale = screen_winners[:job["scale_total"]]
        scale_ids = []

        for delta, name, overrides in top_for_scale:
            exp_id = await submit_experiment(api_key, f"scale_{name}", overrides, steps=2000)
            if exp_id:
                scale_ids.append(exp_id)

        job["scale_ids"] = scale_ids
        await prog_msg.edit(content=format_progress(job))

        # Poll until all scales done
        while scale_ids:
            await asyncio.sleep(120)
            exps = await poll_experiments(api_key, scale_ids)
            job["scale_done"] = sum(1 for e in exps if e["status"] in ("completed", "failed"))
            await prog_msg.edit(content=format_progress(job, scale_exps=exps))
            if job["scale_done"] >= len(scale_ids):
                break

        exps = await poll_experiments(api_key, scale_ids)

        # === PHASE 3: FULL RUNS ===
        job["phase"] = "full"
        ranked = sorted([e for e in exps if e.get("val_bpb")], key=lambda x: x["val_bpb"])
        top_for_full = ranked[:job["full_total"]]
        full_ids = []

        for exp in top_for_full:
            orig_name = re.sub(r"^scale_", "", exp["name"])
            orig_overrides = next(
                (o for d, n, o in top_for_scale if f"scale_{n}" == exp["name"]), {}
            )
            exp_id = await submit_experiment(api_key, f"full_{orig_name}", orig_overrides, steps=13780)
            if exp_id:
                full_ids.append(exp_id)

        job["full_ids"] = full_ids
        scale_exps_final = await poll_experiments(api_key, scale_ids)

        # Poll until all full runs done
        while full_ids:
            await asyncio.sleep(300)
            full_exps = await poll_experiments(api_key, full_ids)
            job["full_done"] = sum(1 for e in full_exps if e["status"] in ("completed", "failed"))
            await prog_msg.edit(content=format_progress(job, scale_exps=scale_exps_final, full_exps=full_exps))
            if job["full_done"] >= len(full_ids):
                break

        job["phase"] = "done"
        final_full = await poll_experiments(api_key, full_ids)
        await prog_msg.edit(content=format_progress(job, scale_exps=scale_exps_final, full_exps=final_full))
        await channel.send(f"✅ **{topic}** pipeline complete!")

    except Exception as e:
        job["phase"] = "error"
        job["error"] = str(e)
        await channel.send(f"❌ Pipeline error: {e}")
        raise
