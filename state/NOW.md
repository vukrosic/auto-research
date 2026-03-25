# NOW — Current Work Context

## ★ MISSION: Surpass transformer architecture for small LLMs
**Best: 1.3564 BPB → Target: <1.2244 BPB | Gap: 0.132 | Deadline: Apr 30, 2026**
Full goal: `goals/surpass_transformer_2026/MISSION.md`

> **This file is the handoff note.** If you are a new agent or resuming a session, read this first after AGENTS.md.
> Update it at every session close and whenever the current focus changes significantly.
> Keep it short — this is a snapshot, not a log.

**Last updated**: 2026-03-25
**Active goal**: surpass_transformer_2026
**Active campaign**: c01_close_the_gap

---

## What We're Doing Right Now

**Wave 0 — Baseline Calibration.** Not started yet.

The explore baseline in `experiments/current_best.json` is stale. It was measured on the old base config (`dim=512, no MoE`) but the current base is `dim=384, MoE4e, bn128u, leaky(0.5)²`. Every experiment result is meaningless without an apples-to-apples baseline at the same step count on the same architecture. This must happen before any real experiments run.

**What needs to happen next (in order)**:
1. Create `explore_baseline_v2` snapshot (unmodified base, 500 steps) → dispatch → record in `current_best.json`
2. Create `validate_baseline_v2` snapshot (unmodified base, 4000 steps) → dispatch → record
3. Begin Wave 1: ~20 explore experiments across 4 axes

---

## Current State

| Item | Value |
|------|-------|
| Best metric | 1.3564 BPB (pre-autoresearch, 4k steps, post-quant) |
| Explore baseline | **STALE** — 1.7362 BPB measured on old config (dim=512, no MoE) |
| Validate baseline | **NOT SET** |
| GPU | novita-rtx3090 — available, nothing running |
| Budget used this month | ~$4 of $40 |
| Active experiments | None running |
| Pending adjudication | None |

## Recent History (Debug Pipeline Run, 2026-03-25)

Ran 6 quick experiments to validate the pipeline, NOT real research:
- `explore_dim_wider_aa11` (dim 384→396): worse, eliminated
- `explore_layers_deeper_bb22` (9→10 layers): worse AND slower, eliminated
- `explore_mlp_mult_cc33` (mlp_mult 2→3): **identical to baseline** — discovered integer division bug (`max(1, mlp_mult // num_experts)` floors to same value for 2 and 3)
- Validate + full versions of the above: same conclusions

These were infrastructure tests, not real research. Findings recorded in `knowledge/parameter-golf/failures.md`.

## Immediate Blockers

- **Stale explore baseline**: must recalibrate before real experiments
- **No validate baseline**: must set before any validate-stage experiments

## What Wave 1 Will Test

Once baselines are set, Wave 1 covers 4 axes:
1. **Expert scaling**: 6/8 MoE experts at smaller dim (1.7 MB headroom available)
2. **Depth scaling**: more layers at narrower dim (12L@d320, 15L@d288, etc.)
3. **Attention variants**: head configs, QK-norm, RoPE base
4. **Vocabulary size**: 2048/4096 BPE tokens

Full wave schedule: `goals/surpass_transformer_2026/plans/2026_w13.md`

## Known Pitfalls / Don't Repeat

- `mlp_mult` changes are a no-op when `num_experts=4` — integer division kills the effect
- Size check every experiment: must stay under 16 MB (int8 zlib-compressed)
- Old explore baseline (1.7362) is wrong — do not compare against it
