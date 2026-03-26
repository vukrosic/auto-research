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

| explore_rope_r2_baseline_50 | explore | 50 | novita-rtx3090 | 40s | 35s | 0.88x | -12.5% | 2.8899 | 2026-03-25T15:51 |

| explore_rope_r2_base_2000_50 | explore | 50 | novita-rtx3090 | 40s | 35s | 0.88x | -12.5% | 2.8911 | 2026-03-25T15:54 |

| explore_rope_r2_base_5000_50 | explore | 50 | novita-rtx3090 | 2m57s | 36s | 0.20x | -79.7% | 2.8912 | 2026-03-25T16:52 |

| explore_rope_r2_base_20000_50 | explore | 50 | novita-rtx3090 | 2m07s | 35s | 0.28x | -72.4% | 2.8904 | 2026-03-25T16:54 |

| explore_rope_r2_base_50000_50 | explore | 50 | novita-rtx3090 | 1m47s | 35s | 0.33x | -67.3% | 2.8905 | 2026-03-25T16:55 |

| explore_timing_smoke_50_20260325_r2 | explore | 50 | novita-rtx3090 | 35s | 38s | 1.09x | +8.6% | 2.8899 | 2026-03-25T18:32 |

| explore_bn320 | explore | 500 | novita-rtx3090 | 7m00s | 37m20s | 5.33x | +433.3% | 1.6566 | 2026-03-26T07:07 |

| explore_bn384 | explore | 500 | novita-rtx3090 | 12m47s | 11m22s | 0.89x | -11.1% | 1.6627 | 2026-03-26T07:48 |

| explore_attnres_vr | explore | 500 | novita-rtx3090 | 12m00s | 11m24s | 0.95x | -5.0% | 1.662 | 2026-03-26T08:03 |

| explore_weight_share | explore | 500 | novita-rtx3090 | 12m00s | 12m06s | 1.01x | +0.8% | 1.6891 | 2026-03-26T08:18 |

| explore_bn320_vr | explore | 500 | novita-rtx3090 | 12m00s | 11m24s | 0.95x | -5.0% | 1.659 | 2026-03-26T08:35 |

| explore_bn288 | explore | 500 | novita-rtx3090 | 12m00s | 11m22s | 0.95x | -5.3% | 1.662 | 2026-03-26T08:51 |

| explore_attnres_wv | explore | 500 | novita-rtx3090 | 12m00s | 12m58s | 1.08x | +8.1% | 1.6714 | 2026-03-26T09:07 |

| explore_bn320_11L | explore | 500 | novita-rtx3090 | 12m12s | 13m35s | 1.11x | +11.3% | 1.6662 | 2026-03-26T09:23 |

| explore_attnres_cumsum | explore | 500 | novita-rtx3090 | 12m00s | 11m33s | 0.96x | -3.8% | 1.6741 | 2026-03-26T09:40 |

| explore_logit_cap15 | explore | 500 | novita-rtx3090 | 12m00s | 11m20s | 0.94x | -5.6% | 1.6583 | 2026-03-26T09:56 |

| explore_12h_6kv | explore | 500 | novita-rtx3090 | 12m00s | 11m26s | 0.95x | -4.7% | 1.6821 | 2026-03-26T10:47 |

| explore_15L_d288 | explore | 500 | novita-rtx3090 | 12m00s | 14m52s | 1.24x | +23.9% | 1.6663 | 2026-03-26T11:00 |

| explore_4e_d384_12h | explore | 500 | novita-rtx3090 | 12m00s | 11m24s | 0.95x | -5.0% | 1.6841 | 2026-03-26T11:16 |

| explore_8e_d288 | explore | 500 | novita-rtx3090 | 12m00s | 12m45s | 1.06x | +6.2% | 1.6708 | 2026-03-26T11:29 |

| explore_8e_d320 | explore | 500 | novita-rtx3090 | 12m00s | 13m52s | 1.16x | +15.6% | 1.6635 | 2026-03-26T11:43 |

| explore_act_power_30 | explore | 500 | novita-rtx3090 | 12m00s | 11m19s | 0.94x | -5.7% | 1.6662 | 2026-03-26T11:58 |

| explore_bn320_cap15 | explore | 500 | novita-rtx3090 | 12m00s | 11m21s | 0.95x | -5.4% | 1.6538 | 2026-03-26T12:11 |

| explore_bn320_cap15_vr | explore | 500 | novita-rtx3090 | 11m23s | 11m22s | 1.00x | -0.1% | 1.6513 | 2026-03-26T12:24 |

| explore_deeper_narrow_12L_d288_6e | explore | 500 | novita-rtx3090 | 12m00s | 14m24s | 1.20x | +20.0% | 1.6656 | 2026-03-26T12:37 |

| explore_logit_cap10 | explore | 500 | novita-rtx3090 | 11m22s | 11m20s | 1.00x | -0.3% | 1.6593 | 2026-03-26T12:53 |

| explore_logit_cap12 | explore | 500 | novita-rtx3090 | 11m22s | 11m20s | 1.00x | -0.3% | 1.6586 | 2026-03-26T13:06 |

| explore_logit_cap20 | explore | 500 | novita-rtx3090 | 11m22s | 11m20s | 1.00x | -0.3% | 1.6616 | 2026-03-26T13:19 |

| explore_logit_cap8 | explore | 500 | novita-rtx3090 | 11m21s | 11m20s | 1.00x | -0.1% | 1.6604 | 2026-03-26T13:31 |

| explore_resid_scale_01 | explore | 500 | novita-rtx3090 | 11m20s | 11m20s | 1.00x | +0.0% | 1.6708 | 2026-03-26T13:44 |

| explore_attnres_vr_gated | explore | 500 | novita-rtx3090 | 11m22s | 11m24s | 1.00x | +0.3% | 1.6599 | 2026-03-26T13:58 |
