# Architecture Search Findings (500-step Explorations)

**Date:** 2026-03-21 (revised with size-budget critique)
**Experiments:** 71 architecture variants at 500 steps each, single seed (1337)
**Baselines:** arch_embed_baseline (1.4793, 12.6 MB), arch_moe_baseline (1.4794, 12.6 MB), arch_conv_baseline (1.4833, 12.6 MB)
**Submission limit:** 16 MB (int8 zlib-compressed)

---

## CRITICAL: Model Size Violations

The top 5 experiments by val_bpb **exceed the 16 MB submission limit** and cannot be submitted as-is:

| Experiment | val_bpb | Model Size | Over Budget |
|-----------|---------|-----------|-------------|
| arch_moe_4e_leaky | 1.4317 | 19.6 MB | **+3.6 MB (22%)** |
| arch_moe_4e | 1.4373 | 19.6 MB | +3.6 MB |
| arch_moe4_qat70 | 1.4377 | 19.6 MB | +3.6 MB |
| arch_moe_4e_mlp4x | 1.4381 | 19.6 MB | +3.6 MB |
| arch_moe_3e | 1.4533 | 16.2 MB | +0.2 MB |

These results prove MoE is powerful, but need follow-up experiments at reduced MODEL_DIM or fewer layers to fit within budget. See "Next Steps" below.

---

## Ranked Results — Legal Submissions Only (<= 16 MB)

| Rank | Experiment | val_bpb | Delta | Size (MB) | Verdict |
|------|-----------|---------|-------|-----------|---------|
| 1 | **arch_embed_bn128_untied** | **1.4483** | **-0.031** | 12.6 | **BEST LEGAL** |
| 2 | arch_embed_bn64_untied | 1.4557 | -0.024 | 12.5 | Strong |
| 3 | arch_moe_2e_11L | 1.4606 | -0.019 | 15.4 | Promising |
| 4 | arch_moe_2e_10L | 1.4659 | -0.014 | 14.1 | Promising |
| 5 | arch_ws_5x2_wide_leaky | 1.4689 | -0.010 | 10.8 | Moderate |
| 6 | arch_moe_2e_leaky | 1.4698 | -0.010 | 12.7 | Moderate |
| 7 | arch_moe2_qat70 | 1.4715 | -0.008 | 12.7 | Moderate |
| 8 | arch_qat_70_leaky | 1.4722 | -0.007 | 12.6 | Moderate |
| 9 | arch_ws_9x2 | 1.4727 | -0.007 | 12.5 | Moderate |
| 10 | arch_qat_50_leaky | 1.4728 | -0.007 | 12.6 | Moderate |
| 11 | arch_moe_2e | 1.4733 | -0.006 | 12.7 | Marginal |
| 12 | arch_moe_2e_mlp3x | 1.4740 | -0.005 | 12.7 | Marginal |
| 13 | arch_qat_90pct | 1.4774 | -0.002 | 12.6 | Marginal |
| 14 | arch_ws_5x2_wide | 1.4789 | -0.000 | 10.8 | Neutral |
| — | **arch_embed_baseline** | **1.4793** | **0.000** | 12.6 | **BASELINE** |
| — | **arch_moe_baseline** | **1.4794** | **0.000** | 12.6 | **BASELINE** |
| — | arch_qat_70pct | 1.4810 | +0.002 | 12.6 | Neutral |
| — | arch_qat_50pct | 1.4812 | +0.002 | 12.6 | Neutral |
| — | arch_qat_from_start | 1.4815 | +0.002 | 12.6 | Neutral |
| — | arch_qat_30pct | 1.4820 | +0.003 | 12.6 | Neutral |
| — | **arch_conv_baseline** | **1.4833** | **+0.004** | 12.6 | **BASELINE** |
| — | arch_baseline_9L | 1.4847 | +0.005 | 12.6 | Neutral |
| — | arch_ws_4x3_wide | 1.4868 | +0.007 | 8.8 | Slight hurt |
| — | arch_ws_6x2 | 1.4886 | +0.009 | 8.5 | Slight hurt |
| — | *(remaining 42 experiments)* | 1.50-1.89 | +0.02 to +0.41 | various | Bad to Terrible |

---

## Analysis by Architecture Category

### 1. Mixture of Experts (MOE) — POWERFUL BUT SIZE-CONSTRAINED

**Best legal:** 1.4606 (2e + 11L, 15.4 MB) | **Best overall:** 1.4317 (4e + leaky, 19.6 MB ILLEGAL)

MOE is the most impactful architecture change, but 4-expert variants blow the 16 MB budget by 22%. Only 2-expert variants fit, and their gains are modest (-0.006 to -0.019 BPB).

| Variant | val_bpb | Delta | Size (MB) | Legal? |
|---------|---------|-------|-----------|--------|
| moe_4e_leaky | 1.4317 | -0.048 | 19.6 | NO |
| moe_4e | 1.4373 | -0.042 | 19.6 | NO |
| moe4_qat70 | 1.4377 | -0.042 | 19.6 | NO |
| moe_4e_mlp4x | 1.4381 | -0.041 | 19.6 | NO |
| moe_3e | 1.4533 | -0.026 | 16.2 | NO (barely) |
| moe_2e_11L | 1.4606 | -0.019 | 15.4 | YES |
| moe_2e_10L | 1.4659 | -0.014 | 14.1 | YES |
| moe_2e_leaky | 1.4698 | -0.010 | 12.7 | YES |
| moe2_qat70 | 1.4715 | -0.008 | 12.7 | YES |
| moe_2e | 1.4733 | -0.006 | 12.7 | YES |
| moe_2e_mlp3x | 1.4740 | -0.005 | 12.7 | YES |

**Key insight:** Expert count matters most (4 > 3 >> 2), but 4 experts at dim=512 is 55% more parameters than baseline. The critical question is: **can 4-expert MoE at reduced dim (~448) beat 2-expert at dim=512?** This is the highest-priority follow-up experiment.

**Confound warning:** Comparing 19.6 MB MoE to 12.6 MB baseline overstates the architecture's benefit. The fair comparison is at equal parameter budget.

---

### 2. Factored Embeddings — BEST LEGAL RESULT (UNTIED ONLY)

**Best:** 1.4483 (bn128 untied, 12.6 MB) | **Worst:** 1.8863 (bn16 w576)

| Variant | val_bpb | Delta | Size (MB) | Notes |
|---------|---------|-------|-----------|-------|
| embed_bn128_untied | 1.4483 | -0.031 | 12.6 | **Best legal result overall** |
| embed_bn64_untied | 1.4557 | -0.024 | 12.5 | Untied + 64 also strong |
| embed_bn256 | 1.5375 | +0.058 | 12.4 | Tied -- hurts |
| embed_bn128_leaky | 1.5459 | +0.067 | 12.2 | Tied + leaky -- still bad |
| embed_bn128 | 1.5555 | +0.076 | 12.2 | Tied -- bad |
| embed_bn64 | 1.6100 | +0.131 | 11.9 | Tied -- very bad |
| embed_bn32 | 1.7143 | +0.235 | 11.6 | Tied -- terrible |
| embed_bn16 | 1.8579 | +0.379 | 11.2 | Tied -- catastrophic |

**Key insight:** Untied vs tied is the critical factor. Untied bn128 beats baseline by 0.031; tied bn128 *hurts* by 0.076. This is the safest bet — it fits in budget with 3.4 MB of headroom and is the #1 priority for validation.

**Combination potential:** Untied bn128 (12.6 MB) + MoE 2e would be ~12.7 MB — still well under 16 MB. If the two wins stack, that could reach -0.04 to -0.05 BPB.

---

### 3. Depthwise Convolution — DEAD END

**Best:** 1.5045 (k3 + 11L, 15.2 MB) | **Worst:** 1.6532 (k5 + bn64)

Every convolution variant hurts. Bigger kernels = worse results. Combinations with other techniques compound damage.

| Variant | val_bpb | Delta | Size (MB) |
|---------|---------|-------|-----------|
| conv_k3_11L | 1.5045 | +0.025 | 15.2 |
| conv_k3 | 1.5134 | +0.034 | 12.5 |
| conv_k5_leaky | 1.5316 | +0.052 | 12.6 |
| conv_k5 | 1.5384 | +0.059 | 12.5 |
| conv_k7 | 1.5606 | +0.081 | 12.5 |
| conv_k9 | 1.5707 | +0.091 | 12.5 |
| conv_k11 | 1.5877 | +0.108 | 12.5 |
| conv_k15 | 1.5911 | +0.112 | 12.5 |
| conv_k5_ws5x2 | 1.5831 | +0.104 | 7.2 |
| conv_k5_bn64 | 1.6532 | +0.174 | 11.9 |

**Verdict:** Abandon. Standard attention is strictly superior at this scale. Possible failure modes (init mismatch, LR mismatch for conv weights) were not investigated, but the consistent monotonic degradation with kernel size suggests a fundamental mismatch, not a tuning issue.

---

### 4. Weight Sharing — PARAMETER-EFFICIENT, USEFUL FOR COMBOS

**Best:** 1.4689 (5x2 wide leaky, 10.8 MB) | **Worst:** 1.5866 (6x2 wide576)

| Variant | val_bpb | Delta | Size (MB) | Notes |
|---------|---------|-------|-----------|-------|
| ws_5x2_wide_leaky | 1.4689 | -0.010 | 10.8 | Only WS variant solidly beating baseline |
| ws_9x2 | 1.4727 | -0.007 | 12.5 | 9 unique blocks = basically full model |
| ws_5x2_wide | 1.4789 | -0.000 | 10.8 | Matches baseline |
| ws_4x3_wide | 1.4868 | +0.007 | 8.8 | |
| ws_6x2 | 1.4886 | +0.009 | 8.5 | |
| ws_5x2 | 1.5102 | +0.031 | 7.2 | Not wide enough |
| ws_3x3 | 1.5465 | +0.067 | 4.5 | Too few unique blocks |

**Verdict:** Not competitive with untied embeddings or MoE on its own. However, WS produces small models (10.8 MB) — could combine with untied embeddings or MoE 2e if parameter budget needs careful allocation. **No WS + untied embedding combinations were tested** — this is a gap.

---

### 5. QAT — NEARLY NEUTRAL ALONE

| Variant | val_bpb | Delta | Size (MB) | Notes |
|---------|---------|-------|-----------|-------|
| qat_70_leaky | 1.4722 | -0.007 | 12.6 | Leaky doing the work, not QAT |
| qat_50_leaky | 1.4728 | -0.007 | 12.6 | Same story |
| qat_90pct | 1.4774 | -0.002 | 12.6 | |
| qat_70pct | 1.4810 | +0.002 | 12.6 | ~neutral |
| qat_50pct | 1.4812 | +0.002 | 12.6 | |
| qat_from_start | 1.4815 | +0.002 | 12.6 | |
| qat_30pct | 1.4820 | +0.003 | 12.6 | |

**Key insight:** QAT alone is within noise (+/-0.003). The leaky ReLU is doing all the work in "qat + leaky" variants. QAT start timing barely matters. However, moe4_qat70 (1.4377) matches plain moe_4e (1.4373) — QAT doesn't hurt MoE, useful for final submission.

---

## Methodology Caveats

1. **Single seed (1337), 500 steps only.** KNOWLEDGE.md notes that 500-step rankings are unreliable within the squared activation family. The -0.048 delta for MoE 4e is likely large enough to survive, but deltas under 0.01 are within noise. No error bars are available.

2. **Unequal parameter counts.** Experiments range from 3.2 MB to 19.6 MB. Comparing models at different sizes conflates architecture quality with parameter budget. The fair benchmark is iso-parameter, which was not done.

3. **No learning curve analysis.** Some architectures may converge faster at 500 steps but plateau earlier. This is especially relevant for MoE, which has more total capacity and may simply learn faster rather than better.

---

## What Works vs What Doesn't

### Pursue to Validation (REVISED — legal models only)
1. **Untied factored embeddings (bn128)** — -0.031 BPB, 12.6 MB, best legal result. Priority #1.
2. **MoE 2e + 11L** — -0.019 BPB, 15.4 MB. Worth validating at 2000 steps with multiple seeds.
3. **MoE 2e + leaky + untied bn128** — untested combination that could stack wins and fit under 16 MB.
4. **MoE 4e at reduced dim (~448)** — new experiment needed to test if 4-expert MoE can fit within 16 MB while retaining its advantage.

### Dead Ends (Do Not Revisit)
1. **Depthwise convolution** — every variant hurts, bigger kernels hurt more
2. **Tied factored embeddings** — catastrophic, especially at small bottlenecks
3. **QAT alone** — nearly zero impact
4. **Conv + anything combos** — compounds the damage

### Gaps in Coverage (Untested Combinations)
1. **MoE 4e at reduced MODEL_DIM** to fit within 16 MB
2. **MoE 2e + untied embeddings** — the two best legal approaches, never combined
3. **MoE 2e + untied embeddings + leaky** — triple stack
4. **Weight sharing + untied embeddings** — WS saves params, could fund untied overhead

---

## Next Steps (Priority Order)

1. **Queue validation (2000 steps, 2 seeds)** of `arch_embed_bn128_untied` — confirm -0.031 holds
2. **Queue budget-fit MoE 4e experiments** — dim=448 and dim=416 with 4 experts to fit under 16 MB
3. **Queue combination experiments** — MoE 2e + untied bn128 + leaky; MoE 2e + untied bn128 + 11L
4. **If MoE 4e fits at reduced dim:** validate at 2000 steps with 2 seeds
5. **Full run (13780 steps)** of best validated combo to see if it beats 1.2244 BPB

---

*71 experiments, 3 GPUs, ~500 steps each. Generated 2026-03-21. Revised 2026-03-21 with size-budget analysis.*
