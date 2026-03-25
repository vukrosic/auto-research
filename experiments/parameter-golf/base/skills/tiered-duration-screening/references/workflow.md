# Tiered Duration Screening

## Defaults

- Stage ladder: `1s to 2s to 3s`
- Promotion counts: `15 -> top 7 -> top 3`
- Baselines: one baseline per stage duration
- Primary comparison metric: `loss`
- Optional secondary metric: `val_bpb`

## How To Specify Duration

Use explicit stage config instead of hard-coding a single wallclock:

```text
stage_1: duration=1s, runs=15, keep=7
stage_2: duration=2s, runs=7, keep=3
stage_3: duration=3s, runs=3, keep=3
```

If the user asks for a different ladder, keep the same structure and replace the duration values.

## Stage Rules

- Compare only against the same-stage baseline.
- Do not mix durations inside a table.
- Keep the architecture change column short and explicit.
- If the stage is duration-limited, set `ITERATIONS` high enough that `MAX_WALLCLOCK_SECONDS` is the limiting factor.

## Report Template

### Stage 1

| Run | Duration | Architecture change | Loss | Baseline loss | Delta loss | Decision |
|---|---:|---|---:|---:|---:|---|
| baseline | 1s | baseline |  |  | 0.000 | baseline |
| candidate-1 | 1s |  |  |  |  |  |

### Stage 2

| Run | Duration | Architecture change | Loss | Baseline loss | Delta loss | Decision |
|---|---:|---|---:|---:|---:|---|
| baseline | 2s | baseline |  |  | 0.000 | baseline |
| promoted-1 | 2s |  |  |  |  |  |

### Stage 3

| Run | Duration | Architecture change | Loss | Baseline loss | Delta loss | Decision |
|---|---:|---|---:|---:|---:|---|
| baseline | 3s | baseline |  |  | 0.000 | baseline |
| finalist-1 | 3s |  |  |  |  |  |

## Conclusion Style

End with a short readout:

- whether the best 1s ideas stayed strong at 2s and 3s
- whether the 3s baseline changed the ranking
- whether the ladder is stable enough to justify a longer validation stage
