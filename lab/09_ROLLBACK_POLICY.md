# Rollback Policy

Policy version: 1.0
Effective: 2026-03-24
Last updated: 2026-03-24

## Purpose

Promotion is not complete unless rollback is defined. This file specifies how to undo a bad promotion.

## When Rollback Applies

A rollback is required when a promoted experiment is discovered to be invalid after promotion. Causes include:

- metric parse error (wrong value extracted from logs)
- stale-base mistake (promoted on old base without revalidation)
- invalid comparison (wrong baseline, wrong stage, wrong budget)
- corrupted run artifact (incomplete training, corrupted checkpoint)
- policy violation (promotion preconditions were not actually met)

## Rollback Procedure

1. **Do not delete the mistaken frontier.** Preserve it as a historical record with status set to `rollback_invalidated`.
2. **Record the reason for rollback** in the experiment's `result.json` or a new `rollback.json` alongside it. Include:
   - what was wrong
   - who or what detected the problem
   - which rollback cause category applies
3. **Restore the last valid frontier.** Update `experiments/current_best.json` to point to the previous valid frontier.
4. **Mark descendants as contaminated.** Any experiment whose `parent_base` is the invalidated frontier must be reviewed:
   - If not yet dispatched: update `parent_base` to the restored frontier
   - If running: let it finish but flag it for revalidation against the restored frontier
   - If done and adjudicated: re-adjudicate against the correct baseline
5. **Update state files.** Regenerate `state/FRONTIER.md` from the restored `current_best.json`.
6. **Write a knowledge entry** in the project's `failures.md` explaining what went wrong and how to prevent recurrence.

## Rollback Is Not Informal

Do not treat rollback as "just revert `base/`." That leaves experiment metadata, state files, and knowledge inconsistent. Follow the full procedure.

## Status Value

Rolled-back experiments should be marked `rollback_invalidated`. This is distinct from `rejected` (which means the experiment was validly evaluated and lost).
