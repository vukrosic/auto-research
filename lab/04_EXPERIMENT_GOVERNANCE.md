# Experiment Governance

Policy version: 1.0
Effective: 2026-03-24
Last updated: 2026-03-24

## Goal

Make experiment decisions auditable and resistant to sloppy promotions.

## Required Records Per Experiment

Each experiment should have written answers for:

- name
- parent base identifier
- hypothesis
- stage
- steps
- baseline metric at creation time
- promotion threshold
- owner
- status

## Promotion Policy

Promotion preconditions are defined in [05_PROMOTION_POLICY.md](/root/research/autoresearch/lab/05_PROMOTION_POLICY.md). That file is the single canonical source for what makes an experiment promotable. Do not duplicate promotion criteria here.

## Rebase Policy

If a candidate beats its baseline on an older base:

- preserve the original result
- set status to `stale_winner`
- create a follow-up validation experiment on the latest base
- never promote a `stale_winner` directly — it must pass revalidation and reach `validated_winner` first

## Status Vocabulary

- `pending`: defined, not yet dispatched
- `running`: actively consuming compute
- `done`: run finished, not yet adjudicated
- `failed`: run invalid due to crash or bad output
- `rejected`: valid result, did not pass policy
- `stale_winner`: beat old baseline but base moved
- `validated_winner`: passed on the latest base and is eligible for promotion
- `promoted`: became the new base
- `rollback_invalidated`: was promoted but later found invalid (see [08_ROLLBACK_POLICY.md](/root/research/autoresearch/lab/08_ROLLBACK_POLICY.md))

## Review Questions

Use these before any promotion:

1. What exact baseline did this beat?
2. Was that baseline current when the experiment was created?
3. Has the base changed since then?
4. Was the candidate validated at the appropriate stage?
5. Can another operator reconstruct the same decision from the files alone?

## Minimal Governance Rule

If the answer to any review question is "I think so" instead of "here is the file", the experiment is not ready to promote.
