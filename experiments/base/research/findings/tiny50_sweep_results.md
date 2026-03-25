# Tiny Model Sweep — 50 Ablation Experiments

**Date:** 2026-03-23 | **Total wall time:** 80.2 min | **Baseline val_bpb:** 1.9093

## Method

All 50 experiments ran on a tiny 3M-parameter model (6 layers, 256d, 4H/2KV, MLP mult=2) for 300 steps with a fixed batch of 65536 tokens. Validation used a 4M-token batch (single eval pass). Experiments were killed immediately after val_bpb was logged to skip int8 quantization and save time (~75s/exp target, 150s hard timeout). Each experiment changes exactly one hyperparameter or mechanism from baseline, except the 5 combination runs at the end. The goal was cheap rapid screening — signals at 300 steps on a 3M model do not scale perfectly to the competition setup (16MB, 13780 steps), but rank-order correlations are useful for prioritization.

## Full Results

| Rank | Experiment | val_bpb | Δ vs baseline | What changed |
|------|-----------|---------|--------------|--------------|
| 1 | **t90_vr_silu** | **1.8064** | **−0.103** | value_residual attn + SiLU MLP |
| 2 | t01_act_relu | 1.8330 | −0.076 | MLP activation: relu |
| 3 | t76_ebn64 | 1.8347 | −0.075 | Embedding bottleneck dim=64 |
| 4 | t10_act_mish | 1.8422 | −0.067 | MLP activation: mish |
| 5 | t70_conv3 | 1.8435 | −0.066 | Conv kernel=3 in attention |
| 6 | t42_ar_vr | 1.8439 | −0.065 | Attention residual: value_residual |
| 7 | t19_act_xsilu | 1.8703 | −0.039 | MLP activation: x_silu |
| 8 | t43_ar_vr_gated | 1.8723 | −0.037 | Attention residual: value_residual_gated |
| 9 | t41_ar_cumsum | 1.8824 | −0.027 | Attention residual: cumsum |
| 10 | t33_gqa_full | 1.8833 | −0.026 | Full MHA (4KV heads = 4Q heads) |
| 11 | t28_8L | 1.8922 | −0.017 | 8 layers (deeper) |
| 12 | t79_qkgain05 | 1.8926 | −0.017 | QK gain init = 0.5 |
| 13 | t62_clip10 | 1.8942 | −0.015 | Grad clip norm = 1.0 |
| 14 | t12_act_leaky05gf | 1.8944 | −0.015 | leaky0.5 + gradient floor |
| 15 | t68_skip05 | 1.8954 | −0.014 | Skip weight init = 0.5 |
| 16 | t57_mom90 | 1.8956 | −0.014 | Muon momentum = 0.90 |
| 17 | t83_wd100 | 1.9080 | −0.001 | Warmdown = 100 steps |
| — | **t00_baseline** | **1.9093** | **0** | 6L 256d 4H/2KV MLP×2 |
| 19 | t38_moe4 | 1.9101 | +0.001 | MoE: 4 experts |
| 20 | t88_wide_shallow | 1.9105 | +0.001 | 4 layers, 320d |
| 21 | t81_wu5 | 1.9114 | +0.002 | Warmup = 5 steps |
| 22 | t23_mlp4 | 1.9161 | +0.007 | MLP mult = 4 |
| 23 | t65_sd01 | 1.9190 | +0.010 | Stochastic depth rate = 0.1 |
| 24 | t67_highway | 1.9209 | +0.012 | Highway network |
| 25 | t47_rope1000 | 1.9234 | +0.014 | RoPE base = 1000 |
| 26 | t22_mlp3 | 1.9263 | +0.017 | MLP mult = 3 |
| 27 | t18_act_bipolar | 1.9270 | +0.018 | bipolar_relu2 activation |
| 28 | t49_rope50k | 1.9270 | +0.018 | RoPE base = 50000 |
| 29 | t21_mlp1 | 1.9322 | +0.023 | MLP mult = 1 |
| 30 | t51_cap100 | 1.9400 | +0.031 | Logit softcap = 100 |
| 31 | t52_mlr08 | 1.9406 | +0.031 | Matrix LR = 0.08 |
| 32 | t25_4L | 1.9422 | +0.033 | 4 layers (shallower) |
| 33 | t59_bs3 | 1.9474 | +0.038 | Muon backend steps = 3 |
| 34 | t91_deep_silu | 1.9539 | +0.045 | 8 layers + SiLU (no value_residual) |
| 35 | t29_d192 | 1.9577 | +0.048 | Model dim = 192 |
| 36 | t50_cap10 | 1.9605 | +0.051 | Logit softcap = 10 |
| 37 | t37_moe2 | 1.9614 | +0.052 | MoE: 2 experts |
| 38 | t55_embed_hi | 1.9617 | +0.052 | Tied embed LR = 0.1 |
| 39 | t35_mha8h | 1.9661 | +0.057 | 8 heads, full MHA |
| 40 | t72_share3c2 | 1.9692 | +0.060 | Weight sharing: 3 blocks × 2 cycles |
| 41 | t97_deep_moe | 2.0052 | +0.096 | 8 layers + 4 experts |
| 42 | t87_deep_narrow | 2.0153 | +0.106 | 8 layers, 224d |
| — | t03_act_relu18 | FAIL | — | relu18 (unimplemented, NaN) |
| — | t05_act_silu | FAIL | — | silu standalone (NaN) |
| — | t06_act_gelu | FAIL | — | gelu (unimplemented, NaN) |
| — | t07_act_swiglu | FAIL | — | swiglu (unimplemented, NaN) |
| — | t08_act_geglu | FAIL | — | geglu (unimplemented, NaN) |
| — | t27_7L | FAIL | — | 7 layers (NaN at init) |
| — | t32_d320 | FAIL | — | dim=320 standalone (NaN) |
| — | t39_moe8 | FAIL | — | 8 experts (NaN) |

Key takeaways from this 300-step, 3M ablation sweep (lower val_bpb is better):
- Best overall: t90_vr_silu val_bpb 1.8064 (delta -0.103). SiLU alone (t05) NaNs, but with ATTNRES_MODE=value_residual it becomes stable and wins.
- Reliable wins: t01_act_relu (-0.076) and t76_ebn64 (-0.075).
- Attention residuals: value_residual (-0.065) and value_residual_gated (-0.037) help; cumsum is smaller (-0.027). Conv kernel=3 helps (-0.066).
- Poor/unstable in this sweep: higher-expert MoE variants, deeper+narrower, RoPE extremes, logit softcap (10/100), weight sharing, highway networks.

Code-level meaning (very short, so you know what “is actually happening”):
- ATTNRES_MODE=value_residual*: captures attention V at an earlier layer and injects it into later layers' attention value stream; gated uses a learned scalar multiplier; mid shifts the capture point.
- ATTNRES_MODE=cumsum: accumulates each layer's attention output and adds it into the next layer's attention input x.
- CONV_KERNEL>0: depthwise 1D conv residual inside each block, applied to x before attention.
- EMBED_BOTTLENECK>0: factorized token embedding (vocab -> bottleneck -> model_dim), with output/head behavior depending on TIE_EMBEDDINGS.
- MLP_ACT: activation choice inside MLP; x_silu is h * silu(h); bipolar_relu2 is relu(h)^2 - 0.25*relu(-h)^2.
- NUM_EXPERTS>0: SoftMoE with soft routing; as experts increase, per-expert width shrinks (can contribute to NaNs at tiny scale).

Next steps:
- Validate-light (2000 steps) for t90_vr_silu, t01_act_relu, t76_ebn64.
- Then test a combo: ReLU + value_residual.
# Tiny Model Sweep — 50 Ablation Experiments

**Date:** 2026-03-23 | **Total wall time:** 80.2 min | **Baseline val_bpb:** 1.9093

## Method

All 50 experiments ran on a tiny 3M-parameter model (6 layers, 256d, 4H/2KV, MLP mult=2) for 300 steps with a fixed batch of 65536 tokens. Validation used a 4M-token batch (single eval pass). Experiments were killed immediately after val_bpb was logged to skip int8 quantization and save time (~75s/exp target, 150s hard timeout). Each experiment changes exactly one hyperparameter or mechanism from baseline, except the 5 combination runs at the end. The goal was cheap rapid screening — signals at 300 steps on a 3M model do not scale perfectly to the competition setup (16MB, 13780 steps), but rank-order correlations are useful for prioritization.

## Full Results

| Rank | Experiment | val_bpb | Δ vs baseline | What changed |
|------|-----------|---------|--------------|--------------|
| 1 | **t90_vr_silu** | **1.8064** | **−0.103** | value_residual attn + SiLU MLP |
| 2 | t01_act_relu | 1.8330 | −0.076 | MLP activation: relu |
| 3 | t76_ebn64 | 1.8347 | −0.075 | Embedding bottleneck dim=64 |
| 4 | t10_act_mish | 1.8422 | −0.067 | MLP activation: mish |
| 5 | t70_conv3 | 1.8435 | −0.066 | Conv kernel=3 in attention |
| 6 | t42_ar_vr | 1.8439 | −0.065 | Attention residual: value_residual |
| 7 | t19_act_xsilu | 1.8703 | −0.039 | MLP activation: x_silu |
| 8 | t43_ar_vr_gated | 1.8723 | −0.037 | Attention residual: value_residual_gated |
| 9 | t41_ar_cumsum | 1.8824 | −0.027 | Attention residual: cumsum |
| 10 | t33_gqa_full | 1.8833 | −0.026 | Full MHA (4KV heads = 4Q heads) |
| 11 | t28_8L | 1.8922 | −0.017 | 8 layers (deeper) |
| 12 | t79_qkgain05 | 1.8926 | −0.017 | QK gain init = 0.5 |
| 13 | t62_clip10 | 1.8942 | −0.015 | Grad clip norm = 1.0 |
| 14 | t12_act_leaky05gf | 1.8944 | −0.015 | leaky0.5 + gradient floor |
| 15 | t68_skip05 | 1.8954 | −0.014 | Skip weight init = 0.5 |
| 16 | t57_mom90 | 1.8956 | −0.014 | Muon momentum = 0.90 |
| 17 | t83_wd100 | 1.9080 | −0.001 | Warmdown = 100 steps |
| — | **t00_baseline** | **1.9093** | **0** | 6L 256d 4H/2KV MLP×2 |
| 19 | t38_moe4 | 1.9101 | +0.001 | MoE: 4 experts |
| 20 | t88_wide_shallow | 1.9105 | +0.001 | 4 layers, 320d |
| 21 | t81_wu5 | 1.9114 | +0.002 | Warmup = 5 steps |
| 22 | t23_mlp4 | 1.9161 | +0.007 | MLP mult = 4 |
| 23 | t65_sd01 | 1.9190 | +0.010 | Stochastic depth rate = 0.1 |
| 24 | t67_highway | 1.9209 | +0.012 | Highway network |
| 25 | t47_rope1000 | 1.9234 | +0.014 | RoPE base = 1000 |
| 26 | t22_mlp3 | 1.9263 | +0.017 | MLP mult = 3 |
| 27 | t18_act_bipolar | 1.9270 | +0.018 | bipolar_relu2 activation |
| 28 | t49_rope50k | 1.9270 | +0.018 | RoPE base = 50000 |
| 29 | t21_mlp1 | 1.9322 | +0.023 | MLP mult = 1 |
| 30 | t51_cap100 | 1.9400 | +0.031 | Logit softcap = 100 |
| 31 | t52_mlr08 | 1.9406 | +0.031 | Matrix LR = 0.08 |
| 32 | t25_4L | 1.9422 | +0.033 | 4 layers (shallower) |
| 33 | t59_bs3 | 1.9474 | +0.038 | Muon backend steps = 3 |
| 34 | t91_deep_silu | 1.9539 | +0.045 | 8 layers + SiLU (no value_residual) |
| 35 | t29_d192 | 1.9577 | +0.048 | Model dim = 192 |
| 36 | t50_cap10 | 1.9605 | +0.051 | Logit softcap = 10 |
| 37 | t37_moe2 | 1.9614 | +0.052 | MoE: 2 experts |
| 38 | t55_embed_hi | 1.9617 | +0.052 | Tied embed LR = 0.1 |
| 39 | t35_mha8h | 1.9661 | +0.057 | 8 heads, full MHA |
| 40 | t72_share3c2 | 1.9692 | +0.060 | Weight sharing: 3 blocks × 2 cycles |
| 41 | t97_deep_moe | 2.0052 | +0.096 | 8 layers + 4 experts |
| 42 | t87_deep_narrow | 2.0153 | +0.106 | 8 layers, 224d |
| — | t03_act_relu18 | FAIL | — | relu18 (unimplemented, NaN) |
| — | t05_act_silu | FAIL | — | silu standalone (NaN) |
| — | t06_act_gelu | FAIL | — | gelu (unimplemented, NaN) |
| — | t07_act_swiglu | FAIL | — | swiglu (unimplemented, NaN) |
| — | t08_act_geglu | FAIL | — | geglu (unimplemented, NaN) |
| — | t27_7L | FAIL | — | 7 layers (NaN at init) |
| — | t32_d320 | FAIL | — | dim=320 standalone (NaN) |
| — | t39_moe8 | FAIL | — | 8 experts (NaN) |

## Key Findings

**Clear winners for follow-up:**

1. **Value residual + SiLU (t90)** is the standout at −0.103. Notably, SiLU alone (t05) fails with NaN, but combined with `ATTNRES_MODE=value_residual` it trains stably and dominates — the value residual path likely provides gradient normalization that stabilizes the gating dynamic. This combination warrants a full-scale validate run.

2. **ReLU activation (t01, −0.076)** is a clean, reliable win with no instability. The model benefits from sparsity at small scale. Simple to combine with other improvements.

3. **Embedding bottleneck at dim=64 (t76, −0.075)** is a parameter-efficiency trick that surprisingly helps even on a 3M model. Compressing embeddings forces more abstract representations.

4. **Value residual attention (t42, −0.065)** works on its own too, and the gated variant (t43) is close behind. All three attention-residual modes beat baseline.

5. **Conv kernel=3 in attention (t70, −0.066)** is competitive with the top activation changes — adds local inductive bias cheaply.

**What doesn't work:** More experts (MoE), deeper+narrower, RoPE extremes, logit softcap, weight sharing, and highway networks all hurt at this scale. Stochastic depth and altered warmup/warmdown schedules are neutral to slightly negative.

**Next steps:** Prioritize validate-light runs (2000 steps, full model) for t90_vr_silu, t01_act_relu, and t76_ebn64. Then test `relu + value_residual` as a combination.

## Implementation Notes (non-obvious knobs)

This sweep's “architecture knobs” are not just high-level concepts; they wire directly into `train_gpt.py`'s `GPT -> Block -> CausalSelfAttention/MLP` forward paths.

### `ATTNRES_MODE`: what actually gets added, where

`ATTNRES_MODE` controls extra residual-like signals inside `GPT.forward()`:

1. `cumsum`
   - Maintains a running tensor `attn_cumsum` of each layer's raw `attn_out`.
   - On layer `i`, `GPT` passes `attn_residual=attn_cumsum` into `Block.forward(...)`.
   - `Block.forward(...)` applies it as `x = x + attn_residual` **before** recomputing attention (so the accumulated attention output becomes part of the next layer's attention input stream).
   - After the block runs, `attn_cumsum` updates with `attn_cumsum += attn_out`.

2. `value_residual`
   - Captures `v0` on the *first encoder layer* (layer index `0`) by calling `Block(..., return_v=True)`.
   - For later layers (`i > 0`), passes that captured `v0` back in as `v_residual`.
   - `CausalSelfAttention.forward(...)` then modifies the internal attention values as:
     - `v = v + v_residual`
     - This happens right before `scaled_dot_product_attention(...)` consumes `(q, k, v)`.

3. `value_residual_gated`
   - Same as `value_residual`, but the injected values are globally gated by a learned scalar:
     - `v = v + sigmoid(v_gate_param) * v_residual`
   - Note: this is one scalar per attention module (not token-wise).

4. `value_residual_mid`
   - Like `value_residual`, but the capture layer is shifted:
     - it captures `v0` at `vr_capture_layer = num_encoder_layers // 2`
     - injection begins only after that capture point for encoder layers, and it continues through decoder layers.

5. `weighted` / `weighted_vector`
   - These do *not* use `attn_residual`/`v_residual`.
   - They create `layer_weights` and replace `x` each layer with a learned softmax-weighted combination of previous `layer_outputs`:
     - `weighted`: scalar weights per previous layer
     - `weighted_vector`: per-dimension weights per previous layer

Practical takeaway: `value_residual*` changes the attention *value stream* (`v`) directly, while `cumsum` changes the attention *input stream* (`x`) by adding accumulated `attn_out`.

### `CONV_KERNEL`: “conv in attention” actually means “extra local mixing inside each block”

When `CONV_KERNEL > 0`, `Block.__init__()` creates a **depthwise** 1D convolution:
- `nn.Conv1d(dim, dim, conv_kernel, padding=conv_kernel-1, groups=dim, bias=False)`

In `Block.forward(...)`, it is applied after the block's input mix:
- `x = x + conv(x.transpose(1,2))[:, :, :x.size(1)].transpose(1,2)`

So `conv_kernel=3` is a cheap local sequence-mixing residual that runs *before* the attention computation (and before the optional `attn_residual` addition).

### `EMBED_BOTTLENECK`: factorized embeddings (vocab -> bottleneck -> model_dim)

When `EMBED_BOTTLENECK > 0`, `GPT.__init__()` switches to:
- `tok_emb = nn.Embedding(vocab_size, embed_bottleneck)`
- `embed_proj = CastedLinear(embed_bottleneck, model_dim, bias=False)`

In `GPT.forward()` it computes:
- `x = tok_emb(input_ids)`
- `x = embed_proj(x)`

The output-side behavior depends on `TIE_EMBEDDINGS`:
- If `TIE_EMBEDDINGS=True` *and* `embed_proj` exists, the tied head uses `embed_proj.weight` in a factored form.
- If `TIE_EMBEDDINGS=False` (as in `t76_ebn64`), the model uses a separate `lm_head` for logits.

Practical takeaway: the bottleneck is a hard low-rank constraint on the token representation pathway, not just “smaller embeddings”.

### `MLP_ACT`: custom activations are implemented inside `MLP.forward()`

For the key activations seen in this sweep:

- `relu`
  - `MLP.forward`: `proj(relu(fc(x)))`
- `silu`
  - `MLP.forward`: `proj(silu(fc(x)))`
- `x_silu` (your best non-`value_residual` activation winner besides ReLU)
  - `h = fc(x)`
  - returns `proj(h * silu(h))`
  - i.e. it multiplies the raw pre-activation `h` by `silu(h)` (a “x*silu(x)” nonlinearity)
- `bipolar_relu2`
  - `relu(h)^2 - 0.25 * relu(-h)^2` then projected back to model_dim
  - output can be negative because the negative side is subtracted

Also important: the MLP output projection (`self.proj`) is `_zero_init=True`, so at initialization the MLP branch starts near-zero and “turns on” as training progresses.

### SoftMoE: why “MoE with more experts” can become unstable at tiny scale

When `NUM_EXPERTS > 0`, the model uses `SoftMoE` (no hard routing):
- `experts`: a list of `MLP(...)` instances
- `router`: `CastedLinear(dim, num_experts, bias=False)`
- forward:
  - `w = router(x).softmax(dim=-1)` producing token-wise mixture weights
  - output is a weighted sum of expert outputs: `sum_i w[..., i] * expert_i(x)`

The implementation also reduces per-expert width as experts increase:
- `expert_mult = max(1, mlp_mult // num_experts)`

So `NUM_EXPERTS=8` changes both the mixture complexity (router head) and the effective expert capacity (narrower experts), which is consistent with the NaN failures you observed.

### `LOGIT_SOFTCAP`: bounded logit nonlinearity

Before computing cross-entropy, logits are squashed as:
- `logits = logit_softcap * tanh(logits_proj / logit_softcap)`

So `LOGIT_SOFTCAP=10` heavily limits logit magnitude early, which can slow or destabilize learning compared to larger values.

### GQA vs full MHA (`NUM_KV_HEADS`)

Attention uses PyTorch's `scaled_dot_product_attention` with:
- `enable_gqa = (num_kv_heads != num_heads)`

Meaning:
- if `NUM_KV_HEADS == NUM_HEADS`: full MHA path
- if `NUM_KV_HEADS < NUM_HEADS`: grouped-query attention (shared K/V across more Q heads)

### `ROPE_BASE`: rotary embedding frequency scaling

Rotary is implemented via:
- `inv_freq = 1 / (base ** (arange(0, dim, 2) / dim))`
- and then applied to `q` and `k` using cached cos/sin tables.

So “RoPE extremes” are literally changing the geometric frequency spread of `q/k` rotations.

### `MUON_BACKEND_STEPS`: how many Newton-Schulz iterations to orthogonalize updates

The Muon optimizer orthogonalizes matrix-shaped gradients using Newton–Schulz iterations (`zeropower_via_newtonschulz5`):
- each parameter update calls `zeropower_via_newtonschulz5(g, steps=backend_steps)`

So `MUON_BACKEND_STEPS=3` is a cheaper, less-accurate approximation than the default (5), which explains why it's not necessarily monotonic: you're trading compute for gradient-shape fidelity.

### Weight sharing (`NUM_UNIQUE_BLOCKS`, `NUM_CYCLES`): changes the network topology (not just parameter count)

In `GPT.__init__()`:
- if `num_unique_blocks > 0`, it enables `self.weight_sharing=True`
- parameters are reused by cycling through the same `self.blocks` for `num_cycles`

In `GPT.forward()` that becomes:
- `if self.weight_sharing:`
  - run blocks in a simple loop: `for _cycle in range(num_cycles): for block in self.blocks: x = block(x, x0)`
  - no encoder/decoder split, and no U-net-like skip connections are used

If weight sharing is disabled, the model uses an encoder/decoder split and applies explicit learned skip contributions in the decoder:
- `x = x + self.skip_weights[i] * skips.pop()`

So `t72_share3c2` isn't just “sharing weights”; it also removes the skip-connection pathway.

### Highway network (`HIGHWAY_NET`): replaces fixed per-dim residual scales with token-wise gates

In `Block.__init__()`, when `highway_net=True`, it creates:
- `highway_gate_attn = CastedLinear(dim, 1, bias=True)`
- `highway_gate_mlp = CastedLinear(dim, 1, bias=True)`

In `Block.forward()`:
- the attention residual contribution becomes token-wise gated:
  - `gate_a = sigmoid(highway_gate_attn(x))` with shape `(B, S, 1)`
  - `x = x + drop_path(gate_a * attn_out)`
- similarly for the MLP residual:
  - `gate_m = sigmoid(highway_gate_mlp(x))`
  - `x = x + drop_path(gate_m * mlp_out)`

When `HIGHWAY_NET=False`, the block uses fixed learned per-dimension scales instead:
- `x = x + drop_path(attn_scale * attn_out)`
- `x = x + drop_path(mlp_scale * mlp_out)`
