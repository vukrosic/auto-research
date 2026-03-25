# Timing Log

Tracks actual vs predicted experiment duration. Use this to improve future estimates.

## Reference (RTX 3090)
- Explore (500 steps): predicted 1680s (28 min)
- Validate (4000 steps): predicted 13320s (3.7 hr)
- Full (13780 steps): predicted 45720s (12.7 hr)
- Per-step: ~644ms/step (measured from debug runs)

## How to Use

After enough runs accumulate (10+), compute:
- Mean actual/predicted ratio per stage
- Std deviation (consistency)
- Update `ops/resources.md` timing reference if ratio drifts >10%

## Log

| Experiment | Stage | Steps | GPU | Predicted | Actual | Ratio | Error% | val_bpb | Dispatched |
|-----------|-------|-------|-----|-----------|--------|-------|--------|---------|------------|
| explore_baseline_v2 | explore | 500 | novita-rtx3090 | 28m00s | 44m59s | 1.61x | +60.7% | 1.6673 | 2026-03-25T11:11 |
| explore_6e_d352 | explore | 500 | novita-rtx3090 | 45m00s | ~15s | — | — | FAILED | 2026-03-25T11:56 |
