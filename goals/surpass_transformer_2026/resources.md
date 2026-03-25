# Resources — Surpass Transformer 2026

**Last updated**: 2026-03-25

## GPU Allocation

| GPU | Type | VRAM | Allocated To This Goal | Cost/hr | Status |
|-----|------|------|----------------------|---------|--------|
| novita-rtx3090 | RTX 3090 | 24 GB | 100% | $0.50 | active |

## Budget

| Item | Value | Notes |
|------|-------|-------|
| Monthly budget | $40 | Human-set ceiling |
| Spent this month (March) | ~$4 | Prior manual research + pipeline testing |
| Remaining this month | ~$36 | |
| Monthly GPU-hours at budget | 80 hr | $40 / $0.50 |
| Monthly GPU-hours at full utilization | 720 hr | 30 days * 24 hr (theoretical max) |
| **Budget-limited hours/month** | **80 hr** | Budget is binding, not calendar |

## Timing Reference (RTX 3090)

| Stage | Steps | Wall Time | GPU-hours | Cost | Runs/month at budget |
|-------|-------|-----------|-----------|------|---------------------|
| Explore | 500 | 28 min | 0.467 hr | $0.23 | ~171 |
| Validate | 4000 | 3.7 hr | 3.7 hr | $1.85 | ~21 |
| Full | 13780 | 12.7 hr | 12.7 hr | $6.35 | ~6 |

## Effective Capacity Per Month

After overhead (10% failure rate, 5% setup/rsync, calibration runs):

| Allocation | Explore | Validate | Full | Buffer |
|------------|---------|----------|------|--------|
| Share | 45% | 30% | 15% | 10% |
| Hours | 36 hr | 24 hr | 12 hr | 8 hr |
| Runs | ~77 | ~6 | ~1 | — |
| Cost | $18 | $12 | $6 | $4 |

**Monthly throughput estimate**: ~77 explores + ~6 validates + ~1 full = ~84 experiments/month

## Quarterly Budget

| Quarter | Budget | GPU-hours | Expected Experiments |
|---------|--------|-----------|---------------------|
| Q1 2026 (remaining: 6 days) | ~$20 | ~40 hr | ~50 |
| Q2 2026 (Apr-Jun) | $120 | ~240 hr | ~250 |
| Q3 2026 (Jul-Sep) | $120 | ~240 hr | ~250 |
| Q4 2026 (Oct-Dec) | $120 | ~240 hr | ~250 |
| **Annual total** | **~$380** | **~760 hr** | **~800 experiments** |

> Note: These assume stable GPU pricing and single-GPU operation.
> Additional GPUs would multiply throughput linearly.
> Budget may be adjusted by human at any time.
