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

- **~45 min on 3090, 500 steps** (updated 2026-03-25 from actual data)
- ⚠️ **87% of wall time is quant eval** — training itself is only ~5 min
- screen many ideas quickly

> **Explore efficiency note**: Consider using `SKIP_QUANT_EVAL=1` for explore-stage runs.
> Non-quant BPB is a reliable proxy (delta vs quant BPB observed: <0.001).
> With SKIP_QUANT_EVAL, explore runs take ~8 min instead of ~45 min (5.6x speedup).
> **If you switch**: you must recalibrate the explore baseline with the same flag set,
> and compare all explore results against that new unquantized baseline only.

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

> **HARD RULE: Every dispatched experiment must have an expected duration.** Record `expected_duration_seconds` in `meta.json` before dispatch. Estimate from known timing data (e.g. 500 steps ≈ 45 min on 3090 with quant eval, ~8 min without). When checking a running experiment:
>
> - **Within 2x expected duration**: normal. Let it run.
> - **2x–5x expected duration**: check the log for progress. If steps are advancing but slow (e.g. first-run compilation overhead), let it finish. If no steps advancing or stuck, kill and mark failed.
> - **>5x expected duration**: kill immediately, mark failed, debug before dispatching more experiments. Something is fundamentally wrong (hanging GPU, infinite loop, data loading stall).
>
> Do not waste compute waiting on a run that should have finished long ago. But also do not kill a run that is just slightly slow — the cost of restarting is higher than waiting.

## Deadline Discipline

> **HARD RULE: Deadlines are operationally critical.** Missing a stated deadline by more than **5%** is a critical system failure, not a soft miss.
>
> For every deadline-bound queue or goal:
> - record the deadline explicitly in machine-readable form
> - record `expected_duration_seconds` before dispatch
> - treat required dispatch budget as `expected_duration_seconds * 1.05`
> - **do not dispatch** if the run does not fit inside the remaining deadline window
> - after every completed run, compare actual vs expected immediately
> - if actual is outside the 5% band, recalibrate all pending siblings before dispatching more
>
> The lab must estimate, measure, adjust, and re-estimate continuously. Hope is not a scheduler.

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

## Pre-Dispatch Validation

> **HARD RULE: Validate config before every dispatch.** A mis-configured experiment wastes a GPU slot.
> Run these checks before `dispatch.sh`:
>
> 1. **dim divisibility**: `model_dim % num_heads == 0` — if not, training crashes instantly
>    - Example bug: dim=352, num_heads=6 → 352%6=4 → crash (occurred 2026-03-25 with `explore_6e_d352`)
>    - Also check: `model_dim % num_kv_heads == 0`
> 2. **Size check**: model must be ≤16 MB after int8 zlib compression (run `check_size.py` if available)
> 3. **Experiment name unique**: no duplicate names in `experiments/snapshots/`
> 4. **Stage baseline exists**: the baseline at the same step count must be in `experiments/current_best.json`
>    before any non-calibration experiment is dispatched
>
> A 30-second config check prevents a 45-minute wasted run.

## Automatic Preflight Gate

> **HARD RULE: Dispatch must be gated by machine-checked preflight.**
> Human review is not sufficient for deadline-bound work.
>
> The runtime entrypoint is `scripts/preflight_experiment.py <project> <experiment> --gpu <gpu>`.
> `dispatch.sh` must call it automatically before any remote launch.
>
> Preflight must:
> - write `preflight.json` into the snapshot directory
> - validate required meta fields and project invariants
> - validate goal queue ownership and deadline window
> - compare `expected_duration_seconds` to measured runs
> - update stale expected durations before dispatch when empirical evidence exists
> - block dispatch if the run does not fit the remaining deadline with the required 5% budget
>
> If preflight blocks a run, the queue is the source of truth: keep the experiment pending,
> surface the blocker, fix the cause, and re-run preflight. Do not jump around the queue.

## Micro-Sprint Runtime Rules

> **HARD RULE: In a micro-sprint, runtime budget starts at training start and includes every tail.**
>
> If the human says "5 minutes of research", the 5 minutes begin at the first training dispatch,
> not at the start of agent planning. From that point onward, the following all count:
> - training time
> - validation time
> - quantization/compression time
> - artifact export time
> - result collection tail
>
> Therefore, before dispatching a micro-sprint batch:
> - measure or infer actual runtime from prior runs with the same timing signature
> - cap validation explicitly (for example `VAL_MAX_SEQS`)
> - disable quantization/compression tails if they are not essential (`SKIP_QUANT_EVAL=1`)
> - disable non-essential export/artifact work if collection can rely on logs
> - set per-run wallclock caps low enough that many runs can fit in the window
>
> A plan that ignores validation or export tails is invalid.

## Prediction Calibration

> **RULE: After every completed experiment, check actual vs predicted duration. Update predictions if off.**
>
> After collecting a result, check `state/timing_log.md`:
> - **If ratio is 1.0x–1.2x**: prediction is good, no action needed
> - **If ratio is 1.2x–1.5x**: note it; after 3+ runs with this ratio, update the reference estimate
> - **If ratio is >1.5x**: immediately investigate root cause and update all pending experiment
>   `expected_duration_seconds` values in meta.json before dispatching more
>
> **Known calibration history:**
> | Date | Stage | Flags | Predicted | Actual | Ratio | Root Cause |
> |------|-------|-------|-----------|--------|-------|------------|
> | 2026-03-25 | explore | default | 28m | 45m | 1.61x | Quant eval (~39 min) not included in estimate |
>
> **Current reference (with quant eval)**:
> - Explore 500 steps: **45 min** (2700s)
> - Validate 4000 steps: ~3.7 hr (estimate, not yet measured)
> - Full 13780 steps: ~12.7 hr (estimate, not yet measured)

> **Deadline-bound override**:
> - For any run class tied to a deadline, predictions must be kept within a **±5%** error band.
> - If two consecutive runs miss the band, stop dispatching that class until the estimate or the runtime path is corrected.
>
> **Breakdown of explore wall time**: ~5 min training + ~39 min quant eval + ~1 min startup = 45 min total

## Efficiency Metric

Track a simple lab ops score:

- GPU utilization
- time from run completion to adjudication
- fraction of runs that produce usable results
