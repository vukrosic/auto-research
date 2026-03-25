# Byte-Level Fallback Head

**Tier**: 3 — Speculative
**Category**: Architecture (output head)
**Extra params**: ~130K
**Extra FLOPs**: Minimal

## Core Idea

The BPB metric is tokenizer-agnostic — it measures bits per raw byte. Add a small secondary output head that predicts UTF-8 bytes (256 classes) alongside the main 1024-token head. If the byte head is more confident on certain tokens, blend predictions. This directly attacks the metric.

## Implementation Sketch

```python
self.byte_head = nn.Linear(512, 256, bias=False)  # 131K params

# At inference:
token_logprobs = main_head(x)      # (batch, seq, 1024)
byte_logprobs = byte_head(x)       # (batch, seq, 256)
# Convert token logprobs to byte-level and blend with byte head
```

The tricky part is converting token-level predictions to byte-level for blending.

## Param Budget

512 × 256 = 131,072 params (~128KB int8). Fits within the ~140KB headroom.

## Risks

- Complex inference logic for token↔byte probability conversion
- The blending math is non-trivial and may not improve BPB
- Training two heads may dilute gradients from the main head
- 140KB headroom is very tight

---

## Literature Review Prompt

> **Prompt for literature review agent:**
>
> I'm training a GPT with a 1024-token BPE vocabulary, evaluated on bits-per-byte (BPB) — a tokenizer-agnostic metric. I want to add a secondary byte-level prediction head to potentially improve BPB.
>
> Research:
> 1. Byte-level language models vs subword models — when does byte-level prediction help?
> 2. Multi-granularity prediction heads (predicting at both token and byte level) — has this been tried?
> 3. How to correctly convert token-level log-probabilities to byte-level for BPB computation
> 4. Mixture of experts at the output level (blending multiple prediction heads)
> 5. ByT5, MegaByte, and other byte-level architectures — any insights for adding byte prediction to existing token models?
>
> This is speculative. I mainly need to know if the math works out — can a secondary byte head improve BPB for a model that's primarily token-based?

## Literature Review

> _Paste into `/lab/research_papers/byte_fallback_head.md`_

**Agent chat URL**: <!-- paste URL here -->

---

## Status

- [ ] Literature review
- [ ] Feasibility analysis (does the math work?)
- [ ] Implementation (if feasible)
- [ ] Experiment
- [ ] Result analysis
