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

### Screen

- cheap
- many variants
- same-stage comparison only

### Explore

- mid-cost
- stronger candidates only

### Validate

- rerun on latest base or longer budget
- promotion-eligible evidence

### Full

- expensive
- used only for ideas that already survived the ladder

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

## Failure Taxonomy

### Hard Failure

- Process crash, non-zero exit, missing output files
- Detection: check exit code, check for `result.json` or expected checkpoint
- Disposition: set `status=failed`, record error in `result.json`, free GPU slot

### Soft Failure

- NaN loss, degenerate metrics (loss stuck at initialization value), training stalled (no log output for extended period)
- Detection: parse last N lines of log for NaN, check metric progression, check log freshness
- Disposition: kill the run, set `status=failed`, record the failure mode. Do not wait indefinitely for recovery.

### Infrastructure Failure

- GPU unreachable via SSH, disk full, SSH credential expiry, network timeout
- Detection: SSH connection failure, `df` check, auth error in SSH output
- Disposition: do not mark the experiment as failed immediately. Mark it `status=blocked` in state. Retry SSH on next session. If still unreachable after two sessions, escalate to human.

### Observability Failure

- Run may be healthy but logs or artifacts are missing or unreadable
- Detection: process is running but log file is empty, truncated, or not parseable
- Disposition: do not adjudicate. Flag for manual inspection. Do not guess the result.

### Default Rule

When in doubt about failure class, prefer containment and clear labeling over guesswork. A mislabeled success is worse than a delayed adjudication.

## Efficiency Metric

Track a simple lab ops score:

- GPU utilization
- time from run completion to adjudication
- fraction of runs that produce usable results
