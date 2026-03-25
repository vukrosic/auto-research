# Resources — Golf Fast Results Sprint

**Last updated**: 2026-03-25T13:04:13Z

## GPU Allocation

| GPU | Allocation Window | Policy | Notes |
|-----|-------------------|--------|-------|
| novita-rtx3090 | After current running experiment completes until 2026-03-25T15:04:13Z | temporary priority | Do not interrupt the active run; this goal gets next queue priority |

## Budget

| Item | Value | Notes |
|------|-------|-------|
| Wall-clock budget | 2 hours | Hard stop at deadline |
| Max per experiment | 10 minutes | Includes training and eval |
| Failure policy | failures consume the same fixed window | No retries without explicit reason |

## Operating Constraints

- `SKIP_QUANT_EVAL=1`
- single final validation pass only
- no long-tail quant roundtrip runs inside this sprint
