---
title: "RoPE base frequency sweep on MoE4e config"
date: "2026-03-22"
status: "ACTIVE"
experiments: ["exp_rope_500_500", "exp_rope_1k_500", "exp_rope_10k_500", "exp_rope_50k_500", "exp_rope_100k_500"]
leads_to: ""
---

# Exploration: RoPE base frequency sweep on MoE4e config

## Question
Does changing the RoPE base frequency from the default (10000) affect val_bpb on our best MoE4e d384 config? Some papers suggest higher bases improve length generalization, but we're training on short sequences — could a lower base help?

## Setup
- **Baseline:** MoE4e bn128u d384 leaky05sq (our best config), ROPE_BASE=10000
- **What I varied:** ROPE_BASE = {500, 1000, 10000, 50000, 100000}
- **Steps:** 500

## Raw Results

| Experiment | ROPE_BASE | val_bpb | Delta vs baseline | Notes |
|---|---|---|---|---|
| exp_rope_500_500 | 500 | — | — | to run |
| exp_rope_1k_500 | 1000 | — | — | to run |
| exp_rope_10k_500 | 10000 | — | — | baseline reference |
| exp_rope_50k_500 | 50000 | — | — | to run |
| exp_rope_100k_500 | 100000 | — | — | to run |

## Observations
(Pending results)

## Next
- [ ] Worth a hypothesis? If any base significantly outperforms 10000 at 500 steps
- [ ] Need more exploration? Test intermediate values if there's a clear trend
- [ ] Dead end? If all within noise (< 0.005 BPB)
