# Per-Layer Learning Rate Scaling

**Tier**: 3 — Low effort, low risk
**Category**: Training trick
**Extra params**: 0
**Extra FLOPs**: 0

## Core Idea

Multiply each layer's gradients by a hand-tuned or learned scalar. Common pattern: linearly decay LR from early to late layers (or vice versa). This is sometimes called "layer-wise LR decay" and is standard in fine-tuning but underexplored for pretraining small models.

## Implementation Sketch

```python
# Simple linear decay: layer 0 gets full LR, layer 8 gets 0.5x
for i, block in enumerate(model.blocks):
    scale = 1.0 - 0.5 * (i / (num_layers - 1))
    for param in block.parameters():
        param.register_hook(lambda grad, s=scale: grad * s)
```

Or: use the existing Muon optimizer's per-param-group LR support.

## Risks

- Minimal — worst case it doesn't help
- May interact with existing per-param-type LR split (matrix/scalar/embed)
- Requires some sweeping to find the right decay schedule

---

## Literature Review Prompt

> **Prompt for literature review agent:**
>
> I'm considering per-layer learning rate scaling for pretraining a small GPT (17M params, 9 layers, Muon optimizer for matrix params, Adam for scalars).
>
> Research:
> 1. Layer-wise LR decay in pretraining (not fine-tuning) — any evidence it helps?
> 2. Which direction works: higher LR for early layers or late layers?
> 3. Typical decay factors used (e.g., 0.8x per layer, linear decay, etc.)
> 4. Interaction with Muon/Newton-Schulz optimizers — does per-layer LR make sense with second-order methods?
> 5. Any work on learned per-layer LR multipliers?
>
> Quick survey is fine.

## Literature Review

> _Paste into `/lab/research_papers/per_layer_lr.md`_

**Agent chat URL**: <!-- paste URL here -->

---

## Status

- [ ] Literature review
- [ ] Experiment: linear decay (early=1.0, late=0.5)
- [ ] Experiment: inverse (early=0.5, late=1.0)
- [ ] Result analysis
