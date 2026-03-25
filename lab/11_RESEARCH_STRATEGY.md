# Research Strategy

Policy version: 1.0
Effective: 2026-03-25

## Purpose

This document defines **how to think about research at the macro level** — campaigns, waves, pivots, convergence, and resource allocation. It sits above the experiment lifecycle (03) and compute ops (07).

## Core Concepts

### Campaign

A **campaign** is a multi-week focused effort on a specific research direction. Examples: "close the architecture gap", "optimize quantization", "scale training efficiency".

- A campaign has a **goal** (measurable), a **budget** (hours/dollars), and **axes** (orthogonal directions to explore).
- A campaign ends when: the goal is met, the budget is exhausted, or all axes are declared exhausted.
- Only one campaign is active per project at a time. Overlapping campaigns create confusion.
- Campaign definitions live in `campaigns/`.

### Wave

A **wave** is a batch of experiments within a campaign, typically 8-15 experiments targeting 1-3 research axes.

- Waves are the unit of planning: "what do we run next?"
- Each wave should take 1-3 days of GPU time.
- A wave ends with an **adjudication**: review all results, update knowledge, decide next wave.
- Waves within a campaign build on each other: wave N+1 is informed by wave N results.

### Research Axis

An **axis** is an independent direction of investigation. Examples: "expert count scaling", "attention architecture", "vocabulary size".

- Axes are orthogonal: exploring one doesn't preclude exploring others.
- Each axis has an **exhaustion state**: active, promising, exhausted, abandoned.
- An axis is **exhausted** when: 3+ experiments show diminishing or negative returns with no unexplored variants.
- An axis is **abandoned** when: a fundamental blocker is discovered (e.g., all variants exceed size limit).

## Campaign Planning

### Starting a Campaign

Before launching a campaign, answer:

1. **What is the gap?** Current metric vs target, in absolute terms.
2. **What mechanisms could close it?** List research axes with rough expected impact.
3. **What's the compute budget?** Total GPU-hours and calendar time available.
4. **What's the explore/validate/full ratio?** How much screening vs confirmation?
5. **What are the pivot triggers?** Concrete conditions that force a strategy change.

### Compute Allocation Formula

Given `H` total GPU-hours and known stage costs:

```
explore_cost   = 0.467 hr  (28 min on 3090)
validate_cost  = 3.7 hr    (on 3090)
full_cost      = 12.7 hr   (on 3090)
overhead       = 0.033 hr  (2 min SSH/rsync per experiment)
failure_rate   = 0.10      (10% of runs fail and must be rerun)
```

**Default allocation** (adjustable per campaign):

| Phase | Share | Purpose |
|-------|-------|---------|
| Explore | 40-50% | Broad search across axes |
| Validate | 25-35% | Confirm explore winners |
| Full | 10-20% | Final confirmation of validated winners |
| Buffer | 10% | Failures, calibration, baselines |

**Effective runs** = `(allocated_hours / stage_cost) * (1 - failure_rate) - calibration_runs`

### Wave Sizing

A wave should:
- Fit in 1-3 days of GPU time
- Cover 1-3 research axes
- Have 8-15 experiments (enough for statistical comparison, few enough to track)
- Include at least 1 control/baseline rerun per axis (to catch drift)

If a wave has >15 experiments, split it. If <5, merge with the next wave's planning.

## Convergence Detection

### Progress Velocity

Track **BPB improvement per GPU-hour** across waves:

```
velocity = (best_metric_before_wave - best_metric_after_wave) / gpu_hours_spent
```

- **Healthy velocity**: >0.001 BPB / GPU-hour at explore stage
- **Slowing**: 0.0001 - 0.001 BPB / GPU-hour
- **Stalled**: <0.0001 BPB / GPU-hour for 2+ consecutive waves

### Pivot Triggers

> **HARD RULE: Do not persist on a failing strategy.** If research is stalled, pivot.

Pivot when ANY of these conditions are met:

1. **Two consecutive waves** produce no experiment that beats baseline at explore
2. **All axes in the campaign** are marked exhausted or abandoned
3. **Progress velocity** is stalled (<0.0001 BPB/GPU-hr) for 2+ waves
4. **Budget** is >50% spent with <25% of the gap closed
5. **A single experiment** reveals a fundamentally better approach (opportunistic pivot)

### Pivot Actions

When a pivot trigger fires:

1. Record the trigger and reasoning in the campaign file
2. Freeze the current wave — don't throw good compute after bad
3. Write knowledge from all completed experiments
4. Choose one of:
   - **Axis pivot**: Abandon exhausted axes, open new ones within the campaign
   - **Campaign pivot**: Close the campaign, start a new one with different goal/approach
   - **Escalate**: If stuck for >1 week with no improvement, flag for human review

## Research Done Criteria

Research on a project is **done** when ANY of:

1. **Target met**: metric beats the target in `projects/<name>.json`
2. **Budget exhausted**: all allocated compute is spent
3. **Calendar deadline**: competition/project deadline reached
4. **Theoretical ceiling**: analysis shows the architecture cannot reach the target (e.g., parameter budget too small)
5. **Diminishing returns**: 3+ campaigns with <0.005 BPB total improvement

When done, write a final report in `campaigns/` summarizing total improvement, key findings, and recommendations for future work.

## Autonomous Decision Authority

The AI agent (Claude Code) has full authority to:

- Create campaigns and waves
- Choose which axes to explore
- Size waves and allocate compute
- Pivot between axes within a campaign
- Promote/reject experiments per policy
- Declare axes exhausted

The AI agent must escalate to human when:

- Pivoting between campaigns (closing one, opening another)
- Spending >50% of total budget in a single wave
- Any action that conflicts with lab policy
- Stuck for >48 hours with no improvement
