<div align="center">
  <h1>Open Research Loop</h1>
  <p><strong>Autoresearch is the working control plane for an open autonomous AI research lab.</strong></p>
  <p>Human mission. Agent execution. Distributed compute. Reproducible results.</p>
</div>

<table>
  <tr>
    <td width="33%" valign="top">
      <strong>Mission Layer</strong><br/>
      Human sets goals and supervises, AI does everything else. Infinitely scalable.
    </td>
    <td width="33%" valign="top">
      <strong>Execution Layer</strong><br/>
      Agents design experiments, dispatch runs, collect results, and decide what to test next.
    </td>
    <td width="33%" valign="top">
      <strong>Open Layer</strong><br/>
      Shared knowledge, public comparisons, and reproducible records turn isolated runs into science.
    </td>
  </tr>
</table>

> `Open Research Loop` is the public name for the system. `autoresearch` is the current repo and worktree name.

## Manifesto

We believe AI research should become far more open than it is today.

For a while, frontier labs held two major advantages:

1. expertise
2. compute

Those advantages still matter, but they are no longer absolute.

Autonomous AI research lowers the expertise barrier by letting a much larger set of people run real research loops:

- students
- independent researchers
- open-source contributors
- startup teams
- smaller labs

Distributed global compute also changes the equation. No single open-source group has the budget of the largest frontier lab, but the total compute available across the world is larger than the compute of any one institution. The limiting factor becomes coordination, not just raw hardware.

That means the open-source opportunity is not merely to imitate closed labs. It is to build a different research system:

- open challenges
- public leaderboards
- reproducible submissions
- lightweight verification
- shared experiment logs
- reusable code and knowledge

The goal is not to remove researchers from research. The goal is to give far more people the ability to contribute meaningfully.

Our bet is simple:

If we build the infrastructure for autonomous, reproducible, public experimentation, open-source AI research can become one of the main engines of progress.

## What This Is

Open Research Loop is a file-based autonomous ML research lab. A human sets mission-level goals and policy. The agent handles planning below that layer: creating experiments, dispatching them to remote GPUs, collecting results, updating knowledge, and deciding what to run next.

This repository is the control plane for that workflow. It is not a polished SaaS product or a generic benchmark suite. It is the working lab system itself.

## What It Does

- keeps lab state in files instead of a hidden database
- manages long-horizon goals under `goals/`
- runs snapshot-based experiments under `experiments/`
- adapts to project-specific repos through `projects/*.json`
- dispatches work to remote GPUs through `scripts/`
- records durable research knowledge under `knowledge/`

The central design choice is explicit state. Plans, experiment metadata, results, policy, and handoff notes all live in versioned files so a new agent session can recover context without hidden memory.

Live experiment archives are intentionally kept local. The public default branch is for the framework, policies, scripts, and lightweight metadata, not for shipping full snapshot history to every GitHub clone.

## Current Status

This repo is publishable as a reference system, but it is still operator-centric.

Today it is optimized for:

- one operator plus one agent
- one or a few remote GPUs
- file-based coordination
- fast experiment screening with strong provenance
- one active research campaign at a time

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
  - public entrypoint and manifesto
- `assets/`
  - README visual assets
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

If you want to inspect the current live lab state in a working clone, read `state/NOW.md`.

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
