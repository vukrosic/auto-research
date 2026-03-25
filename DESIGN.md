# Autoresearch v2 — Design Decisions

Lab-level operating policy now lives in [LAB.md](/root/research/autoresearch/LAB.md). This file is the system design for the execution engine. For status vocabulary, promotion rules, and governance, defer to the lab handbook.

## Core Philosophy

- **Claude Code IS the researcher.** No Anthropic API calls for idea generation. Claude Code itself thinks, writes code, and evaluates.
- **Can't evaluate = can't autoresearch.** Every project needs a single numeric metric (e.g., val_bpb) with a clear direction.
- **No human gates.** Deterministic metric thresholds decide winners. Humans contribute ideas and monitor — never block.
- **Any code change is fair game.** Not just config tweaks — architecture, training loop, data loading, anything.
- **A research organization is a set of markdown files.** All rules, context, and state live in markdown.

## Architecture: Snapshot-Based Versioning

### Why not git branches?
- Git branches create merge hell with 50+ parallel experiments
- Requires full repo history on every GPU
- Snapshots are simpler — just directories

### Why not patches?
- Patches can fail to apply if base drifts
- Claude Code makes arbitrary code changes that may not diff cleanly
- Each experiment must be fully self-contained and reproducible

### Structure
```
experiments/
  base/                     # clean copy of the repo — the current "truth"
  snapshots/
    exp_001_moe_8experts/
      code/                 # FULL copy of the repo with changes applied
      meta.json             # hypothesis, parent_base, stage, priority
      status                # see lab handbook for canonical status vocabulary
      result.json           # val_bpb, steps, gpu, duration
    exp_002_rope_scaling/
      code/
      meta.json
      ...
```

### Future disk optimization
- Current: full copies (fine for small repos like parameter-golf)
- Future: store only changed files + manifest of parent base
- `materialize` step assembles full directory before GPU dispatch
- Can use hardlinks, overlayfs, or `rsync --link-dest` to deduplicate

## Base Evolution (Winner Promotion)

When a winner is found:
1. Winner's snapshot becomes the new `base/`
2. Pending experiments built on old base **keep running** (no wasted GPU time)
3. Each experiment records `parent_base` in meta.json
4. Evaluation compares against the baseline that was current at experiment creation
5. If old-base experiment wins: **rebase** — Claude Code re-applies the idea to new base, queues validation run
6. Only validated-on-latest-base experiments actually promote

Lifecycle:
```
idea → snapshot (on current base) → GPU runs → result
  → validated_winner? → promote to new base (per promotion policy)
  → stale_winner? → rebase onto latest base → validate → promote
  → rejected?  → extract learnings
```

## Metric & Thresholds

- Single metric per project (e.g., `val_bpb`)
- Direction: lower or higher is better
- Threshold: `result < current_best - margin` → auto-promote
- Tiered elimination: explore → validate → full
- Each stage has step budget and threshold

## GPU Dispatch Model

**Hybrid: on-demand dispatch + thin watchdog.**
- Claude Code SSHes in, rsyncs snapshot, starts job via `nohup`
- Tiny watchdog on GPU: if training crashes, writes `status=failed` + error to result.json
- Claude Code checks status via SSH on next cycle
- No daemon to maintain. All intelligence lives in Claude Code.

## Trigger Model

**Manual.** User starts a Claude Code session, says "run a research cycle." Claude does a full loop:
generate ideas → dispatch to available GPUs → check running → evaluate results → promote winners.

No cron, no /schedule, no /loop. Simple and controllable.

## Knowledge System

Inspired by OpenClaw's memory approach — markdown files organized by topic.

```
knowledge/
  parameter-golf/
    architecture.md        # what we know about model architectures at this scale
    training.md            # learning rates, schedules, warmup findings
    failures.md            # what we tried that didn't work and why
    wins.md                # what worked, with metrics
    literature.md          # insights from papers (future: automated via scispace.com or similar)
  meta/
    patterns.md            # cross-project patterns (what generally works)
```

- Claude Code reads knowledge at start of each cycle for context
- Claude Code writes knowledge after evaluating results
- Each file is topical, not timestamped — easy to retrieve by subject
- Literature review: future feature. scispace.com has an AI agent but no API — may need browser automation or alternative approach

## First Target

**Parameter-golf.** Small repo, clear metric (val_bpb), GPU access available. Generalize after proving the loop.

## V1 Code

**Tear down and rebuild.** V1 was designed around API calls and config-only tweaks. Wrong abstractions for v2 where Claude Code makes arbitrary code changes.

## Open Questions

- [ ] Literature review automation (scispace.com has no API — browser automation? alternative?)
- [ ] Multi-repo support: what's the minimum a repo must provide
