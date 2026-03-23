"""Experiment menu — pre-built categories and options the cheap chat model can pick from.

The model outputs a [BUILD_EXPERIMENT] JSON block with selections from this menu.
The backend assembles the final screen config. This keeps the model's job simple:
just pick from a menu, don't generate code.
"""

# ── CATEGORIES ───────────────────────────────────────────────────────────
# Each category has options. Each option has a name, description, and overrides dict.
# The model picks one option per category (or "default" to skip).

CATEGORIES = {
    "activation": {
        "title": "Activation Function",
        "icon": "⚡",
        "description": "How neurons fire. Squared activations are proven best.",
        "options": {
            "relu2": {"desc": "ReLU² — the proven default. Hard to beat.", "overrides": {}},
            "leaky05": {"desc": "Leaky ReLU²(0.5) — lets negative signal through. Best found so far (+0.003 BPB).", "overrides": {"mlp_act": "leaky_relu2_05"}},
            "leaky03": {"desc": "Leaky ReLU²(0.3) — lighter leakiness than 0.5.", "overrides": {"mlp_act": "leaky_relu2_03"}},
            "leaky07": {"desc": "Leaky ReLU²(0.7) — more leakiness, closer to abs².", "overrides": {"mlp_act": "leaky_relu2_07"}},
            "swiglu": {"desc": "SwiGLU — popular in modern LLMs, trades width for gating.", "overrides": {"mlp_act": "swiglu"}},
            "swiglu2": {"desc": "SwiGLU² — gated with squared activation.", "overrides": {"mlp_act": "swiglu2"}},
            "geglu": {"desc": "GeGLU — GELU-gated variant of SwiGLU.", "overrides": {"mlp_act": "geglu"}},
            "gated_relu2": {"desc": "Gated ReLU² — sigmoid gate on top of ReLU².", "overrides": {"mlp_act": "gated_relu2"}},
            "abs2": {"desc": "Abs² — no dead neurons, symmetric. Competitive early but fades.", "overrides": {"mlp_act": "abs2"}},
            "selu2": {"desc": "SELU² — self-normalizing. Untested at scale here.", "overrides": {"mlp_act": "selu2"}},
            "mish": {"desc": "Mish — smooth self-regularized, popular alternative to SiLU.", "overrides": {"mlp_act": "mish"}},
            "silu2": {"desc": "SiLU² — squared SiLU, smooth version of ReLU².", "overrides": {"mlp_act": "silu2"}},
            "relu_cubed": {"desc": "ReLU³ — higher power, more aggressive sparsity.", "overrides": {"mlp_act": "relu_cubed"}},
        },
        "default": "relu2",
    },
    "width": {
        "title": "Model Width",
        "icon": "↔️",
        "description": "Wider = more capacity per layer, but fewer layers fit in 16MB.",
        "options": {
            "dim384": {"desc": "384-dim (6 heads, 3 KV) — compact, room for MoE/extras.", "overrides": {"model_dim": 384, "num_heads": 6, "num_kv_heads": 3}},
            "dim512": {"desc": "512-dim (8 heads, 4 KV) — the proven default.", "overrides": {}},
            "dim640": {"desc": "640-dim (10 heads, 5 KV) — wider but fewer layers may fit.", "overrides": {"model_dim": 640, "num_heads": 10, "num_kv_heads": 5}},
        },
        "default": "dim512",
    },
    "depth": {
        "title": "Model Depth",
        "icon": "📏",
        "description": "More layers = deeper reasoning, but more params and slower.",
        "options": {
            "6L": {"desc": "6 layers — shallow, fast, room for extras.", "overrides": {"num_layers": 6}},
            "9L": {"desc": "9 layers — the proven default.", "overrides": {}},
            "12L": {"desc": "12 layers — deeper, may need dim reduction to fit 16MB.", "overrides": {"num_layers": 12}},
        },
        "default": "9L",
    },
    "moe": {
        "title": "Mixture of Experts",
        "icon": "🧠",
        "description": "Multiple expert MLPs per layer. Powerful but uses more params.",
        "options": {
            "none": {"desc": "No MoE — standard single MLP per layer.", "overrides": {}},
            "moe2": {"desc": "2 experts — fits at dim=512. Modest gain.", "overrides": {"num_experts": 2}},
            "moe4_d384": {"desc": "4 experts at dim=384 — best legal config found! Needs dim=384.", "overrides": {"num_experts": 4, "model_dim": 384, "num_heads": 6, "num_kv_heads": 3}},
            "moe8_d384": {"desc": "8 experts at dim=384 — more experts, heavier routing pressure.", "overrides": {"num_experts": 8, "model_dim": 384, "num_heads": 6, "num_kv_heads": 3}},
            "moe4_d512": {"desc": "4 experts at dim=512 — standard width with MoE. May exceed 16MB.", "overrides": {"num_experts": 4}},
        },
        "default": "none",
    },
    "embeddings": {
        "title": "Embedding Strategy",
        "icon": "📝",
        "description": "How tokens enter and exit the model. Untied factored = best change found.",
        "options": {
            "tied": {"desc": "Tied embeddings — default, input and output share weights.", "overrides": {}},
            "untied_bn128": {"desc": "Untied factored bn128 — BEST legal change found (-0.031 BPB).", "overrides": {"embed_bottleneck": 128, "tie_embeddings": False}},
            "untied_bn64": {"desc": "Untied factored bn64 — smaller bottleneck, less params.", "overrides": {"embed_bottleneck": 64, "tie_embeddings": False}},
        },
        "default": "tied",
    },
    "attention": {
        "title": "Attention Variant",
        "icon": "👁️",
        "description": "How the model attends to previous tokens.",
        "options": {
            "standard": {"desc": "Standard GQA — proven default.", "overrides": {}},
            "value_residual": {"desc": "Value residual — add first-layer values into later layers.", "overrides": {"attnres_mode": "value_residual"}},
            "value_residual_gated": {"desc": "Value residual gated — learned gate on the value skip connection.", "overrides": {"attnres_mode": "value_residual_gated"}},
            "weighted": {"desc": "Weighted residual — learnable scalar per layer for attn+MLP output.", "overrides": {"attnres_mode": "weighted"}},
            "weighted_vector": {"desc": "Weighted residual vector — per-dimension learned scaling.", "overrides": {"attnres_mode": "weighted_vector"}},
        },
        "default": "standard",
    },
    "weight_sharing": {
        "title": "Weight Sharing",
        "icon": "♻️",
        "description": "Reuse layer weights to save params. Smaller model, same depth.",
        "options": {
            "none": {"desc": "No sharing — all layers unique.", "overrides": {}},
            "2block_cycle": {"desc": "2 unique blocks, cycled — half the layer params.", "overrides": {"num_unique_blocks": 2, "num_cycles": 4}},
            "3block_cycle": {"desc": "3 unique blocks, cycled 3x — moderate sharing.", "overrides": {"num_unique_blocks": 3, "num_cycles": 3}},
            "5block_cycle": {"desc": "5 unique blocks, cycled — light sharing for 10-layer model.", "overrides": {"num_unique_blocks": 5, "num_cycles": 2}},
        },
        "default": "none",
    },
    "regularization": {
        "title": "Regularization",
        "icon": "🛡️",
        "description": "Techniques to prevent overfitting and improve generalization.",
        "options": {
            "none": {"desc": "No extra regularization — rely on architecture.", "overrides": {}},
            "stoch_depth_01": {"desc": "Stochastic depth (10%) — randomly skip layers during training.", "overrides": {"stoch_depth_rate": 0.1}},
            "stoch_depth_02": {"desc": "Stochastic depth (20%) — more aggressive layer dropping.", "overrides": {"stoch_depth_rate": 0.2}},
            "grad_clip": {"desc": "Gradient clipping (norm=1.0) — stabilizes training.", "overrides": {"grad_clip_norm": 1.0}},
        },
        "default": "none",
    },
    "mlp_ratio": {
        "title": "MLP Expansion Ratio",
        "icon": "🔧",
        "description": "How wide the feedforward layers are relative to model width.",
        "options": {
            "2x": {"desc": "2x expansion — the default, balanced.", "overrides": {}},
            "3x": {"desc": "3x expansion — wider MLPs, more capacity, more params.", "overrides": {"mlp_mult": 3}},
            "4x": {"desc": "4x expansion — standard in larger models, may not fit.", "overrides": {"mlp_mult": 4}},
        },
        "default": "2x",
    },
    "conv": {
        "title": "Conv Mixer",
        "icon": "🌊",
        "description": "Depthwise conv before attention — local context mixing. 0 = disabled.",
        "options": {
            "none": {"desc": "No conv — standard attention only.", "overrides": {}},
            "conv3": {"desc": "Kernel=3 — short local mixing, low param cost.", "overrides": {"conv_kernel": 3}},
            "conv7": {"desc": "Kernel=7 — medium local context, similar to dilated conv.", "overrides": {"conv_kernel": 7}},
        },
        "default": "none",
    },
    "highway": {
        "title": "Highway Network",
        "icon": "🛣️",
        "description": "Learned gating on residual path — lets model choose how much to transform.",
        "options": {
            "none": {"desc": "No highway — standard residual connections.", "overrides": {}},
            "highway": {"desc": "Highway net — learned gates on attn and MLP residuals.", "overrides": {"highway_net": 1}},
        },
        "default": "none",
    },
    "resid_scale": {
        "title": "Residual Scale Init",
        "icon": "📐",
        "description": "Initial value for learnable per-layer residual scaling. 1.0 = standard.",
        "options": {
            "one": {"desc": "1.0 — standard, equivalent to no scaling.", "overrides": {}},
            "half": {"desc": "0.5 — dampen early residuals, let them grow.", "overrides": {"resid_scale_init": 0.5}},
            "zero": {"desc": "0.0 — start from pure residual, learn scale from scratch.", "overrides": {"resid_scale_init": 0.0}},
        },
        "default": "one",
    },
}

# ── PRESETS (curated combos) ─────────────────────────────────────────────
PRESETS = {
    "safe_bet": {
        "title": "🏆 Safe Bet",
        "description": "The best known config. MoE4 + untied bn128 + leaky at dim=384.",
        "selections": {
            "activation": "leaky05",
            "width": "dim384",
            "depth": "9L",
            "moe": "moe4_d384",
            "embeddings": "untied_bn128",
            "attention": "standard",
            "weight_sharing": "none",
            "regularization": "none",
            "mlp_ratio": "2x",
        }
    },
    "vanilla": {
        "title": "🫧 Vanilla Baseline",
        "description": "Stock config. Use this to establish your baseline before experimenting.",
        "selections": {
            "activation": "relu2",
            "width": "dim512",
            "depth": "9L",
            "moe": "none",
            "embeddings": "tied",
            "attention": "standard",
            "weight_sharing": "none",
            "regularization": "none",
            "mlp_ratio": "2x",
        }
    },
    "compact_deep": {
        "title": "🗼 Compact & Deep",
        "description": "Narrow but deep with weight sharing. Trade width for depth.",
        "selections": {
            "activation": "leaky05",
            "width": "dim384",
            "depth": "12L",
            "moe": "none",
            "embeddings": "untied_bn128",
            "attention": "value_residual",
            "weight_sharing": "3block_cycle",
            "regularization": "stoch_depth_01",
            "mlp_ratio": "2x",
        }
    },
    "wide_shallow": {
        "title": "🌊 Wide & Shallow",
        "description": "Fewer layers, wider model. Bet on per-layer capacity.",
        "selections": {
            "activation": "leaky05",
            "width": "dim640",
            "depth": "6L",
            "moe": "none",
            "embeddings": "untied_bn128",
            "attention": "standard",
            "weight_sharing": "none",
            "regularization": "none",
            "mlp_ratio": "3x",
        }
    },
    "moe_explorer": {
        "title": "🔬 MoE Explorer",
        "description": "4 experts with stochastic depth. Push the MoE frontier.",
        "selections": {
            "activation": "leaky05",
            "width": "dim384",
            "depth": "9L",
            "moe": "moe4_d384",
            "embeddings": "untied_bn128",
            "attention": "value_residual",
            "weight_sharing": "none",
            "regularization": "stoch_depth_01",
            "mlp_ratio": "2x",
        }
    },
}


def build_menu_summary() -> str:
    """Build a text summary of all categories and options for the system prompt."""
    lines = ["## Experiment Menu\n"]
    lines.append("### Categories (pick one option per category, or skip with 'default')\n")
    for cat_id, cat in CATEGORIES.items():
        lines.append(f"**{cat['icon']} {cat['title']}** (`{cat_id}`)")
        for opt_id, opt in cat["options"].items():
            default_marker = " ← DEFAULT" if opt_id == cat["default"] else ""
            lines.append(f"  - `{opt_id}`: {opt['desc']}{default_marker}")
        lines.append("")

    lines.append("### Presets (ready-made combos)\n")
    for preset_id, preset in PRESETS.items():
        lines.append(f"- `{preset_id}`: {preset['title']} — {preset['description']}")

    return "\n".join(lines)


def selections_to_overrides(selections: dict) -> dict:
    """Convert a dict of {category: option_name} to merged overrides."""
    merged = {}
    for cat_id, opt_id in selections.items():
        cat = CATEGORIES.get(cat_id)
        if not cat:
            continue
        opt = cat["options"].get(opt_id)
        if not opt:
            continue
        merged.update(opt["overrides"])
    return merged


def selections_to_description(selections: dict) -> str:
    """Human-readable description of selections."""
    parts = []
    for cat_id, opt_id in selections.items():
        cat = CATEGORIES.get(cat_id)
        if not cat:
            continue
        if opt_id == cat.get("default"):
            continue  # Skip defaults
        opt = cat["options"].get(opt_id)
        if opt:
            parts.append(f"{cat['icon']} {cat['title']}: {opt_id}")
    return ", ".join(parts) if parts else "all defaults (vanilla baseline)"


def build_screen_from_selections(topic: str, configs: list[dict]) -> str:
    """Build a screen .py file from a list of config dicts.

    Each config dict: {"name": "...", "selections": {"category": "option", ...}}
    First entry is always auto-added as baseline.
    """
    lines = [
        f'WHY = "User-designed experiment via chat"',
        "",
        "CONFIGS = [",
        '    ("baseline", "Control — all defaults.", {}),',
    ]
    for cfg in configs:
        name = cfg.get("name", "variant")
        sels = cfg.get("selections", {})
        overrides = selections_to_overrides(sels)
        desc = selections_to_description(sels)
        if not overrides:
            continue  # Skip if identical to baseline
        lines.append(f"    ({repr(name)}, {repr(desc)}, {repr(overrides)}),")
    lines.append("]")
    return "\n".join(lines) + "\n"
