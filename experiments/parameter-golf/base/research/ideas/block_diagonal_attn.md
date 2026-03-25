# Head Count / Head Dimension Sweep

**Tier**: 2
**Category**: Architecture (attention)
**Extra params**: 0 (same total, redistributed)
**Extra FLOPs**: Same

> **Note**: This overlaps with ROADMAP Phase 3 experiments `p3_heads_16_8`, `p3_heads_8_2`, `p3_heads_8_8`.
> This file adds literature context and a more detailed hypothesis. Consolidate with Phase 3 when running.

## Core Idea

Trade head dimension for head count: 16 heads × 32-dim instead of 8 heads × 64-dim. Same total parameters, double the number of attention patterns. The hypothesis: small models are head-starved and benefit from more diverse (but lower-capacity) attention patterns.

## Implementation

Already available via config:
```
NUM_HEADS=16 NUM_KV_HEADS=8   # 16×32-dim, 2:1 GQA
NUM_HEADS=16 NUM_KV_HEADS=4   # 16×32-dim, 4:1 GQA (saves KV params)
```

## Param Budget

Zero change. Same total QKV parameter count, just partitioned differently.

## Risks

- Smaller head_dim (32) may not capture complex attention patterns
- Flash attention may be less efficient with very small head dims
- 32-dim heads have less capacity per head — quality vs quantity tradeoff

---

## Literature Review Prompt

> **Prompt for literature review agent:**
>
> I have a small GPT (17M params, dim=512). Currently using 8 attention heads (head_dim=64, 4 KV heads with GQA). Considering switching to 16 heads (head_dim=32, 8 KV heads).
>
> Research:
> 1. Optimal head dimension for small transformers — is 32 too small?
> 2. Multi-head attention: more heads with smaller dim vs fewer heads with larger dim — what wins for language modeling?
> 3. Any evidence that small models benefit from more attention patterns (more heads)?
> 4. Block-diagonal attention / grouped query attention papers — what head counts work best at small scale?
> 5. Flash attention performance with head_dim=32 vs 64 — any efficiency concerns?
> 6. Has anyone systematically swept num_heads for models in the 10-50M range?
>
> Focus on language modeling. Concrete BPB/perplexity comparisons at small scale preferred.

## Literature Review

> _Paste into `/lab/research_papers/block_diagonal_attn.md`_

**Agent chat URL**: <!-- paste URL here -->

---

## Status

- [ ] Literature review
- [ ] Experiment: 16 heads, head_dim=32
- [ ] Experiment: 16 heads, 4 KV heads (4:1 GQA)
- [ ] Result analysis
