# Autoresearch

Autoresearch is a file-based autonomous ML research lab. A human sets mission-level goals and policy. The agent handles planning below that layer: creating experiments, dispatching them to remote GPUs, collecting results, updating knowledge, and deciding what to run next.

This repository is the control plane for that workflow. It is not a polished SaaS product or a general benchmark suite. It is the working lab system itself.

## What It Does

- keeps all lab state in files rather than a hidden database
- manages long-horizon goals under `goals/`
- runs snapshot-based experiments under `experiments/`
- adapts to project-specific repos through `projects/*.json`
- dispatches work to remote GPUs through `scripts/`
- records durable research knowledge under `knowledge/`

The main design choice is explicit state. Plans, experiment metadata, results, policy, and handoff notes all live in versioned files so a new agent session can recover context without hidden memory.

## Current Status

This repo is publishable as a reference system, but it is still operator-centric.

Today it is optimized for:

- one operator plus one agent
- one or a few remote GPUs
- file-based coordination
- one active research project at a time
- fast experiment screening with strong provenance

The current live project is `parameter-golf`, a system for running architecture and training sweeps against the OpenAI 16MB language-model challenge.

## Core Concepts

### 1. Goals

The human creates long-horizon goals under `goals/<slug>/MISSION.md`.

The agent is allowed to create and update:

- yearly, quarterly, monthly, and weekly plans
- campaign files
- progress tracking
- reports
- queue materialization

### 2. Projects

Each project is defined in `projects/<name>.json`.

A project config specifies:

- the metric to optimize
- how to run an experiment
- how to detect completion
- how to parse metrics from logs or summary JSON
- stage budgets such as `explore`, `validate`, and `full`
- which GPUs are valid for that project

### 3. Snapshots

Each experiment lives under `experiments/<project>/snapshots/<experiment>/`.

Snapshots contain:

- the experiment metadata
- run status
- collected results
- optional preflight records
- a self-contained code snapshot during execution

This avoids branch-management complexity and makes remote dispatch simpler.

## Repository Map

- `README.md`
  - public entrypoint
- `AUTONOMOUS_SYSTEM.md`
  - high-level system architecture
- `AGENTS.md`
  - onboarding for a new agent session
- `RESEARCH.md`
  - execution runbook for a research cycle
- `LAB.md`
  - policy index for lab governance
- `goals/`
  - human missions and agent-managed plans
- `projects/`
  - project adapters and execution contracts
- `experiments/`
  - current base code, snapshots, frontier state
- `knowledge/`
  - accumulated findings and failures
- `scripts/`
  - dispatch, polling, collection, promotion, reporting
- `state/`
  - derived handoff views and operational dashboards

## Execution Loop

At a high level, the system does this:

1. read the active goals and current state
2. check running experiments
3. collect finished results
4. compare results against the correct baseline
5. promote winners when policy allows
6. generate or materialize new experiments
7. dispatch the next batch to remote GPUs
8. update reports, knowledge, and handoff state

The agent is the decision-maker. The scripts provide mechanical operations; the agent decides what to test, what to reject, and what to scale.

## Setup Expectations

This is currently a Linux-first workflow that expects:

- `bash`
- `python3`
- `git`
- `rsync`
- `ssh`
- `sshpass`

For remote execution you also need:

- a local `scripts/gpu_config.sh` copied from `scripts/gpu_config.example.sh`
- project configs in `projects/*.json` that point to valid local repos and remote directories
- a project repo initialized under `experiments/<project>/base/`

## Where To Start Reading

If you want to understand the system in order:

1. `AUTONOMOUS_SYSTEM.md`
2. `AGENTS.md`
3. `RESEARCH.md`
4. `projects/parameter-golf.json`

If you want to inspect the current live lab state, read `state/NOW.md`.

## Known Rough Edges

- The repo still contains live operational state, not just clean framework code.
- Some project configs use absolute local paths and named remote GPUs.
- The snapshot directory is large because it currently stores many experiment records in-repo.
- Some folders such as `ops/` are historical and kept mainly for reference.

## Intended Use

This repo is best read as:

- a working example of an autonomous research control plane
- a reference for file-based experiment orchestration
- a starting point for people building their own autonomous lab tooling

It is not yet a one-command install for arbitrary projects, and the README should be read with that expectation.
