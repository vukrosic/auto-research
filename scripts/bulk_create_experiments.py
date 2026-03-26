#!/usr/bin/env python3
"""Bulk-create explore experiments for 24-hour search sprint."""
import json
import os
import shutil
import datetime
import subprocess

AUTORESEARCH = "/root/research/autoresearch"
PROJECT = "parameter-golf"
SNAPSHOTS = f"{AUTORESEARCH}/experiments/{PROJECT}/snapshots"
BASE_DIR = f"{AUTORESEARCH}/experiments/{PROJECT}/base"
BASE_ID_FILE = f"{AUTORESEARCH}/experiments/{PROJECT}/base_id.txt"

# Read parent base id
with open(BASE_ID_FILE) as f:
    PARENT_BASE = f.read().strip()

# Read current best baseline metric for explore stage
with open(f"{AUTORESEARCH}/experiments/{PROJECT}/current_best.json") as f:
    best = json.load(f)
stage_baselines = best.get("stage_baselines", {})
if "explore" in stage_baselines:
    baseline_metric = stage_baselines["explore"].get("val_bpb", 1.6673)
else:
    baseline_metric = 1.6673

# Common fast settings for all experiments
FAST_ENV = {
    "SKIP_QUANT_EVAL": "1",
    "VAL_LOSS_EVERY": "500",
}

def make_env(overrides):
    """Merge fast settings with experiment-specific overrides."""
    env = dict(FAST_ENV)
    env.update(overrides)
    return env

# ============================================================
# EXPERIMENT DEFINITIONS
# Format: (name, env_overrides, hypothesis, expected_duration_seconds)
# ============================================================

experiments = []

# --- WAVE 1: Logit softcap sweep (7 experiments) ---
for cap in [5, 8, 10, 12, 18, 20, 25]:
    experiments.append((
        f"explore_logit_cap{cap}",
        {"LOGIT_SOFTCAP": str(float(cap))},
        f"Logit softcap={cap} (baseline=30, cap15 gave -0.54%). Sweep to find optimum.",
        720
    ))

# --- WAVE 2: Residual / scaling innovations (10 experiments) ---
for scale in ["0.0", "0.1", "0.5"]:
    name = f"explore_resid_scale_{scale.replace('.','')}"
    experiments.append((
        name,
        {"RESID_SCALE_INIT": scale},
        f"Residual scale init={scale} (0.0=ReZero, 0.1=LayerScale, 0.5=moderate). Unexplored axis.",
        720
    ))

for rate in ["0.05", "0.1", "0.2", "0.3"]:
    name = f"explore_stoch_depth_{rate.replace('.','')}"
    experiments.append((
        name,
        {"STOCH_DEPTH_RATE": rate},
        f"Stochastic depth rate={rate}. Regularization via random layer dropping.",
        720
    ))

experiments.append((
    "explore_highway",
    {"HIGHWAY_NET": "1"},
    "Highway network: input-dependent sigmoid gates for attn/mlp scales.",
    720
))

for sw in ["0.0", "0.5"]:
    name = f"explore_skip_weight_{sw.replace('.','')}"
    experiments.append((
        name,
        {"SKIP_WEIGHT_INIT": sw},
        f"Skip weight init={sw} (1.0=default). Controls initial skip connection strength.",
        720
    ))

# --- WAVE 3: Activation tuning (7 experiments) ---
for power in ["1.5", "3.0", "4.0"]:
    name = f"explore_act_power_{power.replace('.','')}"
    experiments.append((
        name,
        {"ACT_POWER": power},
        f"Activation power={power} (baseline=2.0). Squaring is key, but is 2.0 optimal?",
        720
    ))

for floor in ["0.0", "0.25", "0.75", "1.0"]:
    name = f"explore_gate_floor_{floor.replace('.','')}"
    experiments.append((
        name,
        {"ACT_GATE_FLOOR": floor},
        f"Gate floor={floor} (baseline=0.5). Controls minimum gate value in leaky activation.",
        720
    ))

# --- WAVE 4: QK gain tuning (4 experiments) ---
for gain in ["0.5", "1.0", "2.0", "3.0"]:
    name = f"explore_qk_gain_{gain.replace('.','')}"
    experiments.append((
        name,
        {"QK_GAIN_INIT": gain},
        f"QK attention gain={gain} (baseline=1.5). Controls initial attention sharpness.",
        720
    ))

# --- WAVE 5: Untested attnres modes (2 experiments) ---
experiments.append((
    "explore_attnres_vr_gated",
    {"ATTNRES_MODE": "value_residual_gated"},
    "Gated value residual attention. value_residual gave -0.32%, gated version may be better.",
    720
))
experiments.append((
    "explore_attnres_vr_mid",
    {"ATTNRES_MODE": "value_residual_mid"},
    "Mid-layer value residual. Different residual connection point.",
    720
))

# --- WAVE 6: RoPE at 500 steps (4 experiments, prev only tested at 50) ---
for base in [2000, 5000, 20000, 50000]:
    experiments.append((
        f"explore_rope_{base}",
        {"ROPE_BASE": str(float(base))},
        f"RoPE base={base} (baseline=10000). Previous tests at 50 steps showed no signal, retest at 500.",
        720
    ))

# --- WAVE 7: Stacking winners (10 experiments) ---
experiments.append((
    "explore_bn320_cap15",
    {"EMBED_BOTTLENECK": "320", "LOGIT_SOFTCAP": "15.0"},
    "Stack two best single improvements: bn320 (-0.64%) + logit_cap15 (-0.54%).",
    720
))
experiments.append((
    "explore_bn320_cap10",
    {"EMBED_BOTTLENECK": "320", "LOGIT_SOFTCAP": "10.0"},
    "bn320 + logit_cap10. If cap15 is good, maybe tighter is better.",
    720
))
experiments.append((
    "explore_bn320_cap20",
    {"EMBED_BOTTLENECK": "320", "LOGIT_SOFTCAP": "20.0"},
    "bn320 + logit_cap20. Moderate softcap + best bottleneck.",
    720
))
experiments.append((
    "explore_bn320_vr_cap15",
    {"EMBED_BOTTLENECK": "320", "ATTNRES_MODE": "value_residual", "LOGIT_SOFTCAP": "15.0"},
    "Triple stack: bn320 + value_residual + logit_cap15. Three independent improvements.",
    720
))
experiments.append((
    "explore_cap15_vr",
    {"LOGIT_SOFTCAP": "15.0", "ATTNRES_MODE": "value_residual"},
    "logit_cap15 + value_residual. Two independent improvements without bn320.",
    720
))
experiments.append((
    "explore_bn320_resid01",
    {"EMBED_BOTTLENECK": "320", "RESID_SCALE_INIT": "0.1"},
    "bn320 + LayerScale(0.1). Test if residual scaling stacks with bottleneck.",
    720
))
experiments.append((
    "explore_bn320_highway",
    {"EMBED_BOTTLENECK": "320", "HIGHWAY_NET": "1"},
    "bn320 + highway nets. Two structural changes that may compound.",
    720
))
experiments.append((
    "explore_bn320_stoch01",
    {"EMBED_BOTTLENECK": "320", "STOCH_DEPTH_RATE": "0.1"},
    "bn320 + stochastic depth. Regularization + capacity.",
    720
))
experiments.append((
    "explore_bn320_power15",
    {"EMBED_BOTTLENECK": "320", "ACT_POWER": "1.5"},
    "bn320 + activation power 1.5. Test if squaring exponent compounds with bottleneck.",
    720
))
experiments.append((
    "explore_bn320_power30",
    {"EMBED_BOTTLENECK": "320", "ACT_POWER": "3.0"},
    "bn320 + activation power 3.0. Higher power + larger bottleneck.",
    720
))

# --- WAVE 8: Architecture combos with bn320 (12 experiments) ---
experiments.append((
    "explore_bn320_12h6kv",
    {"EMBED_BOTTLENECK": "320", "NUM_HEADS": "12", "NUM_KV_HEADS": "6"},
    "bn320 + more attention heads (12h, 6kv). Finer attention + better embeddings.",
    720
))
experiments.append((
    "explore_bn320_12h3kv",
    {"EMBED_BOTTLENECK": "320", "NUM_HEADS": "12", "NUM_KV_HEADS": "3"},
    "bn320 + 12 heads, aggressive GQA (3kv). More heads, fewer KV.",
    720
))
experiments.append((
    "explore_bn320_6h3kv",
    {"EMBED_BOTTLENECK": "320", "NUM_HEADS": "6", "NUM_KV_HEADS": "3"},
    "bn320 + fewer heads (6h, 3kv). Original head config + better embeddings.",
    720
))

# MoE combos need narrow dims to fit under 16MB
experiments.append((
    "explore_bn320_8e_d288",
    {"EMBED_BOTTLENECK": "320", "NUM_EXPERTS": "8", "MODEL_DIM": "288", "NUM_HEADS": "6", "NUM_KV_HEADS": "3"},
    "bn320 + 8 experts at d288. More experts + better embeddings, narrow to fit 16MB.",
    900
))
experiments.append((
    "explore_bn320_8e_d320",
    {"EMBED_BOTTLENECK": "320", "NUM_EXPERTS": "8", "MODEL_DIM": "320", "NUM_HEADS": "8", "NUM_KV_HEADS": "4"},
    "bn320 + 8 experts at d320. More experts, wider than d288.",
    900
))
experiments.append((
    "explore_bn320_6e_d320",
    {"EMBED_BOTTLENECK": "320", "NUM_EXPERTS": "6", "MODEL_DIM": "320", "NUM_HEADS": "8", "NUM_KV_HEADS": "4"},
    "bn320 + 6 experts at d320. Moderate MoE + better embeddings.",
    900
))

# Deeper with bn320
experiments.append((
    "explore_bn320_10L",
    {"EMBED_BOTTLENECK": "320", "NUM_LAYERS": "10"},
    "bn320 + 10 layers. More depth + better embeddings (check size!).",
    840
))
experiments.append((
    "explore_bn320_15L_d288",
    {"EMBED_BOTTLENECK": "320", "NUM_LAYERS": "15", "MODEL_DIM": "288", "NUM_HEADS": "6", "NUM_KV_HEADS": "3"},
    "bn320 + 15 layers at d288. Very deep + narrow + better embeddings.",
    960
))
experiments.append((
    "explore_bn320_12L_d336",
    {"EMBED_BOTTLENECK": "320", "NUM_LAYERS": "12", "MODEL_DIM": "336", "NUM_HEADS": "6", "NUM_KV_HEADS": "3"},
    "bn320 + 12 layers at d336. Deeper + slightly narrower + better embeddings.",
    900
))

# --- WAVE 9: Optimizer edge cases (6 experiments) ---
experiments.append((
    "explore_muon_mom090",
    {"MUON_MOMENTUM": "0.90"},
    "Muon momentum=0.90 (baseline=0.95). Lower momentum = less smoothing.",
    720
))
experiments.append((
    "explore_muon_mom099",
    {"MUON_MOMENTUM": "0.99"},
    "Muon momentum=0.99 (baseline=0.95). Higher momentum = more smoothing.",
    720
))
experiments.append((
    "explore_muon_steps3",
    {"MUON_BACKEND_STEPS": "3"},
    "Muon Newton-Schulz steps=3 (baseline=5). Fewer orthogonalization steps.",
    720
))
experiments.append((
    "explore_muon_steps8",
    {"MUON_BACKEND_STEPS": "8"},
    "Muon Newton-Schulz steps=8 (baseline=5). More orthogonalization iterations.",
    720
))
experiments.append((
    "explore_warmup50",
    {"WARMUP_STEPS": "50"},
    "Warmup steps=50 (baseline=20). Longer warmup for more stable early training.",
    720
))
experiments.append((
    "explore_warmup5",
    {"WARMUP_STEPS": "5"},
    "Warmup steps=5 (baseline=20). Minimal warmup to start learning faster.",
    720
))

# --- WAVE 10: Wild cards / novel combos (5 experiments) ---
experiments.append((
    "explore_swiglu",
    {"MLP_ACT": "swiglu"},
    "SwiGLU activation (not squared). Different activation function entirely.",
    720
))
experiments.append((
    "explore_geglu",
    {"MLP_ACT": "geglu"},
    "GEGLU activation. Gated activation alternative.",
    720
))
experiments.append((
    "explore_bn320_swiglu",
    {"EMBED_BOTTLENECK": "320", "MLP_ACT": "swiglu"},
    "bn320 + SwiGLU. Best bottleneck + different activation.",
    720
))
experiments.append((
    "explore_bn256_cap15",
    {"EMBED_BOTTLENECK": "256", "LOGIT_SOFTCAP": "15.0"},
    "bn256 + logit_cap15. Slightly smaller bottleneck + softcap, check interaction.",
    720
))
experiments.append((
    "explore_cap15_resid01",
    {"LOGIT_SOFTCAP": "15.0", "RESID_SCALE_INIT": "0.1"},
    "logit_cap15 + LayerScale. Two independent improvements.",
    720
))

# ============================================================
# CREATE ALL EXPERIMENTS
# ============================================================

created = 0
skipped = 0

for name, env_overrides, hypothesis, expected_dur in experiments:
    snap_dir = f"{SNAPSHOTS}/{name}"

    if os.path.exists(snap_dir):
        print(f"SKIP (exists): {name}")
        skipped += 1
        continue

    # Create snapshot directory and copy base code
    os.makedirs(snap_dir)
    shutil.copytree(BASE_DIR, f"{snap_dir}/code")

    # Build meta.json
    meta = {
        "name": name,
        "project": PROJECT,
        "hypothesis": hypothesis,
        "parent_base": PARENT_BASE,
        "stage": "explore",
        "steps": 500,
        "priority": 1,
        "created_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "gpu": None,
        "baseline_metric": baseline_metric,
        "promotion_threshold": 0.01,
        "env_overrides": make_env(env_overrides),
        "changes_summary": "",
        "owner": "autonomous_lab",
        "expected_duration_seconds": expected_dur,
    }

    with open(f"{snap_dir}/meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    # Set status to pending
    with open(f"{snap_dir}/status", "w") as f:
        f.write("pending")

    print(f"CREATED: {name}")
    created += 1

print(f"\n=== Done: {created} created, {skipped} skipped (already exist) ===")
print(f"Total pending experiments ready for dispatch.")
