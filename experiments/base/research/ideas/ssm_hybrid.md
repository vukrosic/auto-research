# SSM-Attention Hybrid (Mamba-style)

**Tier**: 3 — High ceiling, high risk
**Category**: Architecture (layer type)
**Extra params**: Similar or fewer per SSM layer
**Extra FLOPs**: Less (SSMs are cheaper than attention)

## Core Idea

Replace the first 2-3 layers (which handle local patterns) with lightweight state-space model (SSM) layers like Mamba. Keep the remaining layers as full attention for long-range dependencies. SSMs excel at local sequential patterns at a fraction of the cost.

## Why This Could Work

- Early layers in transformers mostly learn local n-gram patterns — SSMs handle this natively
- SSM layers are much cheaper per-layer than attention → can add more layers within compute budget
- Hybrid architectures (Jamba, Zamba) show this works at scale

## Implementation Sketch

Would need a minimal Mamba/S4 block implementation (~100 lines). The key operation is a selective scan (linear recurrence).

## Risks

- Custom CUDA kernel likely needed for efficiency (Mamba's triton kernel)
- SSM implementation complexity is high for a research experiment
- May not work well with only 1024 sequence length (SSMs shine on longer sequences)
- Mamba's selective scan may not have a good bf16 implementation

---

## Literature Review Prompt

> **Prompt for literature review agent:**
>
> I'm considering a hybrid SSM-attention architecture for a small GPT (17M params, 9 layers, seq_len=1024). The idea: replace early layers with Mamba-style SSM blocks, keep later layers as attention.
>
> Research:
> 1. Jamba, Zamba, and other hybrid SSM-attention architectures — which layers should be SSM vs attention?
> 2. Does the hybrid approach work at small scale (<50M params)?
> 3. Mamba/S4 performance on short sequences (1024 tokens) — is it still beneficial vs attention?
> 4. Minimal SSM implementation complexity — can it be done in pure PyTorch without custom kernels?
> 5. Parameter count comparison: SSM layer vs attention layer for same model dim
> 6. Any evidence that early layers specifically benefit from SSM (local pattern capture hypothesis)?
>
> I need to know if this is practical to implement and test in a few days with a single GPU.

## Literature Review

> _Paste into `/lab/research_papers/ssm_hybrid.md`_

**Agent chat URL**: <!-- paste URL here -->

---

## Status

- [ ] Literature review
- [ ] Feasibility assessment (implementation complexity)
- [ ] Implementation (if feasible)
- [ ] Experiment
- [ ] Result analysis
