# Shared-Weight Layer Cycling

**Tier**: 1 — Highest ROI
**Category**: Architecture
**Extra params**: 0 (or ~50 scalars for per-cycle scaling)
**Extra FLOPs**: 2x (double the effective depth)

## Core Idea

Use 4-5 unique transformer blocks but pass through them 2-3 times. A model with 5 unique blocks cycled twice has 10 effective layers but only 5 layers worth of parameters. This trades compute for depth — which is exactly the right trade when you're parameter-limited but compute-allowed.

## Why This Could Work Here

- The model is **depth-starved** (9 layers). Language modeling benefits from depth more than width at small scale.
- The 16MB cap limits parameters, not FLOPs. The 600s budget is generous enough for 2x FLOPs.
- Current throughput: ~43ms/step on 8xH100. Doubling depth to ~86ms/step still allows ~7,000 steps — plenty for convergence.

## Hypothesis

A 5-unique-block × 2-cycle model (10 effective layers) will outperform the current 9-unique-block model because:
1. Deeper models learn better hierarchical representations
2. Weight sharing acts as implicit regularization
3. The parameter savings can be reinvested into wider layers

## Implementation Sketch

```python
# Instead of:
self.blocks = nn.ModuleList([Block(i, config) for i in range(9)])

# Do:
self.blocks = nn.ModuleList([Block(i, config) for i in range(5)])
self.num_cycles = 2
# Optional: per-cycle learned scalars to break symmetry
self.cycle_scales = nn.Parameter(torch.ones(self.num_cycles, len(self.blocks)))

# In forward:
for cycle in range(self.num_cycles):
    for i, block in enumerate(self.blocks):
        x = block(x) * self.cycle_scales[cycle, i]
```

### Variants to Try

1. **5 blocks × 2 cycles** = 10 effective layers, reinvest saved params into width (dim=640+)
2. **4 blocks × 3 cycles** = 12 effective layers (aggressive sharing)
3. **5 blocks × 2 cycles, no U-Net**: Disable skip connections since the encoder/decoder split becomes ambiguous with cycling
4. **With per-cycle layer norm**: Each cycle gets its own RMSNorm parameters (cheap symmetry-breaking)

### Interaction with Existing Features

- **U-Net skip weights**: Needs rethinking — the encoder/decoder split changes with cycling
- **resid_mix**: Still connects to embedding, should work
- **RoPE**: Position encoding is input-dependent, so cycling is fine
- **Muon optimizer**: Shared weights get gradient from all positions — may need LR adjustment

## Param / Size Budget

With 5 unique blocks instead of 9, we save roughly:
- 4 × (attn + MLP + norms) ≈ 4 × 1.6M ≈ 6.4M params saved
- Can reinvest into wider remaining blocks (e.g., dim=640 instead of 512)
- Or add more unique blocks while staying under 16MB

## Risks

- Gradient magnitude scales with cycle count (each weight gets gradient from N positions) — likely need LR/N
- **U-Net skip connections fundamentally break** — the encoder/decoder split assumes unique layer indices. Cycling makes this ambiguous. Likely need to disable U-Net skips entirely, which removes an existing feature.
- The 2x compute cost reduces available training steps (from ~13,780 to ~7,000–9,000 depending on non-layer overhead). This is significant — fewer steps means less optimization.
- Weight sharing may create representational bottlenecks if layers need to specialize
- Step time is NOT simply 2x layer count — data loading, optimizer step (Muon's Newton-Schulz), and gradient sync add fixed overhead. Actual slowdown needs measurement.

---

## Literature Review Prompt

> **Prompt for literature review agent:**
>
> I'm training a parameter-constrained GPT language model (17M params, 16MB compressed model cap) and considering shared-weight layer cycling — reusing the same transformer blocks multiple times in a forward pass to increase effective depth without adding parameters.
>
> Research the following:
> 1. Universal Transformers and weight-sharing across layers — what were the key findings? Did they help for language modeling specifically?
> 2. ALBERT-style weight sharing — how much did it hurt vs. help, and at what model scales?
> 3. Any work on cycling through blocks multiple times (not just sharing all layers, but explicit multi-pass architectures)
> 4. How does gradient magnitude change with weight sharing, and what LR adjustments are recommended?
> 5. Does weight sharing act as regularization? Evidence for/against at small model scales (<50M params)
> 6. Interaction between weight sharing and residual connections — any stability concerns?
> 7. "Looped Transformers" or "recurrent depth" approaches — recent work on this?
> 8. Per-cycle conditioning or symmetry-breaking techniques (so the model knows which pass it's on)
>
> I care most about language modeling perplexity results, not classification. The model trains for ~14K steps on 8B tokens. Practical findings and concrete numbers preferred.

## Literature Review

> _Paste your agent's output into `/lab/research_papers/shared_weight_cycling.md`_

**Agent chat URL**: <!-- paste URL here -->

---

## Status

- [ ] Literature review
- [ ] Implementation
- [ ] Experiment: 5 blocks × 2 cycles
- [ ] Experiment: 9 blocks × 2 cycles
- [ ] Experiment: with reinvested params (wider)
- [ ] Result analysis
