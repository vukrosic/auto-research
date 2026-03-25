---
title: "Gradient scaling with activation magnitude is the primary mechanism behind squared activation gains"
status: "CONFIRMED"
origin: "Activation ablation wave 24 (gradient variants)"
finding: "findings/F001_activation_design_rules.md"
created: "2026-03-12"
---

# H002: Gradient scaling with activation magnitude is the primary mechanism behind squared activation gains

## Hypothesis
The performance gain from squaring activations is primarily explained by gradient magnitude scaling proportionally with activation magnitude. Flattening gradients to a constant will degrade performance by >0.05 BPB, while preserving proportional gradient scaling with a different function shape will preserve performance.

## Prior Evidence
- relu^2 backward: grad = 2x for x>0 (proportional to input)
- Standard relu backward: grad = 1 for x>0 (constant)
- Hypothesis: the 2x scaling is what matters, not the quadratic output shape

## Test Plan (pre-registered)
- **Baseline:** relu^2 (natural 2x gradient for x>0)
- **Treatments:** const-grad (force gradient=1), grad-floor (min gradient), grad-1.5x, grad-3x, x^2 gradient
- **Steps:** 500
- **Seeds:** 1
- **Success criterion:** const-grad >0.05 BPB worse than relu^2; proportional variants within 0.01 BPB
- **Kill criterion:** If const-grad performs equally to relu^2
- **Confounds:** Output magnitude differences; need to check both gradient AND output effects

## Experiments

| Name | Gradient type | val_bpb | Delta vs relu^2 | Pass? |
|---|---|---|---|---|
| relu^2 (baseline) | 2x (natural) | 1.4805 | — | — |
| const_grad | flat (=1) | +0.08 to +0.11 | +0.08-0.11 | YES (much worse) |
| grad_floor | min + proportional | best variant | ~0 | YES |
| grad_1.5x | 1.5x scaling | competitive | ~0 | YES |
| grad_3x | 3x scaling | competitive | ~0 | YES |
| x^2_grad | x^2 scaling | catastrophic | worst | Confirms proportional, not quadratic |

## Result
**CONFIRMED.** Flat/constant gradients cost +0.08 to +0.11 BPB (27-37x the noise floor). This is the single largest effect measured in the entire ablation study. Proportional gradient variants (gradfloor, 1.5x, 3x) all perform within noise of relu^2. The specific gradient multiplier doesn't matter much — what matters is that gradients scale with activation magnitude at all.

## Caveats
- "2x backward for x>0" falsified as the specific reason — 2·relu(x) matches scale but scores +0.023 worse, proving the quadratic output shape matters too
- Gradient scaling is necessary but not sufficient — you also need the right output shape
- Tested only at 500 steps; long-run confirmation at 2000+ steps for the key comparison
