# Lab Rules

This file is the governing policy for the lab once these documents are installed into a target repo.

## Authority

- The human owns mission, scope, budget, and hard constraints.
- The AI owns planning and execution below the mission layer unless the user chooses supervised mode.
- Human-written mission files are not rewritten by the AI without explicit approval.

## Source Of Truth

The lab must be file-based.

Primary records live in the target repo:

- goals and plans
- project config
- experiment records
- knowledge files
- reports and handoff notes

Derived dashboards are useful, but if they disagree with experiment records, the primary records win.

## Required Discipline

1. Every experiment must have a named hypothesis.
2. Every experiment must record its parent base or baseline.
3. Every experiment must be evaluated against the correct same-step baseline.
4. Every adjudication must update durable knowledge.
5. Every session must end with a handoff note.

## Status Vocabulary

Use this status model for experiment records:

- `pending`
- `running`
- `done`
- `failed`
- `rejected`
- `stale_winner`
- `validated_winner`
- `promoted`
- `rollback_invalidated`

## Promotion Rule

An experiment is promotable only when:

- the result is valid
- the metric beats the required threshold
- the comparison used the correct same-step baseline
- the experiment was validated on the latest base

If a strong result was produced on an older base, mark it `stale_winner` and re-run it on the latest base before promotion.

## Rollback Rule

If a promoted result is later found invalid because of bad evaluation, broken logging, stale comparison, or implementation error:

- mark it `rollback_invalidated`
- restore the previous valid base
- record the failure mode in knowledge and the handoff note

## Planning Hierarchy

Planning should cascade in this order:

1. mission
2. year
3. quarter
4. month
5. week
6. wave or batch
7. experiment

Results should roll upward in the reverse direction.

## Knowledge Rule

Do not let findings remain only in chat or commit history.

At minimum, maintain:

- wins
- failures
- training notes
- architecture or design notes

## Compute Rule

Do not spend compute without a clear hypothesis and comparison target.

In autonomous mode, keep a pipeline of ready work so compute does not sit idle unnecessarily.

In supervised mode, stop at the agreed approval gates before dispatching or scaling.

## Mode Rule

Autonomous mode:

- the AI may plan, create experiments, dispatch work, adjudicate results, and update knowledge without routine approvals

Supervised mode:

- the AI must present brief proposals and wait for approval before dispatch, promotion, campaign pivots, or broad repo changes

## Design Rule

If a rule matters operationally, it should be written into repo files before it is trusted in practice.
