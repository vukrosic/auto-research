# Autonomous Planning

Policy version: 1.0
Effective: 2026-03-25

## Purpose

Rules for Claude Code to autonomously plan and execute multi-day research without human intervention. The goal is **zero GPU idle time** — every hour the GPU is not training is wasted.

## Planning Cadence

### Weekly Plan

At the start of each week (or when resources change):

1. Assess available resources: GPUs, hours, budget remaining
2. Review active campaign: progress, velocity, remaining axes
3. Compute exact capacity: how many runs of each type fit in the week
4. Design wave schedule: which waves run when, with decision points between them
5. Write the plan to `ops/week_<YYYY>_w<WW>.md`

### Daily Cycle

Each day the agent should:

1. **Check running experiments** — collect results from completed runs
2. **Adjudicate** — review results, update knowledge
3. **Dispatch next** — send next pending experiment to idle GPU
4. **Plan ahead** — ensure there are always 3+ pending experiments ready to dispatch

If operating under a hard deadline:
5. **Measure against the clock** — recompute remaining time, remaining queue budget, and report whether the plan is on track within a 5% error band

> **HARD RULE: The GPU queue must never be empty while there are unexplored ideas.**
> Before the current experiment finishes, the next experiment must be designed, snapshotted, and ready to dispatch. If you find the GPU idle with no pending experiments, this is a planning failure — design and dispatch immediately.

### Experiment Pipeline Management

Maintain a **rolling pipeline** of experiments in different stages:

```
[designing] → [pending] → [running] → [done] → [adjudicating]
     ↑                                              |
     └──────────── knowledge feeds back ────────────┘
```

**Pipeline depth targets**:
- Always have 3-5 experiments in `pending` state
- Never have more than 1 experiment in `running` state per GPU
- Adjudicate within 1 hour of experiment completion
- Design replacements within 2 hours of adjudication

### Batch Design

When designing a batch of experiments:

1. **Spread across axes** — don't put all eggs in one basket. A wave of 10 should cover 2-3 axes.
2. **Include controls** — at least 1 baseline rerun per wave to catch environmental drift.
3. **Vary magnitude** — for each axis, test small and large perturbations (e.g., dim+16 AND dim+64).
4. **Minimize correlation** — each experiment should test one change. Combos come after singles win.
5. **Front-load cheap** — explore before validate before full. Information per GPU-hour is highest at explore.

## GPU Scheduling

### Single GPU Strategy

With 1 GPU, experiments run serially. Maximize throughput:

- Run explores back-to-back during broad search phases
- Batch validates together (longer runs = fewer context switches)
- Schedule full runs overnight or on weekends (12+ hours, less monitoring needed)
- Use inter-experiment gaps (rsync, setup) for adjudication and planning

### Transition Points

**Explore → Validate transition**: When a wave of explores is complete, don't immediately validate all winners. Design the next explore wave first, interleave validates between explore waves so the GPU never waits for planning.

**Validate → Full transition**: Full runs are expensive. Only run when:
- The experiment has been validated at 4000 steps
- The improvement is large enough that even with noise, it's likely real (>0.01 BPB)
- There are no higher-value explores waiting

### Overnight Runs

> Runs dispatched before sleep should be the longest, most valuable experiments.
> Explores during active monitoring, validates/full runs during downtime.

## Resource Tracking

### ops/resources.md

Maintained as the live inventory:

```markdown
## GPU Fleet
| GPU | Type | Status | Current Experiment | Available Until |
|-----|------|--------|--------------------|-----------------|

## Compute Budget
| Item | Value |
|------|-------|
| Total budget | $X |
| Spent | $Y |
| Remaining | $Z |
| Burn rate | $W/day |
| Runway | N days |

## Calendar
| Date | Constraint |
|------|-----------|
```

Update after every dispatch and collection.

## Week Plan Structure

Weekly plans live in `ops/week_<YYYY>_w<WW>.md` and contain:

1. **Resources**: GPU inventory, budget, calendar constraints
2. **Capacity calculations**: Exact run counts per stage with math shown
3. **Wave schedule**: Which waves, which days, which axes
4. **Decision points**: When to review and pivot
5. **Success criteria**: What "a good week" looks like

The week plan is a **living document** — update it as results come in and plans change. Append updates at the bottom, don't delete the original plan (for audit trail).

## Failure Modes to Avoid

1. **GPU sitting idle** — always have pending experiments. This is the #1 sin.
2. **Validating too early** — don't promote every explore winner. Batch explores, then pick the best.
3. **Explore paralysis** — don't run 200 explores without validating anything. After 2-3 explore waves, validate the top candidates.
4. **Sunk cost** — don't keep exploring an axis because you already spent time on it. If it's not working, pivot.
5. **Planning in a vacuum** — always read knowledge files before designing experiments. Don't re-run failed approaches.
6. **Perfect plans** — a good plan executed now beats a perfect plan next week. Dispatch something.
7. **Deadline blindness** — dispatching work that cannot finish inside the remaining window is a planning failure. Use exact times, expected durations, and a 5% tolerance budget.

## Deadline-Bound Planning

> **HARD RULE: Deadline-bound plans must be exact enough to manage, not approximate enough to excuse misses.**
>
> For a deadline-bound goal:
> - compute remaining wall-clock exactly
> - if the runtime budget starts at first dispatch, do not charge planning time against it
> - once the first dispatch happens, treat the runtime window as live and binding
> - sum expected durations for the remaining queue
> - include validation, quantization, compression, export, and collection tails in every estimate
> - include a 5% tolerance on each run
> - do not dispatch the next run unless it fits
> - after every completed run, compare actual vs expected and update all remaining estimates
> - if estimates are wrong, fix either the runtime path or the plan immediately
