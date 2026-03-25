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
