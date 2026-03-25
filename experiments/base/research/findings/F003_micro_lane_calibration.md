---
title: "Micro-Lane Calibration for Architecture Screening"
status: "DRAFT"
hypotheses: ["H005"]
published: ""
created: "2026-03-22"
---

# F003: Micro-Lane Calibration for Architecture Screening

## TL;DR

This report is the calibration shell for the reduced-model `micro_explore` lane. It measures whether the `nano` and `micro` rungs preserve large-margin architecture signals well enough to screen ideas before the normal 500-step full-width explore stage.

## Key Result

Pending wave 0. The critical outputs are:

- same-rung deltas for all 7 treatments
- sign agreement between `nano` and `micro`
- top-3 recall on `micro` for the known positives
- promotion recommendations from `research/compare_micro_lane.py`

## Background

The repo already uses 500-step exploration as a cheap screen, but it still runs leaderboard-shaped models. A reduced-model lane only makes sense if it buys real throughput without destroying the sign of obvious wins and losses.

Wave 0 uses known positive and negative architecture controls rather than novel ideas. If the lane cannot recover these controls, it should not be trusted for broader exploration.

## Method

- **Rungs:**
  - `nano`: 3L / 128d / 4h / 2kv / 500 steps
  - `micro`: 5L / 192d / 4h / 2kv / 500 steps
- **Fixed settings:** tokenizer, dataset, batch tokens, sequence length, activation, seed
- **Wave size:** 16 total runs
- **Ideas:** baseline, untied bn128, tied bn128, `moe_2e`, `moe_4e`, `attnres_vr`, `attnres_vr_mid`, `conv_k5`
- **Comparator:** same-rung baseline only
- **Exclusions:** OOM-tainted, shared-GPU-tainted, and incomplete runs are excluded from calibration metrics

## Results

### Raw Delta Table

| Idea | nano val_bpb | nano delta | micro val_bpb | micro delta | Sign agreement | Promotion decision |
|---|---:|---:|---:|---:|---|---|
| embed_bn128_untied | | | | | | |
| embed_bn128_tied | | | | | | |
| moe_2e | | | | | | |
| moe_4e | | | | | | |
| attnres_vr | | | | | | |
| attnres_vr_mid | | | | | | |
| conv_k5 | | | | | | |

### Gate Evaluation

| Gate | Threshold | Result |
|---|---|---|
| Micro positives beat baseline | 3 / 3 | |
| Negative controls lose on both rungs | 2 / 2 | |
| Top-3 recall on `micro` | at least 2 / 3 | |
| `micro` speedup vs full-width baseline | at least 2x | |
| Micro separation | positives all better than negatives | |

### Promotion Output

The lane uses:

- hard fail: `nano_delta >= +0.015` and `micro_delta >= +0.010`
- hard pass: `micro_delta <= -0.010`
- remaining score: `micro_delta + 0.5 * nano_delta`
- maximum promotions: 4

Paste the `research/compare_micro_lane.py` output here after wave 0.

## Discussion

- Whether the reduced models preserve sign, not whether they preserve exact ranking
- Whether `nano` is good enough for rejection
- Whether `micro` is good enough for shortlist promotion
- What ideas remain too sensitive to use as lane controls

## Reproducibility

- **Queue:** `queues/micro_wave0_calibration.txt`
- **Comparison script:** `research/compare_micro_lane.py`
- **Configs:** runner profiles `nano_3L128` and `micro_5L192`
- **Commit:** <fill after running>
- **Hardware:** <fill after running>
- **How to rerun:** `bash infra/run_queue.sh queues/micro_wave0_calibration.txt`
