# NOW — Current Work Context

## ★ MISSION: Surpass transformer architecture for small LLMs
**Best: 1.3564 BPB → Target: <1.2244 BPB | Gap: 0.132 | Deadline: Apr 30, 2026**
Full goal: `goals/surpass_transformer_2026/MISSION.md`

> **This file is the handoff note.** If you are a new agent or resuming a session, read this first after AGENTS.md.
> Update it at every session close and whenever the current focus changes significantly.
> Keep it short — this is a snapshot, not a log.

**Last updated**: 2026-03-25T13:15Z
**Active goal**: surpass_transformer_2026
**Active campaign**: c01_close_the_gap

---

## What We're Doing Right Now

**GPU is IDLE. Ready to dispatch next experiment.**

Wave 1 queue has 12 experiments pending. Dispatch now:
```
bash scripts/dispatch.sh explore_6e_d352_v2 novita-rtx3090
```

Then after each finishes:
```
bash scripts/collect_result.sh <name>
bash scripts/dispatch.sh <next_in_queue> novita-rtx3090
```

Queue order: see `state/ACTIVE_RUNS.md`.

---

## Timing Situation (READ BEFORE PLANNING)

**Explore runs take ~45 min, not 28 min.** Root cause: quant eval is 87% of wall time.
- Training: ~5 min (500 steps × 644ms)
- Quant eval: ~39 min
- Total: ~45 min

**Option to consider**: Use `SKIP_QUANT_EVAL=1` for explore stage → cuts to ~8 min (5.6x faster).
If doing this: recalibrate explore baseline with same flag first. Non-quant BPB is a reliable proxy (delta < 0.001).

---

## Current State

→ For live running/queued experiments: **`state/ACTIVE_RUNS.md`**
→ For metric frontier: **`state/FRONTIER.md`** and `experiments/current_best.json`

| Item | Value |
|------|-------|
| Best metric | 1.3564 BPB (pre-autoresearch, 4k steps, post-quant) |
| Explore baseline | 1.6673 BPB at 500 steps (calibrated 2026-03-25) |
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
