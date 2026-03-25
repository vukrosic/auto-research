# Lab Handbook Critique

Reviewer: Claude Code (Opus 4.6)
Date: 2026-03-24

---

## Overall Assessment

The lab handbook is well-structured. It reads like someone who got burned by sloppy promotions and wrote the rules they wished they'd had. The constitution, promotion policy, and governance docs are the strongest pieces — they form a coherent chain of authority. The weaker areas are where the handbook stays aspirational instead of mechanical, and where the two layers (lab operating system vs. project execution system) overlap without a clear resolution.

---

## What Works

**The constitution is genuinely useful.** It does the one thing a constitution should do: draw a clear line between what the agent can decide and what it can't. The "Mandatory Defaults" section (missing = not promotable, ambiguous = reject or rerun) is the most operationally valuable paragraph in the entire handbook. It eliminates a class of judgment calls that an agent will inevitably get wrong.

**Promotion policy is tight.** Nine preconditions, all checkable. The stale-winner rule is good — it blocks the most common failure mode in iterative research (beating yesterday's baseline and calling it progress). The "Frontier Principle" closing line is memorable and durable.

**Status vocabulary in 04_EXPERIMENT_GOVERNANCE is well-chosen.** Eight states, no ambiguity between them, clear progression. `stale_winner` and `validated_winner` as distinct states is a design decision that pays for itself.

**Templates are lean.** They ask for what the policy requires and nothing more. The experiment brief maps 1:1 to promotion preconditions, which means filling out the template is the same act as making the experiment promotable. That's good design.

---

## Structural Problems

### 1. Two promotion policies exist and they disagree on detail

`05_PROMOTION_POLICY.md` has 9 preconditions. `04_EXPERIMENT_GOVERNANCE.md` has 5. They're not contradictory, but they're not the same list either. The governance version omits: recorded stage/step budget (#3 in promotion policy), recorded baseline at creation (#4), recorded threshold (#5), and the reconstructibility requirement is stated differently.

This is a real problem. An agent following governance thinks it needs 5 things. An agent following promotion policy thinks it needs 9. The constitution says it wins conflicts, but it doesn't resolve this one — it just says "follow written promotion policy" without specifying which document *is* the promotion policy.

**Fix:** Pick one canonical list and make the other reference it. Don't maintain two lists of preconditions.

### 2. The two layers have no explicit interface

LAB.md says the repo has a "lab operating system" and a "project execution system." But there's no document that says: "here is exactly where lab policy ends and project execution begins." RESEARCH.md talks about `status=winner` and promotes directly. The lab layer talks about `validated_winner` as a prerequisite. RESEARCH.md says `current_best.json` tracks the frontier. The state layer says `state/FRONTIER.md` does.

An agent reading RESEARCH.md first will build one mental model. An agent reading the lab handbook first will build a different one. Neither is wrong, but they're not reconciled.

**Fix:** Either RESEARCH.md should defer to the lab handbook for all policy decisions (and only describe the mechanical steps), or the lab handbook should absorb RESEARCH.md entirely. The current state where both describe the same lifecycle with different terminology and different state files is a drift factory.

### 3. State layer duplicates information that already lives in experiment snapshots

`state/ACTIVE_RUNS.md` tracks running experiments. But `experiments/snapshots/*/status` also tracks running experiments. `state/FRONTIER.md` tracks the current best. But `experiments/current_best.json` (per RESEARCH.md) also tracks the current best. `state/ADJUDICATION_QUEUE.md` tracks finished-but-unjudged runs, which is the same as "all experiments with status=done."

Every piece of duplicated state is a consistency bug waiting to happen. The handbook is aware of this risk (ACTIVE_RUNS.md even warns "if a run exists on a GPU but not here, state is already drifting"), but it introduces the duplication anyway without a reconciliation mechanism.

**Fix:** Decide whether state files are the source of truth or a derived cache. If they're derived, define when and how they're regenerated. If they're primary, remove the redundant fields from experiment snapshots.

### 4. No versioning or change control for lab policy

The constitution says the agent can't change its own constitution. Good. But nothing says how the human *should* change it. There's no version number, no changelog, no "last updated" field. If the human edits promotion policy between cycles, the agent has no way to know whether an experiment that was valid under old policy is still valid under new policy.

The monthly cadence says "rewrite lab policies that are being violated in practice," which is wise, but without versioning this is invisible to the agent.

**Fix:** Add a simple version or last-modified date to policy files. When policy changes, note what changed and whether it's retroactive.

---

## Gaps

### 5. No rollback procedure

The promotion policy says what must be true to promote. It never says what happens if a promotion turns out to be wrong. If you promote experiment X, dispatch three new experiments on X as base, then discover X's result was a measurement error — what do you do? The handbook is silent.

This matters because the agent has standing power to promote. If it promotes incorrectly, there's no written procedure to undo it. "Just revert base/" manually is probably what would happen, but that leaves experiment metadata inconsistent.

### 6. No compute failure model

06_COMPUTE_OPS says "detect failed or stalled runs" and lists required artifacts. But there's no policy for: GPU becomes unreachable mid-run, GPU runs out of disk, training produces NaN and hangs without crashing, SSH credentials expire. These are all things that *will* happen. The existing `status=failed` covers crashes, but not the messier cases.

### 7. Cadence assumes continuous operation but trigger model is manual

07_CADENCE defines morning/midday/end-of-day rhythms. DESIGN.md says the trigger model is manual ("user starts a Claude Code session"). These don't match. A manual trigger model means the agent doesn't have mornings and evenings — it has "sessions." The cadence doc should either be rewritten for a session-based model or the trigger model should be updated.

### 8. No experiment naming convention

Templates ask for a name. Governance requires a name. But nothing defines what a valid name looks like. RESEARCH.md shows `exp_001_moe_8experts` as an example, but that's a sample, not a rule. Without a convention, names will drift (some with sequence numbers, some without, some with dates, some with hyphens vs underscores). This makes glob patterns and scripts fragile.

### 9. Knowledge system has no pruning policy

05_KNOWLEDGE_SYSTEM says "delete or rewrite claims that no longer survive better evidence." But there's no trigger for when this review happens. The monthly cadence says "consolidate knowledge," but that's vague. Over time, knowledge files will accumulate stale claims that no one revisits because there's no forcing function.

### 10. Open Questions file is a good idea but has no owner

`state/OPEN_QUESTIONS.md` lists questions but doesn't say who should answer them or when. Lab questions like "how should base identifiers be formalized?" are policy decisions (human-owned per org structure). Project questions are research decisions (agent-owned). But the file doesn't distinguish ownership, and nothing in the cadence says "review open questions."

---

## Terminology Inconsistencies

| Concept | RESEARCH.md | Lab Handbook |
|---|---|---|
| Current best tracker | `experiments/current_best.json` | `state/FRONTIER.md` |
| Winning status | `winner` | `validated_winner` (pre-promotion) |
| Promotion action | copy `code/` to `base/` | not specified mechanically |
| Status values | 6 values (no `stale_winner`, no `validated_winner`) | 8 values |
| Experiment metadata | `meta.json` fields | experiment brief template fields |

These aren't just cosmetic. An agent that reads RESEARCH.md will set `status=winner` and promote. An agent that reads the lab handbook will set `status=stale_winner`, create a revalidation run, wait for `validated_winner`, then promote. These are different behaviors with different correctness properties.

---

## Minor Issues

- LAB.md numbering skips from "2. Constitution" to "3. Org Structure" but both are file `02_*`. The numbering in LAB.md doesn't match the file numbering scheme.
- 05_PROMOTION_POLICY and 05_KNOWLEDGE_SYSTEM share the `05_` prefix, which breaks the assumption that the number indicates reading order.
- The "Design Rule" in LAB.md ("rules in markdown before code") is good but is itself an orphan — no policy file enshrines it as a constitutional principle.
- FRONTIER.md records `val_bpb_quant` as the metric, but project config uses `val_bpb`. Which is primary?

---

## Recommendations (Priority Order)

1. **Merge the two promotion checklists** into one canonical list in 05_PROMOTION_POLICY. Have 04_EXPERIMENT_GOVERNANCE reference it.
2. **Reconcile RESEARCH.md with the lab handbook.** Either make RESEARCH.md a pure execution runbook that defers to lab policy, or absorb it.
3. **Decide whether state files are source of truth or cache.** Document the answer. Add a reconciliation step to the cadence.
4. **Add a rollback procedure** — even a one-paragraph policy for "what to do when a promotion was wrong."
5. **Align status vocabularies** between RESEARCH.md and the lab handbook.
6. **Add version/date stamps** to policy files.
7. **Define experiment naming convention.**
8. **Rewrite cadence for session-based operation** to match the actual trigger model.

---

## Summary

The handbook's strength is in what it forbids: it's harder to promote a bad experiment under these rules than under no rules. The weakness is in coherence across documents — there are two parallel descriptions of the same lifecycle, and they've already diverged. The single most valuable change would be making RESEARCH.md and the lab handbook tell the same story with the same vocabulary.
