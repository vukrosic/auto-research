# Autoresearch — Execution Runbook

For lab policy, governance, promotion rules, and templates, start with [LAB.md](/root/research/autoresearch/LAB.md).

You (Claude Code) are the autonomous researcher. This file tells you the mechanical steps of a research cycle. It does not define policy — all policy decisions defer to the lab handbook.

> **YOU ARE THE DECISION-MAKER.** Scaling decisions (explore → validate → full) are yours, not automated. After collecting results, YOU review each experiment against the same-step-count baseline and decide what to advance. Scripts collect data — you interpret it. Thresholds are guidelines, not gates. Every experiment you scale up is one you don't run at explore. Think about opportunity cost before spending compute.

## Strategic Planning (before the loop)

Before running experiments, ensure the strategic layer is in place:

1. **Active campaign**: Check `campaigns/` for an active campaign. If none, create one per [template](/root/research/autoresearch/lab/templates/CAMPAIGN.md). See [Research Strategy](/root/research/autoresearch/lab/11_RESEARCH_STRATEGY.md).
2. **Week plan**: Check `ops/week_<YYYY>_w<WW>.md` for a current week plan. If stale or missing, create one per [template](/root/research/autoresearch/lab/templates/WEEK_PLAN.md). See [Autonomous Planning](/root/research/autoresearch/lab/12_AUTONOMOUS_PLANNING.md).
3. **Resources**: Check `ops/resources.md` for current GPU inventory and budget.
4. **Pipeline depth**: Ensure 3-5 experiments are in `pending` state before starting. The GPU must never be idle.

Only proceed to the loop once the strategic context is set. The loop executes within the plan — it doesn't replace planning.

## The Loop

When the user says "run a research cycle" (or similar), execute these steps:

### 0. Calibrate Stage Baselines (if needed)

> **HARD RULE: Never evaluate an experiment without a baseline at the same step count.**
> If you are about to run experiments at N steps and there is no baseline at N steps, you MUST train the unmodified base code at N steps first and record the result. This applies to every step count — standard stages (explore/validate/full) AND non-standard counts (e.g. 5 steps for debug runs). An experiment result is meaningless without an apples-to-apples baseline. A result that is "very bad" compared to a mismatched baseline tells you nothing — it could be normal for that step count.

- Check if `current_best.json` has `stage_baselines` for all active stages (explore, validate)
- If running at a non-standard step count: check if a baseline exists for that exact count. If not, train one first.
- If any are missing (e.g., after a promotion): run `scripts/calibrate_baselines.sh <gpu> [stage]`
- For custom step counts: run the base code manually at that step count and record the result in `current_best.json` under `stage_baselines`
- This runs the base code at the stage's step count and records what metric to beat
- **Without calibrated baselines, explore experiments will be compared against the full-run metric and always rejected**

### 1. Reconcile State

- Regenerate `state/*.md` from primary records (see [state/README.md](/root/research/autoresearch/state/README.md))
- If state files disagree with experiment snapshots, snapshot records win

### 2. Orient

- Read `knowledge/<project>/` to understand what's been tried and what works
- Read `experiments/base/KNOWLEDGE.md` if it exists
- Check `experiments/snapshots/` for experiments in any active status
- Check GPU availability: `scripts/gpu_status.sh`

### 3. Check Running Experiments

For each experiment with `status` = `running`:
- SSH to the GPU and check if training is still going
- If done: pull results, parse metrics, write `result.json`, set `status=done`
- If crashed (hard failure): write error to `result.json`, set `status=failed`
- If stalled or producing bad output: kill, set `status=failed`, record failure mode
- If GPU unreachable: do not mark failed — retry next cycle
- See [07_COMPUTE_OPS.md](/root/research/autoresearch/lab/07_COMPUTE_OPS.md)

### 4. Adjudicate Completed Experiments

For each experiment with `status` = `done`:
- Read `result.json` for the metric
- Compare against the baseline and threshold in `meta.json`
- Apply the status vocabulary from [04_EXPERIMENT_GOVERNANCE.md](/root/research/autoresearch/lab/04_EXPERIMENT_GOVERNANCE.md):
  - If the experiment beats its threshold and its `parent_base` matches the current base: set `status=validated_winner`
  - If the experiment beats its threshold but its `parent_base` is stale: set `status=stale_winner`, create a revalidation experiment
  - If the experiment does not beat its threshold: set `status=rejected`
- Update `knowledge/<project>/wins.md` or `knowledge/<project>/failures.md`

### 5. Promote Validated Winners

For each experiment with `status` = `validated_winner`:
- Check all promotion preconditions in [05_PROMOTION_POLICY.md](/root/research/autoresearch/lab/05_PROMOTION_POLICY.md)
- If all preconditions are met:
  - Copy the winner's `code/` to `experiments/base/`
  - Update `experiments/current_best.json` with new metric, experiment name, and timestamp
  - Write the promotion record (see promotion policy for required fields)
  - Set `status=promoted`
  - Log the promotion in `knowledge/<project>/wins.md`
- If any precondition is not met: do not promote. Record which precondition failed.

### 6. Generate Ideas

- Think about what to try next based on knowledge, frontier, open questions, and the gap to target
- For each idea:
  - Create a new experiment snapshot: `scripts/new_experiment.sh <name>`
  - Name must follow [09_NAMING_CONVENTION.md](/root/research/autoresearch/lab/09_NAMING_CONVENTION.md)
  - Make code changes in `experiments/snapshots/<name>/code/`
  - Write `meta.json` with hypothesis, stage, parent_base, baseline metric, and promotion threshold
  - Set `status=pending`

### 7. Dispatch

The **experiment queue** is all snapshots with `status=pending`, ordered by `meta.json.created_at` (oldest first). There is no separate queue file — the snapshots ARE the queue. This is the single source of truth for dispatch order.

When a GPU becomes available, the dispatcher picks the next experiment from the queue:
- `dispatch_pending()` in `autonomous_lab.py` handles this automatically
- Manual dispatch: `scripts/dispatch.sh <experiment_name> <gpu_name>`
- A file lock (`.cycle.lock`) prevents concurrent dispatchers from double-booking

Future: `created_at` ordering will be replaced by a ranking mechanism (e.g. priority score, expected value). The queue model stays the same — only the sort key changes.

### 8. Report

Summarize the session using the [Cycle Report template](/root/research/autoresearch/lab/templates/CYCLE_REPORT.md):
- Experiments checked, adjudicated, dispatched
- Key findings and knowledge updates
- Current frontier and active runs
- Next batch candidates

## Experiment Directory Structure

```
experiments/
  base/                          # clean copy of the repo — current best
  current_best.json              # canonical frontier record
  snapshots/
    explore_moe_width_7ac2/
      code/                      # full repo copy with changes
      meta.json                  # see below
      status                     # see status vocabulary
      result.json                # filled after training completes
```

### meta.json format
```json
{
  "name": "explore_moe_width_7ac2",
  "hypothesis": "8 experts might fit at dim=320 and improve over 4 experts",
  "parent_base": "base::pre_autoresearch_baseline::2026-03-24T00:00:00Z",
  "stage": "explore",
  "steps": 500,
  "priority": 1,
  "created_at": "2026-03-24T12:00:00Z",
  "gpu": null,
  "baseline_metric": 1.3564,
  "promotion_threshold": 0.01,
  "expected_duration_seconds": 1680,
  "changes_summary": "Modified MoE expert count from 4 to 8, reduced dim to 320"
}
```

### result.json format
```json
{
  "val_bpb": 1.3564,
  "val_bpb_quant": 1.3612,
  "steps_completed": 500,
  "gpu": "novita-rtx3090",
  "duration_seconds": 1680,
  "log_tail": "last 20 lines of training log"
}
```

### Status Vocabulary

Defined in [04_EXPERIMENT_GOVERNANCE.md](/root/research/autoresearch/lab/04_EXPERIMENT_GOVERNANCE.md). The canonical values are:

- `pending` — defined, not yet dispatched
- `running` — actively consuming compute
- `done` — run finished, not yet adjudicated
- `failed` — run invalid due to crash or bad output
- `rejected` — valid result, did not pass policy
- `stale_winner` — beat old baseline but base moved; needs revalidation
- `validated_winner` — passed on the latest base, eligible for promotion
- `promoted` — became the new base
- `rollback_invalidated` — was promoted but later found invalid (see [09_ROLLBACK_POLICY.md](/root/research/autoresearch/lab/09_ROLLBACK_POLICY.md))

## Project Config

Project-specific settings live in `projects/<name>.json`:
```json
{
  "name": "parameter-golf",
  "repo_path": "/root/research/parameter-golf",
  "metric": "val_bpb",
  "target": 1.2194,
  "current_best": 1.3564,
  "run_command": "bash infra/run_experiment.sh {name} {steps}",
  "stages": {
    "explore": {"steps": 500, "threshold": 0.01},
    "validate": {"steps": 4000, "threshold": 0.005},
    "full": {"steps": 13780, "threshold": 0.0}
  },
  "gpus": ["novita-rtx3090"]
}
```

## GPU Operations

All GPU operations go through helper scripts in `scripts/`:
- `scripts/gpu_status.sh` — check what's running on each GPU
- `scripts/new_experiment.sh <name>` — create snapshot from base
- `scripts/dispatch.sh <experiment> <gpu>` — rsync + start training
- `scripts/check_experiment.sh <experiment>` — check if training is done
- `scripts/collect_result.sh <experiment>` — pull results back
- `scripts/promote.sh <experiment>` — promote winner to base

## Knowledge Files

```
knowledge/
  parameter-golf/
    architecture.md     # what works at this model scale
    training.md         # LR, schedule, warmup findings
    failures.md         # what didn't work and why
    wins.md             # what worked, with metrics and dates
```

Claude Code reads these at the start of each cycle and writes to them after adjudicating results.

## Tips for Claude Code

- **Be bold with code changes.** Architecture changes, new layers, novel activations — anything goes.
- **Be conservative with adjudication.** Only promote experiments that satisfy all preconditions in promotion policy.
- **Learn from failures.** Every rejected experiment teaches something. Write it down.
- **Batch wisely.** If you have GPUs idle, dispatch experiments. If none idle, just generate ideas.
- **Don't repeat failures.** Always check `knowledge/<project>/failures.md` before proposing.
- **Never promote stale winners.** If base changed, revalidate first.

## Strategic Layer

| Document | Purpose |
|----------|---------|
| [Research Strategy](/root/research/autoresearch/lab/11_RESEARCH_STRATEGY.md) | Campaigns, waves, pivots, convergence detection |
| [Autonomous Planning](/root/research/autoresearch/lab/12_AUTONOMOUS_PLANNING.md) | Week planning, GPU scheduling, pipeline management |
| [ops/resources.md](/root/research/autoresearch/ops/resources.md) | Live GPU and budget inventory |
| `ops/week_<YYYY>_w<WW>.md` | Current week plan with schedule and decision points |
| `campaigns/<name>.md` | Active research campaigns with axes and wave logs |
| [Campaign template](/root/research/autoresearch/lab/templates/CAMPAIGN.md) | How to start a new campaign |
| [Week plan template](/root/research/autoresearch/lab/templates/WEEK_PLAN.md) | How to plan a week |
