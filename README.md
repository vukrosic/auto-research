<div align="center">
  <h1>Open Research Loop</h1>
  <p><strong>Autoresearch is the working control plane for an open autonomous AI research lab.</strong></p>
  <p>Human mission. Agent execution. Distributed compute. Reproducible results.</p>
</div>

> `Open Research Loop` is the public name for the system. `autoresearch` is the current repo and worktree name.

## Mission

The goal is not just to automate my own experiments.

The goal is to help build public infrastructure for autonomous AI research:

- humans set direction, constraints, and taste
- agents do the lower-level research work
- experiments stay reproducible
- results become public knowledge instead of private notebook fragments
- more people can contribute to real AI research

If this works, open-source AI research becomes less dependent on a tiny number of elite institutions and more dependent on coordination, taste, and iteration speed.

## Why This Exists

For a while, frontier labs had two overwhelming advantages:

1. expertise
2. compute

Those advantages still matter, but they are no longer absolute.

Strong coding agents reduce the expertise barrier because they can now:

- inspect repos
- modify code
- design batches of experiments
- run short research loops
- compare outcomes against baselines
- update plans and knowledge after each round

Distributed compute changes the picture too. No open group has the budget of the biggest labs, but the total compute available across the world is larger than the compute of any one institution. The bottleneck becomes coordination, not just ownership.

That creates an opening for a different research model:

- open challenges
- public leaderboards
- reproducible submissions
- lightweight verification
- shared experiment logs
- reusable code and knowledge

This repo is an attempt to build toward that model.

## What This Repo Is

Open Research Loop is a file-based autonomous ML research lab.

A human sets mission-level goals and policy. The agent handles planning below that layer: proposing experiments, creating snapshots, dispatching runs to remote GPUs, collecting results, updating knowledge, and deciding what to test next.

This repository is the control plane for that workflow.

It is:

- a working autonomous research system
- a reference for file-based experiment orchestration
- a lab operating system for long-horizon research work
- a public artifact showing how autonomous research can actually be run

It is not:

- a polished SaaS product
- a benchmark suite
- a one-command install for arbitrary repos
- a fake demo disconnected from real research

## What The System Does Today

Today the repo can:

- keep lab state in files instead of a hidden database
- manage long-horizon goals under `goals/`
- run snapshot-based experiments under `experiments/`
- adapt to project-specific repos through `projects/*.json`
- dispatch work to remote GPUs through `scripts/`
- collect results and compare them to the correct baseline
- promote winners and preserve provenance
- record durable research knowledge under `knowledge/`
- recover context across agent sessions without hidden memory

The central design choice is explicit state. Plans, experiment metadata, results, policy, knowledge, and handoff notes all live in versioned files.

## Who Starts Where

There are two different entrypoints:

- Human operator: start in this README, then use the quick start below
- AI agent: start with `AGENTS.md`, then `state/NOW.md`

The human sets direction, constraints, and goals.
The agent reads the lab state, runs the loop, and updates the records.

## What I Want This To Become

Right now this is a working operator-centric lab system.

The longer-term goal is much bigger:

1. One human should be able to direct many agent-run research loops.
2. One control plane should be able to run many different ML repos.
3. Open-source contributors should be able to reproduce, inspect, and extend the process.
4. Public challenges and leaderboards should be able to plug into the same research engine.
5. Distributed compute and distributed contributors should be able to coordinate through explicit records.

The end state is not "one guy automates his own experiments better."

The end state is open autonomous research infrastructure.

## What Still Needs To Be Built

This repo is publishable, but it is still early.

The biggest missing pieces are:

- a cleaner project adapter layer so arbitrary repos can plug in without custom shell assumptions
- better multi-project support so goals map cleanly to projects
- separation between public framework code and large local experiment archives
- cleaner installation and onboarding for new users
- better reporting and public-facing result artifacts
- stronger verification and submission flows for open challenges
- easier scaling from one GPU to many GPUs
- more durable cross-project research memory
- eventually, public leaderboard and contribution workflows

In short: the research loop works, but the universal product layer around it is still being built.

## Current Status

Today this system is optimized for:

- one operator plus one strong coding agent
- one or a few remote GPUs
- file-based coordination
- fast experiment screening with strong provenance
- one active research campaign at a time

The current live project is `parameter-golf`, where the system is being used to run architecture and training sweeps against the OpenAI 16MB language-model challenge.

This repo should be read as an active lab system first and a clean framework second.

## Why Files Instead Of Hidden Services

I want the lab to be inspectable.

Hidden orchestration services make it harder for:

- a new agent session to recover context
- a human to audit what happened
- contributors to reproduce decisions
- open-source users to adapt the system

File-based state is not the fanciest architecture, but it is durable, inspectable, and agent-friendly.

Primary records live in the repo:

- goals
- policies
- experiments
- results
- frontier state
- research knowledge
- handoff notes

That is a feature, not an implementation accident.

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

- experiment metadata
- run status
- collected results
- optional preflight records
- a self-contained code snapshot during execution

This avoids branch-management complexity and makes remote dispatch simpler.

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

The agent is the decision-maker. The scripts provide the mechanical operations. The research judgment lives in the loop that reads evidence and decides what to try next.

## Repository Map

- `README.md`
  - public entrypoint and mission
- `AUTONOMOUS_SYSTEM.md`
  - high-level system architecture
- `AGENTS.md`
  - onboarding for a new agent session
- `RESEARCH.md`
  - execution runbook for a research cycle
- `LAB.md`
  - policy index for lab governance
- `DESIGN.md`
  - execution-engine design decisions
- `UNIVERSALIZATION_PLAN.md`
  - how this grows from a live lab into a more general system
- `goals/`
  - human missions and agent-managed plans
- `projects/`
  - project adapters and execution contracts
- `experiments/`
  - base code, snapshots, frontier state
- `knowledge/`
  - accumulated findings and failures
- `scripts/`
  - dispatch, polling, collection, promotion, reporting
- `state/`
  - derived dashboards and handoff views

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

It is currently best suited for operators who are comfortable with terminals, SSH, GPUs, and reading the code before trying to generalize it.

## Quick Start

This is the shortest honest way to get a local operator setup running today.

### 1. Clone location

Today the safest path is:

```bash
mkdir -p /root/research
cd /root/research
git clone <your-fork-or-this-repo-url> autoresearch
```

Current examples and a few helper scripts still assume `/root/research/autoresearch`, so using that path avoids friction.

You can clone it somewhere else, but right now that may require patching a few older scripts or adding a symlink.

### 2. Clone the target repo separately

This repo is the control plane, not the model repo itself.

For the current live example, the project repo is expected separately, for example:

```bash
cd /root/research
git clone <target-project-repo-url> parameter-golf
```

Project configs point at those target repos through `projects/*.json`.

### 3. Configure SSH access to your GPU

Copy the example GPU config:

```bash
cd /root/research/autoresearch
cp scripts/gpu_config.example.sh scripts/gpu_config.sh
```

Then fill in:

- host
- port
- user
- password

Remote working directories are not defined in `gpu_config.sh`; they live in each `projects/<name>.json` under `gpu_remote_dirs`.

This workflow currently uses `ssh`, `rsync`, and `sshpass`.

### 4. Check project paths

Open the relevant project config and make sure these fields match your machine:

- `repo_path`
- `gpu_remote_dirs`
- enabled GPU names

For example, `projects/parameter-golf.json` currently assumes the target repo is at `/root/research/parameter-golf`.

### 5. Initialize the project base snapshot

Once the target repo exists locally:

```bash
cd /root/research/autoresearch
bash scripts/init_base.sh parameter-golf
```

Or override the repo path explicitly:

```bash
bash scripts/init_base.sh parameter-golf /absolute/path/to/your/repo
```

### 6. Confirm GPU connectivity

```bash
bash scripts/gpu_status.sh
```

If this fails, fix SSH and remote directory issues before trying to run experiments.

### 7. Start from the right document

If you are the human operator:

1. read `README.md`
2. read `AUTONOMOUS_SYSTEM.md`
3. read `RESEARCH.md`

If you are the agent:

1. read `AGENTS.md`
2. read `state/NOW.md`
3. continue from the live lab state

### 8. Run a loop

Once you have pending experiment snapshots, a simple serial batch loop for the current parameter-golf workflow is:

```bash
bash scripts/run_loop.sh 3
```

If you do not have pending snapshots yet, create one with:

```bash
bash scripts/new_experiment.sh parameter-golf explore_smoke_test
```

Then edit the snapshot metadata and code before dispatching.

The loop command is not the whole system, but it is the fastest way to prove dispatch, polling, collection, and result logging work end to end.

## Want Help Setting Up Your Own Loop?

This repo is still operator-first.

If you already have a repo, a research problem, or a benchmark you want to attack, the fastest path right now is usually guided setup rather than trying to infer the whole workflow from scratch.

Best fit:

- engineers or researchers who want an autonomous experiment loop on their own repo
- people blocked on SSH, GPU workflow, prompts, or experiment structure
- builders who want to go from "interesting idea" to "first real batch of runs"

I offer a limited number of **1:1 Autonomous AI Research Setup Calls** for **$99**.

In one focused session, we work on your exact setup:

- repo choice and workflow
- SSH and remote GPU access
- agent prompt structure
- first short experiments
- the next 24 hours of iteration

The goal is not generic mentoring. The goal is to get your autonomous research workflow operational or clearly unblocked.

Paying for a setup call also directly supports my open-source work on Open Research Loop.

## Reading Order

If you want to understand the system in order:

1. `AUTONOMOUS_SYSTEM.md`
2. `AGENTS.md`
3. `RESEARCH.md`
4. `DESIGN.md`
5. `UNIVERSALIZATION_PLAN.md`
6. `projects/parameter-golf.json`

If you want to inspect the current live lab state in a working clone, read `state/NOW.md`.

## Known Rough Edges

- The repo still contains live operational state, not just framework code.
- Some project configs use absolute local paths and named remote GPUs.
- The snapshot directory is large because it currently stores many experiment records in-repo.
- Some workflows are still parameter-golf-specific.
- The install path is still too manual for broad adoption.

## Intended Use

This repo is best read as:

- a working example of an autonomous research control plane
- a reference for file-based experiment orchestration
- a blueprint for more open AI research infrastructure
- a public build log for a system that is still evolving

If this direction matters to you, star the repo. Social proof helps push the idea that open autonomous research should exist as public infrastructure, not just as a private lab capability.
