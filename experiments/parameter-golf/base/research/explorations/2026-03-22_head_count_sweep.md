---
title: "Attention head count sweep at d384 MoE4e"
date: "2026-03-22"
status: "ACTIVE"
experiments: ["exp_heads3_500", "exp_heads6_500", "exp_heads8_500", "exp_heads12_500"]
leads_to: ""
---

# Exploration: Attention head count sweep at d384 MoE4e

## Question
At dim=384 with MoE4e, we use 6 heads (3 KV). Is this optimal? Fewer heads = larger head dim = more expressive per head. More heads = more diversity. What's the tradeoff at this model scale?

## Setup
- **Baseline:** MoE4e bn128u d384, 6 heads / 3 KV heads
- **What I varied:** NUM_HEADS = {3, 6, 8, 12}, NUM_KV_HEADS = {heads/2}
- **Steps:** 500
- **Constraint:** All must stay under 16 MB submission size

## Raw Results

| Experiment | Heads | KV Heads | Head dim | val_bpb | Delta | Size (MB) |
|---|---|---|---|---|---|---|
| exp_heads3_500 | 3 | 2 | 128 | — | — | — |
| exp_heads6_500 | 6 | 3 | 64 | — | — | ~14.3 (baseline) |
| exp_heads8_500 | 8 | 4 | 48 | — | — | — |
| exp_heads12_500 | 12 | 6 | 32 | — | — | — |

## Observations
(Pending results)

## Next
- [ ] Worth a hypothesis? If head count shows clear non-monotonic trend
- [ ] Need more exploration? Test with/without GQA ratios
- [ ] Dead end? If 6 heads is clearly optimal or all within noise
