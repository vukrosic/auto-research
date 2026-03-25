# Parameter Golf Research Pipeline

**Date:** 2026-03-22
**Purpose:** A tight, non-indefinite research loop with clear decision gates, a reduced-model pre-screen lane, scaling strategy, and X post cadence at every milestone.

---

## The Loop

Every research cycle follows five phases. Each phase ends with a **gate** — a decision point that determines what happens next.

```
PHASE 1: PLAN ──────────────────────────────────────────────
  Trigger:  Wave complete, OR no active experiments
  Action:   Debate (direction / scale / pivot) → wave plan
  Gate:     Human approves plan
            │
PHASE 2: MICRO-EXPLORE (500 steps) ────────────────────────
  Trigger:  Approved plan deployed
  Action:   16 reduced-model runs, 500 steps each across nano + micro rungs
  Gate:     Collect → Compare → promote shortlist
  Decision: Top-K plus margin winners advance to Phase 3
            Micro lane fails calibration → fall back to normal explore only
            │
PHASE 3: EXPLORE (500 steps) ──────────────────────────────
  Trigger:  Micro winners identified, OR micro lane skipped
  Action:   4-8 full-width experiments, 500 steps each (~30 min)
  Gate:     Collect → Compare → X post (stage 1)
  Decision: Winners (>0.01 BPB gain) advance to Phase 4
            No winners → back to Phase 1 (pivot debate)
            │
PHASE 4: VALIDATE (2000-4000 steps) ───────────────────────
  Trigger:  Explore winners identified
  Action:   1-3 winners x 2 seeds, 2000 or 4000 steps
  Gate:     Collect → Compare → X post (stage 2)
  Decision: Winner holds across seeds → Phase 5
            Winner doesn't replicate → back to Phase 1
            Marginal → one more validate round, then decide
            │
PHASE 5: FULL (13780 steps) ───────────────────────────────
  Trigger:  Validate winner clear, budget permits
  Action:   1 config x 2 seeds, 13780 steps (~13 hrs)
  Gate:     Collect → X post (stage 3)
  Decision: Beats 1.2244 → submit to leaderboard
            Doesn't beat → back to Phase 1
```

---

## Step Counts & When to Use

| Phase | Steps | Time (reference single-GPU) | Cost | When | Advance if |
|-------|------:|-------------|------|------|------------|
| Micro-explore | 500 | ~5-15 min | ~$1-2 | Architecture-only pre-screening | Promotion rules pass |
| Explore | 500 | ~28 min | ~$3 | Always first for new ideas | >0.01 BPB vs baseline |
| Validate-light | 2000 | ~1.8 hr | ~$8 | Quick confirmation of explore win | >0.005 BPB, 2 seeds agree |
| Validate-full | 4000 | ~3.7 hr | ~$15 | Strong explore signal or close call | >0.005 BPB, 2 seeds agree |
| Full | 13780 | ~12.7 hr | ~$50 | Only clear validated winners | Beats 1.2244 BPB |

**Micro-explore defaults:**
- `nano`: 3L/128d/4h/2kv, 500 steps, `MAX_WALLCLOCK_SECONDS=1200`
- `micro`: 5L/192d/4h/2kv, 500 steps, `MAX_WALLCLOCK_SECONDS=1800`
- Fixed across both rungs: tokenizer, dataset, batch tokens, sequence length, activation, and seed
- Scope: architecture-only experiments; no optimizer, LR, or schedule sweeps in this lane

**Micro promotion rules:**
- Hard fail if `nano_delta >= +0.015` and `micro_delta >= +0.010`
- Hard pass if `micro_delta <= -0.010`
- Rank remaining ideas by `score = micro_delta + 0.5 * nano_delta`
- Promote at most 4 ideas into full-width explore

**When to use 2000 vs 4000 for validation:**
- 2000: Explore winner was strong (>0.015 BPB), just confirming it's real
- 4000: Explore winner was moderate (0.005-0.015 BPB), need to see if it persists

**Maximum depth per direction:** 2 validate rounds + 1 full run. If it hasn't won by then, archive and pivot.

---

## The Three Debate Types

Debates replace free-form planning. Each type uses specific agents and has a specific trigger.

### Direction Debate
**When:** Start of new wave, no active winners, exploring new territory.
**Agents:** Architect + Explorer + Skeptic
**Focus:** What new ideas to try. Cast a wide net.
**Output:** 4-8 explore experiments across 1-2 idea categories.

### Scale Debate
**When:** Explore winners found, deciding how to validate/scale.
**Agents:** Architect + Challenger + Optimizer
**Focus:** Will this hold at full training? What's the scaling plan?
**Output:** Validate queue (2-4 experiments, 2 seeds each).

### Pivot Debate
**When:** 3+ waves without improvement, budget <$10, or strategic crossroads.
**Agents:** All 5 (Architect + Skeptic + Explorer + Challenger + Optimizer)
**Focus:** Are we saturated? What's the highest-EV path forward?
**Output:** Strategic reassessment, possibly new direction entirely.

### Debate Triggers (mandatory)

| Event | Debate Type |
|-------|-------------|
| Starting a new wave (no active winners) | Direction |
| Micro-explore shortlist ready | Scale |
| Explore → Validate transition | Scale |
| Validate winner identified, deciding full run | Scale |
| 3+ consecutive waves with no improvement | Pivot |
| Budget below $10 remaining | Pivot |
| After a failed full run | Pivot |

---

## Explore vs. Deepen Decision Logic

```
gap = current_best - leaderboard_target

IF gap > 0.05 BPB:
    → EXPLORE: need breakthrough, cast wide net
    → Debate type: Direction

IF gap <= 0.05 BPB:
    → DEEPEN: squeeze winning config
    → Debate type: Scale

IF budget < $10:
    → Debate type: Pivot (reassess everything)

IF 3+ waves with no improvement:
    → Debate type: Pivot
```

---

## X Post Cadence

Every phase gate produces a post. No exceptions.

| After | Post Content | Images |
|-------|-------------|--------|
| Micro-explore complete | "Screened N architecture ideas on nano + micro rungs, what got promoted" | Delta chart by rung |
| Explore complete | "Tested N ideas at 500 steps, top results, what we're dropping, what advances" | Bar chart: BPB by experiment |
| Validate complete | "Confirmed winner X at Y BPB across 2 seeds, advancing/killing" | Loss curves overlaid |
| Full complete | "New best: X BPB (rank #N)" | Full training curve + leaderboard comparison |
| Pivot debate | "Changing direction: from X to Y, here's why" | Optional |

**Rule:** Posts happen at gates, not spontaneously. The gate analysis is the post source material.

---

## The /wave Skill

One unified skill replaces all `/research mode=X` commands:

```
/wave              → Show wave status + auto-suggest next action
/wave plan         → Run debate → generate wave plan → show for approval
/wave approve      → Lock plan, write queue to active.txt, ready to deploy
/wave results      → Collect + compare + draft X post
/wave pivot        → Force pivot debate regardless of state
```

### Typical session flow

```bash
/wave                    # "Wave 29 micro-explore complete. 4 ideas promoted."
/wave plan               # Runs Scale debate → generates wave_30_plan.md
                         # Review plan...
/wave approve            # Writes queue, activates it
/deploy queues/active.txt  # Send to GPUs
# ... wait for training ...
/wave results            # Collect, compare, draft X post
                         # "Winner: X at Y BPB. Advancing to full."
/wave plan               # Runs Scale debate for full run
/wave approve
/deploy queues/active.txt
# ... wait ...
/wave results            # Final result + X post
```

---

## Kill Criteria (Universal)

These apply at every phase:

1. **Size violation** (>16 MB): Redesign or drop immediately
2. **Micro control failure** (known positives/negatives do not separate): Abort micro lane
3. **Explore no-win** (<0.005 BPB vs baseline at 500 steps): Drop direction
4. **Seed divergence** (>0.005 BPB between seeds): Result is noise, drop
5. **Validate plateau** (improvement shrinks from explore): Won't scale, drop
6. **Full run miss** (doesn't beat 1.2244 BPB): Archive, pivot
7. **Budget exceeded**: Submit best result, stop

---

## Budget Allocation

Given ~$40 total:

| Allocation | Budget | Notes |
|-----------|--------|-------|
| Explore waves (total) | ~$12 | 4 waves x $3 each |
| Validate rounds (total) | ~$16 | 2 directions x $8 each |
| Full run | ~$12 | 1 config x 2 seeds |
| **Total** | **~$40** | |

**Rule:** Never spend >50% of remaining budget on a single full run.
**Rule:** Always check `/cost` before any validate or full deployment.

---

## Queue Naming Convention

| Phase | Format | Example |
|-------|--------|---------|
| Micro-explore | `micro_<rung>_<idea>` | `micro_nano_moe_2e` |
| Explore | `explore/<idea>_<variant>` | `explore/qat_pct70` |
| Validate | `validate/<idea>_<variant>_s<seed>_<steps>` | `validate/moe4e_bn128u_s1337_4k` |
| Full | `full/<idea>_<variant>_s<seed>` | `full/moe4e_bn128u_s1337` |

---

## Wave Plan Format

Every wave produces `queues/wave_NN_plan.md`.
Approved experiments are copied into `queues/active.txt`; no other live queue files should exist outside `queues/archive/`.

```markdown
# Wave NN — <Topic>

**Created:** YYYY-MM-DD
**Debate type:** Direction | Scale | Pivot
**Status:** PENDING | APPROVED

## Decision
What we're testing and why.

## Debate Summary
Key positions, agreements, disagreements.

## Experiments
<queue entries>

## Kill Criteria
Specific conditions that stop this wave early.

## Advancement Gate
What the next phase looks like if winners emerge.

## Budget Estimate
Per-experiment and total cost.
```

---

## Anti-Patterns

1. **Running explore without debate** — wastes budget on directions already falsified
2. **Skipping seeds** — single-seed results are noise at this scale
3. **Going to full without validate** — full runs cost 10x; confirm first
4. **No X post after a gate** — forces clarity and external accountability
5. **Keeping alternate live queue files** — archive everything except `queues/active.txt`
6. **More than 2 explore directions at once** — focus beats breadth at this budget
7. **Re-running failed approaches** — check KNOWLEDGE.md every time
8. **Running indefinitely** — every wave must end with a gate decision
