"""Generic action handlers for the chat router.

Each handler takes a data dict (from the model's [ACTION] JSON) and returns
a markdown string to inject into the chat response, or None on failure.
"""
import json
import glob as gl
import re
import subprocess
import uuid
from pathlib import Path

from api.config import settings
from api.experiment_menu import (
    CATEGORIES, PRESETS,
    selections_to_overrides, selections_to_description, build_screen_from_selections,
)

PG_ROOT = Path(settings.parameter_golf_path)
SCREENS_DIR = PG_ROOT / "screens"
RESULTS_DIR = PG_ROOT / "results"

VALID_OVERRIDES = [
    "num_layers", "model_dim", "num_heads", "num_kv_heads", "mlp_mult",
    "tie_embeddings", "tied_embed_init_std", "logit_softcap", "rope_base",
    "qk_gain_init", "attnres_mode", "mlp_act", "act_power", "act_gate_floor",
    "embed_bottleneck", "num_unique_blocks", "num_cycles", "conv_kernel",
    "num_experts", "resid_scale_init", "stoch_depth_rate", "highway_net",
    "skip_weight_init",
]


# ── Helpers ──────────────────────────────────────────────────────────────

def _write_screen_file(topic: str, content: str) -> Path:
    SCREENS_DIR.mkdir(parents=True, exist_ok=True)
    screen_id = f"chat_{topic}_{uuid.uuid4().hex[:6]}"
    screen_path = SCREENS_DIR / f"{screen_id}.py"
    screen_path.write_text(content)
    return screen_path


def _run_screen(screen_path: Path, ladder: str = "quick") -> str:
    result = subprocess.run(
        ["python3", "infra/tiered_screen.py", "--screen", str(screen_path), "--ladder", ladder],
        capture_output=True, text=True, timeout=300, cwd=str(PG_ROOT),
    )
    topic = screen_path.stem
    reports = sorted(gl.glob(str(RESULTS_DIR / f"tiered_screen_{topic}_*.md")))
    if reports:
        return Path(reports[-1]).read_text()
    output = result.stdout
    if result.returncode != 0:
        output += f"\n\nSTDERR:\n{result.stderr[-500:]}" if result.stderr else ""
    return output or "Screen completed but no report found."


def _find_results(pattern: str = "*", limit: int = 50) -> list[dict]:
    """Scan results/ for summary.json files matching a pattern."""
    results = []
    for p in sorted(RESULTS_DIR.glob("*/summary.json")):
        name = p.parent.name
        if pattern != "*" and pattern.lower() not in name.lower():
            continue
        try:
            data = json.loads(p.read_text())
            data["name"] = name
            results.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    # Sort by val_bpb (lower = better)
    results.sort(key=lambda r: (r.get("final_quant_eval") or {}).get("val_bpb", 999))
    return results[:limit]


def _find_screen_reports(pattern: str = "*", limit: int = 10) -> list[dict]:
    """Find tiered screen markdown reports."""
    reports = []
    for p in sorted(RESULTS_DIR.glob("tiered_screen_*.md"), reverse=True):
        if pattern != "*" and pattern.lower() not in p.name.lower():
            continue
        reports.append({"file": p.name, "content": p.read_text()[:2000]})
        if len(reports) >= limit:
            break
    return reports


# ── Action Handlers ──────────────────────────────────────────────────────

def handle_screen(data: dict) -> str:
    """Run a tiered screen from menu selections."""
    topic = data.get("topic", "experiment")
    configs = data.get("configs", [])
    ladder = data.get("ladder", "quick")
    if not configs:
        return "No configs provided."

    content = build_screen_from_selections(topic, configs)
    screen_path = _write_screen_file(topic, content)
    return _run_screen(screen_path, ladder)


def handle_screen_raw(data: dict) -> str:
    """Run a tiered screen from raw override dicts."""
    topic = data.get("topic", "experiment")
    variants = data.get("variants", [])
    ladder = data.get("ladder", "quick")
    why = data.get("why", "")
    if not variants:
        return "No variants provided."

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


def handle_leaderboard(data: dict) -> str:
    """Show top experiments ranked by val_bpb."""
    pattern = data.get("filter", "*")
    limit = min(data.get("limit", 20), 50)
    results = _find_results(pattern, limit)

    if not results:
        return "No results found." + (f" (filter: `{pattern}`)" if pattern != "*" else "")

    lines = ["## Leaderboard", ""]
    if pattern != "*":
        lines.append(f"*Filter: `{pattern}`*\n")
    lines.extend([
        "| # | Experiment | Val BPB | Quant BPB | Size (MB) |",
        "|--:|-----------|--------:|----------:|----------:|",
    ])
    for i, r in enumerate(results, 1):
        name = r.get("name", "?")
        qeval = r.get("final_quant_eval") or {}
        leval = r.get("last_eval") or {}
        val_bpb = leval.get("val_bpb", "—")
        quant_bpb = qeval.get("val_bpb", "—")
        size_bytes = r.get("int8_zlib_total_submission_bytes", 0)
        size_mb = f"{size_bytes / 1_000_000:.1f}" if size_bytes else "—"
        lines.append(f"| {i} | `{name}` | {val_bpb} | {quant_bpb} | {size_mb} |")

    lines.append(f"\n*{len(results)} results shown. Target: < 1.2244 BPB*")
    return "\n".join(lines)


def handle_compare(data: dict) -> str:
    """Compare two or more experiments side by side."""
    names = data.get("names", [])
    if len(names) < 2:
        return "Need at least 2 experiment names to compare."

    results = []
    for name in names:
        matches = _find_results(name, 1)
        if matches:
            results.append(matches[0])
        else:
            results.append({"name": name, "error": "not found"})

    lines = ["## Comparison", "",
             "| Metric | " + " | ".join(f"`{r.get('name', '?')}`" for r in results) + " |",
             "|--------| " + " | ".join("---:" for _ in results) + " |"]

    # Val BPB row
    row = "| Val BPB |"
    for r in results:
        v = (r.get("last_eval") or {}).get("val_bpb", "—")
        row += f" {v} |"
    lines.append(row)

    # Quant BPB row
    row = "| Quant BPB |"
    for r in results:
        v = (r.get("final_quant_eval") or {}).get("val_bpb", "—")
        row += f" {v} |"
    lines.append(row)

    # Size row
    row = "| Size (MB) |"
    for r in results:
        s = r.get("int8_zlib_total_submission_bytes", 0)
        row += f" {s / 1_000_000:.1f} |" if s else " — |"
    lines.append(row)

    # Steps row
    row = "| Steps |"
    for r in results:
        v = (r.get("last_eval") or {}).get("max_steps", "—")
        row += f" {v} |"
    lines.append(row)

    # Delta vs first
    if len(results) >= 2:
        base_bpb = (results[0].get("final_quant_eval") or {}).get("val_bpb")
        if base_bpb:
            row = f"| Delta vs `{results[0].get('name')}` |"
            for r in results:
                v = (r.get("final_quant_eval") or {}).get("val_bpb")
                if v and base_bpb:
                    row += f" {v - base_bpb:+.4f} |"
                else:
                    row += " — |"
            lines.append(row)

    return "\n".join(lines)


def handle_knowledge(data: dict) -> str:
    """Query KNOWLEDGE.md for specific topics — returns matching paragraphs/lines."""
    question = data.get("question", "").lower()
    path = PG_ROOT / "KNOWLEDGE.md"
    if not path.exists():
        return "KNOWLEDGE.md not found."

    text = path.read_text()
    keywords = [w for w in question.split() if len(w) >= 2]
    if not keywords:
        return text[:2000]

    # Search line-by-line with context
    lines = text.split("\n")
    hits = []
    for i, line in enumerate(lines):
        if any(kw in line.lower() for kw in keywords):
            # Grab surrounding context (2 lines before/after)
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            block = "\n".join(lines[start:end])
            if block not in hits:
                hits.append(block)

    if hits:
        result = "\n\n".join(hits[:15])  # Cap at 15 matches
        if len(result) > 3000:
            result = result[:3000] + "\n... (truncated)"
        return f"## Knowledge: {question}\n\n{result}"
    else:
        return f"No matches for '{question}' in knowledge base."


def handle_tournament(data: dict) -> str:
    """Run bracket elimination tournament between configs."""
    bracket = data.get("bracket", [])
    ladder = data.get("ladder", "quick")

    if len(bracket) < 4:
        return "Need at least 4 configs for a tournament."
    if len(bracket) > 8:
        bracket = bracket[:8]

    # Pad to even number
    if len(bracket) % 2 != 0:
        bracket.append({"name": "baseline", "selections": {}})

    lines = ["## Tournament Mode", ""]
    round_num = 1
    current = bracket

    while len(current) > 1:
        lines.append(f"### Round {round_num} — {len(current)} configs")
        pairs = [(current[i], current[i + 1]) for i in range(0, len(current), 2)]
        winners = []

        for p1, p2 in pairs:
            lines.append(f"\n**{p1['name']}** vs **{p2['name']}**")

            # Build screen with both configs
            configs = [p1, p2]
            topic = f"tournament_r{round_num}_{p1['name']}_vs_{p2['name']}"
            content = build_screen_from_selections(topic, configs)
            screen_path = _write_screen_file(topic, content)

            # Scale ladder by round
            round_ladder = ladder
            if round_num == 2:
                round_ladder = "standard"
            elif round_num >= 3:
                round_ladder = "thorough"

            report = _run_screen(screen_path, round_ladder)

            # Parse winner from report — look for lowest non-baseline loss
            winner = None
            best_delta = 0
            for cfg in [p1, p2]:
                for line in report.split("\n"):
                    if cfg["name"] in line and "baseline" not in cfg["name"]:
                        # Try to extract delta
                        delta_match = re.search(r'([+-]\d+\.\d+)', line)
                        if delta_match:
                            delta = float(delta_match.group(1))
                            if delta < best_delta:
                                best_delta = delta
                                winner = cfg

            if winner is None:
                # Default to first if can't parse
                winner = p1

            lines.append(f"Winner: **{winner['name']}** (delta: {best_delta:+.4f})")
            lines.append(f"\n<details><summary>Full report</summary>\n\n{report}\n</details>\n")
            winners.append(winner)

        current = winners
        round_num += 1

    lines.append(f"\n## Champion: **{current[0]['name']}**")
    return "\n".join(lines)


def handle_predict(data: dict) -> str:
    """User predicts which config wins, then we run and score."""
    guess = data.get("guess", "")
    configs = data.get("configs", [])
    topic = data.get("topic", "predict")
    ladder = data.get("ladder", "quick")

    if not configs or not guess:
        return "Need configs and a guess to play predict mode."

    # Run the screen
    content = build_screen_from_selections(topic, configs)
    screen_path = _write_screen_file(topic, content)
    report = _run_screen(screen_path, ladder)

    # Find the actual winner from the report
    best_name = None
    best_delta = 0.0
    for cfg in configs:
        name = cfg.get("name", "")
        for line in report.split("\n"):
            if name in line and "baseline" not in name:
                delta_match = re.search(r'([+-]\d+\.\d+)', line)
                if delta_match:
                    delta = float(delta_match.group(1))
                    if delta < best_delta:
                        best_delta = delta
                        best_name = name

    if best_name is None:
        best_name = "baseline"

    correct = guess.lower().strip() == best_name.lower().strip()

    verdict = "CORRECT! You nailed it!" if correct else f"Not quite — **{best_name}** won!"
    emoji = "🎯" if correct else "❌"

    return f"## Prediction Results\n\nYour guess: **{guess}**\nActual winner: **{best_name}** ({best_delta:+.4f} vs baseline)\n\n{emoji} {verdict}\n\n---\n\n{report}"


def handle_explain(data: dict) -> str:
    """Explain why a config/result performed the way it did."""
    name = data.get("name", "")
    overrides = data.get("overrides", {})

    knowledge_path = PG_ROOT / "KNOWLEDGE.md"
    knowledge = knowledge_path.read_text() if knowledge_path.exists() else ""

    # Build explanation from knowledge base
    explanations = []
    for key, val in overrides.items():
        if key == "mlp_act":
            # Search knowledge for activation info
            for line in knowledge.split("\n"):
                if str(val).lower() in line.lower() or "activation" in line.lower():
                    if line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
                        explanations.append(line.strip())
        elif key == "num_experts":
            for line in knowledge.split("\n"):
                if "moe" in line.lower() or "expert" in line.lower():
                    if line.strip().startswith(("10.", "11.", "16.", "17.", "18.")):
                        explanations.append(line.strip())
        elif key in ("embed_bottleneck", "tie_embeddings"):
            for line in knowledge.split("\n"):
                if "embed" in line.lower() or "bn128" in line.lower():
                    if line.strip().startswith(("12.",)):
                        explanations.append(line.strip())

    if not explanations:
        return f"No specific knowledge base entries found for `{name}` with overrides: {overrides}. The model should explain based on general ML principles."

    # Deduplicate
    explanations = list(dict.fromkeys(explanations))
    result = f"## Analysis: `{name}`\n\n**Config overrides:** `{json.dumps(overrides)}`\n\n**Relevant findings from knowledge base:**\n\n"
    for e in explanations[:10]:
        result += f"- {e}\n"

    return result


def handle_what_if(data: dict) -> str:
    """Check param count and submission size for a hypothetical config."""
    selections = data.get("selections", {})
    overrides = selections_to_overrides(selections) if selections else data.get("overrides", {})
    desc = selections_to_description(selections) if selections else str(overrides)

    # Defaults
    dim = overrides.get("model_dim", 512)
    layers = overrides.get("num_layers", 9)
    heads = overrides.get("num_heads", 8)
    kv_heads = overrides.get("num_kv_heads", 4)
    mlp_mult = overrides.get("mlp_mult", 2)
    vocab = 1024
    tied = overrides.get("tie_embeddings", True)
    bn = overrides.get("embed_bottleneck", 0)
    experts = overrides.get("num_experts", 0)
    unique_blocks = overrides.get("num_unique_blocks", 0)

    # Param count estimate
    # Embedding: vocab * dim (or vocab * bn + bn * dim if bottleneck)
    if bn > 0:
        embed_params = vocab * bn + bn * dim
        if not tied:
            embed_params += dim * bn + bn * vocab  # output head
    else:
        embed_params = vocab * dim
        if not tied:
            embed_params += dim * vocab

    # Per layer: attn (Q, K, V, O) + MLP (up, down)
    head_dim = dim // heads
    q_params = dim * dim  # Q projection
    k_params = dim * (kv_heads * head_dim)  # K projection
    v_params = dim * (kv_heads * head_dim)  # V projection
    o_params = dim * dim  # O projection
    attn_params = q_params + k_params + v_params + o_params

    mlp_hidden = dim * mlp_mult
    if experts > 0:
        mlp_per_expert = dim * mlp_hidden + mlp_hidden * dim  # up + down
        mlp_params = mlp_per_expert * experts + dim * experts  # + router
    else:
        mlp_params = dim * mlp_hidden + mlp_hidden * dim

    # Layer norms (2 per layer, each has dim params)
    norm_params = 2 * dim

    layer_params = attn_params + mlp_params + norm_params
    actual_layers = unique_blocks if unique_blocks > 0 else layers
    total_layer_params = layer_params * actual_layers

    # Final norm
    final_norm = dim

    total = embed_params + total_layer_params + final_norm

    # Size estimate (int8 zlib ≈ 0.94x of int8)
    int8_bytes = total  # 1 byte per param
    zlib_bytes = int(int8_bytes * 0.94)
    size_mb = zlib_bytes / 1_000_000

    fits = size_mb <= 16.0
    emoji = "✅" if fits else "❌"

    lines = [
        f"## What-If Analysis",
        f"",
        f"**Config:** {desc}",
        f"",
        f"| Component | Params |",
        f"|-----------|-------:|",
        f"| Embeddings | {embed_params:,} |",
        f"| Attention (per layer) | {attn_params:,} |",
        f"| MLP (per layer) | {mlp_params:,} |",
        f"| Layers ({actual_layers} unique × {'cycled' if unique_blocks > 0 else 'all'}) | {total_layer_params:,} |",
        f"| **Total** | **{total:,}** |",
        f"",
        f"**Estimated submission size:** {size_mb:.1f} MB {emoji} {'FITS' if fits else 'TOO LARGE'} (limit: 16 MB)",
    ]

    if not fits:
        lines.append(f"\n⚠️ Over by {size_mb - 16:.1f} MB. Try reducing dim, layers, or expert count.")

    return "\n".join(lines)


def handle_share(data: dict) -> str:
    """Format a result as a shareable card."""
    topic = data.get("topic", "experiment")
    results_list = data.get("results", [])
    takeaway = data.get("takeaway", "")

    if not results_list:
        return "No results to share."

    lines = [
        f"```",
        f"🧪 Experiment: {topic}",
        f"🎯 Target: < 1.2244 BPB",
        f"",
    ]
    for r in results_list:
        name = r.get("name", "?")
        loss = r.get("loss", r.get("val_bpb", "?"))
        delta = r.get("delta", "")
        emoji = "🟢" if str(delta).startswith("-") else "🔴" if str(delta).startswith("+") else "⚪"
        delta_str = f" [{delta}]" if delta else ""
        lines.append(f"{emoji} {name}: {loss}{delta_str}")

    lines.extend([
        f"",
        f"💡 {takeaway}" if takeaway else "",
        f"",
        f"🔬 Built with Auto-Research",
        f"```",
    ])
    return "\n".join(lines)


def handle_remix(data: dict) -> str:
    """Take an existing experiment name and suggest one tweak."""
    name = data.get("name", "")
    tweak = data.get("tweak", {})

    if not name or not tweak:
        return "Need an experiment name and a tweak to remix."

    # Find original result
    matches = _find_results(name, 1)
    if matches:
        original = matches[0]
        orig_bpb = original.get("final_quant_eval") or {}.get("val_bpb", "?")
        return f"## Remix: `{name}` → `{name}_remix`\n\nOriginal quant BPB: {orig_bpb}\nTweak applied: `{json.dumps(tweak)}`\n\nReady to screen this remix."
    else:
        return f"Experiment `{name}` not found in results. Proceeding with tweak: `{json.dumps(tweak)}`"


# ── Registry ─────────────────────────────────────────────────────────────

ACTION_HANDLERS = {
    "screen": handle_screen,
    "screen_raw": handle_screen_raw,
    "leaderboard": handle_leaderboard,
    "compare": handle_compare,
    "knowledge": handle_knowledge,
    "tournament": handle_tournament,
    "predict": handle_predict,
    "explain": handle_explain,
    "what_if": handle_what_if,
    "share": handle_share,
    "remix": handle_remix,
}


def dispatch_action(data: dict) -> str:
    """Route an action to its handler. Returns markdown result."""
    action_type = data.get("type", "")
    handler = ACTION_HANDLERS.get(action_type)
    if not handler:
        return f"Unknown action type: `{action_type}`. Available: {', '.join(ACTION_HANDLERS.keys())}"
    try:
        return handler(data)
    except Exception as e:
        return f"Action `{action_type}` failed: {e}"
