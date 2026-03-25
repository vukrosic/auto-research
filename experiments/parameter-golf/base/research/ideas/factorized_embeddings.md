# Factorized Embeddings

**Tier**: 1 — Highest ROI
**Category**: Architecture
**Extra params**: Negative (saves ~400K params)
**Extra FLOPs**: Negligible

## Core Idea

The current embedding is 1024×512 = 524,288 params. With only 1024 tokens, a full 512-dim representation per token is overkill. Factor it into:

```
embed: 1024 × 64  (65,536 params)
proj:  64 × 512   (32,768 params)
total:             98,304 params → saves ~426K params (~400KB int8)
```

The bottleneck dimension (64) can be tuned: 32, 64, 128.

## Why This Could Work Here

- Vocab size is tiny (1024 tokens). Most token-level distinctions can be captured in far fewer than 512 dims.
- The saved params can be reinvested: +1-2 layers, or wider model (512→544 dim)
- With tied embeddings, the output projection also becomes factored — may slightly help or hurt output quality

## Hypothesis

A 64-dim embedding bottleneck loses negligible quality for a 1024-token vocab, and reinvesting the saved 400KB into model capacity yields a net BPB improvement.

## Implementation Sketch

```python
class FactoredEmbedding(nn.Module):
    def __init__(self, vocab_size, bottleneck_dim, model_dim):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, bottleneck_dim)
        self.proj = nn.Linear(bottleneck_dim, model_dim, bias=False)

    def forward(self, x):
        return self.proj(self.embed(x))

# For tied output head:
# logits = F.linear(x, proj.weight) @ embed.weight.T
# Or keep untied if param budget allows
```

### Variants

1. **Bottleneck=64**: Aggressive, saves most
2. **Bottleneck=128**: Conservative, might preserve more quality
3. **Untied output**: Factor only input embed, keep full output projection
4. **SVD init**: Initialize from SVD of the pretrained full embedding

## Param / Size Budget

**Important**: The code keeps tensors with ≤65,536 elements as fp16 (not int8). This affects size math:
- Baseline embed (1024×512 = 524K elements) → int8: ~524KB + row scales
- Factored 1024×64 (65,536 elements) → right at the fp16/int8 boundary
- Factored 64×512 (32,768 elements) → fp16: ~64KB

| Bottleneck | Params | Compressed size (approx) | Size saved vs baseline ~525KB | Reinvestment |
|-----------|--------|-------------------------|-------------------------------|-------------|
| 32 | 33K + 16K = 49K | ~33KB (int8) + ~32KB (fp16) ≈ 65KB | ~460KB | +1 layer or dim +28 |
| 64 | 65K + 33K = 98K | ~65KB (boundary) + ~64KB (fp16) ≈ 130KB | ~395KB | +1 layer or dim +24 |
| 128 | 131K + 65K = 196K | ~131KB (int8) + ~128KB (fp16) ≈ 260KB | ~265KB | dim +16 |

## Risks

- Tied embeddings become more complex (two-step projection)
- The bottleneck might hurt rare token representations
- Quantization of two small matrices vs one larger one — unclear which compresses better

---

## Literature Review Prompt

> **Prompt for literature review agent:**
>
> I'm training a small GPT (17M params) with a tiny vocabulary of 1024 BPE tokens and 512 model dimension. The input/output embeddings are tied. I want to factorize the embedding into a low-rank bottleneck (e.g., 1024×64 then 64×512) to save parameters.
>
> Research the following:
> 1. ALBERT's factorized embedding — what bottleneck sizes worked and what were the perplexity impacts?
> 2. Does embedding factorization help or hurt more at small vocab sizes (<2K tokens)?
> 3. How does factorized embedding interact with tied input/output embeddings?
> 4. Optimal bottleneck dimension as a function of vocab size and model dim
> 5. Any evidence that small vocabularies already have low intrinsic dimensionality in their embeddings?
> 6. Interaction with int8 quantization — do factored small matrices quantize better or worse?
> 7. Can the saved parameters be reliably reinvested (more layers/width) for net gains?
>
> I care about language modeling BPB/perplexity, not classification. Practical guidance preferred.

## Literature Review

> _Paste your agent's output into `/lab/research_papers/factorized_embeddings.md`_

**Agent chat URL**: <!-- paste URL here -->

---

## Status

- [ ] Literature review
- [ ] Implementation
- [ ] Experiment: bottleneck=64
- [ ] Experiment: bottleneck=128
- [ ] Experiment: reinvest into +1 layer
- [ ] Result analysis
