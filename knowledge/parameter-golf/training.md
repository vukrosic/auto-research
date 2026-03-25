# Training Knowledge — Parameter Golf

## Activation Functions
- leaky(0.5)² is the best activation found (satisfies H1+H2+H3)
- Gradients must scale with activation magnitude (flat/constant = +0.08-0.11 BPB penalty)
- Don't compress output range (bounded activations hurt)
- Let negative signal through (leaky > relu by ~0.003 BPB)
- Don't square gated activations (swiglu² catastrophic)
- Quantization preserves activation ranking (int8 gap ~0.005 BPB for all)
- 500-step rankings unreliable within squared family — need 2000+ steps to validate

## Timing (single RTX 3090)
- 500 steps: ~28 min
- 4000 steps: ~3.7 hr
- 13780 steps: ~12.7 hr
