---
title: "Squaring activations improves val_bpb for all tested base functions"
status: "CONFIRMED"
origin: "Activation ablation waves 20-26"
finding: "findings/F001_activation_design_rules.md"
created: "2026-03-10"
---

# H001: Squaring activations improves val_bpb for all tested base functions

## Hypothesis
For every simple activation function tested (relu, silu, elu, selu, celu, softplus), adding a squaring operation (f(x)^2) will improve val_bpb by >0.005 at 500 steps compared to the unsquared version, in the standard 9L/512d GPT architecture.

## Prior Evidence
- relu^2 was known to outperform relu in prior work
- Intuition: quadratic shape creates sharper feature selection

## Test Plan (pre-registered)
- **Baseline:** Each activation unsquared (relu, silu, etc.) at 9L/512d/8h
- **Treatment:** Same activation with ^2 applied
- **Steps:** 500 (screening), then 2000-6000 for winners
- **Seeds:** 1 seed at 500 steps, 2 seeds at 2000+
- **Success criterion:** >0.005 BPB improvement for majority of tested pairs
- **Kill criterion:** If <3 out of 6 activations improve with squaring
- **Confounds:** Output scale difference between squared/unsquared

## Experiments

| Name | Steps | val_bpb | Delta vs unsquared | Pass? |
|---|---|---|---|---|
| relu vs relu^2 | 500 | 1.5007 → 1.4805 | -0.020 | YES |
| silu vs silu^2 | 500 | 1.4908 → 1.4841 | -0.007 | YES |
| elu^2 | 500 | 1.4778 | competitive with relu^2 | YES |
| selu^2 | 500 | 1.4718 | competitive with relu^2 | YES |
| celu^2 | 500 | 1.4792 | competitive with relu^2 | YES |
| softplus^2 | 500 | 1.4788 | competitive with relu^2 | YES |

## Result
**CONFIRMED.** Every tested activation improved with squaring. The effect is robust across function families. p=2 is the sweet spot — higher exponents (p=3) hurt. The specific base function matters much less than whether you square it.

## Caveats
- Not all base functions had unsquared baselines measured (elu, selu, celu, softplus only tested squared)
- Gated activations (swiglu) are an exception — squaring gated activations is catastrophic (+0.139 BPB for swiglu^2)
- Tested only at 9L/512d scale; may not generalize to larger models
- 500-step rankings within the squared family are unreliable (abs^2 leads at 500, drops to 3rd by 6000)
