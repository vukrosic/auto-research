# Research Index

Research is organized in three stages: **Explorations** (free-form probing), **Hypotheses** (formal testable claims), and **Findings** (publication-ready results).

Runnable experiment definitions live in [`../experiments/specs/`](../experiments/specs/). Those specs link back to the docs below and are indexed by `auto-research` for scheduling and web control.

## Findings (Published)

| ID | Title | Status | Hypotheses |
|----|-------|--------|------------|
| F001 | [Activation Design Rules](findings/F001_activation_design_rules.md) | DRAFT | H001, H002, H003 |
| F002 | [Architecture Sweep at 16MB Scale](findings/F002_architecture_sweep.md) | DRAFT | H004 |
| F003 | [Micro-Lane Calibration for Architecture Screening](findings/F003_micro_lane_calibration.md) | DRAFT | H005 |

## Hypotheses

| ID | Claim | Status | Origin |
|----|-------|--------|--------|
| H001 | [Squaring activations improves val_bpb](hypotheses/H001_squared_activations.md) | CONFIRMED | Activation exploration |
| H002 | [Gradient scaling with magnitude is critical](hypotheses/H002_gradient_scaling.md) | CONFIRMED | Activation exploration |
| H003 | [Negative leakage improves squared activations](hypotheses/H003_negative_leakage.md) | CONFIRMED | Activation exploration |
| H004 | [Untied factored embeddings beat tied at 16MB](hypotheses/H004_untied_embeddings.md) | CONFIRMED | Architecture exploration |
| H005 | [Micro-LLM architecture screens preserve large-margin signs and promotion signal](hypotheses/H005_micro_surrogate_architecture.md) | PROPOSED | Micro-explore calibration |

## Explorations (Recent)

| Date | Title | Status |
|------|-------|--------|
| | *No explorations yet — use the template to start one* | |

## How It Works

```
Curiosity → Micro-Explore (500 steps, nano + micro ladder)
                ↓  "What survives cheap screening?"
         Exploration (500 steps, full-width shortlist)
                ↓  "I see a pattern..."
         Hypothesis (formal claim + pre-registered test plan)
                ↓  "Run the test"
         Validate (2000-4000 steps, multi-seed)
                ↓  "Confirmed / Falsified"
         Finding (publication-ready write-up)
                ↓
         X Post (/post skill)
```

See templates in each directory for the expected format.
