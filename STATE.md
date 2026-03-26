# autoresearch — current state
**last updated:** 2026-03-26 12:35 UTC

---

## what is running right now

A bash loop is running in the background on this VPS, dispatching experiments to the GPU one at a time.

**process:** PID 747016
```
bash scripts/run_loop.sh 14
```
- started: 2026-03-26 10:47 UTC
- working dir: `/root/research/autoresearch/`
- log: `/tmp/loop_batch1.log`
- results log: `/root/research/autoresearch/reports/loop_results.jsonl`

**what it does:**
1. finds the next `pending` experiment in `experiments/parameter-golf/snapshots/`
2. dispatches to `novita-rtx3090` via `scripts/dispatch.sh`
3. polls every 60s with `scripts/check_experiment.sh` until done
4. collects results with `scripts/collect_result.sh`
5. repeats until 14 experiments done

---

## gpu

- **novita-rtx3090** — see `scripts/gpu_config.sh` for credentials
- ~12-14 min per experiment (500 steps, SKIP_QUANT_EVAL=1, VAL_LOSS_EVERY=500)
- ~861ms/step for deeper models (15L+), 644ms/step for baseline

---

## project

**parameter-golf** — OpenAI 16MB LM challenge, scored by val_bpb (lower = better)

- baseline at 500 steps: **1.6673 BPB** (9L d384 bn128, leaky(0.5)²)
- current best (4k steps): **1.3564 BPB** (MoE4e + bn128 + leaky)
- leaderboard leader: **1.1194 BPB** — gap to close = 0.237 BPB
- config: `projects/parameter-golf.json`
- knowledge base: `knowledge/parameter-golf/`

---

## experiment queue (as of 11:37 UTC)

**running:**
- `explore_bn320_cap15_vr` — triple stack: bn320 + cap15 + value_residual

**pending:**
1. `explore_deeper_narrow_12L_d288_6e` — 12L d288 with 6 experts (old queue)
2. `explore_logit_cap10` — softcap=10
3. `explore_logit_cap12` — softcap=12
4. `explore_logit_cap20` — softcap=20
5. `explore_logit_cap8` — softcap=8 (very tight)
6. `explore_resid_scale_01` — LayerScale (RESID_SCALE_INIT=0.1)

---

## results so far (this session, sorted best→worst)

| experiment | val_bpb | vs baseline |
|-----------|---------|-------------|
| explore_bn320 | 1.6566 | -0.0107 (**) |
| explore_logit_cap15 | 1.6583 | -0.0090 (**) |
| explore_bn320_vr | 1.6590 | -0.0083 (**) |
| explore_attnres_vr | 1.6620 | -0.0053 (*) |
| explore_bn288 | 1.6620 | -0.0053 (*) |
| explore_bn384 | 1.6627 | -0.0046 (*) |
| explore_bn320_11L | 1.6662 | -0.0011 (n.s.) |
| explore_15L_d288 | 1.6663 | -0.0010 (n.s.) |
| explore_attnres_wv | 1.6714 | +0.0041 (n.s.) |
| explore_attnres_cumsum | 1.6741 | +0.0068 (n.s.) |
| explore_8e_d320 | 1.6635 | -0.0038 (*) |
| explore_8e_d288 | 1.6708 | +0.0035 (n.s.) |
| explore_12h_6kv | 1.6821 | +0.0148 (**) |
| explore_4e_d384_12h | 1.6841 | +0.0168 (**) |
| explore_weight_share | 1.6891 | +0.0218 (**) |

**NEW BEST: bn320_cap15 = 1.6538 (-0.0135, -0.81%)** — stacking works! bn320+cap15 compound at 69% efficiency.

**key findings so far:**
- stacking works: bn320+cap15 = 1.6538 (new best)
- cubing activation (act_power=3) = no gain over squaring
- more heads (12h/6kv) hurts: +0.89%
- 15L d288 = n.s. (too narrow for that depth)
- 8e d320 = weak positive (-0.0038, probably noise)

---

## what to do when the loop finishes

1. **read results** — check `reports/loop_results.jsonl` and `snapshots/*/result.json`
2. **analyze** — does bn320+cap15 stack? where is softcap optimum? does LayerScale work?
3. **design round 2** — write next batch to `experiments/parameter-golf/batch2_*.json`, create with `scripts/create_batch.py`
4. **run loop again** — `bash scripts/run_loop.sh <N> > /tmp/loop_batch2.log 2>&1 &`
5. **update this file**

---

## bigger picture

The leaderboard leader uses techniques we haven't implemented yet:
- int6 quantization (fits 11L d512 in 16MB)
- BigramHash(1536) vocab
- XSA (cross-sequence attention)
- EMA/SWA weight averaging
- Test-time training (TTT)

Knob sweeps alone won't close the 0.237 BPB gap. After this sprint, need to implement code-level features.

---

## key files

```
scripts/run_loop.sh          — the dispatch-collect loop
scripts/create_batch.py      — bulk create experiments from JSON
scripts/dispatch.sh          — dispatch one experiment to GPU
scripts/collect_result.sh    — collect one result from GPU
scripts/check_experiment.sh  — poll if experiment is done
experiments/parameter-golf/batch1_stack_and_softcap.json  — batch 1 definition
reports/2026-03-26_24h_search_plan.md   — 24h plan with round structure
reports/2026-03-26_weight_decay_and_architecture.md  — full results history
reports/loop_results.jsonl   — machine-readable results from this loop
```
