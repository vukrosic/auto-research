# Mission — Golf Rope 5-Minute Micro Sprint

Human-set at `2026-03-25T15:32:08Z`.

## Objective

Run a parameter-golf rope-parameter micro sprint with a strict 5-minute research window measured from the first training dispatch, and identify the best rope setting from the tested batch.

## Constraints

- Use the `parameter-golf` project.
- Interrupt any currently running or queued work on the GPU in favor of this goal.
- The queue file for this goal is the single source of truth for dispatch order.
- The 5-minute deadline starts at the first successful training dispatch, not at planning time.
- Every runtime tail counts against the 5-minute budget: validation, quantization, compression/export, and collection.
- The sprint must prioritize many short experiments over a few long ones.
- Disable or cap any expensive tail work that is not required for directional rope screening.
- Generate a written report when the 5-minute training window ends.

## Success Criteria

- Complete a same-settings micro baseline and multiple rope candidates.
- Produce a ranked rope recommendation or a clear rejection of the tested range.
- Leave exact timing and runtime evidence for the next agent.
