# experiment report — 2026-03-26
**project:** parameter-golf (OpenAI 16MB LM challenge)
**gpu:** novita RTX 3090 (single)
**total experiments:** 9
**steps each:** 500
**baseline:** 1.6673 BPB (9L d384 bn128, 15.20M params)

---

## full results table (sorted best → worst)

| experiment | config | params | ms/step | train_s | actual_total | predicted | val_bpb | vs baseline | signal |
|------------|--------|--------|---------|---------|--------------|-----------|---------|-------------|--------|
| **bn256** | bn=256 | 15.38M | 642ms | 321s | 7.0min | 7min | **1.6632** | **-0.0041 (-0.25%)** | `**` |
| bn192 | bn=192 | 15.29M | 642ms | 321s | 7.0min | 7min | 1.6649 | -0.0024 (-0.14%) | `*` |
| 11L_d352_bn256 | 11L+d352+bn256 | 15.74M | 770ms | 385s | 8.0min | 7min | 1.6654 | -0.0019 (-0.11%) | `*` |
| 11L_d352_clean | 11L+d352 | 15.56M | 769ms | 385s | 8.0min | 7min | 1.6662 | -0.0011 (-0.07%) | `*` |
| 12L_d336 | 12L+d336 | 15.45M | 818ms | 409s | 8.5min | 7min | 1.6681 | +0.0008 (+0.05%) | `n.s.` |
| 12L_d320 | 12L+d320 | 14.05M | 749ms | 375s | 7.8min | 7min | 1.6712 | +0.0039 (+0.23%) | `n.s.` |
| wd_muon01 | muon_wd=0.01 | 15.20M | 642ms | 321s | 7.0min | 7min | 1.6728 | +0.0055 (+0.33%) | `*` |
| wd_muon04 | muon_wd=0.04 | 15.20M | 645ms | 323s | 7.0min | 7min | 1.6844 | +0.0171 (+1.02%) | `**` |
| **wd_both** | muon_wd=0.04+adam_wd=0.01 | 15.20M | 642ms | 321s | 7.0min | 7min | **2.9883** | **+1.3210 (+79%) ← catastrophic** | `***` |

---

## timing: predicted vs actual

| session | experiments | predicted | actual | verdict |
|---------|-------------|-----------|--------|---------|
| weight decay | 3 | 21min | ~21min | ✓ on target |
| embed bottleneck | 2 | 14min | ~14min | ✓ on target |
| architecture | 4 | 28min | ~34min | ✗ over — bigger models 770-820ms/step not 645ms |

**root cause of timing overruns:** larger model configs (11L, 12L) run at 770-820ms/step vs baseline 645ms/step. predicted time was based on baseline step time. fix: measure step time per config before estimating.

---

## key findings

### what works
- **embed bottleneck scaling:** 128→256 gives -0.0041 BPB. monotonic improvement. 128 was a capacity bottleneck on the `1024→128→384` projection.
- **11L d352:** -0.0011 BPB vs baseline (15.56M params, under 16MB). confirmed clean.

### what doesn't work
- **weight decay (all forms):** hurts. muon_wd=0.01 costs +0.0055; muon_wd=0.04 costs +0.0171. not useful at this scale/steps.
- **12L at d320-d336:** worse than 11L d352. going narrower loses more than adding a layer gains. d320=14.05M params (too thin), d336=15.45M (borderline).
- **combining bn256 + 11L:** doesn't stack cleanly — 11L+bn256=1.6654 is *worse* than bn256 alone=1.6632 at 500 steps. may stack better at 4k steps.

### biggest surprise
**adam weight decay on embeddings = catastrophic.** train loss plateau at ~5.0 from step 50 onward. embed_lr=0.6 combined with wd=0.01 fights the factored embedding space. never touches <5.0 BPB vs baseline reaching ~2.75. completely blocked learning.

### size constraint note
10L d384 (16.83M params) was previously marked "validated_winner" but is **over the 16MB competition limit**. invalid. all results above are from configs under 16MB.

---

## what's next

survivors to scale to 4k steps:
1. **bn256** — primary candidate, clean win at explore
2. **11L_d352** — confirmed, needs 4k validation
3. **11L_d352_bn256** — might stack better at longer training

eliminated: weight decay (all), 12L at d320/d336, 10L d384 (size violation)

---

## notes for next sprint

- use `VAL_MAX_SEQS=512` to cap val time from ~90s → ~5s per run → fit 5-6 experiments in 15min
- larger models (11L+) take ~770-820ms/step vs 645ms baseline — account for this in time budgets
- fast-sprint 11L_d352 result of 1.627 BPB is suspicious vs clean run 1.6662 — investigate snapshot code diff

---

## batch 2 — embed bottleneck continuation + novel architectures (2026-03-26, continuing)

**new baseline understanding:** total wall time per experiment = ~37min on RTX 3090 (not 7min). training is 5.4min but VAL_LOSS_EVERY=50 triggers 10× validation passes, each ~3min. fix: set VAL_LOSS_EVERY=500 for remaining experiments (1 val pass only → ~12min total).

### batch 2 results table

| experiment | config | params | ms/step | train_s | wall_total | val_bpb | vs baseline | signal |
|------------|--------|--------|---------|---------|------------|---------|-------------|--------|
| **bn320** | bn=320 | ~15.47M | 644ms | 322s | 37.3min | **1.6566** | **-0.0107 (-0.64%)** | `***` |
| bn384 | bn=384 | ~15.55M | 643ms | 322s | 11.4min | 1.6627 | -0.0046 (-0.28%) | `*` |
| attnres_vr | value_residual | ~15.20M | 642ms | 321s | 11.4min | 1.6620 | -0.0053 (-0.32%) | `*` |
| weight_share | 5 blocks×2 cycles | ~10.5M | 670ms | 335s | 12.1min | 1.6891 | +0.0218 (+1.3%) | `**` |

### embed bottleneck monotonic trend (all at 500 steps)

| bottleneck | val_bpb | delta vs baseline |
|-----------|---------|------------------|
| 128 (baseline) | 1.6673 | — |
| 192 | 1.6649 | -0.0024 |
| 256 | 1.6632 | -0.0041 |
| **320** | **1.6566** | **-0.0107** |
| 384 | 1.6627 | -0.0046 |

**trend reverses at 384!** 320→384 is worse (-0.0046 vs -0.0107 at 320). peak bottleneck is ~320. likely: 1024→384→384 is wasteful — the projection becomes near-identity and adds params without compression benefit. bn320 is the winner.

### timing fix for batch 2

- **problem:** VAL_LOSS_EVERY=50 → 10 val passes × ~3min each = 30min overhead → 37min total per run
- **fix:** added VAL_LOSS_EVERY=500 to remaining experiments → 1 val pass → ~12min total
- experiments bn384, attnres_vr, weight_share: confirmed ~11-12min with fix (was 37min)

### batch 2 findings
- **bn320 wins** at 1.6566 (-0.0107). strongest single improvement found so far.
- **attnres_vr** (value_residual) +0.0053 improvement. independent, stackable candidate.
- **bn384 reversal**: 1024→384→384 is wasteful — near-identity projection, worse than 320. bottleneck peak is ~320.
- **weight_share**: 5 unique blocks × 2 cycles = 10 effective layers hurts at 500 steps (+0.0218). shared weights need more training steps to specialize. may revisit at 4k+ steps.

### batch 3 — stacking + fine-tuning (dispatched)

| experiment | config | params | ms/step | train_s | wall_total | val_bpb | vs baseline | signal |
|------------|--------|--------|---------|---------|------------|---------|-------------|--------|
| bn320_vr | bn=320+value_residual | ~15.47M | 644ms | 322s | 11.4min | 1.6590 | -0.0083 (-0.50%) | `**` |
| bn288 | bn=288 | ~15.43M | 643ms | 321s | 11.4min | 1.6620 | -0.0053 (-0.32%) | `*` |
| attnres_wv | weighted_vector | ~15.22M | 722ms | 361s | 13.0min | 1.6714 | +0.0041 (+0.25%) | `n.s.` |

### batch 3 findings
- **stacking fails at 500 steps**: bn320+value_residual (1.6590) is worse than bn320 alone (1.6566). the two improvements interfere during early training.
- **bn288 confirms peak at 320**: 288→320 jump is -0.0054, the sharpest improvement in the whole series. 320 is the bottleneck optimum for this architecture.
- **attnres weighted_vector**: +0.0041 worse and 12% slower per step. added complexity doesn't pay off.
- **attnres value_residual remains the best attnres variant**: -0.0053 clean.

### batch 4 — deeper combos + novel params

| experiment | config | params | ms/step | train_s | wall_total | val_bpb | vs baseline | signal |
|------------|--------|--------|---------|---------|------------|---------|-------------|--------|
| bn320_11L | bn=320+11L+d352 | ~15.82M | 772ms | 386s | 13.6min | 1.6662 | -0.0011 (-0.07%) | `n.s.` |
| attnres_cumsum | cumsum | ~15.20M | 650ms | 325s | 11.6min | 1.6741 | +0.0068 (+0.41%) | `n.s.` |
| logit_cap15 | softcap=15.0 | ~15.20M | 640ms | 320s | 11.4min | 1.6583 | -0.0090 (-0.54%) | `**` |

---

## 24-hour sprint — 2026-03-26 (continuing from 10:47 UTC)

**new baseline understanding:** leaderboard leader is at 1.1194 BPB (not 1.2244). gap = 0.237 BPB. leaders use int6 quant, BigramHash(1536), XSA, TTT, EMA/SWA — code-level changes, not just hyperparameters.

### round 1 — architecture sweep + stacking (14 experiments, 10:47–~14:00 UTC)

**thesis:** do bn320+cap15 stack? where is softcap optimum? do architecture changes compound?

| experiment | config | ms/step | wall_total | val_bpb | vs baseline | signal |
|-----------|--------|---------|------------|---------|-------------|--------|
| **bn320_cap15** | **bn=320+softcap=15** | 644ms | ~12min | **1.6538** | **-0.0135 (-0.81%)** | `***` |
| act_power_30 | act_power=3.0 | 644ms | ~12min | 1.6662 | -0.0011 (-0.07%) | `n.s.` |
| 8e_d320 | 8 experts d320 | ~720ms | ~14min | 1.6635 | -0.0038 (-0.23%) | `*` |
| 8e_d288 | 8 experts d288 | ~720ms | ~14min | 1.6708 | +0.0035 (+0.21%) | `n.s.` |
| 15L_d288 | 15 layers d288 | 861ms | ~16min | 1.6663 | -0.0010 (-0.06%) | `n.s.` |
| 12h_6kv | 12 heads 6kv | 644ms | ~12min | 1.6821 | +0.0148 (+0.89%) | `**` |
| 4e_d384_12h | 4e+12h+6kv | 644ms | ~12min | 1.6841 | +0.0168 (+1.01%) | `**` |
| bn320_cap15_vr | bn=320+cap15+vr | 644ms | ~12min | RUNNING | — | — |
| deeper_narrow | 12L+d288+6e | — | — | pending | — | — |
| logit_cap8/10/12/20 | softcap sweep | — | — | pending | — | — |
| resid_scale_01 | LayerScale | — | — | pending | — | — |

### round 1 findings so far

- **bn320+cap15 stacks! new best: 1.6538.** not fully additive (got -0.0135 vs -0.0197 expected) but 69% of the theoretical maximum. stacking works better than earlier combos.
- **cubing activation (act_power=3) = no gain.** squaring (2.0) is optimal. cubic adds no benefit.
- **more heads hurts** (-12h_6kv +0.89%). 4e+12h is even worse (+1.01%). head count is tuned correctly at 6h/3kv.
- **15L d288 = n.s.** depth doesn't compensate for narrowing to d288.
- **8e d320 = weak positive** (-0.0038). narrower dim but more experts. not worth the speed cost.

### what's next after round 1
- softcap sweep results will show if 15 is the peak or if 10/12 is better
- if triple stack (bn320+cap15+vr) works → design quad stack
- LayerScale may give independent improvement → new axis to combine
- round 2: design experiments around confirmed winners
