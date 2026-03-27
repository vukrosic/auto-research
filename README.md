<div align="center">
  <h1>Open Research Loop</h1>
  <p><strong>The docs-only control plane for an open autonomous AI research lab.</strong></p>
  <p>Human mission. Agent execution. Distributed compute. Reproducible results.</p>
</div>

> `Open Research Loop` is the public name for the system. `autoresearch` is the current repo and worktree name.

## Non-Negotiable Rules

- If the human gives a time budget like `2 hours`, the lab must write it down explicitly in durable repo state as seconds and as an absolute deadline before dispatching work.
- Every time-boxed sprint must start with calibration or a documented calibration source.
- The lab must track predicted versus actual runtime after every run and recalibrate when drift appears.
- Experiment design must be reactive. Design one active set, run it, read the results, then design the next set. Do not pre-plan multiple future sets as if the earlier results are already known.
- Do not launch work that does not fit the remaining budget with explicit margin.

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

Open Research Loop is a file-based operating system for autonomous research labs.

In this version, the repo is intentionally docs-only. It is meant to be cloned into another AI project so the agent can read the handbook, create the working folders, and run the lab inside the target codebase.

It is:

- a manifesto for open autonomous research
- a reference for file-based research orchestration
- a portable lab operating system you can drop into another repo
- a set of prompts and templates an AI can use to bootstrap itself

It is not:

- a live experiment archive
- a project-specific codebase
- a benchmark suite
- a polished SaaS product

## What The System Does

The system is designed so a human sets mission-level direction and policy while the agent handles the lower-level research loop:

- create the lab folders and durable records inside the target repo
- translate mission into year, quarter, month, and week plans
- design experiments against explicit hypotheses
- compare results against the correct baselines
- update durable knowledge and handoff state
- run either autonomously or under human approval gates

The central design choice is explicit state. Plans, experiment metadata, results, policy, knowledge, and handoff notes should live in repo files, not in hidden services or temporary model memory.

## Why Files Instead Of Hidden Services

I want the lab to be inspectable.

Hidden orchestration services make it harder for:

- a new agent session to recover context
- a human to audit what happened
- contributors to reproduce decisions
- open-source users to adapt the system

File-based state is not the fanciest architecture, but it is durable, inspectable, and agent-friendly.

That is a feature, not an implementation accident.

## Who Starts Where

There are two entry points:

- Human operator: start in this README, then read `SETUP.md`
- AI agent: start with `AGENTS.md`, then `LAB.md`, `OPERATING_MODEL.md`, `FOLDER_BLUEPRINT.md`, and `TEMPLATES.md`

The human sets direction, constraints, and taste.
The agent creates the lab structure inside the target repo and runs the loop within policy.

## Repository Map

This repo now contains only the core documents:

- `README.md`
  - manifesto, framing, and repo entrypoint
- `AGENTS.md`
  - agent onboarding and behavior
- `LAB.md`
  - governance, authority, and policy
- `SETUP.md`
  - install flow for a target repo
- `OPERATING_MODEL.md`
  - lifecycle, planning hierarchy, and research loop
- `FOLDER_BLUEPRINT.md`
  - the folders and files the AI should create in the target repo
- `PROMPTS_AUTONOMOUS.md`
  - prompts for autonomous operation
- `PROMPTS_SUPERVISED.md`
  - prompts for supervised operation
- `TEMPLATES.md`
  - starter templates for goals, plans, configs, experiments, and reports

## How To Use It

1. Copy these markdown files into the root of the repo you actually want to research on.
2. Start your AI coding agent in that repo.
3. Have it read the operating docs.
4. Choose autonomous or supervised mode.
5. Let the agent create the missing folders and starter files in the target repo.

This repo does not ship `experiments/`, `goals/`, `knowledge/`, `projects/`, `state/`, `logs/`, `reports/`, or `scripts/`. Those are meant to be created inside the target repo when the lab is instantiated.

## What I Want This To Become

The longer-term goal is bigger than one operator automating one personal workflow.

The goal is open autonomous research infrastructure:

1. One human should be able to direct many agent-run research loops.
2. One control plane should be able to run many different ML repos.
3. Open-source contributors should be able to reproduce, inspect, and extend the process.
4. Public challenges and leaderboards should be able to plug into the same research engine.
5. Distributed compute and distributed contributors should be able to coordinate through explicit records.

The end state is not "one guy automates his own experiments better."

The end state is open autonomous research infrastructure.
