# Autoresearch Lab

## ★ ACTIVE MISSIONS

See [`goals/ACTIVE.md`](/root/research/autoresearch/goals/ACTIVE.md) for the current list of active research goals.
New goals: create `goals/<slug>/MISSION.md`, add to `goals/ACTIVE.md`, AI generates the plan cascade.

---

This repository has two layers:

- **Lab operating system**: how the research organization works (policy, governance, authority)
- **Project execution system**: how a specific project gets run (mechanical steps)

Use this file as the entry point for the lab layer.

## Lab Handbook

1. [Lab Charter](/root/research/autoresearch/lab/01_CHARTER.md)
2. [Constitution](/root/research/autoresearch/lab/02_CONSTITUTION.md) — highest-policy document
3. [Org Structure](/root/research/autoresearch/lab/02_ORG.md)
4. [Research Lifecycle](/root/research/autoresearch/lab/03_RESEARCH_LIFECYCLE.md)
5. [Experiment Governance](/root/research/autoresearch/lab/04_EXPERIMENT_GOVERNANCE.md) — statuses, records, review discipline
6. [Promotion Policy](/root/research/autoresearch/lab/05_PROMOTION_POLICY.md) — canonical promotion preconditions
7. [Knowledge System](/root/research/autoresearch/lab/06_KNOWLEDGE_SYSTEM.md)
8. [Compute Operations](/root/research/autoresearch/lab/07_COMPUTE_OPS.md)
9. [Cadence](/root/research/autoresearch/lab/08_CADENCE.md) — session-based operation model
10. [Rollback Policy](/root/research/autoresearch/lab/09_ROLLBACK_POLICY.md)
11. [Naming Convention](/root/research/autoresearch/lab/10_NAMING_CONVENTION.md)
12. [Research Strategy](/root/research/autoresearch/lab/11_RESEARCH_STRATEGY.md) — campaigns, waves, pivots, convergence
13. [Autonomous Planning](/root/research/autoresearch/lab/12_AUTONOMOUS_PLANNING.md) — GPU scheduling, pipeline management
14. [Planning Hierarchy](/root/research/autoresearch/lab/13_PLANNING_HIERARCHY.md) — year → quarter → month → week → wave cascade
15. [Live State](/root/research/autoresearch/state/README.md) — derived operational views
16. [Templates](/root/research/autoresearch/lab/templates/README.md)

## Execution Docs

- [Agent Onboarding](/root/research/autoresearch/AGENTS.md) — **start here** if you're a new AI agent
- [Execution Runbook](/root/research/autoresearch/RESEARCH.md) — mechanical steps for running a research cycle
- [System Design](/root/research/autoresearch/DESIGN.md) — architecture decisions for the execution engine
- [Parameter Golf Project Config](/root/research/autoresearch/projects/parameter-golf.json)

## Goals

- [Goals Overview](/root/research/autoresearch/goals/README.md) — active research goals (1-year missions)
- [Surpass Transformer 2026](/root/research/autoresearch/goals/surpass_transformer_2026/MISSION.md) — current active goal

## Interface Between Layers

- Lab docs define authority, policy, status vocabulary, promotion legality, and truth-maintenance requirements.
- The execution runbook defines mechanical steps only. It defers to lab policy for all decisions.
- If the runbook describes a decision differently from lab policy, lab policy wins.
- Experiment snapshot records are the primary source of truth. State markdown files are derived views.

## Design Rule

If a rule matters operationally, it should exist in markdown in the lab system before it exists in code.

## Autonomous Lab Rule

This lab is agent-autonomous, not human-directed. Human authority sets policy. Agent authority executes research within that policy.
