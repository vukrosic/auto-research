# Cadence

Policy version: 1.0
Effective: 2026-03-24
Last updated: 2026-03-24

## Operating Model

This lab runs on a session-based trigger model. A human starts a Claude Code session and says "run a research cycle." There is no daemon, no cron, no continuous loop.

Cadence is therefore defined around sessions, not clock time.

Exception: a goal may define a hard calendar deadline and a report time. In that case, the session must treat that deadline as binding and continuously track progress against it.

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
- Recompute remaining time to any active hard deadline after every collection and every dispatch

### Session Close

- Update `state/FRONTIER.md` from `experiments/current_best.json`
- Update `state/ACTIVE_RUNS.md` from snapshot statuses
- Clear `state/ADJUDICATION_QUEUE.md`
- Record top open questions in `state/OPEN_QUESTIONS.md`
- **Update `state/NOW.md`** — write what is happening right now, what blocked, what the next action is, any pitfalls discovered this session. This is the handoff note for the next agent or session.

## Strategic Reviews

These are real calendar cadences, not session events. They should happen at these intervals regardless of session frequency. See also `lab/13_PLANNING_HIERARCHY.md` for the full cascade rules.

### Daily Review (at session open)

- Check running experiments, collect results
- Adjudicate completed experiments
- Update week plan with results
- Dispatch next experiments (GPU must never be idle)

### Weekly Review (at week boundary)

- Review all experiments from the week
- Update month plan with week results
- Compute velocity: BPB improvement / GPU-hours
- Generate next week plan
- Update campaign wave log

### Monthly Review (at month boundary)

- Review all experiments from the month
- Update quarter plan with month results
- Assess axis exhaustion: any axes to close or open?
- Compute monthly velocity and compare to milestone
- Generate next month plan
- Knowledge audit: prune stale claims, add new findings

### Quarterly Review (at quarter boundary)

- Review the full quarter against milestone
- Update year plan with quarter results
- Assess phase gate criteria: can we move to next phase?
- Compute quarterly velocity and extrapolate to year-end
- Generate next quarter plan
- Major strategic decisions: pivot campaigns, adjust resource allocation

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

## Deadline Rule

> **HARD RULE: Deadline misses beyond 5% are critical failures.**
>
> If a goal has a deadline:
> - write the exact current time when the goal starts
> - if the user specifies a runtime budget from training start, record `training_window_seconds`
>   and `training_window_anchor=first_dispatch`
> - stamp `training_started_at` on the first successful dispatch
> - write the exact report time
> - maintain a machine-readable queue or plan with expected durations
> - update the expected completion picture after every finished run
> - if progress is behind plan by more than 5%, stop and replan before spending more compute
