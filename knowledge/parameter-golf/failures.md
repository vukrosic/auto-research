# Failed Approaches — Parameter Golf

Don't retry these without new evidence.

- **LR tuning alone** — FORBIDDEN per project rules. Must be architecture/mechanism changes.
- **Bounded activations** (tanh², sigmoid², erf², arctan²) — output compression hurts
- **Squaring gated activations** (swiglu², swirelu²) — catastrophically unstable
- **Constant-gradient activations** — +0.08-0.11 BPB penalty
- **Pure output scaling** (2·relu vs relu²) — doesn't replicate squaring benefit
- **Depthwise convolution** — all kernel sizes hurt (+0.025 to +0.174 BPB), bigger = worse
- **Tied factored embeddings** — catastrophic at all bottleneck sizes
- **Conv + anything combos** — conv damage compounds with other techniques

## Debug Pipeline Run (2026-03-25)

- **dim 396 (wider)**: val_bpb 3.7421 at 5 steps, 3.0823 at 15 steps. Consistently worse than baseline. Eliminated at validate.
- **num_layers 10 (deeper)**: val_bpb 3.7446 at 5 steps. Worse AND slower per step (695ms vs 624ms). Eliminated at explore.
- **mlp_mult 3x (wider MLP)**: val_bpb 3.7377/3.0239/2.5587 at 5/15/50 steps. Essentially identical to baseline at all stages. Neutral — no improvement. May revisit if combined with other changes.
