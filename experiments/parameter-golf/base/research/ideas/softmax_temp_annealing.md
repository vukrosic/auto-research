# Softmax Temperature Annealing

**Tier**: 3 — Speculative
**Category**: Training trick
**Extra params**: 0
**Extra FLOPs**: 0

## Core Idea

Start training with attention softmax temperature τ=2.0 (soft, diffuse attention patterns) and anneal to τ=0.5 (sharp, confident) by end of training. Early training benefits from exploring associations broadly; late training benefits from precise, confident attention.

## Implementation Sketch

```python
# In attention:
attn_weights = (Q @ K.T) / (sqrt(head_dim) * temperature)
# temperature starts at 2.0, linearly anneals to 0.5 over training
```

Note: the model already has `logit_softcap=30.0` and `qk_gain_init=1.5` which interact with temperature.

## Risks

- Interacts with existing qk_gain and logit_softcap in unpredictable ways
- May destabilize early training if temperature is too high
- Annealing schedule needs tuning

---

## Literature Review Prompt

> **Prompt for literature review agent:**
>
> I want to anneal the attention softmax temperature during training of a small GPT (17M params). Start with high temperature (soft attention) and anneal to low temperature (sharp attention).
>
> Research:
> 1. Has attention temperature annealing been studied? Any results for language modeling?
> 2. Temperature scaling in attention — what's the typical range that works?
> 3. Interaction between attention temperature and learning rate schedules
> 4. "Warm-up then sharpen" training strategies for attention
> 5. Any connection to entropy regularization in attention?
>
> Brief results are fine — this is a quick check on feasibility.

## Literature Review

> _Paste into `/lab/research_papers/softmax_temp_annealing.md`_

**Agent chat URL**: <!-- paste URL here -->

---

## Status

- [ ] Literature review
- [ ] Implementation
- [ ] Experiment
- [ ] Result analysis
