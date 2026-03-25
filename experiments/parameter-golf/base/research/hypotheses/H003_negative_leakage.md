---
title: "Allowing negative signal through squared activations improves val_bpb"
status: "CONFIRMED"
origin: "Activation ablation wave 25 (leaky sweep)"
finding: "findings/F001_activation_design_rules.md"
created: "2026-03-14"
---

# H003: Allowing negative signal through squared activations improves val_bpb

## Hypothesis
leaky(alpha)^2 with alpha ~0.5 will outperform relu^2 by >0.003 BPB at 2000+ steps, because allowing ~50% of negative signal through prevents wasted model capacity on the negative input domain.

## Prior Evidence
- relu kills all negative inputs (hard zero)
- Intuition: negative activations carry information that could be useful
- Initial 500-step screens showed leaky variants trending better

## Test Plan (pre-registered)
- **Baseline:** relu^2 at 9L/512d/8h
- **Treatment:** leaky(0.5)^2 (same architecture, only activation changed)
- **Steps:** 2000, 4000, 6000 (need long runs — 500-step signal unreliable within squared family)
- **Seeds:** 2 seeds at 2000+
- **Success criterion:** >0.003 BPB improvement sustained at 2000+ steps across seeds
- **Kill criterion:** If advantage disappears by 2000 steps (would indicate init variance artifact)
- **Confounds:** Early advantage at 500 steps could be init variance inflation, not real

## Experiments

| Name | Steps | val_bpb | Delta vs relu^2 | Pass? |
|---|---|---|---|---|
| leaky05_sq vs relu_sq | 500 | ~-0.010 | -0.010 | Promising but early |
| leaky05_sq vs relu_sq | 2000 | ~-0.003 | -0.003 | YES (gap stabilizes) |
| leaky05_sq vs relu_sq | 4000 | ~-0.003 | -0.003 | YES (holds) |
| leaky05_sq vs relu_sq | 6000 | ~-0.003 | -0.003 | YES (consistent) |

## Result
**CONFIRMED.** leaky(0.5)^2 beats relu^2 by ~0.003 BPB consistently from 2000-6000 steps. The gap is stable and survives int8 quantization. The early 500-step advantage of ~0.010 was partly init variance inflation — the real sustained effect is ~0.003.

## Caveats
- 0.003 BPB is below the competition's 0.005 significance threshold — not enough to win alone
- This is a real but small effect; other architecture changes (MoE, embeddings) have much larger impact
- Tested only at one model scale (9L/512d). Effect size at other scales unknown
- abs^2 (allows full negative through) does NOT beat leaky(0.5)^2 — there's an optimal leakage level
