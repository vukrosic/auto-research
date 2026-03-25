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
| explore_6e_d352_v2 | explore | 500 | novita-rtx3090 | 45m00s | 57m54s | 1.29x | +28.7% | 1.6644 | 2026-03-25T12:18 |
| explore_fast_baseline_500 | explore | 500 | novita-rtx3090 | 9m00s | 12m17s | 1.36x | +36.5% | 1.6289 | 2026-03-25T13:19 |
| explore_fast_6e_d320 | explore | 500 | novita-rtx3090 | 9m00s | 12m35s | 1.40x | +39.8% | 1.64 | 2026-03-25T13:31 |
| explore_fast_10L_d384 | explore | 500 | novita-rtx3090 | 9m00s | 12m59s | 1.44x | +44.3% | 1.616 | 2026-03-25T13:44 |
| explore_fast_11L_d352 | explore | 500 | novita-rtx3090 | 9m00s | 14m49s | 1.65x | +64.6% | 1.6271 | 2026-03-25T13:57 |
| explore_6e_d320 | explore | 500 | novita-rtx3090 | 45m00s | 42m46s | 0.95x | -5.0% | 1.6756 | 2026-03-25T14:13 |
| explore_rope_r2_baseline_50 | explore | 50 | novita-rtx3090 | 40s | 3m47s | 5.67x | +467.5% | 2.8899 | 2026-03-25T15:51 |
| explore_rope_r2_base_2000_50 | explore | 50 | novita-rtx3090 | 40s | 2m07s | 3.17x | +217.5% | 2.8911 | 2026-03-25T15:54 |
| explore_rope_r2_base_5000_50 | explore | 50 | novita-rtx3090 | 2m57s | 1m26s | 0.49x | -51.4% | 2.8912 | 2026-03-25T16:52 |
| explore_rope_r2_base_20000_50 | explore | 50 | novita-rtx3090 | 2m07s | 59s | 0.46x | -53.5% | 2.8904 | 2026-03-25T16:54 |
| explore_rope_r2_base_50000_50 | explore | 50 | novita-rtx3090 | 1m47s | 1m02s | 0.58x | -42.1% | 2.8905 | 2026-03-25T16:55 |
