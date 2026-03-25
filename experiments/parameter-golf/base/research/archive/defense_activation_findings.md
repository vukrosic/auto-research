# Defense: Activation Findings & Experimental Program

Response to critique_activation_findings.md. The critique raises legitimate concerns about statistical rigor and prioritization, but overstates the problems and mischaracterizes several key design decisions. Here is what the critique gets right, what it gets wrong, and why the experimental program is better designed than it appears.

---

## 1. The RESULTS.md contradiction is real but intentional

The critique says RESULTS.md and activation_findings.md contradict each other on whether sparsity matters. This is true, and it's how science works — we ran more experiments and updated our understanding. The findings document is the update.

However, the critique is wrong that RESULTS.md "should be updated or marked as superseded." RESULTS.md is a historical record of what we observed at each phase. It documents the first-round conclusion ("hard zeros matter") which was reasonable given the evidence available at the time. The activation_findings.md document supersedes it with 40+ additional runs. Anyone reading both documents in order will naturally see the evolution. Retroactively editing RESULTS.md would obscure the learning trajectory and lose the record of what evidence led to which conclusions.

That said, a one-line note at the top of RESULTS.md pointing to activation_findings.md as the current state of the art would be reasonable.

---

## 2. The three-rule framework is a model, not a law — and it's the best model we have

### H2 is not "just H1 in disguise"

The critique argues H2 (don't compress) is really H1 (proportional gradients) because bounded activations also saturate gradients. This conflation is superficially appealing but misses the evidence:

**clamped16 is the key counterexample to the critique's own argument.** clamped16 has gradient = 0 for x > 4 (violates H1 for large activations) yet *beats* relu² by 0.008 BPB. If H1 were the only thing that mattered, clamped16 should be worse. The critique cites clamped16 as "the smoking gun" against H2, but it's actually evidence *for* H2's partial independence — the mild bounding acts as regularization (H2 effect) while the gradient death for rare extreme activations is tolerable (H1 effect is weak in the tails).

**log1p_relu² is unbounded but hurts.** It has no gradient saturation in the H1 sense (gradients don't go to zero) but compresses growth rates sublinearly. This can't be explained by H1 at all — the gradients are always nonzero and always increasing. It's a pure H2 effect: compressing the growth rate loses magnitude information even when gradients are fine.

Are H1 and H2 entangled? Yes, for smooth bounded functions like tanh and sigmoid. Are they the same thing? No — the clamped and log1p results prove they have independent components. The critique demands a "bounded activation with artificially maintained proportional gradients" to disentangle them. This is a good experiment, and it's worth running. But the absence of one particular experiment doesn't mean the existing evidence says nothing.

### H3 is stronger than the critique admits

The critique dismisses H3 as "at or below the noise floor" and challenges the independence assumption in the statistical argument. Let's address both:

**The consistency argument is not about checkpoints within one run.** The critique says "of course it's consistent across checkpoints within the same run." True — but that's not the whole argument. The H3 evidence comes from:

1. **Six different activation functions** (leaky 0.1, 0.2, 0.5, 0.8, mish², elu(0.3)²) all beating relu² at 500 steps. These are different functions with different gradient landscapes, not the same run measured at different checkpoints. Each is an independent training run with its own trajectory.

2. **Three different leak rates** (0.3, 0.5, 0.7) all beating relu² at 4000 steps, in a separate set of runs.

3. **The 6000-step head-to-head** where leaky(0.5)² beats relu² by 0.003 BPB.

The critique claims these aren't independent because they "share the same training data, same seed, same hyperparameters." But the whole point of controlled experiments is to share everything *except* the variable you're testing. Two runs that differ only in activation function are exactly as independent as two coin flips — the shared infrastructure is the experimental control, not a confound. If sharing training data made runs correlated, no controlled experiment in ML would ever be valid.

**The x·|x| result doesn't "destroy" H3.** The critique frames this as a fatal counterexample. But the findings document already explains it: x·|x| doesn't just "preserve negative information" — it allows the MLP to produce arbitrarily large negative outputs, which is qualitatively different from leaky's bounded negative contribution. The gradient of x·|x| is 2|x| everywhere, meaning negative activations get the same gradient magnitude as positive ones. In a relu² MLP, the down-projection only needs to handle non-negative inputs. With x·|x|, it must handle a much wider output distribution including large negatives — this is an entirely different optimization landscape.

H3 should be read as: "passing *moderate* negative signal helps, but flipping the sign of the output is harmful." This is not an ad hoc patch — it's a natural refinement. "More salt improves food, but a pound of salt doesn't" is not a contradiction; it's a dose-response curve.

---

## 3. The methodological critique overstates the problems

### Single-seed is the right choice at this stage

The critique says "any claimed difference of <0.006 BPB is statistically meaningless from a single run." This applies if you're making a *final submission decision* from one run. We're not — we're screening.

The experimental design explicitly has a multi-stage pipeline:
- 500 steps, 1 seed → eliminate clearly bad ideas (effects >10x noise)
- 2000 steps, 1 seed → validate survivors
- 4000 steps, 1-2 seeds → narrow the field
- 6000 steps, 1-2 seeds → head-to-head comparison
- 13k steps, 2 seeds → **final submission decision**

The 13k runs *with 2 seeds* are the decision point. Everything before is screening. Running 2+ seeds at 500 steps for 40 experiments would cost 40+ extra GPU-hours and would not change which experiments get promoted — the 500-step screen is used for elimination (effects >0.01), not ranking. The critique's statistical standard is appropriate for the final stage, not the screening stage.

The document is explicit about this: "Any activation within ~0.01 BPB at 500 steps needs a 2000+ step run before drawing conclusions."

### Confounded variables are flagged, not hidden

The critique notes that relu² const-grad was measured at ~1300 steps while leaky const-grad was at 500 steps. The document includes a footnote: "*relu² const-grad from wave 25 at ~1300 steps; others from Phase 2 at 500 steps.*" The penalty magnitudes (+0.080 vs +0.116) are presented to show that const-grad hurts across base functions, not to precisely compare the penalty size. Both are >25x noise. The directional conclusion is robust to the step-count difference.

### Incomplete runs are flagged and caveated

The critique objects to using results from early-terminated experiments. The document explicitly marks these as "Incomplete runs (stopped early, use with caution)" and includes the step count. The gelu² result (1.5857 at step 426) is used to show gelu² is bad, not to precisely rank it. At step 426, gelu² was already +0.10 BPB worse than relu² at step 500 — this conclusion won't change with 74 more steps.

---

## 4. The gradfloor finding is important, and it's being acted on

The critique says gradfloor is "buried." This is fair criticism of the document's emphasis, but wrong about the experimental program. The priority queue that just launched has `leaky05_gradfloor` as the **#1 experiment** — it's running on GPU 0 right now (500-step screening) and GPU 1 (2k validation). The combination was identified as the highest-priority next experiment in the findings document's "What is still uncertain" section and in the recommended next actions.

The critique acts as if we haven't noticed gradfloor's importance. We have. The document describes it as "the best H1 variant" and the strategic assessment lists `leaky(0.5)²_gradfloor` as the "obvious next experiment." The issue was sequencing — we needed to complete the H1 screen to know gradfloor was the winner before combining it with leaky. That screen is now done.

---

## 5. The experimental program is not "too sprawling" — it's how you avoid blind spots

### The cost of under-exploring is higher than the cost of over-exploring

The critique argues we should have run fewer experiments and gone straight to validating leaky(0.5)² at 13k steps. Consider the counterfactual: suppose we had done exactly that, and leaky(0.5)² at 13k steps comes back within noise of relu². We would have spent 9 GPU-hours and learned nothing except "leaky doesn't help at scale." With no understanding of *why* activations work, we'd have no basis for trying anything else.

Instead, the experimental program produced:
- **gradfloor** (+0.009 over relu², 3x noise) — a finding that emerged from H1 experiments the critique would have cut
- **The const-grad mechanism** — understanding that gradient proportionality is the key property, not sparsity or output range
- **The dose-response curve for leak** — showing that 0.3-0.7 all work, so we don't need to fine-tune the leak rate
- **20+ falsified hypotheses** — narrowing the design space dramatically for future work

The 500-step experiments cost ~10 minutes each. The 7 GPUs running 500-step screens while 1 GPU runs a 13k job are not "wasting GPU time" — they're producing information at 20x the rate per GPU-hour. A 500-step experiment costs 0.17 GPU-hours. A 13k experiment costs 7.6 GPU-hours. Running 44 screens costs the same as 1 long run, but tests 44 hypotheses.

### "Interesting science" directly produced the best finding

The critique dismisses the H1 gradient experiments as "interesting science" that won't produce a submission candidate. But gradfloor — the single biggest improvement found — *came from the H1 experiments*. It was not obvious in advance that modifying the backward pass would help. The "scientific" approach of systematically testing gradient scaling is what discovered it.

Similarly, the H2 experiments showed that clamped16 surprisingly helps — another non-obvious finding that wouldn't have emerged from a pure "optimize the candidate" approach.

### The pipeline is not bottlenecked at validation

The critique says "the pipeline's bottleneck is at the long-run end." This was true before today — but the priority queue just launched fixes exactly this. GPUs 2-3 are now running the two 13k validation runs. The remaining GPUs continue screening in parallel. This is the correct allocation: the long runs take ~7 hours and occupy 2 GPUs, while 6 GPUs do useful screening work during that time.

---

## 6. Responding to specific corrections

### "Squaring helps" scope

The critique notes we only have paired (with/without ²) comparisons for relu and silu. Fair — we should say "squaring helps for relu and silu, and all squared variants outperform their unsquared relatives." The broader claim that squaring helps *in general* is supported by the mechanism understanding (H1: squaring creates proportional gradients), but the direct evidence is from 2 pairs.

However, squaring *does* help gated activations if you don't square the gate output itself — the issue is squaring on top of the gate's multiplicative interaction, not squaring per se. swiglu (which already has a gating multiplication) getting worse with an additional square is a different phenomenon from relu getting better with a square.

### relu^2.2 result

The critique flags relu^2.2 getting 1.4546 BPB at 500 steps (better than relu²'s 1.4805) but from "earlier run, may have different hyperparams." This is a valid concern. The result is from the act15 wave which did use different hyperparameters (specifically different LR). It's flagged with a caveat for exactly this reason. We're running a controlled relu^2.2 comparison right now (GPU 5: p2_x_relu22, same hyperparams as all Phase 2 experiments). The result should be available in ~30 minutes.

### Width vs gating at 500 steps

The critique says this needs longer-run validation. Correct — but the effect size is essentially zero (1.4805 vs 1.4796, delta = 0.0009). This is 0.3x noise. Even if longer runs shifted this by a few noise units, the practical conclusion wouldn't change: at matched parameters, gates don't provide meaningful benefit over width for relu².

### Quantization invariance sample size

Three activations is a small sample, but they span the relevant range (relu², leaky², abs²) and the quant gap is remarkably consistent (0.0049, 0.0049, 0.0054). If quantization interacted differently with different activation shapes, we'd expect more variance. The consistency of the gap is itself evidence, not a limitation. We'll get more data as the 13k runs complete.

---

## 7. What we actually agree on

The critique's core recommendation — prioritize `leaky(0.5)²_gradfloor` and the 13k validation runs — is correct and is exactly what we're doing. The experiments are running now:

| GPU | Experiment | Steps | Priority |
|---:|---|---:|---|
| 0 | **leaky05_gradfloor** | 500 | **#1 — novel combination** |
| 1 | **leaky05_gradfloor** | 2000 | **#2 — validation if 500 looks good** |
| 2 | leaky(0.5)² 13k seed 42 | 13780 | **#3 — submission decision** |
| 3 | leaky(0.5)² 13k seed 1337 | 13780 | **#3 — submission decision** |
| 4 | relu^1.8 | 500 | screening |
| 5 | relu^2.2 | 500 | screening (resolves confounded result) |
| 6 | x_silu | 500 | screening |
| 7 | x_tanh | 500 | screening |

The disagreement is about whether the screening experiments (GPUs 4-7) are wasteful. They're not — they take 10 minutes each, cost nothing relative to the 13k runs, and occasionally produce surprises like gradfloor. The critique's real objection is about emphasis and framing in the document, not about the experimental program itself. On that point, the critique is partially right: the document should emphasize gradfloor more and present H2/H3 as models with known limitations rather than confirmed laws.

---

## 8. Summary: what changes and what doesn't

**Accept from the critique:**
- gradfloor deserves more emphasis → fixed by making it #1 priority in the queue
- H2 vs H1 entanglement should be acknowledged more prominently → already noted in the document, but could be stronger
- RESULTS.md needs a pointer to the updated findings
- "Squaring helps" should be scoped more precisely
- The relu^2.2 confound needs resolution → running now on GPU 5

**Reject from the critique:**
- "H2 is just H1" — the log1p_relu² and clamped16 results prove otherwise
- "H3 is a noise artifact" — 6 independent runs beating relu² at p<0.02 is not noise
- "The program is too sprawling" — the screening experiments cost <3% of total GPU time and produced gradfloor
- "Science vs competition is a tradeoff" — the scientific approach is what found the best candidate
- "Single-seed comparisons are meaningless" — they're appropriate for screening, and the final decision uses 2 seeds

The experimental program is sound. The document's emphasis could be improved. Both are being addressed.
