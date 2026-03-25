# Wave 30 — Attention Residual Modes on Best Known Config

**Created:** 2026-03-22
**Source:** research pipeline planning
**Status:** PENDING APPROVAL

---

## Decision

Test attention residual connection modes stacked on the best known config (MoE4e + bn128_untied + leaky at dim=384). All modes are zero or near-zero parameter cost additions. If any mode improves BPB, it stacks cleanly with existing gains.

## Context

- **Best known:** MoE4e + bn128_untied + leaky at dim=384 → 1.3637 BPB at 4000 steps
- **Question:** Can attnres modes extract additional signal without consuming parameter budget?
- **Budget remaining:** ~$40 total (see /cost)
- **Wave 29 (attnres sweep) was deferred** — this wave covers it with proper Stage 1 format

## Architect's Position

MoE4e + bn128_untied at dim=384 is near the optimal parameter budget allocation. Adding attnres modes is essentially free compute for potential signal improvement. Value residual connections (V_res) propagating first-layer V to deeper layers is the most architecturally principled approach — it reduces attention's job by pre-loading long-range information. The weighted and cumsum variants add minimal complexity. Avoid the gated variant which has a mixed track record.

## Challenger's Position

The attnres experiments already ran briefly and showed cumsum hurts. Need to be careful about interpreting 500-step results — the ranking may shift at longer steps. Also, MoE already routes around the attention bottleneck, so attnres may add redundant capacity in an MoE context. Demand 2000-step validation before claiming any winner.

## Explorer's Position

Beyond attnres modes, consider: head count variations (12 heads vs 6 heads at same dim), QK gain sweep (we only tested 1.5, try 2.0 and 1.0), and tying attnres to the SoftMoE routing. Also: the attnres modes could be stacked with wider MLPs (MLP_MULT=3 or 4 instead of 2) since the parameter budget has headroom.

## Kill Criteria

- Any variant exceeds 16 MB → abort that variant
- Any variant at 4000 steps doesn't beat 1.3637 → drop that variant
- If all variants fail → pivot to new direction (see KNOWLEDGE.md Tier 2 ideas)

## Advancement Gate

**If any attnres mode beats 1.3637 at 4000 steps:**
→ Stage 2: Same config at 4000 steps × 2 seeds + try stacking with bn128_untied
→ Stage 3: Full 13,780-step run if Stage 2 confirms

**If no attnres improvement:**
→ Pivot to head count sweep or QAT design

## Budget Estimate

| Experiment | Steps | Est. Cost |
|---|---|---|
| exp30_vres_4k | 4000 | $4 |
| exp30_vres_mid_4k | 4000 | $4 |
| exp30_12heads_4k | 4000 | $4 |
| exp30_4heads_4k | 4000 | $4 |
| exp30_qkgain2_4k | 4000 | $4 |
| exp30_qkgain1_4k | 4000 | $4 |
| **Total** | | **~$24** |

## Proposed `active.txt` Payload

On approval, copy these lines into `queues/active.txt` rather than creating a second live queue file:

```text
exp30_vres_4k 4000 NUM_EXPERTS=4 MLP_ACT=leaky_relu2_05 MODEL_DIM=384 NUM_HEADS=6 NUM_KV_HEADS=3 EMBED_BOTTLENECK=128 TIE_EMBEDDINGS=0 ATTNRES_MODE=value_residual
exp30_vres_mid_4k 4000 NUM_EXPERTS=4 MLP_ACT=leaky_relu2_05 MODEL_DIM=384 NUM_HEADS=6 NUM_KV_HEADS=3 EMBED_BOTTLENECK=128 TIE_EMBEDDINGS=0 ATTNRES_MODE=value_residual_mid
exp30_12heads_4k 4000 NUM_EXPERTS=4 MLP_ACT=leaky_relu2_05 MODEL_DIM=384 NUM_HEADS=12 NUM_KV_HEADS=6 EMBED_BOTTLENECK=128 TIE_EMBEDDINGS=0
exp30_4heads_4k 4000 NUM_EXPERTS=4 MLP_ACT=leaky_relu2_05 MODEL_DIM=384 NUM_HEADS=4 NUM_KV_HEADS=2 EMBED_BOTTLENECK=128 TIE_EMBEDDINGS=0
exp30_qkgain2_4k 4000 NUM_EXPERTS=4 MLP_ACT=leaky_relu2_05 MODEL_DIM=384 NUM_HEADS=6 NUM_KV_HEADS=3 EMBED_BOTTLENECK=128 TIE_EMBEDDINGS=0 QK_GAIN_INIT=2.0
exp30_qkgain1_4k 4000 NUM_EXPERTS=4 MLP_ACT=leaky_relu2_05 MODEL_DIM=384 NUM_HEADS=6 NUM_KV_HEADS=3 EMBED_BOTTLENECK=128 TIE_EMBEDDINGS=0 QK_GAIN_INIT=1.0
```

---

*Approved by:* _________  *Date:* _________
