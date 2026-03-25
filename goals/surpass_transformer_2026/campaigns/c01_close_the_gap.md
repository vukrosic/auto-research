# Campaign: Close the Gap (c01)

**Status**: active
**Created**: 2026-03-25
**Project**: parameter-golf

## Goal

Reduce val_bpb from 1.3564 toward 1.2194 (leaderboard). Realistic week target: break **1.34 BPB** at explore (500 steps), confirming at least one new mechanism that stacks with the current best config.

Full target (1.2194) likely requires multiple campaigns and 8xH100 final training. This campaign focuses on **finding mechanisms that improve the architecture**, not hitting the final number.

## Starting Position

| Metric | Value |
|--------|-------|
| Current best | 1.3564 BPB (4k steps, post-quant) |
| Explore baseline | 1.7362 BPB (500 steps, OLD calibration — needs recalibration) |
| Leaderboard target | 1.2194 BPB |
| Gap | 0.137 BPB |
| Starting config | 9L, d384, 6H/3KV, MoE4e, bn128u, leaky(0.5)^2, 15.2M params, 14.3 MB |
| Size headroom | 1.7 MB (16.0 - 14.3 MB) |
| Param headroom | ~0.8M params (rough estimate for 1.7 MB) |

## Budget

| Resource | Allocated | Used | Remaining |
|----------|-----------|------|-----------|
| GPU-hours | 72 | 0 | 72 |
| Calendar | 7 days | 0 | 7 days |
| Dollar budget | $36 | $0 | $36 |

## Research Axes

Based on KNOWLEDGE.md analysis. Ordered by expected impact (gut estimate, will be updated).

| # | Axis | Status | Expected Impact | Rationale | Experiments Run | Best Result |
|---|------|--------|-----------------|-----------|-----------------|-------------|
| 1 | Expert scaling | active | high | MoE 4>3>>2, does 6 or 8 at smaller dim help? 1.7MB headroom allows it | 0 | — |
| 2 | Depth scaling | active | high | More layers at smaller dim — 12L@d320 still fits, more representational depth | 0 | — |
| 3 | Attention architecture | active | medium | Head size, QK-norm, window/linear attention — unexplored territory | 0 | — |
| 4 | Vocabulary size | active | medium | 2048/4096 BPE — more vocab = less modeling burden, proven in literature | 0 | — |
| 5 | Normalization & residuals | active | medium | Post-norm, deep scaling, scaled residuals — stability at depth | 0 | — |
| 6 | MoE routing variants | active | low-medium | Hard top-k vs soft, expert dropout — current soft routing may not be optimal | 0 | — |
| 7 | Training dynamics | active | low | Schedule, warmup/cooldown — careful, LR tuning alone is FORBIDDEN | 0 | — |
| 8 | Embedding architecture | active | low | bn64, bn256, different factorization — bn128 is best known but not exhaustively tested | 0 | — |

### Axis Notes

**Exhausted/closed axes** (from prior research — do NOT revisit):
- Activation functions (leaky(0.5)^2 is optimal, 60+ runs)
- Convolutions (all dead)
- Tied embeddings (catastrophic)
- dim=400 vs dim=384 (no advantage)
- QAT alone (within noise)

## Pivot Triggers

1. **2 consecutive waves with no explore beating baseline** → abandon lowest-performing axes, open combo experiments
2. **All single-mechanism axes exhausted** → pivot to mechanism combinations
3. **Budget >50% spent with <0.005 BPB improvement** → narrow to top 2 axes only, go deeper
4. **Fundamental size constraint discovered** → recalculate size budget, adjust dim/expert targets

## Wave Log

### Wave 0 — 2026-03-25 (setup)
- Recalibrate explore baseline with updated base config
- Axes: none (infrastructure)
- Decision: proceed to Wave 1 after baseline is set

### Wave 1 — 2026-03-25 to 2026-03-27
- Axes: Expert scaling (#1), Depth scaling (#2), Attention (#3), Vocab (#4)
- Experiments: ~20 explores
- See `ops/week_2026_w13.md` for detailed schedule

## Outcome

[To be filled when campaign completes]
