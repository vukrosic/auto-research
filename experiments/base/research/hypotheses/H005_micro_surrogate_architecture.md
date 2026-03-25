---
title: "Micro-LLM architecture screens preserve large-margin signs and promotion signal"
status: "PROPOSED"
origin: "Micro-explore wave 0 calibration"
finding: "findings/F003_micro_lane_calibration.md"
created: "2026-03-22"
---

# H005: Micro-LLM architecture screens preserve large-margin signs and promotion signal

## Hypothesis

Reduced-model architecture screens on a fixed two-rung ladder:

- `nano`: 3L / 128d / 4h / 2kv / 500 steps
- `micro`: 5L / 192d / 4h / 2kv / 500 steps

preserve the sign of large-margin wins and losses against the same-rung baseline well enough to reject bad ideas cheaply and promote a small shortlist into the normal full-width 500-step explore stage.

More specifically:

1. Large-margin positives and negatives keep the same sign on both rungs.
2. `nano` is sufficient for cheap rejection.
3. `micro` is sufficient for promotion-quality confirmation.

## Prior Evidence

- The repo already contains a dormant reduced-scale sweep in `queues/archive/wave_27_scale_sweep/wave27_scale_sweep_500.txt`.
- Existing 200-step results show `pico` and `ultra` are below the fidelity floor, while `nano` and `micro` are still viable LLMs.
- Architecture findings already establish strong controls:
  - positives: untied bn128 embeddings, `moe_2e`, `moe_4e`
  - negatives: tied bn128 embeddings, `conv_k5`

## Test Plan (pre-registered)

> **Lock this section before running experiments.** Any edits after results arrive must be noted.

- **Baselines:**
  - `micro_nano_baseline`
  - `micro_micro_baseline`
- **Treatments:** the same 7 architecture ideas on both rungs
  - `embed_bn128_untied`
  - `embed_bn128_tied`
  - `moe_2e`
  - `moe_4e`
  - `attnres_vr`
  - `attnres_vr_mid`
  - `conv_k5`
- **Steps:** 500 on both rungs
- **Seeds:** 1 (`1337`) for calibration wave 0
- **Success criterion:**
  - `embed_bn128_untied`, `moe_2e`, and `moe_4e` beat baseline on `micro`
  - `embed_bn128_tied` and `conv_k5` lose to baseline on both rungs
  - at least 2 of the 3 known positives land in the top 3 by `micro` delta
  - `micro` baseline is at least 2x faster than a clean full-width 500-step explore baseline on the same host
- **Kill criterion:**
  - if `micro` cannot separate the known positives from the known negatives, abort the lane
  - if a run is OOM-tainted, shared-GPU-tainted, or incomplete, exclude it from calibration metrics and rerun if needed
- **Confounds to control:**
  - fixed tokenizer, dataset, batch tokens, sequence length, activation, and seed
  - architecture-only scope in wave 0
  - same-rung delta comparisons only

## Experiments

| Name | Rung | Steps | val_bpb | Delta vs rung baseline | Pass? |
|---|---|---:|---:|---:|---|
| micro_nano_baseline | nano | 500 | | | |
| micro_nano_embed_bn128_untied | nano | 500 | | | |
| micro_nano_embed_bn128_tied | nano | 500 | | | |
| micro_nano_moe_2e | nano | 500 | | | |
| micro_nano_moe_4e | nano | 500 | | | |
| micro_nano_attnres_vr | nano | 500 | | | |
| micro_nano_attnres_vr_mid | nano | 500 | | | |
| micro_nano_conv_k5 | nano | 500 | | | |
| micro_micro_baseline | micro | 500 | | | |
| micro_micro_embed_bn128_untied | micro | 500 | | | |
| micro_micro_embed_bn128_tied | micro | 500 | | | |
| micro_micro_moe_2e | micro | 500 | | | |
| micro_micro_moe_4e | micro | 500 | | | |
| micro_micro_attnres_vr | micro | 500 | | | |
| micro_micro_attnres_vr_mid | micro | 500 | | | |
| micro_micro_conv_k5 | micro | 500 | | | |

## Result

Pending wave 0.

## Caveats

- This hypothesis is about screening utility, not leaderboard competitiveness of the reduced models.
- Single-seed calibration is acceptable for the lane decision, not for publication-grade architectural claims.
- Sign preservation is the target. Fine ranking within a narrow band is not.
