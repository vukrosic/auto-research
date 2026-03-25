# Progressive Dimension Growth

**Tier**: 3
**Category**: Architecture (width scheduling)
**Extra params**: ~same total, redistributed
**Extra FLOPs**: Similar

## Core Idea

Instead of uniform dim=512 across all 9 layers, start narrow and widen:
- Layers 0-2: dim=384 (cheap feature extraction)
- Layers 3-5: dim=512 (mid-level composition)
- Layers 6-8: dim=640 (complex output representations)

Early layers extract simpler features and need less capacity. Final layers compose complex representations and benefit from more width. Total params stay roughly constant.

## Implementation Sketch

Requires adapter projections between dimension changes:
```python
dims = [384, 384, 384, 512, 512, 512, 640, 640, 640]
# Need linear projections at boundaries: 384→512, 512→640
self.adapters = nn.ModuleList([
    nn.Linear(dims[i], dims[i+1], bias=False)
    for i in range(len(dims)-1) if dims[i] != dims[i+1]
])
```

The adapters cost params (384×512 + 512×640 = 196K + 328K = 524K) but may be offset by the smaller early layers.

## Risks

- Adapter projections add params and may bottleneck information flow
- RoPE dimensions must match per layer — needs careful handling
- Non-standard architecture makes debugging harder
- The hypothesis (early=simple, late=complex) may not hold for 9 layers

---

## Literature Review Prompt

> **Prompt for literature review agent:**
>
> I'm considering a progressive/funnel architecture for a 9-layer GPT (17M params) where early layers are narrower and later layers are wider (e.g., 384→512→640 dimension).
>
> Research:
> 1. Funnel Transformer and similar progressive architectures — did varying width help for language modeling?
> 2. Evidence that early transformer layers learn simpler features than later layers (justifying less capacity)
> 3. Cost of dimension-change adapter projections — do they bottleneck or help?
> 4. Any work on non-uniform width in GPT-style autoregressive models specifically?
> 5. PaLM and other models that use varying dimensions — lessons learned?
>
> Small model results (<50M params) most relevant.

## Literature Review

> _Paste into `/lab/research_papers/progressive_dims.md`_

**Agent chat URL**: <!-- paste URL here -->

---

## Status

- [ ] Literature review
- [ ] Implementation
- [ ] Experiment
- [ ] Result analysis
