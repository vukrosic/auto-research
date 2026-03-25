# Knowledge Base

Persistent research memory for autonomous AI agents working on Parameter Golf.
**Update this file** whenever an experiment produces a significant finding — positive or negative.

Last updated: 2026-03-21

---

## Proven Facts (experimentally confirmed, high confidence)

### Activation Functions (60+ runs, 500–13000 steps)

1. **Squaring the activation is the single most impactful design choice.** All squared activations (relu², selu², abs², leaky²) significantly outperform their unsquared versions. The specific base function matters much less than whether you square it.

2. **Gradients must scale with activation magnitude (H1).** Flat/constant gradients cost +0.08–0.11 BPB (27–37x noise floor). This is the largest single effect measured. relu²'s backward gradient (2x for x>0) naturally provides this. Any replacement activation must preserve this property.

3. **Don't compress output range (H2).** Bounded activations (tanh², sigmoid², erf²) cost +0.01 to +0.10 BPB. The more aggressively outputs are compressed, the worse the result.

4. **Let negative signal through (H3).** leaky(0.5)² beats relu² by ~0.003 BPB consistently from 2000–6000 steps. The gap is stable and survives quantization. However, 0.003 BPB is below the competition's 0.005 significance threshold — **not enough to win on its own**.

5. **leaky(0.5)² is the best activation found.** Satisfies all three rules (H1+H2+H3). Progression: -0.010 at 500 steps → -0.003 at 2000+ steps (the early advantage is inflated by init variance).

6. **Don't square gated activations.** swiglu² costs +0.139 BPB (46x noise), swirelu² costs +0.042 BPB. The double multiplicative interaction is unstable.

7. **Quantization preserves activation ranking.** The int8 quant gap is ~0.005 BPB for all activations tested. Rankings are identical pre- and post-quant.

8. **500-step rankings are unreliable within the squared family.** abs² leads at 500 steps but drops to 3rd by 6000 steps. Any activation within ~0.01 BPB at 500 steps requires 2000+ step validation.

9. **relu² keeps improving through 13k steps** with no sign of collapse. Post-quant at 13k: 1.2498 BPB (vs leaderboard baseline 1.2244).

### Falsified Hypotheses

| Hypothesis | Test | Result |
|---|---|---|
| "Sparsity (hard zeros) is why relu² works" | abs² has no zeros, performs equally | **Falsified** |
| "Bigger outputs explain ²" | 2·relu(x) matches scale but scored +0.023 worse | **Falsified** — quadratic shape matters |
| "Gates always help" | gated_relu² tied with relu² at matched params | **Falsified** — width lost to gate costs as much as gate contributes |

### Architecture (71 experiments completed, 500-step screens)

- **Baseline model**: 9L, 512dim, 8 heads (4 KV), 1024 vocab, tied embeddings, ~17M params → 12.6 MB submission
- **Submission limit**: 16 MB (int8 zlib-compressed). All architecture choices must respect this.
- **Leaderboard baseline**: 1.2244 BPB (8xH100, 600s)
- **Our best legacy single-GPU result**: relu² at 13k steps → 1.2498 post-quant BPB

10. **MoE 4-expert fits under 16 MB at dim=384.** At dim=512, 4 experts → 24.7 MB (too large). At dim=384 (6 heads, 3 KV): 15.0M params → 14.2 MB ✓. At dim=400 (8 heads, 4 KV): 16.3M params → 15.3 MB ✓. dim=384 is the sweet spot (most room for extras like bn128).

11. **MoE expert count matters most.** 4 > 3 >> 2 experts. The jump from 2→4 is worth ~0.04 BPB at 500 steps. But only 2-expert fits under 16 MB at dim=512 (-0.006 to -0.019 BPB).

12. **Untied factored embeddings (bn128) are the best legal architecture change.** -0.031 BPB at 12.6 MB. Tied factored embeddings are catastrophic — bn128 tied *hurts* by +0.076 BPB. The untied/tied distinction is the critical factor, not the bottleneck width.

16. **MoE4e + bn128 untied + leaky at dim=384 is the best legal config found.** 15.2M params, 14.3 MB submission. At 4000 steps: 1.3564 quant BPB — beats MoE4e d384 alone (1.3637) by 0.007 BPB. bn128 untied and MoE stack cleanly. Full 13k runs in progress.

17. **dim=400 offers no advantage over dim=384 for MoE4e.** d400 (1.3661) ties or slightly loses to d384 (1.3637) despite 8% more params. The MoE architecture benefits more from expert diversity than raw width.

18. **MoE4e d384 is highly consistent across seeds.** s1337: 1.3637, s42: 1.3633. Δ=0.0004, well within noise. This config is robust.

13. **Depthwise convolution is a dead end.** Every variant hurts (+0.025 to +0.174 BPB). Monotonically worse with larger kernels. Combinations with other techniques compound damage.

14. **Weight sharing is not competitive alone** but produces small models (10.8 MB). Only ws_5x2_wide_leaky beats baseline (-0.010 BPB). Potentially useful combined with other techniques that add parameters.

15. **QAT alone is within noise (+/-0.003 BPB).** Does not hurt MoE — important for final submission.

## Failed Approaches (don't retry without new evidence)

- **LR tuning** — FORBIDDEN per project rules. Focus on architecture/mechanism changes only.
- **Bounded activations** (tanh, sigmoid, erf, arctan) — all squared variants hurt due to output compression
- **Squaring gated activations** (swiglu², swirelu²) — catastrophically unstable
- **Constant-gradient activations** — +0.08-0.11 BPB penalty, violates H1
- **Pure output scaling** (2·relu vs relu²) — does not replicate the benefit of squaring
- **Depthwise convolution** — all kernel sizes hurt (+0.025 to +0.174 BPB), bigger = worse
- **Tied factored embeddings** — catastrophic at all bottleneck sizes (+0.058 to +0.379 BPB)
- **QAT alone** — within noise, no measurable benefit without other changes
- **Conv + anything combos** — conv damage compounds with other techniques

## Open Questions

- [x] ~~Does weight sharing help?~~ Only ws_5x2_wide_leaky beats baseline (-0.010). Not competitive alone.
- [x] ~~Factorized embeddings?~~ Untied bn128 = -0.031 BPB (best legal result). Tied = catastrophic.
- [x] ~~Depthwise causal conv?~~ Dead end. All variants hurt.
- [x] ~~Soft MoE at 17M scale?~~ Powerful (+0.048) but 4-expert blows 16 MB budget by 22%.
- [x] ~~QAT alone?~~ Within noise. Doesn't hurt MoE — useful for submission.
- [ ] leaky(0.5)² at full 13k steps — does the 0.003 gap hold?
- [x] ~~Can MoE 4-expert fit under 16 MB at reduced dim?~~ YES. dim=384 → 14.2 MB, dim=400 → 15.3 MB. Both legal.
- [x] ~~Does MoE 4e + untied bn128 + leaky stack?~~ YES. Best combo found: 1.3564 quant BPB at 4k steps, 14.3 MB.
- [ ] **Does MoE4e bn128u d384 hold at 13k steps?** Full runs in progress on 4 GPUs.
- [ ] **Can we close the 0.10+ BPB gap to 1.2244 leaderboard?** Need 13k results + possible further tricks.
- [ ] **Does QAT help the reduced-dim MoE4e config?** Testing with QAT_START_FRAC=0.7.

## Current Best Configuration

```
Architecture:  9-layer GPT, 384-dim, 6 heads, 3 KV heads
Activation:    leaky(0.5)²
Embeddings:    Untied factored bn128 (vocab→128→384, separate output head)
MoE:           4 soft experts (expert_mult=1, hidden=384 per expert)
Vocab:         1024 BPE
Optimizer:     Muon
Params:        15.2M → 14.3 MB submission
Best result:   1.3564 post-quant BPB (4k steps, 5090) — 13k runs in progress
Target:        <1.2194 BPB (beat leaderboard by ≥0.005)
Gap to close:  ~0.10+ BPB (awaiting 13k results)
```

### Best Legal Architecture Candidates (4000-step validation, quant BPB)

```
#1  MoE4e + bn128u + leaky d384:  1.3564 BPB, 14.3 MB  ← BEST (full runs started)
#2  MoE4e + leaky d384 s42:       1.3633 BPB, 14.2 MB
#3  MoE4e + leaky d384 s1337:     1.3637 BPB, 14.2 MB
#4  MoE4e + leaky d400 s1337:     1.3661 BPB, 15.3 MB
    MoE4e + bn128u + leaky + QAT: IN PROGRESS (13k)
```

## Core Research Principle: Tiered Elimination

**The central method for all architecture search in this repo.**

Run many ideas cheaply. Kill losers early. Scale only survivors. Never spend full compute on an unscreened idea.

### The Rule

> If an architecture doesn't beat the baseline at short duration, it almost certainly won't beat it at long duration. The 1s ranking predicts the 3s ranking. Trust the ladder.

### How It Works

1. **Screen wide** — run 10–15 architecture variants at the shortest budget (1s / ~1 step). Most ideas die here.
2. **Promote narrow** — take the top 5 and re-run at 2x duration. The noise floor drops; weak ideas that looked good at 1s get exposed.
3. **Finalize** — top 3 at 3x duration. Only run full experiments (500+ steps) on these finalists.
4. **Write the report** — always output `results/tiered_screen_<date>.md` with three markdown tables (one per stage), delta vs. baseline, and a conclusion.

### Why This Works

- CUDA/Python startup is constant overhead — amortize it by running all variants in a **single process** (see `infra/tiered_screen.py`).
- Each step is a noisy signal. More steps = less noise. The ladder buys signal incrementally instead of all at once.
- Elimination is irreversible by default — don't re-promote dropped candidates without new evidence.

### Implementation

- Write `screens/<topic>.py` with a `CONFIGS` list (copy `screens/template.py`).
- Run: `python3 infra/tiered_screen.py --screen screens/<topic>.py [--ladder quick|standard|thorough]`
- Report written to: `results/tiered_screen_<topic>_<date>.md`
- Move finished screen files to `screens/archive/`.
- Use the `/tiered-screen` skill to let Claude pick candidates and orchestrate.

---

## Research Pipeline

| Stage | Steps | Time (reference single-GPU) | Purpose | Threshold to advance |
|-------|------:|-------------|---------|---------------------|
| Tiered Screen (1s) | ~1 | seconds | Eliminate bad ideas | beat baseline delta |
| Tiered Screen (3s) | ~3 | seconds | Confirm finalists | consistent delta across stages |
| Explore | 500 | ~28 min | Screen many ideas fast | >0.01 BPB improvement |
| Validate | 2000 | ~1.8 hr | Confirm explore winners | >0.005 BPB on 2+ seeds |
| Scale | 5000 | ~4.6 hr | Near-final signal | Consistent improvement |
| Full | 13780 | ~12.7 hr | Pre-submission | Beats 1.2244 BPB |
