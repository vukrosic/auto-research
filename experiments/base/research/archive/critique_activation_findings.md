# Critique: Activation Findings Document & Experimental Program

This critique examines the activation_findings.md document, the experimental methodology, the conclusions drawn, and what we should actually do next.

---

## 1. The document contradicts RESULTS.md and doesn't acknowledge it

**RESULTS.md (earlier)** concluded:
> "relu^2 is optimal. Two necessary properties: (1) Hard zeros (sparsity), (2) Quadratic amplification"

**activation_findings.md (later)** says:
> "Sparsity is not the mechanism" (falsified), and leaky(0.5)² beats relu²

These are opposite conclusions from the same project. The findings document never explicitly says "we were wrong in RESULTS.md" — it just quietly presents the new evidence. This is a problem for anyone reading both documents. RESULTS.md should either be updated or marked as superseded. As it stands, a reader could follow the wrong advice depending on which document they read first.

**More importantly:** the original RESULTS.md conclusion about sparsity was based on exactly the same kind of 500-step screening that the findings document now warns is unreliable for ranking. The lesson about 500-step unreliability should be applied retroactively — how many of the RESULTS.md conclusions were also premature?

---

## 2. The "three rules" framework is overfit to the data

The TL;DR presents three clean rules (H1, H2, H3) as if they independently predict activation quality. But:

### H2 is probably not an independent rule

The document itself admits this (line 293): "We cannot cleanly separate H2 from H1 with these experiments." Every bounded activation also has saturating gradients. The H2 results table perfectly correlates with degree of gradient saturation. The one experiment that could disentangle them — a bounded activation with artificially maintained proportional gradients — was never run.

**clamped16 beating relu² is the smoking gun.** If H2 ("don't compress the output range") were truly a rule, then clamping should always hurt. The fact that it helped (-0.008 BPB) suggests that what we're calling "H2" is really: "don't saturate your gradients" (which is just H1 again) plus "don't make your output range absurdly small" (which is a trivial scaling issue, not a deep principle).

### H3 is at or below the noise floor

The document claims H3 is "supported by consistency across 6+ variants." But look at the actual evidence:

- At 500 steps: 6 variants beat relu². Sounds convincing — but we've established that 500-step rankings are unreliable for differences <0.01 BPB. Every one of these deltas is in that unreliable range.
- At 4000 steps: the leak sweep shows 0.3/0.5/0.7 all within 0.0013 BPB of each other, which is within noise. They all beat relu² by 0.0015-0.0028 BPB — right at the ~0.003 noise floor.
- At 6000 steps: only leaky(0.5)² was tested. The 0.003 advantage over relu² is exactly the noise floor. One run per activation, one seed.

The statistical argument ("probability of all six landing on the same side by chance is ~1.6%") assumes independence. These are not independent — they all share the same training data, same seed, same hyperparameters. The correlation between runs sharing a code path is much higher than between coin flips. The actual effective number of independent tests is closer to 2-3, not 6, which puts the probability much higher than 1.6%.

**The x·|x| result destroys the H3 narrative.** If "preserving negative-side information helps" were a general rule, then x·|x| (which perfectly preserves all negative information with identical gradient magnitude to relu²) should be the best activation. Instead it's **worse than relu²** by +0.021 BPB. The document explains this away with "full sign preservation is actively harmful" — but that's an ad hoc patch. The real conclusion is: **we don't actually understand why leaky helps**. It might be negative-side information, or it might be that leaky's slightly different gradient landscape happens to work better with this specific optimizer/architecture combination. Those are very different conclusions with very different implications.

### The rules don't predict well out-of-sample

Consider the cross-hypothesis table:
- mish² satisfies all three rules and gets 1.4693 — good
- gelu² "satisfies" H2 and H3 (sort of) but gets 1.5857 — catastrophic
- x·|x| satisfies all three rules and gets 1.5014 — bad

If the three rules were genuinely predictive, every "all three ✓" activation should cluster together. They don't. The document handles this by retroactively marking gelu² as "✗ complex grad profile" for H1, but that's post-hoc reclassification to make the theory fit. By that logic you could mark *any* failing activation as "✗ something" and declare the theory confirmed.

---

## 3. Methodological problems

### 3a. Single-seed comparisons for everything below +0.01

Every activation was tested with a single seed (either 42 or 1337). The estimated noise floor is ~0.003 BPB. That means:

- Any claimed difference of <0.006 BPB is statistically meaningless from a single run
- The entire leaky vs relu² comparison rests on a signal that's 1x the noise floor
- The leak sweep used different seeds for different leak rates (0.5 got seed 42, 0.3/0.7 got seed 1337), making within-sweep comparisons unreliable

The document acknowledges this in places but then proceeds to draw conclusions from these comparisons anyway. "The gap is at the noise floor but it's consistent across checkpoints" — of course it's consistent across checkpoints within the same run. A seed-related advantage doesn't come and go between checkpoints; it's baked into the entire trajectory. Consistency across checkpoints within one run is not the same as consistency across independent trials.

### 3b. Confounded variables in cross-phase comparisons

The document mixes results from different phases, waves, and setups:

- relu² const-grad was from "wave 25 at ~1300 steps"; leaky const-grad was from "Phase 2 at 500 steps"
- relu^2.2 results are "from earlier run, may have different hyperparams"
- RESULTS.md used `WALLCLOCK=1955s`; Phase 2 experiments may use different settings

The cross-reference table comparing const-grad penalties across base functions mixes step counts (1300 vs 500), which makes the penalty magnitudes not directly comparable. The document adds a footnote but the table presents them side by side as if they're comparable.

### 3c. Incomplete runs used as evidence

Several experiments stopped early:
- gelu² stopped at step 426/500 — used as evidence for H3
- bipolar_relu² stopped at step 200/500 — listed with caveat but still included
- relu²_linneg0.5 stopped at step 200/500 — same
- arctan² stopped at step 421/500 — used as H2 evidence

Early-terminated experiments may have been killed for a reason (wallclock limit, NaN, etc.) or may have been on unusual trajectories that would have changed by step 500. Using their incomplete numbers as data points is questionable. The gelu² result (1.5857 at step 426) is particularly suspect — if it stopped due to instability, the high BPB might reflect the instability rather than the activation's true steady-state performance.

### 3d. The 500-step screening paradox

The document says: "500 steps is reliable for screening out clearly bad ideas" but "NOT reliable for ranking within the squared family." But where's the boundary? The document doesn't define what "clearly bad" means quantitatively. Is +0.01 clearly bad? Is +0.02? abs² leads at 500 but ties at 5000 — how do we know which current "losers" at 500 would catch up?

This is especially problematic because the entire Phase 2 experiment design relies on 500-step screening to decide what gets promoted to longer runs. If the screening threshold is wrong, we might be eliminating activations that would have been competitive at 13k steps.

---

## 4. The gradfloor result is more important than the document admits

`relu²_gradfloor` (gradient floored at 0.5) beat the natural relu² by 0.009 BPB at 500 steps. This is 3x the leaky advantage and 3x the noise floor. Unlike the leaky advantage, it's clearly above noise from a single run.

But the document buries this in the H1 results section and mentions it only once more in "What is still uncertain." This should be the #1 finding:

- It's a larger effect than the entire leaky vs relu² story (+0.009 vs +0.003)
- It has a clear mechanistic explanation (preventing neuron death)
- It hasn't been tested on leaky, which could stack the effects

The fact that `leaky(0.5)²_gradfloor` hasn't been tried yet — despite being the obvious combination of the two best findings — suggests the experimental program is more focused on testing hypotheses than on finding the best activation. Those are different goals. For competition purposes, the combination experiment should have been queued immediately.

---

## 5. The experimental program is too sprawling

The Phase 2 plan calls for:
- 9 H2 experiments (done)
- 9 H3 experiments (done)
- 11 cross-hypothesis experiments (partially done)
- 12 × 2000-step validation runs (pending)
- 6 × 4000-step validation runs (pending)
- 3 × 6000-step validation runs (pending)
- 2 × 13780-step final runs (pending)

That's 52+ experiments, many of which test subtle distinctions that won't change what we actually submit. For example:

- Do we really need both erf² AND softsign² to confirm that bounded activations hurt? One bounded activation failing is enough to not use bounded activations.
- Do we need mish² AND gelu² AND elu(0.3)²? If we're not going to submit any of them (leaky(0.5)² is the known best), what's the ROI?
- The cross-hypothesis experiments (leaky³, leaky^1.5, softplus variants) are interesting science but won't produce a submission candidate — we already know p=2 is optimal and leaky is the best base.

**The opportunity cost is real.** Every GPU-hour spent on the 47th activation experiment is a GPU-hour not spent on:
- Testing leaky(0.5)²_gradfloor (the most promising combination)
- Running leaky(0.5)² at 13k steps (the single experiment that decides submission)
- Exploring *other axes entirely* — architecture, learning rate schedules, data preprocessing, etc.

---

## 6. Specific claims that need correction or qualification

### "Squaring helps" is stated too broadly

The document says squaring "helps" for every simple activation. But:
- We only tested relu and silu with vs without squaring. elu, selu, celu, softplus only have squared results — no unsquared baselines.
- Squaring *hurts* gated activations. So it's not universal.
- The document's own data shows relu^2.2 getting 1.4546 vs relu²'s 1.4805 — *better* than squaring. But this is from "earlier run, may have different hyperparams." If that result is real, then p=2 isn't the sweet spot — and the whole "squaring is special" narrative needs revision.

### "Width > gating at matched params" is measured at 500 steps only

Full-width relu² essentially ties gated_relu² at 500 steps (1.4805 vs 1.4796). But we just said 500-step rankings are unreliable for differences this small. This conclusion needs longer-run validation before being stated as a rule.

### The quantization invariance claim is too strong

"Quantization does not change the activation ranking" is tested on exactly 3 activations at one checkpoint. This is a sample of 3. The claim that the ranking is preserved is trivially true when you only have 3 items whose pre-quant order is already marginal. The real question — does quantization interact differently with different activation shapes at scale — requires testing the full leaderboard, which hasn't been done.

---

## 7. What we actually know vs what we claim to know

**Genuinely solid findings (high confidence, >10x noise):**
- Removing proportional gradients is catastrophic (+0.08-0.12 BPB). H1 is real.
- Extreme output compression is bad (sigmoid², arctan²: +0.04-0.10 BPB)
- Squaring gated activations is bad (+0.04-0.14 BPB)
- relu² is much better than relu, silu, gelu without squaring (+0.02-0.05 BPB)
- A gradient floor of 0.5 helps relu² by ~0.009 BPB (3x noise, single seed)

**Suggestive but not proven (1-3x noise, limited seeds):**
- leaky(0.5)² is slightly better than relu² (~0.003 BPB)
- The leak rate doesn't matter much in 0.3-0.7
- The base function matters less than squaring at 2000+ steps

**Actively uncertain or possibly wrong:**
- Whether H2 is independent of H1 (probably not)
- Whether H3 is real or a seed/noise artifact (genuinely unclear)
- Whether gradfloor stacks with leaky (untested)
- Whether any of these findings hold at 13k steps on H100s (different hardware, different step budget)
- Whether leaky(0.8)²'s 500-step lead is real (likely not, given abs² precedent)
- Whether relu^2.2 is actually better than relu² (confounded by hyperparameter differences)

---

## 8. What the experimental program should do next

In priority order, based on maximizing competition placement:

1. **Run `leaky(0.5)²_gradfloor` at 500 steps** (~10 min). This is the most likely improvement: +0.009 (gradfloor on relu²) and +0.003 (leaky over relu²) could stack to +0.012, which is 4x noise and would be the biggest single-activation improvement found.

2. **Run `leaky(0.5)²` at 13k steps, 2 seeds** (~9 hrs). This is the validation experiment that decides submission. Everything else is secondary until we know if the leaky advantage survives at scale.

3. **If gradfloor + leaky stacks: run that at 13k steps instead.** Replace #2 with the better candidate.

4. **Stop running H2/H3/cross-hypothesis experiments.** They're interesting science but have near-zero probability of producing a submission-winning activation. The key findings are in. Move GPU time to other competition axes.

5. **Update RESULTS.md** to reflect the current understanding. The "hard zeros are necessary" conclusion is wrong and could mislead future work.

---

## 9. Meta-critique: hypothesis testing vs optimization

The experimental program treats activation search as a science project (test hypotheses, understand mechanisms) when the goal is a competition (find the best activation and submit it). These objectives diverge:

- A science project benefits from testing 9 H2 variants to map the full dose-response curve
- A competition benefits from testing 2-3 promising candidates at full scale

The 500-step screening → 2000-step → 4000-step → 6000-step → 13k-step pipeline is a good idea in theory, but only 5 activations have ever reached 2000 steps, only 4 have reached 4000 steps, and only 3 have reached 6000 steps. The pipeline's bottleneck is at the long-run end, not the screening end. We have excess screening capacity and insufficient validation capacity.

Meanwhile, the single most promising combination (gradfloor + leaky) hasn't even been tried at any step count. The 11 cross-hypothesis experiments testing edge cases like "softplus with beta=0.5" are using GPU time that should go to validating the likely winner.

**Bottom line:** We have enough understanding to pick a candidate. The remaining uncertainty is whether leaky(0.5)² (or leaky(0.5)²_gradfloor) holds up at 13k steps. Run that experiment. Everything else is intellectual curiosity, not competition strategy.
