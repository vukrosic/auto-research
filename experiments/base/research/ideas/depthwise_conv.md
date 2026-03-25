# Depthwise Convolution Prefix

**Tier**: 2
**Category**: Architecture (hybrid attention+conv)
**Extra params**: ~4.5K/layer (~40K total)
**Extra FLOPs**: Negligible

## Core Idea

Add a causal depthwise conv1d (kernel=3 or 5) before attention in each block. This gives the model a cheap local receptive field — letting attention focus on long-range dependencies rather than wasting heads on adjacent-token patterns.

## Implementation Sketch

```python
# In each Block, before attention:
self.conv = nn.Conv1d(model_dim, model_dim, kernel_size=3,
                       padding=2, groups=model_dim)  # causal: pad left only

def forward(self, x, ...):
    # x: (batch, seq, dim)
    x = x + self.conv(x.transpose(1,2))[:, :, :seq_len].transpose(1,2)
    x = x + self.attn(self.ln1(x))
    ...
```

## Param Budget

- kernel=3, dim=512, depthwise: 512 × 3 = 1,536 params/layer
- 9 layers: ~14K params total (~14KB int8)
- kernel=5: 512 × 5 = 2,560 params/layer, ~23K total

## Risks

- May slow down training step (extra op per layer)
- Causal padding must be correct or it leaks future info
- Benefit may be small if attention already handles local patterns fine

---

## Literature Review Prompt

> **Prompt for literature review agent:**
>
> I'm adding depthwise causal convolutions before attention layers in a small (17M param, 9 layer) GPT trained on 1024-length sequences.
>
> Research:
> 1. Hybrid conv+attention architectures (ConvBERT, CvT, LiteTransformer) — did local conv before attention help for language modeling?
> 2. What kernel sizes work best for language (3? 5? 7?)?
> 3. Depthwise vs full conv — is depthwise sufficient for the local pattern capture role?
> 4. Does this help more at small model sizes where attention heads are scarce?
> 5. Any results from Mamba/H3-style architectures that suggest local conv is complementary to attention?
> 6. Causal conv implementation details — padding, efficiency in PyTorch
>
> Focus on language modeling perplexity. Small models preferred.

## Literature Review

> _Paste into `/lab/research_papers/depthwise_conv.md`_

**Agent chat URL**: <!-- paste URL here -->

---

## Status

- [ ] Literature review
- [ ] Implementation
- [ ] Experiment: kernel=3
- [ ] Experiment: kernel=5
- [ ] Result analysis
