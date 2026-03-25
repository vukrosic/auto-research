# Tiny50 Follow-Up Results — Best-of-Best Combo Sweep

**Date:** 2026-03-23  
**Archived queue:** `queues/archive/tiny/tiny50_followup_best.txt`  
**Hardware:** 1x RTX 3090 on CUDA  
**Status:** finished, 50/50 runs recorded  
**Baseline:** `u00_baseline = 1.9106 val_bpb`

## TL;DR

The best overall follow-up run was `u12_8L_vr_silu` at `1.7889 val_bpb`, a `-0.1217` improvement over baseline. The clearest pattern was that depth only really paid off once it was paired with `ATTNRES_MODE=value_residual`, and most of the rest of the leaderboard was dominated by `CONV_KERNEL=3` combinations.

The strongest families were:
- deep + value residual + `silu`
- deep + value residual + `relu`
- `conv3` crossed with `ebn64`, `value_residual`, or both

## Method

This queue was a focused follow-up to `queues/archive/tiny/tiny50_diverse.txt`, using the best ideas from the first 50-run sweep and recombining them:
- `value_residual`
- `silu`
- `relu`
- `EMBED_BOTTLENECK=64`
- `CONV_KERNEL=3`
- a few stabilizer variants such as `value_residual_gated`, `value_residual_mid`, and `QK_GAIN_INIT=0.5`

All runs used the same fast tiny setup as before unless explicitly changed:
- tiny model around 3M params
- baseline architecture: 6 layers, 256 dim, 4 heads, 2 KV heads, MLP mult 2
- 300 training steps
- `TRAIN_BATCH_TOKENS=65536`
- one validation pass with `VAL_BATCH_SIZE=4194304`
- queue runner killed after `val_bpb` to skip int8 eval during the fast sweep

Artifacts for every run are stored in `results/u*/summary.json` and `results/u*/train.log`.

## Top Results

| Rank | Run | val_bpb | Delta vs baseline | Family | Main change |
|------|-----|---------|-------------------|--------|-------------|
| 1 | `u12_8L_vr_silu` | 1.7889 | -0.1217 | T90 family | 8 layers + value residual + SiLU |
| 2 | `u25_8L_vr_relu` | 1.7960 | -0.1146 | ReLU crossovers | 8 layers + value residual + ReLU |
| 3 | `u42_conv3_vr_silu_ebn64` | 1.8020 | -0.1086 | Conv / attnres crossings | conv3 + embed bottleneck 64 + value residual + SiLU |
| 4 | `u39_conv3_ebn64` | 1.8033 | -0.1073 | Conv / attnres crossings | conv3 + embed bottleneck 64 |
| 5 | `u43_conv3_vr_relu_ebn64` | 1.8126 | -0.0980 | Conv / attnres crossings | conv3 + embed bottleneck 64 + value residual + ReLU |
| 6 | `u36_conv3_vr` | 1.8127 | -0.0979 | Conv / attnres crossings | conv3 + value residual |
| 7 | `u04_conv3_ctrl` | 1.8141 | -0.0965 | Controls / recentering | conv3 only |
| 8 | `u37_conv3_vrg` | 1.8176 | -0.0930 | Conv / attnres crossings | conv3 + gated value residual |
| 9 | `u15_conv3_vr_silu` | 1.8204 | -0.0902 | T90 family | conv3 + value residual + SiLU |
| 10 | `u35_ebn64_conv3_relu` | 1.8207 | -0.0899 | EBN size ablations | embed bottleneck 64 + conv3 + ReLU |
| 11 | `u41_conv3_vr_relu` | 1.8250 | -0.0856 | Conv / attnres crossings | conv3 + value residual + ReLU |
| 12 | `u40_conv3_full` | 1.8279 | -0.0827 | Conv / attnres crossings | conv3 + full MHA |
| 13 | `u05_vr_ctrl` | 1.8320 | -0.0786 | Controls / recentering | value residual only |
| 14 | `u38_conv3_cumsum` | 1.8321 | -0.0785 | Conv / attnres crossings | conv3 + cumsum residual |
| 15 | `u03_ebn64_ctrl` | 1.8361 | -0.0745 | Controls / recentering | embed bottleneck 64 only |

## Family Summary

| Family | Best run | Best val_bpb | Family average | Read |
|--------|----------|--------------|----------------|------|
| Controls / recentering | `u04_conv3_ctrl` | 1.8141 | 1.8537 | `conv3` was the strongest clean single change in the follow-up queue. |
| T90 family: silu + stabilizers | `u12_8L_vr_silu` | 1.7889 | 1.8463 | The original `vr+silu` idea only became dominant again once depth was added. |
| ReLU crossovers | `u25_8L_vr_relu` | 1.7960 | 1.8581 | ReLU became excellent when paired with both depth and value residual. |
| EBN size ablations | `u35_ebn64_conv3_relu` | 1.8207 | 1.8511 | Bottlenecks helped most when combined with `conv3`, not as stand-alone winners. |
| Conv / attnres crossings | `u42_conv3_vr_silu_ebn64` | 1.8020 | 1.8167 | This was the strongest non-depth cluster and produced most of the top table. |
| Alternate activations with stabilizers | `u48_ebn64_xsilu` | 1.8382 | 1.8546 | `x_silu` was decent, but `mish` and the alternate activations did not beat the best `relu`/`silu` combos. |

## Main Findings

- `NUM_LAYERS=8` was only good when stabilized. `u24_8L_relu` scored `1.9007`, but adding `ATTNRES_MODE=value_residual` in `u25_8L_vr_relu` dropped that to `1.7960`.
- `conv3` was the most reliable cheap improvement. `u04_conv3_ctrl` alone reached `1.8141`, and 8 of the top 10 runs used `CONV_KERNEL=3`.
- `value_residual` remained one of the best core primitives. Even the plain control `u05_vr_ctrl` was strong at `1.8320`, and it paired especially well with depth.
- `EMBED_BOTTLENECK=64` looked more like a supporting constraint than a standalone champion. It was good by itself at `1.8361`, but much better when paired with `conv3`.
- The re-centered `vr+silu` control was only mid-pack in this queue: `u01_vr_silu_ctrl = 1.8536`. The follow-up result suggests the real win is the interaction between `vr+silu` and depth, not the shallow combo alone.
- `value_residual_gated` and `cumsum` helped, but plain `value_residual` was usually better.

## Implementation Notes

These are the important knobs behind the top results and what they actually do in `train_gpt.py`.

| Knob | Where it is implemented | What it does |
|------|--------------------------|--------------|
| `NUM_LAYERS=8` | `GPT.__init__()` | Builds 8 non-shared `Block`s instead of 6. In the non-weight-sharing path the model still uses the encoder/decoder split plus learned `skip_weights`, so this is not just “more blocks”, it also changes the depth of both halves of the stack. |
| `ATTNRES_MODE=value_residual` | `GPT.forward()` + `CausalSelfAttention.forward()` | The model captures an early layer's attention values `v`, stores them in `v_res`, and then later layers inject them directly into the current attention value stream with `v = v + v_residual` before `scaled_dot_product_attention(...)`. |
| `ATTNRES_MODE=value_residual_gated` | `CausalSelfAttention.v_gate_param` | Same as `value_residual`, but the injected value stream is multiplied by `sigmoid(v_gate_param)`, a learned scalar gate. |
| `ATTNRES_MODE=value_residual_mid` | `GPT.forward()` | Same mechanism, but the capture point is moved from the first encoder layer to the middle encoder layer. |
| `ATTNRES_MODE=cumsum` | `GPT.forward()` + `Block.forward()` | Accumulates each layer's `attn_out` into `attn_cumsum` and feeds that back into the next blocks as `attn_residual`, so it modifies the attention input stream rather than the value tensor. |
| `CONV_KERNEL=3` | `Block.__init__()` + `Block.forward()` | Adds a depthwise `Conv1d` residual branch. In each block, `x` is mixed by the convolution before attention runs: `x = x + conv(...)`. This gives the block a cheap local sequence-mixing bias. |
| `EMBED_BOTTLENECK=64`, `TIE_EMBEDDINGS=0` | `GPT.__init__()` + `GPT.forward()` | Replaces the direct token embedding with a factorized path: `vocab -> bottleneck -> model_dim`. Because `TIE_EMBEDDINGS=0`, logits come from a separate `lm_head` instead of tied embeddings. |
| `MLP_ACT=silu` / `relu` / `mish` / `x_silu` | `MLP.forward()` | Chooses the MLP nonlinearity. `x_silu` is implemented as `h * silu(h)`, `mish` uses `F.mish(...)`, and `relu` / `silu` are the plain activation versions. |
| `NUM_KV_HEADS=4` | `CausalSelfAttention.__init__()` | Makes KV heads equal to Q heads, turning grouped-query attention into full MHA for that run. |

## Practical Read Of The Sweep

If I had to compress this follow-up queue into one line, it would be:

`value_residual` is the stabilizer, `conv3` is the most reliable cheap gain, and depth is only worth paying for when one of those stabilizers is already in place.

That implies the most promising directions after this sweep are:
- validate `u12_8L_vr_silu` at longer horizon
- validate `u25_8L_vr_relu` at longer horizon
- validate one of the strongest `conv3 + ebn64` hybrids, especially `u42_conv3_vr_silu_ebn64`

## Reproducibility

- **Archived queue:** `queues/archive/tiny/tiny50_followup_best.txt`
- **Runner:** `cp queues/archive/tiny/tiny50_followup_best.txt queues/active.txt && python3 infra/run_queue_tiny.py queues/active.txt --summary-every 5`
- **Progress log:** `logs/queue_progress_tiny50_followup_best.json`
- **Results:** `results/u*/summary.json`
- **Commit:** `66aee98`
