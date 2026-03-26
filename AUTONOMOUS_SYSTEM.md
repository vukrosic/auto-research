# Autonomous System Overview

This repository implements an autonomous ML research system. The human defines mission-level goals and policy. The agent executes research inside those constraints by creating experiments, dispatching them to remote GPUs, collecting results, updating knowledge, and deciding what to run next.

The system is intentionally file-centric. Plans, policy, run state, results, and knowledge all live in markdown or JSON inside the repo. There is no separate database or orchestration service that holds hidden state.

## What Makes It Autonomous

- The human sets direction through `goals/<goal>/MISSION.md` and the lab policy documents in `lab/`.
- The agent owns planning below the mission layer: campaigns, quarter/month/week plans, queues, experiment design, dispatch, evaluation, and reporting.
- The agent can make arbitrary code changes inside experiment snapshots, not just config edits.
- Research decisions are made from recorded metrics, baselines, and policy, not from ad hoc human approval at each step.

## System Layers

There are two connected layers:

1. Lab operating system
   - Defines authority, governance, lifecycle, promotion rules, rollback policy, naming, cadence, and planning hierarchy.
   - Main entry point: [LAB.md](/root/research/autoresearch/LAB.md)

2. Project execution system
   - Runs experiments for a specific project using a universal project contract.
   - Main entry points: [RESEARCH.md](/root/research/autoresearch/RESEARCH.md) and [DESIGN.md](/root/research/autoresearch/DESIGN.md)

The rule is simple: lab policy decides what is legal; execution scripts decide how to do it.

## Core Files and Directories

- `AGENTS.md`
  - Onboarding for a new agent session.

- `LAB.md`
  - Index into the permanent lab handbook.

- `RESEARCH.md`
  - Mechanical runbook for a research cycle.

- `DESIGN.md`
  - Execution-engine architecture decisions.

- `goals/`
  - Human missions plus AI-managed plans, queues, resources, and reports.

- `projects/`
  - Per-project run contract.

- `experiments/`
  - Base code, experiment snapshots, frontier records.

- `knowledge/`
  - Persistent findings by topic.

- `state/`
  - Derived dashboards and handoff views. Useful, but not authoritative.

- `scripts/`
  - The control plane for preflight, dispatch, polling, result collection, reporting, and cycles.

## Primary Data Model

The system revolves around a small number of explicit records.

### 1. Goal

A goal is a long-horizon objective under `goals/<slug>/`.

- `MISSION.md`
  - Human-authored objective. AI should not rewrite it.

- `goal.json`
  - Optional machine-readable timing and scheduling metadata.

- `queue.json`
  - Optional goal-scoped dispatch queue.

- `plans/`, `campaigns/`, `progress.md`, `resources.md`, `reports/`
  - AI-managed execution and reporting artifacts.

### 2. Project Config

Each project has a config file in `projects/<name>.json` that defines:

- Primary metric and optimization direction.
- Run command.
- Process pattern.
- Log and result locations.
- Metric parsing rules.
- Stage budgets such as `explore`, `validate`, `full`.
- GPU mappings and remote working directories.

This is the universal adapter contract that lets the same lab run different projects.

### 3. Experiment Snapshot

Each experiment lives at:

`experiments/<project>/snapshots/<experiment>/`

Key files:

- `code/`
  - Full copy of the repo under test with experiment changes applied.

- `meta.json`
  - Hypothesis, parent base, stage, steps, baseline, threshold, expected duration, env overrides, goal ownership.

- `status`
  - Current lifecycle state.

- `result.json`
  - Parsed outcome after the run completes.

Snapshots are the authoritative experiment records.

### 4. Frontier Record

Each project keeps its current promoted baseline in:

- `experiments/<project>/current_best.json`
- `experiments/<project>/base/`
- `experiments/<project>/base_id.txt`

This is the reference point for comparison and promotion.

## Status Model

Canonical statuses include:

- `pending`
- `running`
- `done`
- `failed`
- `rejected`
- `stale_winner`
- `validated_winner`
- `promoted`
- `rollback_invalidated`

These statuses are not just labels. They define the legal next actions in the research lifecycle.

## Execution Loop

At a high level, the autonomous loop is:

1. Reconcile state from snapshot records.
2. Read goals, plans, knowledge, and project context.
3. Check any currently running experiments.
4. Collect completed results.
5. Adjudicate outcomes against the correct same-step baseline.
6. Promote winners when policy allows.
7. Generate or materialize new experiments.
8. Dispatch the next eligible work to available GPUs.
9. Update reports, knowledge, and handoff state.

The important design choice is that the agent is the decision-maker. Scripts gather facts and perform mechanical steps, but the agent decides what to try, what to scale, and what to reject.

## Dispatch and Runtime Flow

The main execution path is:

1. `new_experiment.sh`
   - Creates a new snapshot from the current base.

2. `preflight_experiment.py`
   - Validates metadata, invariants, timing assumptions, goal-window fit, and GPU readiness.

3. `dispatch.sh`
   - Rsyncs the snapshot to the remote machine, starts the run under a wrapper, records `running`, assigned GPU, PID, and dispatch time.

4. `check_experiment.sh`
   - Polls the remote GPU to determine whether the process is still alive, completed, or failed.

5. `collect_result.sh`
   - Pulls logs and artifacts back, parses metrics, writes `result.json`, and updates status.

6. `autonomous_lab.py`
   - Orchestrates multi-project cycles and queue handling.

7. `run_loop.sh`
   - Simple serial batch runner for repeated explore experiments.

8. `run_goal_window.sh`
   - Deadline-driven goal runner that materializes queue entries, runs cycles until report time, then generates a goal report.

The GPU side stays intentionally thin. Most intelligence remains in this repo, not on the remote machine.

## Source of Truth Rule

Primary records win:

- Experiment truth lives in `experiments/<project>/snapshots/*/`
- Frontier truth lives in `experiments/<project>/current_best.json`
- Derived views in `state/` and ad hoc summary files are secondary

If `state/*.md` disagrees with the snapshot records, the snapshot records are correct and state should be regenerated.

## Promotion and Base Evolution

When an experiment proves strong enough:

- If it was evaluated on the latest base and passes promotion policy, it can become `validated_winner` and then `promoted`.
- If it wins on an older base, it becomes `stale_winner` and must be rebased and revalidated.
- Pending experiments on an older base are allowed to keep running. This avoids wasting compute already in progress.

This gives the system a clean evolutionary model without forcing all queued work to restart every time the frontier moves.

## Knowledge and Memory

The system keeps durable learning in markdown under `knowledge/`.

Typical categories:

- `wins.md`
- `failures.md`
- `training.md`
- `architecture.md`

The goal is not just to run experiments, but to build a reusable research memory so future cycles do not repeat old mistakes.

## Why Snapshots Instead of Git Branches

The system uses directory snapshots because:

- They avoid merge complexity when many experiments diverge in parallel.
- They are self-contained and easy to rsync to a remote machine.
- They make arbitrary code changes safer than patch-based approaches.
- They fit the current scale of the projects being explored.

This is more disk-heavy than branch-based orchestration, but operationally simpler.

## Current Operating Pattern

Today the system is primarily optimized for:

- One or a few remote GPUs.
- File-based coordination.
- Fast experiment screening with strong provenance.
- Human-set goals with agent-run execution.

The current production example is `parameter-golf`, with additional project scaffolding already present for future onboarding.

## What the System Is Not

- It is not a hidden service backend with opaque state.
- It is not a pure config-sweep tool.
- It is not fully automatic in the sense of self-generated human missions.
- It is not using a separate research API to invent ideas.

It is an agent-autonomous lab built on explicit files, small scripts, and recorded evidence.

## Recommended Reading Order

For someone new to the system:

1. [AGENTS.md](/root/research/autoresearch/AGENTS.md)
2. [state/NOW.md](/root/research/autoresearch/state/NOW.md)
3. [LAB.md](/root/research/autoresearch/LAB.md)
4. [RESEARCH.md](/root/research/autoresearch/RESEARCH.md)
5. [DESIGN.md](/root/research/autoresearch/DESIGN.md)
6. `projects/<project>.json`
7. `experiments/<project>/current_best.json`

That sequence gives a new agent enough context to safely resume execution.
