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

## Weight Decay Study (2026-03-26)

Tested decoupled weight decay on the current MoE4e+bn128u+leaky(0.5)² base at 500 steps (baseline val_bpb=1.6673, SKIP_QUANT_EVAL=1):

| Experiment | Muon WD | Adam WD | val_bpb | Delta vs baseline |
|-----------|---------|---------|---------|-------------------|
| baseline  | 0       | 0       | 1.6673  | —                 |
| wd_muon01 | 0.01    | 0       | 1.6728  | +0.0055 (worse)   |
| wd_muon04 | 0.04    | 0       | 1.6844  | +0.0171 (worse)   |
| wd_both   | 0.04    | 0.01    | 2.9883  | +1.3210 (catastrophic) |

**Conclusions:**
- **Muon WD hurts at all tested values.** Even mild WD=0.01 degrades by +0.0055 BPB. Stronger WD=0.04 is worse still.
- **Adam WD on embeddings is catastrophic.** The `wd_both` run never learned — train loss plateaued at ~5.0 from step 50 onward. The embed_lr=0.6 combined with WD=0.01 fights the embedding learning. The Adam WD applies to tok_emb and scalar params including the factored embed bottleneck, which likely destroys the embedding space.
- **Weight decay is not useful for this architecture/scale.** The model is already small (16MB) and training is short (500-13780 steps). WD's regularization benefit doesn't materialize — it just slows convergence.
- **Do not revisit** unless the training schedule changes dramatically (10x+ more steps) or the model size constraint is relaxed.

Note: A previous leaderboard submission (2026-03-20_Int6_MLP3x_SmearGate_BigramHash_MuonWD_SWA) used muon_wd=0.04 + adam_wd=0.01, but that was a different architecture with different LRs. The current base with leaky(0.5)² does not benefit.

## Debug Pipeline Run (2026-03-25)

- **dim 396 (wider)**: val_bpb 3.7421 at 5 steps, 3.0823 at 15 steps. Consistently worse than baseline. Eliminated at validate.
- **num_layers 10 (deeper)**: val_bpb 3.7446 at 5 steps. Worse AND slower per step (695ms vs 624ms). Eliminated at explore.
- **mlp_mult 3x (wider MLP)**: val_bpb 3.7377/3.0239/2.5587 at 5/15/50 steps. Essentially identical to baseline at all stages. Neutral — no improvement. May revisit if combined with other changes.
