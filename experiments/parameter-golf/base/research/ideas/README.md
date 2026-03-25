# Architecture Ideas for Parameter Golf

**Context**: 17M-param GPT, 16MB int8+zlib cap, 600s on 8xH100, beat 1.2244 BPB by ≥0.005.

Each idea has its own file below. Literature reviews go in `/lab/research_papers/<idea>.md` (matching the attnres pattern). When an idea is promoted to an active experiment, create `/lab/experiments/<idea>/PLAN.md`.

---

## Tier 1 — Highest Expected ROI

| Idea | File | Why |
|------|------|-----|
| Quantization-Aware Training | [qat.md](qat.md) | 4h run quant gap is 0.0325 BPB (6x the target). Even partial recovery could win. Must measure 600s gap first. |
| Shared-Weight Layer Cycling | [shared_weight_cycling.md](shared_weight_cycling.md) | Free depth (5 unique → 10 effective layers), zero extra params. Trades compute for depth. |
| Factorized Embeddings | [factorized_embeddings.md](factorized_embeddings.md) | Vocab=1024, full 512-dim embed is wasteful. Reclaim ~400KB for depth/width. |

## Tier 2 — Strong Candidates

| Idea | File | Why |
|------|------|-----|
| Depthwise Conv Prefix | [depthwise_conv.md](depthwise_conv.md) | Cheap local patterns free attention for long-range. ~14K-23K params. |
| GEGLU / SwiGLU MLP | [geglu.md](geglu.md) | Different gated activation — relu² is already self-gated, so this is a swap not an upgrade. Needs testing. |
| Sparse MoE | [sparse_moe.md](sparse_moe.md) | 2x MLP capacity at same FLOPs via 2-expert routing. Unclear if it helps at 17M scale. |
| Head Count Sweep | [block_diagonal_attn.md](block_diagonal_attn.md) | 16×32-dim heads vs 8×64-dim. Overlaps with ROADMAP Phase 3 `p3_heads_16_8`. |

## Tier 3 — Speculative / High-Risk

| Idea | File | Why |
|------|------|-----|
| Progressive Dimension Growth | [progressive_dims.md](progressive_dims.md) | Narrow early → wide late. Adapter projections may eat the savings. |
| SSM-Attention Hybrid | [ssm_hybrid.md](ssm_hybrid.md) | Replace early layers with Mamba-style recurrence. High implementation cost. |
| Byte-Level Fallback Head | [byte_fallback_head.md](byte_fallback_head.md) | Exploit BPB metric's tokenizer-agnostic nature. Math may not work out. |
| Softmax Temp Annealing | [softmax_temp_annealing.md](softmax_temp_annealing.md) | Training trick, zero params. Interacts with existing qk_gain and logit_softcap. |
| Per-Layer LR Scaling | [per_layer_lr.md](per_layer_lr.md) | Training trick, zero params. Low risk, low effort. |

> **Note**: No BPB gain estimates are given because there is no evidence to support specific numbers.
> Tier placement reflects a qualitative judgment of likelihood × potential magnitude.

---

## Workflow

1. Pick an idea → read its file
2. Run the **literature review prompt** with your agent
3. Paste the agent's output into `/lab/research_papers/<idea>.md`
4. Paste the agent chat URL into the idea file
5. If promising after lit review → create `/lab/experiments/<idea>/PLAN.md`
6. Run experiments, log results in ROADMAP.md

## Status Tracker

| Idea | Lit Review | Experiment | Result |
|------|-----------|------------|--------|
| attnres | ✅ done | 🔄 in progress | cumsum hurts, value_res converging |
| qat | ⬜ todo | ⬜ | — |
| shared_weight_cycling | ⬜ todo | ⬜ | — |
| factorized_embeddings | ⬜ todo | ⬜ | — |
| depthwise_conv | ⬜ todo | ⬜ | — |
| geglu | ⬜ todo | ⬜ | — |
| sparse_moe | ⬜ todo | ⬜ | — |
| block_diagonal_attn | ⬜ todo | ⬜ | — |
| progressive_dims | ⬜ todo | ⬜ | — |
| ssm_hybrid | ⬜ todo | ⬜ | — |
| byte_fallback_head | ⬜ todo | ⬜ | — |
| softmax_temp_annealing | ⬜ todo | ⬜ | — |
| per_layer_lr | ⬜ todo | ⬜ | — |
