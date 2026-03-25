# NOW — Current Work Context

## ★ ACTIVE GOALS
1. `surpass_transformer_2026` — best `1.3564 BPB`, target `<1.2244 BPB`, deadline `2026-04-30`
2. `golf_fast_results_20260325` — fast golf sprint, start `2026-03-25T13:04:13Z`, deadline/report `2026-03-25T15:04:13Z`

> **This file is the handoff note.** If you are a new agent or resuming a session, read this first after AGENTS.md.
> Update it at every session close and whenever the current focus changes significantly.
> Keep it short — this is a snapshot, not a log.

**Last updated**: 2026-03-25T13:20:17Z
**Primary active goal right now**: golf_fast_results_20260325
**Long-horizon goal still active**: surpass_transformer_2026
**Active campaigns**: `c01_close_the_gap`, `c01_fast_signal_under_10min`

---

## What We're Doing Right Now

**`explore_fast_baseline_500` is RUNNING on `novita-rtx3090`.**

Current loop:
```
bash scripts/check_experiment.sh parameter-golf explore_fast_baseline_500
```

Automation:
```
scripts/run_goal_window.sh golf_fast_results_20260325 60
```

Goal runner state:
- PID file: `goals/golf_fast_results_20260325/runner.pid`
- Log: `logs/golf_fast_results_20260325.runner.log`
- Report due at: `goals/golf_fast_results_20260325/reports/2026-03-25T15-04-13Z_report.md`

Queue policy:
- The sprint queue in `goals/golf_fast_results_20260325/queue.json` is currently ahead of the legacy parameter-golf queue.
- `explore_6e_d320` was briefly auto-dispatched by a verification cycle and was immediately killed and returned to `pending`.

---

## Timing Situation (READ BEFORE PLANNING)

**Explore runs take ~45 min, not 28 min.** Root cause: quant eval is 87% of wall time.
- Training: ~5 min (500 steps × 644ms)
- Quant eval: ~39 min
- Total: ~45 min

**Fast lane is now active**: `SKIP_QUANT_EVAL=1` is implemented in `parameter-golf/train_gpt.py`.
Current sprint experiments also force `VAL_LOSS_EVERY=500` and `MAX_WALLCLOCK_SECONDS=600`.

---

## Current State

→ For live running/queued experiments: **`state/ACTIVE_RUNS.md`**
→ For metric frontier: **`state/FRONTIER.md`** and `experiments/parameter-golf/current_best.json`

| Item | Value |
|------|-------|
| Best metric | 1.3564 BPB (pre-autoresearch, 4k steps, post-quant) |
| Explore baseline | 1.6673 BPB at 500 steps (calibrated 2026-03-25) |
| Fast sprint queue | `explore_fast_baseline_500` → `explore_fast_6e_d320` → `explore_fast_10L_d384` → `explore_fast_11L_d352` |
| Budget used this month | ~$4 of $40 |

---

## Known Pitfalls / Don't Repeat

- `mlp_mult` changes are a no-op when `num_experts=4` — integer division kills the effect
- `dim % num_heads` must be 0 — **4 of our initial experiments had this bug** (caught before running 3 of them)
  - explore_6e_d352 crashed. explore_6e_d320, explore_11L_d352, explore_12L_d320 were fixed in-place.
  - All pending experiments now validated: `dim % num_heads == 0` ✓
- Size check every experiment: must stay under 16 MB (int8 zlib-compressed)
- Old explore baseline (1.7362) is wrong — do not compare against it
- Old explore timing (28 min) is wrong — actual is 45 min. All pending experiments updated to 2700s.
