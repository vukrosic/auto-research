# Sparse Mixture of Experts (MoE)

**Tier**: 2
**Category**: Architecture (MLP)
**Extra params**: ~512/layer for router + expert duplication
**Extra FLOPs**: ~same (only 1 expert active per token)

## Core Idea

Replace the single MLP per layer with 2 expert MLPs, each half the width. A lightweight sigmoid router selects which expert processes each token. Result: double the total MLP capacity at the same FLOPs — the model can specialize different experts for different token types.

## Implementation Sketch

```python
class MoEMLP(nn.Module):
    def __init__(self, dim, num_experts=2):
        self.experts = nn.ModuleList([MLP(dim, hidden=dim) for _ in range(num_experts)])  # half-width each
        self.router = nn.Linear(dim, num_experts, bias=False)  # tiny

    def forward(self, x):
        # x: (batch, seq, dim)
        scores = self.router(x).softmax(dim=-1)           # (batch, seq, 2)
        idx = scores.argmax(dim=-1)                        # top-1 routing
        # Dispatch to experts (simplified — real impl needs scatter/gather)
        out = torch.zeros_like(x)
        for e in range(len(self.experts)):
            mask = (idx == e)
            if mask.any():
                out[mask] = self.experts[e](x[mask])
        return out
```

### Variant: Shared Down-Projection

Experts share `W_down` but have independent `W_up`. Saves params while keeping specialization in the up-projection where it matters most.

## Param Budget

- 2 experts, each hidden=512 (vs current single expert hidden=1024): same total MLP params
- Router: dim × 2 = 1,024 params/layer (~9K total). Negligible.
- With shared down-proj: saves ~2.4M params across 9 layers (one 512→512 down-proj shared vs duplicated) → reinvest

## Risks

- Token routing is discrete → need straight-through or soft routing
- Load balancing loss adds complexity
- May not help with only 2 experts (limited specialization)
- PyTorch MoE dispatch with masking loops is very slow without custom kernels
- **Simpler alternative**: soft merging (weighted average of both experts) avoids discrete routing entirely and is trivially efficient. With only 2 experts, soft merge may be strictly better than hard routing.

---

## Literature Review Prompt

> **Prompt for literature review agent:**
>
> I want to add a simple 2-expert Mixture of Experts (MoE) to the MLP layers of a 17M-param GPT. Each expert would be half-width, so total params stay the same but capacity doubles.
>
> Research:
> 1. Does MoE help at very small scales (10-50M params)? Most MoE papers study large models.
> 2. 2-expert MoE vs. single wider MLP — when does specialization actually emerge?
> 3. Routing strategies for tiny MoE: top-1 hard routing vs. soft merging vs. expert choice
> 4. Load balancing: is it needed with only 2 experts, or does it self-balance?
> 5. Efficient PyTorch implementation of 2-expert MoE (without Megablocks/Triton kernels)
> 6. Shared projections between experts — does sharing down-proj work?
> 7. Training stability: does MoE introduce routing collapse at small scale?
>
> I care about language modeling perplexity, not classification. Focus on whether this is practical for 17M params trained for ~14K steps.

## Literature Review

> _Paste into `/lab/research_papers/sparse_moe.md`_

**Agent chat URL**: <!-- paste URL here -->

---

## Status

- [ ] Literature review
- [ ] Implementation
- [ ] Experiment: 2 experts, half-width
- [ ] Experiment: shared down-projection
- [ ] Result analysis
