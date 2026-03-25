# Cadence

Policy version: 1.0
Effective: 2026-03-24
Last updated: 2026-03-24

## Operating Model

This lab runs on a session-based trigger model. A human starts a Claude Code session and says "run a research cycle." There is no daemon, no cron, no continuous loop.

Cadence is therefore defined around sessions, not clock time.

## Session Cadence

### Session Open

- Reconcile state: regenerate `state/*.md` from experiment snapshot records
- Inspect active runs (SSH to GPUs, check for completions, crashes, stalls)
- Adjudicate all finished runs before proposing new work
- Read knowledge files for current project context

### Mid-Session

- Generate hypotheses from knowledge, frontier, and open questions
- Dispatch experiments to available GPUs
- Monitor dispatched runs for early failures
- Update knowledge from adjudicated results

### Session Close

- Update `state/FRONTIER.md` from `experiments/current_best.json`
- Update `state/ACTIVE_RUNS.md` from snapshot statuses
- Clear `state/ADJUDICATION_QUEUE.md`
- Record top open questions in `state/OPEN_QUESTIONS.md`
- Make the next session's first action obvious

## Strategic Reviews

These are real calendar cadences, not session events. They should happen at these intervals regardless of session frequency.

### Weekly Research Review

- What actually improved the frontier
- What failed repeatedly
- Where the search space is saturated
- Whether the project strategy should change

### Weekly Ops Review

- Wasted GPU time
- Flaky scripts
- Slow adjudication points
- Documentation drift between markdown and code

### Monthly Lab Review

- Archive stale queues
- Knowledge audit: prune, rewrite, or downgrade stale claims
- Rewrite lab policies that are being violated in practice
- Review open questions for staleness and ownership

## Standing Questions

Every strategic review should answer:

1. What is our current best system?
2. Why do we believe it is best?
3. What are the top three bets for the next cycle?
4. What process failure caused the most waste this period?

## State Reconciliation Rule

At session open, if `state/*.md` files disagree with experiment snapshot records, snapshot records win. Regenerate the state files. Do not trust stale dashboards.
