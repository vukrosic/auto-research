<div align="center">
  <h1>Open Research Loop</h1>
  <p><strong>The docs-only control plane for an open autonomous AI research lab.</strong></p>
  <p>Human mission. Agent execution. Reproducible state.</p>
</div>

> `Open Research Loop` is the public name for the system. `autoresearch` is the current repo and worktree name.

## Mission

The point of this repo is not just to automate one person's experiments.

The point is to make autonomous AI research more open, inspectable, and reusable:

- humans set direction, constraints, and taste
- agents do lower-level research work
- important state lives in files, not hidden memory
- results can be resumed, audited, and shared

## What This Repo Is

This repo is a docs-only operating system for running an autonomous research lab inside another codebase.

It is:

- a portable lab handbook
- a file-based operating model
- a prompt and template kit
- a concrete product spec for the first useful workflow

It is not:

- a live experiment archive
- a benchmark suite
- a hosted platform
- a polished end-user product

## Core Design Choice

The lab is file-based on purpose.

Plans, experiment records, project configs, knowledge, and handoff state should live in the target repo so:

- a new agent can recover context
- a human can inspect what happened
- contributors can reproduce decisions
- the workflow does not depend on hidden orchestration

## Where To Start

Human operator:
- read this file
- read `PRODUCT_SPEC.md` if you care about the first concrete workflow
- read `INTAKE_PROMPT.md` if you care about how the first conversation should work
- read `SETUP.md`

AI agent:
- start with `AGENTS.md`
- then read `LAB.md`, `OPERATING_MODEL.md`, `PRODUCT_SPEC.md`, `INTAKE_PROMPT.md`, `FOLDER_BLUEPRINT.md`, and `TEMPLATES.md`

## Repository Map

- `README.md`
  - repo entrypoint and framing
- `PRODUCT_SPEC.md`
  - first shippable workflow and maturity gates
- `INTAKE_PROMPT.md`
  - first-conversation scoping behavior
- `LAB.md`
  - authority, rules, and policy
- `OPERATING_MODEL.md`
  - execution mechanics and research loop
- `AGENTS.md`
  - agent onboarding and startup behavior
- `SETUP.md`
  - human install flow
- `FOLDER_BLUEPRINT.md`
  - durable folder structure for target repos
- `TEMPLATES.md`
  - starter files for goals, plans, configs, experiments, and reports
- `PROMPTS_AUTONOMOUS.md`
  - prompt entrypoints for autonomous operation
- `PROMPTS_SUPERVISED.md`
  - prompt entrypoints for approval-gated operation
- `OPERATOR_TIPS.md`
  - practical tips for the human operator

## How To Use It

1. Copy these markdown files into the repo you actually want to research on.
2. Start your AI coding agent in that repo.
3. Have it read the documents in the order defined by `AGENTS.md`.
4. Choose autonomous or supervised mode.
5. Let the agent create the working folders and durable starter files in the target repo.

This repo does not ship runtime folders like `experiments/`, `goals/`, `knowledge/`, `projects/`, `state/`, `logs/`, or `reports/`.
Those are meant to be created inside the target repo when the lab is instantiated.

## Long-Term Direction

The long-term goal is open autonomous research infrastructure:

1. one human can direct many agent-run loops
2. one control plane can work across many repos
3. contributors can inspect and extend the process
4. public knowledge compounds instead of staying private

The first step is smaller:
make the workflow from user question to autonomous research run actually work.
