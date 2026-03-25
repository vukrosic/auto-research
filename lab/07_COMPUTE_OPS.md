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

## Required Artifacts

For each run, preserve:

- launch command
- assigned GPU
- start time
- end time or last heartbeat
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
