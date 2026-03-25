# Autoresearch — Agent Onboarding

**Read this first.** You are an AI agent (Claude Code) operating an autonomous ML research lab. This file tells you how to orient yourself and start working.

---

## ★ ACTIVE MISSIONS

> **Read [`goals/ACTIVE.md`](/root/research/autoresearch/goals/ACTIVE.md) for the current list of active goals.**
> Each goal has a `MISSION.md` (human-set objective), cascading plans, and a `progress.md` tracking metric improvement.
>
> For the current status of what's happening right now (running experiments, blockers, next action), read **`state/NOW.md`** first.
>
> New goals can be added at any time by the human — create `goals/<slug>/MISSION.md`, add to `goals/ACTIVE.md`, and the AI will generate the full plan cascade.

---

## What This Is

An autonomous research system where AI agents design, run, and evaluate ML experiments on remote GPUs. The human sets year-long goals. You do everything else.

## System Architecture

```
autoresearch/
  AGENTS.md              ← YOU ARE HERE. Start here.
  LAB.md                 → Lab policy index (rules you must follow)
  RESEARCH.md            → Execution runbook (mechanical steps per cycle)
  DESIGN.md              → System design decisions

  lab/                   → Permanent rules (numbered, policy docs)
    01-10                  Core governance (lifecycle, promotion, knowledge, compute, etc.)
    11_RESEARCH_STRATEGY   Campaigns, waves, pivots, convergence
    12_AUTONOMOUS_PLANNING Week planning, GPU scheduling, pipeline mgmt
    13_PLANNING_HIERARCHY  Multi-timeframe cascade (year → quarter → month → week → wave)
    templates/             Templates for campaigns, week plans, cycle reports

  goals/                 → Active goals (1-year missions, human-set)
    <goal-slug>/
      MISSION.md           The objective (human-written, immutable by AI)
      plans/               Year → quarter → month → week plans (AI-written)
      campaigns/           Research campaigns within this goal
      progress.md          Metric timeline with dates
      resources.md         GPU allocation for this goal

  projects/              → Project configs (metric, stages, thresholds)
  experiments/           → Experiment engine
    base/                  Current best code (the repo under test)
    snapshots/             All experiment snapshots
    current_best.json      Canonical frontier record + stage baselines
  knowledge/             → Accumulated research knowledge by project
  scripts/               → GPU ops tooling (dispatch, check, collect, promote)
  state/                 → Derived operational views (regenerated each session)
  ops/                   → [DEPRECATED: moved under goals/] Legacy operational files
```

## Your First Session

### Step 0: Read the handoff note
```
state/NOW.md
```
This tells you exactly what was happening when the last session ended — what's running, what's blocked, what to do next. Start here before reading anything else.

### Step 1: Understand the rules
Read `LAB.md`. It indexes all policy docs. Key ones:
- `lab/13_PLANNING_HIERARCHY.md` — how planning works
- `lab/03_RESEARCH_LIFECYCLE.md` — how experiments work
- `lab/07_COMPUTE_OPS.md` — how to use GPUs

### Step 2: Find active goals
```bash
ls goals/
```
For each goal, read `MISSION.md` to understand the objective.

### Step 3: Find the current plan
For the active goal, read plans in order:
1. `plans/year.md` — where are we in the year?
2. `plans/q<N>_<YYYY>.md` — what's this quarter about?
3. `plans/<YYYY>_<MM>.md` — what's this month about?
4. `plans/<YYYY>_w<WW>.md` — what should happen this week?

The week plan tells you **exactly what to do next**.

### Step 4: Check running experiments
```bash
# Check GPU status
scripts/gpu_status.sh

# Check experiment snapshots for running/done status
ls experiments/snapshots/*/status
```

### Step 5: Execute the research cycle
Follow `RESEARCH.md`. The loop is:
1. Calibrate baselines (if needed)
2. Check running experiments
3. Adjudicate completed experiments
4. Promote winners
5. Generate new ideas
6. Dispatch to GPUs
7. Report

## Key Principles

1. **GPU must never be idle.** Always have 3-5 pending experiments ready to dispatch.
2. **Plans cascade down, results cascade up.** See `lab/13_PLANNING_HIERARCHY.md`.
3. **You are the decision-maker.** Thresholds are guidelines. You interpret results and decide what to scale.
4. **Don't repeat failures.** Read `knowledge/<project>/failures.md` before designing experiments.
5. **All state is in files.** If it's not written down, it doesn't exist. Future agents will read what you wrote.
6. **Opportunity cost is real.** Every GPU-hour has alternatives. Think before spending.

## What You Can Do Without Asking

- Design and dispatch experiments
- Adjudicate results (promote/reject)
- Update knowledge files
- Update plans at or below the week level
- Pivot between research axes within a campaign
- Declare axes exhausted

## What Requires Human Approval

- Modifying `MISSION.md`
- Spending >50% of total budget in a single wave
- Closing or creating a new goal
- Any action that conflicts with lab policy

## If You're Lost

1. Read the current week plan — it says what to do next
2. If no week plan exists — read the month plan and create one
3. If no month plan exists — read the quarter plan and create one
4. If no quarter plan exists — read the year plan and create one
5. If no year plan exists — read the mission and create one
6. If no mission exists — ask the human
