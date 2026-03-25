# Compute Operations

Policy version: 1.0
Effective: 2026-03-24
Last updated: 2026-03-24

## Purpose

Compute is a lab resource. Treat it like scarce capital.

## Operating Rules

- keep a current inventory of available GPUs
- prefer short screens before long validations
- keep enough baseline runs to catch drift
- do not let zombie runs occupy queue slots
- preserve enough logs to reconstruct failures

## Debug Runs

> **HARD RULE: Debug runs must be fast.** When debugging the pipeline, minimize all overhead:
> - Set `VAL_LOSS_EVERY` higher than step count (skip mid-run val evals)
> - Set `VAL_BATCH_SIZE=4096` (tiny val set for any eval that does run)
> - Set `MAX_WALLCLOCK_SECONDS` low
> - Comment out or skip `export_experiment_artifacts.py` — the quant eval (`final_int8_zlib_roundtrip`) takes ~3 minutes alone
> - The goal is seconds, not minutes. If a debug run takes >60 seconds, something is wrong — fix the overhead before continuing.

## Run Classes

### Explore

- cheap (~28 min on 3090, 500 steps)
- screen many ideas quickly

### Validate

- mid-cost (~3.7 hr on 3090, 4000 steps)
- confirm explore winners on latest base

### Full

- expensive (~12.7 hr on 3090, 13780 steps)
- only for ideas that already survived the ladder

## Runbook

At minimum, the operator should be able to answer:

- What is running now?
- Which runs are blocked?
- Which GPUs are idle?
- Which finished runs still need adjudication?
- Which candidates are waiting on rebase validation?

## Timing Expectations

> **HARD RULE: Every dispatched experiment must have an expected duration.** Record `expected_duration_seconds` in `meta.json` before dispatch. Estimate from known timing data (e.g. 500 steps ≈ 28 min on 3090, so 5 steps ≈ 17 seconds). When checking a running experiment:
>
> - **Within 2x expected duration**: normal. Let it run.
> - **2x–5x expected duration**: check the log for progress. If steps are advancing but slow (e.g. first-run compilation overhead), let it finish. If no steps advancing or stuck, kill and mark failed.
> - **>5x expected duration**: kill immediately, mark failed, debug before dispatching more experiments. Something is fundamentally wrong (hanging GPU, infinite loop, data loading stall).
>
> Do not waste compute waiting on a run that should have finished long ago. But also do not kill a run that is just slightly slow — the cost of restarting is higher than waiting.

## Required Artifacts

For each run, preserve:

- launch command
- assigned GPU
- start time
- end time or last heartbeat
- expected duration
- stdout or nohup log
- parsed metric result

## Failure Handling

Experiments end in one of two states: `done` (metrics parsed successfully) or `failed` (anything else).

A run is marked `failed` when:
- Process crashed (OOM, Traceback, RuntimeError)
- Process exited but no metrics found in logs
- GPU unreachable after repeated attempts

When in doubt, mark `failed` and record the reason in `result.json`. A mislabeled success is worse than a delayed adjudication.

## Efficiency Metric

Track a simple lab ops score:

- GPU utilization
- time from run completion to adjudication
- fraction of runs that produce usable results
