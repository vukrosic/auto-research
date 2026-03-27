# Operating Model

This document describes how the lab should function once installed into a real repo.

## Two Operating Modes

Autonomous mode:

- the AI runs the loop end to end
- it pauses only for mission changes, budget changes, or policy conflicts

Supervised mode:

- the AI still does the work
- it stops at explicit approval gates before dispatch, promotion, large code changes, or strategic pivots

## Core Objects

The lab revolves around five durable objects:

1. goals
2. project configs
3. experiment records
4. knowledge files
5. handoff and reporting files

All of them should live inside the target repo.

## Planning Hierarchy

Use this cascade:

1. `MISSION.md`
2. `plans/year.md`
3. `plans/q<N>_<YYYY>.md`
4. `plans/<YYYY>_<MM>.md`
5. `plans/<YYYY>_w<WW>.md`
6. campaign and wave docs
7. experiment briefs and snapshots

High-level intent cascades downward. Findings cascade upward.

## Standard Research Loop

1. Reconcile state from the durable files.
2. Read the active goal and current plans.
3. Review knowledge so failed ideas are not repeated.
4. Check running experiments.
5. Collect completed results.
6. Compare against the correct same-step baseline.
7. Reject, revalidate, or promote.
8. Update knowledge and reports.
9. Design the next batch.
10. Dispatch or stage the next work.
11. Write `state/NOW.md` before ending the session.

## Experiment Discipline

Every experiment should record:

- name
- hypothesis
- project
- parent base
- stage
- step count
- baseline metric
- promotion threshold
- expected duration
- predicted duration
- prediction source
- prediction sample count
- predicted startup / validation / post-train overhead when available
- change summary

Every completed experiment should record:

- primary metric
- runtime
- prediction error
- prediction error ratio
- actual startup / validation / post-train overhead when available
- steps completed
- environment used
- relevant log tail or artifact pointer

## Deadline Fit Rule

Before launching a run, the lab must have a machine-readable estimate for:

- remaining budget seconds
- predicted duration for the next run
- projected remaining sweep time after that run

The next run should not start unless it still fits the remaining budget with explicit margin.
If recent actual runtimes differ materially from predicted runtimes, the lab must recalibrate before queueing more work.
Batch plans should be updated after every completed run, not only at the start of a sweep.

## Baseline Rule

Never evaluate an experiment against a mismatched baseline.

If the lab wants to test at a new step count, it must first produce a baseline for that same step count using the unmodified base.

## Promotion Rule

Promotion should follow this logic:

- winner on latest base: eligible for promotion
- winner on old base: stale, must be revalidated
- valid miss: rejected, but still logged as a useful finding

## Repo Integration Contract

The target repo should expose, directly or through thin helper scripts:

- how to launch a run
- how to determine whether a run is still active
- where logs go
- where result artifacts appear
- how the primary metric is parsed

These are project-level details, not template-level details.

## State Model

Recommended source-of-truth priority:

1. experiment records
2. project config
3. goal and plan files
4. knowledge files
5. state dashboards

Dashboards can be regenerated. Primary records cannot be inferred safely after the fact.

## Session End Rule

Every session should leave the next session a clean handoff:

- what is running
- what finished
- what was learned
- what should happen next
- what is blocked
