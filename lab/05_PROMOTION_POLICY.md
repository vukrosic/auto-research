# Promotion Policy

Policy version: 1.0
Effective: 2026-03-24
Last updated: 2026-03-24
Retroactivity: changes to this policy are not retroactive unless explicitly stated.

## Goal

The frontier should advance only on evidence that survives audit.

## Promotion Preconditions

An experiment is promotion-eligible only if all conditions below are met:

1. The experiment has a recorded identity and hypothesis.
2. The experiment has a recorded `parent_base`.
3. The experiment has a recorded stage and step budget.
4. The experiment has a recorded baseline metric at creation time.
5. The experiment has a recorded threshold for success.
6. The experiment has a valid result on the project's primary metric.
7. The experiment beat its threshold under the correct comparison.
8. The experiment's result is valid for the latest base, or it has been revalidated on the latest base.
9. The promotion can be reconstructed from files alone.

## Comparison Rule

Compare an experiment only against the baseline appropriate to:

- the same project
- the same stage
- the same budget
- the base that was current when the experiment was created

Do not compare across mismatched durations or mismatched bases and call it a win.

## Stale Winner Rule

If an experiment beats the baseline from an older base revision:

- mark it `stale_winner`
- preserve the result
- create a rebase-validation follow-up
- do not promote the stale result directly

## Validation Rule

Promotion requires one of:

- direct validity on the current base
- successful revalidation on the current base

## Automatic Rejection Rule

An experiment must not be promoted if any of these are true:

- result is missing
- baseline is missing
- threshold is missing
- parent base is missing
- status is inconsistent with available files
- the metric parser failed or returned an obviously invalid value

## Promotion Record

Every promotion should leave behind:

- promoted experiment id
- previous frontier id
- metric delta
- comparison baseline
- promotion timestamp
- reason the result is believed to be valid

## Frontier Principle

The frontier is not "the most exciting run." It is the best validated run under current written policy.
