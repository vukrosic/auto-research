# Quantization-Aware Training (QAT)

**Tier**: 1 — Highest ROI
**Category**: Training technique
**Extra params**: 0
**Extra FLOPS**: Negligible (~5% overhead from fake-quant ops)

## The Opportunity

The 4h unlimited run showed:
- Pre-quant BPB: 1.1749
- Post-quant BPB: 1.2074
- **Quant gap: 0.0325 BPB**

The target improvement is 0.005 BPB. The quant gap alone is **6.5x** the target. Even recovering 15% of the quant gap would beat the record.

**Caveat**: The 0.0325 gap was measured on a model trained for 14,400s (24x longer than the 600s competition run). The actual quant gap for the 600s baseline may be smaller — less-trained models have noisier weights that may be less sensitive to quantization. **First step: measure the actual quant gap on a 600s/13,780-step run.**

## Hypothesis

Training with simulated int8 quantization noise (straight-through estimator) in the last 20-30% of steps will make weights more robust to quantization, reducing the gap by 30-60%.

## Implementation Sketch

```python
# Fake quantization with straight-through estimator
# IMPORTANT: must match the actual quantization scheme in quantize_float_tensor():
#   - per-row scales for 2D tensors, clip at 99.99984 percentile, clamp -127..127
def fake_quant_int8(w):
    # Per-row scale (matching actual quant code)
    scale = w.abs().amax(dim=-1, keepdim=True) / 127.0
    scale = scale.clamp_min(1.0 / 127.0)
    w_q = (w / scale).round().clamp(-127, 127) * scale
    return w + (w_q - w).detach()  # STE: forward uses quantized, backward sees original grads

# Apply in the FORWARD PASS, not to param.data (which would break optimizer states).
# Best approach: modify CastedLinear.forward() to apply fake_quant during QAT phase:
class CastedLinear(nn.Linear):
    def forward(self, x):
        w = self.weight
        if self.training and self.qat_enabled:
            w = fake_quant_int8(w)
        return F.linear(x, w.to(x.dtype))
```

### Variants to Try

1. **Basic**: Fake-quant all matrix weights for last 30% of training
2. **Annealed**: Gradually increase quant noise (smooth transition)
3. **Per-row**: Match the actual per-row int8 scheme used in submission quantization
4. **Aggressive**: Fake-quant from step 1 (likely hurts convergence but maximizes robustness)

## Param / Size Budget

Zero extra parameters. The model is identical — only training procedure changes.

## Risks

- STE can destabilize training if introduced too aggressively
- May need LR reduction during QAT phase
- Fake-quant granularity must match actual submission quantization (per-row scales)

---

## Literature Review Prompt

> **Prompt for literature review agent:**
>
> I'm training a 17M-parameter GPT language model that gets quantized to int8 post-training (per-row scales, zlib compressed). The quantization causes a 0.0325 BPB loss. I want to use quantization-aware training (QAT) to reduce this gap.
>
> Research the following:
> 1. Best practices for QAT in small language models (<50M params), specifically int8 quantization
> 2. Straight-through estimator (STE) variants — which work best for int8?
> 3. When to introduce fake quantization during training (from start vs. last N% of steps)
> 4. Per-channel vs per-tensor fake quantization — does matching the inference scheme matter?
> 5. Any results showing QAT effectiveness specifically for language model perplexity (not just classification accuracy)
> 6. Interaction between QAT and learning rate schedules (should LR be reduced during QAT phase?)
> 7. Recent work on "quantization-friendly" architectures — any architectural changes that make int8 quantization less lossy?
>
> Focus on practical findings that apply to a model trained for ~14K steps with Muon optimizer. I care about rules of thumb and concrete numbers (e.g., "QAT typically recovers X% of quant gap").

## Literature Review

> _Paste your agent's output into `/lab/research_papers/qat.md`_

**Agent chat URL**: <!-- paste URL here -->

---

## Status

- [ ] **Measure actual 600s quant gap** (may differ from the 4h run's 0.0325)
- [ ] Literature review
- [ ] Implementation
- [ ] Experiment: basic QAT (last 30%)
- [ ] Experiment: annealed QAT
- [ ] Experiment: per-row matched QAT
- [ ] Result analysis
