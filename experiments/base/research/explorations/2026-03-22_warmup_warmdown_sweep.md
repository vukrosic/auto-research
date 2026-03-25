---
title: "Warmup and warmdown schedule sweep"
date: "2026-03-22"
status: "ACTIVE"
experiments: ["exp_wu50_wd200_500", "exp_wu100_wd500_500", "exp_wu200_wd1000_500", "exp_wu50_wd0_500"]
leads_to: ""
---

# Exploration: Warmup and warmdown schedule sweep

## Question
The default warmup/warmdown settings were tuned for the baseline model. With MoE4e + bn128u + leaky05sq, the training dynamics are different (4 expert gates, factored embeddings). Are the current warmup/warmdown schedules still optimal?

## Setup
- **Baseline:** MoE4e bn128u d384 leaky05sq, default WARMUP_STEPS and WARMDOWN_ITERS
- **What I varied:** WARMUP_STEPS = {50, 100, 200}, WARMDOWN_ITERS = {0, 200, 500, 1000}
- **Steps:** 500
- **Note:** At 500 steps, warmdown has limited impact — this is mainly a warmup sensitivity check

## Raw Results

| Experiment | Warmup | Warmdown | val_bpb | Delta | Notes |
|---|---|---|---|---|---|
| exp_wu50_wd200_500 | 50 | 200 | — | — | Fast warmup |
| exp_wu100_wd500_500 | 100 | 500 | — | — | Moderate |
| exp_wu200_wd1000_500 | 200 | 1000 | — | — | Slow warmup |
| exp_wu50_wd0_500 | 50 | 0 | — | — | No warmdown |

## Observations
(Pending results)

## Next
- [ ] Worth a hypothesis? If warmup sensitivity is large (>0.01 BPB)
- [ ] Need longer runs? Warmdown effects only visible at 2000+ steps
- [ ] Dead end? If all schedules perform within noise at 500 steps
