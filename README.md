# Open Research Loop Template Kit

This repo branch is a markdown-only starter kit for embedding an autonomous research lab into another codebase.

It ships only the operating documents and prompts. It does not ship live experiments, project configs, scripts, logs, reports, credentials, or example research state.

## What This Is For

Use this kit when you want an AI coding agent to operate a research program inside a real repo.

The model should be able to:

- read policy and operating rules from files
- create the missing lab folders in the target repo
- plan work across goals, campaigns, and weekly waves
- run autonomously or with explicit human checkpoints
- keep state, knowledge, and decisions in versioned files instead of hidden memory

## Included Files

- `README.md`
  - Human overview and install path.
- `AGENTS.md`
  - AI onboarding and expected behavior.
- `LAB.md`
  - Governance, authority, and operating rules.
- `SETUP.md`
  - How to install the kit into a target repo.
- `OPERATING_MODEL.md`
  - Lifecycle, planning hierarchy, and execution loop.
- `FOLDER_BLUEPRINT.md`
  - The folders and files the AI should create in the target repo.
- `PROMPTS_AUTONOMOUS.md`
  - Copy-paste prompts for autonomous mode.
- `PROMPTS_SUPERVISED.md`
  - Copy-paste prompts for supervised mode.
- `TEMPLATES.md`
  - Starter templates for goals, plans, campaigns, project configs, experiment records, and reports.

## Intentionally Not Included

This kit does not contain:

- `experiments/`
- `knowledge/`
- `goals/`
- `projects/`
- `state/`
- `logs/`
- `reports/`
- `scripts/`
- any live project data
- any machine-specific or secret config

Those belong in the target repo, not in the template kit.

## How To Use It

1. Copy these markdown files into the root of the repo you actually want to research on.
2. Open your AI coding agent in that repo.
3. Tell the agent to read `AGENTS.md`, `LAB.md`, `OPERATING_MODEL.md`, `FOLDER_BLUEPRINT.md`, and `TEMPLATES.md`.
4. Use either `PROMPTS_AUTONOMOUS.md` or `PROMPTS_SUPERVISED.md`.
5. Let the agent create the missing folders and starter files inside the target repo.

## Design Principle

The lab should be inspectable. Missions, plans, experiments, knowledge, and handoff notes should live in repo files that a new human or a new AI session can read without hidden state.
