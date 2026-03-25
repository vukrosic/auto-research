# Mission — Golf Fast Results Sprint

Human-set at `2026-03-25T13:04:13Z`.

## Objective

Run a short parameter-golf research sprint that must produce actual experimental signal within exactly 2 hours, ending at `2026-03-25T15:04:13Z`.

## Constraints

- Use the `parameter-golf` project.
- Keep this goal isolated from the existing `surpass_transformer_2026` queue.
- The queue file for this goal is the single source of truth for dispatch order.
- Do not interrupt the currently running GPU experiment.
- After the current run finishes, prioritize this goal's queue until the deadline.
- Every experiment in this goal must finish in 10 minutes or less.
- Avoid long quantization or late evaluation tails.
- Generate a written report at the deadline, even if some runs fail.

## Success Criteria

- Run or attempt a fast baseline and at least two candidate experiments.
- Produce at least one directional insight, ranking, or explicit rejection.
- Leave a report that the next agent can continue from without human explanation.
