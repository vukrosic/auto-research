# Response To Critique

Date: 2026-03-24
Context: response to [CRITIQUE.md](/root/research/autoresearch/lab/CRITIQUE.md)

## Overall Position

The critique is substantially correct.

The handbook is strongest where it prohibits bad behavior and weakest where multiple documents describe the same process with different vocabularies. The right response is not cosmetic cleanup. The right response is to define a single constitutional story, a single execution story, and a clear interface between them.

This document records the decisions that should govern the next revision of the lab handbook.

## Decision 1: There Will Be One Canonical Promotion Policy

Accepted.

The canonical promotion checklist is the one in [05_PROMOTION_POLICY.md](/root/research/autoresearch/lab/05_PROMOTION_POLICY.md).

[04_EXPERIMENT_GOVERNANCE.md](/root/research/autoresearch/lab/04_EXPERIMENT_GOVERNANCE.md) should not maintain a second independent checklist. Its job is to define statuses, records, and review discipline around the canonical policy.

Resolution:

- `05_PROMOTION_POLICY.md` is the only file that defines promotion preconditions.
- `04_EXPERIMENT_GOVERNANCE.md` should reference that file instead of restating a competing list.
- Any future promotion rule must be added in one place only.

## Decision 2: The Interface Between Lab Policy And Execution Must Be Explicit

Accepted.

The current split between "lab operating system" and "project execution system" is conceptually right but operationally underspecified.

The clean interface should be:

- Lab docs define authority, policy, status vocabulary, promotion legality, and truth-maintenance requirements.
- `RESEARCH.md` defines the execution runbook only.
- If `RESEARCH.md` describes a decision, it must defer to the relevant lab policy doc.

Resolution:

- `RESEARCH.md` should become a mechanical runbook.
- `RESEARCH.md` should stop defining winning semantics independently.
- `RESEARCH.md` should use the lab status vocabulary.
- `RESEARCH.md` should treat promotion as an action authorized by policy, not as a default consequence of a good metric.

## Decision 3: State Files Are Derived Operational Views, Not Primary Truth

Accepted.

The critique is right that duplicate state creates drift. The correct model is:

- Primary truth lives in experiment snapshot records and project config.
- State files are operator-facing summaries derived from that truth.

That means:

- `experiments/snapshots/*` remain the authoritative record for experiment status
- `experiments/current_best.json` remains the machine-friendly frontier record
- `state/*.md` are derived human-readable dashboards

Resolution:

- State files are not authoritative.
- State files should say they are derived views.
- Cadence should include a reconciliation pass that regenerates or rewrites state views from primary records.
- If state and snapshot records disagree, snapshot records win.

## Decision 4: Policy Files Need Versioning

Accepted.

An autonomous lab cannot safely operate against mutable policy without visible versioning.

Resolution:

- Every policy file should carry:
  - policy version
  - effective date
  - last updated date
  - retroactivity note
- Constitution changes are major policy changes.
- Promotion-policy changes that affect validity of in-flight experiments must explicitly state whether they apply retroactively.

Minimal rule:

- If retroactivity is unspecified, assume policy changes are not retroactive.

## Decision 5: Rollback Must Be First-Class

Accepted.

Promotion is not complete unless rollback is defined.

Rollback policy should say:

1. Preserve the mistaken promoted frontier as a historical record.
2. Mark the frontier as invalidated rather than deleting it.
3. Restore the last valid frontier.
4. Mark descendants of the invalid promotion as contaminated or needing review.
5. Record the reason for rollback and whether it was:
   - metric parse error
   - stale-base mistake
   - invalid comparison
   - corrupted run artifact
   - policy violation

Resolution:

- Add a dedicated rollback policy file.
- Do not treat rollback as an informal git or filesystem action.

## Decision 6: Compute Ops Needs A Failure Taxonomy

Accepted.

The current compute ops doc is too optimistic.

The lab should classify compute failures into at least:

- hard failure: crash, process exit, missing files
- soft failure: NaNs, degenerate metrics, stalled training
- infrastructure failure: GPU unreachable, disk full, SSH auth failure
- observability failure: run may be healthy but logs or artifacts are missing

Resolution:

- Compute ops should define detection rules and default dispositions for each class.
- The default disposition should prefer containment and clear labeling over guesswork.

## Decision 7: Cadence Must Match Session-Based Operation

Accepted.

The current cadence reads like a continuously running lab. The actual trigger model is session-based.

Resolution:

- Rewrite cadence around session open, mid-session, and session close.
- Weekly and monthly reviews can remain real cadences because those are strategic reviews, not runtime loops.

Proposed session model:

- Session open: reconcile state, inspect active runs, adjudicate finished work
- Mid-session: dispatch, monitor, and update knowledge
- Session close: frontier summary, open questions, next batch

## Decision 8: Experiment Naming Needs A Rule

Accepted.

Naming drift will eventually break tooling and reading flow.

Resolution:

- Define one naming grammar.
- Recommended format:
  - `<stage>_<topic>_<mechanism>_<shortid>`
- Examples:
  - `screen_moe_width_7ac2`
  - `validate_bn128_untied_f31d`
  - `full_residual_gate_91bf`

Required properties:

- lowercase only
- underscores only
- short enough for filenames and remote logs
- stage encoded in the name
- globally unique suffix

## Decision 9: Knowledge Needs A Review Trigger

Accepted.

Knowledge pruning cannot rely on vague periodic goodwill.

Resolution:

- Every strategic review must include a knowledge audit.
- Every promotion or rollback must trigger a targeted knowledge update.
- Any claim contradicted by a validated result must be:
  - rewritten
  - downgraded in confidence
  - or moved to a superseded section

The lab should not silently accumulate obsolete lessons.

## Decision 10: Open Questions Need Ownership

Accepted.

Open questions should be split by owner:

- human-policy questions
- agent-research questions
- joint system-design questions

Resolution:

- `state/OPEN_QUESTIONS.md` should include an `owner` field and a `review_by` field for each question.

## Terminology Unification

This is the central coherence issue.

The lab should adopt one vocabulary:

- `pending`
- `running`
- `done`
- `failed`
- `rejected`
- `stale_winner`
- `validated_winner`
- `promoted`

And one frontier model:

- `experiments/current_best.json` is the canonical machine-readable frontier record
- `state/FRONTIER.md` is the derived human-readable frontier summary

And one winning model:

- `winner` is too ambiguous and should be retired from policy language
- use `stale_winner` or `validated_winner` instead

## The Correct Story Of The System

The next revision should make the system tell one story:

1. The constitution grants the agent operational autonomy.
2. Promotion policy defines what legally counts as promotable.
3. Experiment governance defines statuses, records, and review discipline.
4. `RESEARCH.md` explains how to execute the loop without redefining policy.
5. Snapshot records are primary truth.
6. State markdown files are derived dashboards.

If any document says otherwise, that document is wrong.

## Concrete Next Revision Plan

Priority order:

1. Rewrite `RESEARCH.md` as an execution-only runbook.
2. Remove duplicate promotion criteria from `04_EXPERIMENT_GOVERNANCE.md`.
3. Add version headers to policy files.
4. Add `ROLLBACK_POLICY.md`.
5. Rewrite `07_CADENCE.md` into session-based operation.
6. Add a naming convention file or section.
7. Mark state files explicitly as derived.
8. Update status language everywhere from `winner` to `stale_winner` or `validated_winner`.

## Final Position

The handbook does not need a different philosophy. It needs tighter constitutional discipline.

The critique's main point is right: the danger is not that the lab lacks rules. The danger is that two different rule systems are beginning to form. An autonomous lab cannot tolerate that for long.
