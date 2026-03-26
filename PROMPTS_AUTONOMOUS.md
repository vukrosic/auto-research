# Autonomous Prompts

Use these prompts after copying the kit into the target repo.

## Bootstrap The Lab

```text
Read AGENTS.md, LAB.md, OPERATING_MODEL.md, FOLDER_BLUEPRINT.md, TEMPLATES.md, and SETUP.md.

We are installing a file-based autonomous research lab into this repo.

Your job:
- create the missing folders and starter files described in FOLDER_BLUEPRINT.md
- use TEMPLATES.md to materialize the initial mission, project config, plans, knowledge files, and handoff note
- keep all durable state in repo files
- ask only for critical missing facts that cannot be inferred safely

Operate in autonomous mode.
Do not wait for routine approval.
Stop only for mission changes, budget changes, destructive pivots, or policy conflicts.
```

## Start Or Continue The Loop

```text
Operate as the research agent for this repo.

Read AGENTS.md, LAB.md, OPERATING_MODEL.md, the active goal files, project configs, knowledge files, and state/NOW.md if it exists.

Then:
1. reconcile state
2. check running work
3. adjudicate completed work against the correct same-step baselines
4. update knowledge and reports
5. design the next wave
6. dispatch or stage the next work
7. update state/NOW.md

Proceed autonomously unless LAB.md says you must stop.
```

## Time-Boxed Research Sprint

```text
Run a time-boxed autonomous research sprint in this repo.

Before dispatching anything, create or update a goal with machine-readable timing metadata, define the training window, and ensure each proposed run fits the deadline.

Use the operating docs in this repo as the authority.
Keep the sprint file-based and leave a complete handoff at the end.
```

## Recovery Prompt

```text
Recover this lab from files only.

Read the operating docs, then rebuild context from goals, plans, project configs, experiment records, knowledge files, and state/NOW.md.

Identify:
- what is active
- what is blocked
- what is missing
- the next concrete action

If critical records are missing, recreate them from TEMPLATES.md and document the recovery assumptions.
```
