---
title: "Untied factored embeddings outperform tied embeddings at 16MB scale"
status: "CONFIRMED"
origin: "Architecture sweep wave 27"
finding: "findings/F002_architecture_sweep.md"
created: "2026-03-18"
---

# H004: Untied factored embeddings outperform tied embeddings at 16MB scale

## Hypothesis
Factored embeddings with a bottleneck (vocab -> bn -> dim) will improve val_bpb by >0.01 when the output head is untied (separate parameters), but will hurt when tied (shared weights), at the 9L/512d 16MB model scale.

## Prior Evidence
- Standard tied embeddings force the same matrix to serve both input representation and output prediction
- At small vocab (1024 BPE), these dual roles may conflict
- Factored embeddings reduce the embedding parameter count, freeing budget for model capacity

## Test Plan (pre-registered)
- **Baseline:** Standard tied embeddings, 9L/512d, ~17M params / 12.6 MB
- **Treatments:** Factored bn64/bn128/bn256, both tied and untied variants
- **Steps:** 500 (screening)
- **Seeds:** 1 at 500, 2 at validation
- **Success criterion:** Untied variant >0.01 BPB better than baseline; tied variant worse
- **Kill criterion:** If tied and untied perform similarly (would invalidate the tying hypothesis)
- **Confounds:** Parameter count differences between tied/untied

## Experiments

| Name | Config | val_bpb | Delta vs baseline | Pass? |
|---|---|---|---|---|
| baseline (tied) | standard | 1.4805 | — | — |
| bn128_untied | factored bn128, untied | -0.031 | -0.031 | YES (best legal) |
| bn128_tied | factored bn128, tied | +0.076 | +0.076 | YES (confirms tied hurts) |
| bn64_untied | factored bn64, untied | ~-0.02 | ~-0.02 | YES |
| bn256_untied | factored bn256, untied | ~-0.025 | ~-0.025 | YES |

## Result
**CONFIRMED.** Untied bn128 = -0.031 BPB at 12.6 MB — the best single legal architecture change found. Tied bn128 = +0.076 BPB (catastrophic). The untied/tied distinction is critical, not the bottleneck width. This is consistent with the hypothesis that input and output roles conflict at this scale.

## Caveats
- 500-step screening only for most variants; bn128_untied confirmed at 4000 steps in combination with MoE
- The effect could be specific to small vocab (1024 BPE) — larger vocabularies may behave differently
- Interaction with MoE confirmed positive (they stack cleanly), but interaction with other changes not fully explored
