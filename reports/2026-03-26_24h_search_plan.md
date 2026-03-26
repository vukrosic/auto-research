# 24-hour search sprint — 2026-03-26
**goal:** find stacking improvements to close the gap from 1.3564 → <1.12 BPB
**gpu:** single RTX 3090
**throughput:** ~12-14 min/experiment (500 steps, SKIP_QUANT_EVAL=1, VAL_LOSS_EVERY=500)
**capacity:** ~90-100 experiments in 24 hours

---

## leaderboard reality check (updated 2026-03-26 11:00 UTC)
- **leader: 1.1194 BPB** (merged, pure neural)
- **our best: 1.3564 BPB** → gap = 0.237 BPB
- leader uses: 11L d512, int6 quant, BigramHash(1536), XSA, TTT, EMA/SWA, partial RoPE
- our quick-search knob sweeps yield ~0.005-0.01 per win → need 20+ to close gap
- **reality: knob sweeps alone won't close the gap. need code-level features.**

## macro strategy (revised)

### track 1: knob sweeps (this sprint, 24h)
- sweep all env-var-tunable knobs to find the best possible config with current code
- goal: find 5-8 stacking improvements → maybe ~0.05-0.10 BPB total at 4k steps
- this is what we can do RIGHT NOW without code changes

### track 2: code-level features (next sprint)
- implement from leaderboard: EMA/SWA, XSA, partial RoPE, int6 quant
- each is a discrete code change that can be tested independently
- this is where the big BPB gains are

### track 3: novel approaches
- BigramHash vocabulary
- TTT (test-time training)
- n-gram cache (legality debated but interesting research)

## known independent improvements (from previous session)
| knob | delta | mechanism |
|------|-------|-----------|
| bn320 | -0.0107 (-0.64%) | embed bottleneck capacity |
| logit_cap15 | -0.0090 (-0.54%) | output distribution sharpness |
| value_residual | -0.0053 (-0.32%) | attention signal preservation |

## x post narrative arc
- "N experiments in 24h, automated, single 3090"
- systematic search → unexpected discoveries → stacking → compound gains
- show the analysis-between-rounds workflow — that's the differentiator
- reversals and surprises are the hook

---

## round 1 (14 experiments, ~3.3 hours)
**thesis:** do winners stack? where is the softcap optimum? new axes?

### batch 1a — stale architecture experiments (6)
| experiment | change | question |
|-----------|--------|----------|
| explore_12h_6kv | 12 heads, 6 KV | does head count matter at d384? |
| explore_15L_d288 | 15L, d288 | very deep narrow — viable? |
| explore_4e_d384_12h | 4 experts, 12h, 6kv | MoE + more heads |
| explore_8e_d288 | 8 experts, d288 | max MoE narrow |
| explore_8e_d320 | 8 experts, d320 | max MoE medium |
| explore_deeper_narrow_12L_d288_6e | 12L, d288, 6e | deep narrow MoE |

### batch 1b — targeted new experiments (8)
| experiment | change | question |
|-----------|--------|----------|
| explore_bn320_cap15 | bn320 + cap15 | do two best stack? |
| explore_logit_cap10 | cap=10 | tighter cap better? |
| explore_logit_cap20 | cap=20 | bracket from above |
| explore_logit_cap8 | cap=8 | very tight cap |
| explore_logit_cap12 | cap=12 | fine bracket 10-15 |
| explore_bn320_cap15_vr | bn320+cap15+vr | triple stack |
| explore_resid_scale_01 | resid_scale=0.1 | LayerScale — new axis |
| explore_act_power_30 | act_power=3.0 | cubing vs squaring |

**expected completion:** ~14:00 UTC

---

## round 2 (designed after round 1 analysis)
**candidate themes based on round 1 outcomes:**
- if softcap sweep shows clear optimum → fine-tune around peak
- if LayerScale works → sweep resid_scale values
- if stacking works → add more independent improvements
- if stacking fails → focus on single strongest changes at 4k steps
- new axes to try: stochastic depth, highway nets, QK gain, gate floor, warmup steps

## round 3+ (adaptive)
- deeper combos of confirmed winners
- architecture + mechanism cross-products
- validate top 2-3 at 4k steps (~46 min each)

---

## decision checkpoints
- **after round 1:** which axes are live? which are dead? does stacking work?
- **after round 2:** what's the strongest single config at 500 steps?
- **after round 3:** validate top configs at 4k steps
- **12h mark:** mid-sprint review — are we on track? pivot needed?
- **20h mark:** final validation runs, prep X post with full results
