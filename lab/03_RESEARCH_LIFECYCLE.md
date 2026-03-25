# Research Lifecycle

> **THE AI AGENT IS THE RESEARCHER.** Scaling decisions (explore → validate → full) are made by Claude Code, not by automated scripts or threshold logic. After results come in, the agent reviews every experiment, compares it to the baseline, and makes a judgment call: does this show enough promise to deserve more compute? Thresholds in `meta.json` are guidelines, not automatic gates. The agent can override them in either direction with written reasoning.

> **OPPORTUNITY COST IS REAL.** Every experiment you run is one you don't run. A single GPU running a 4-hour validate means 8 explore ideas you didn't test. Before scaling an experiment up, ask: is this the best use of the next N hours of compute? If you have 5 explore results and 1 GPU, you pick the most promising one — not all of them. Eliminate experiments that are much worse than baseline. Advance experiments that are near or above baseline and whose mechanism has a reason to improve at longer training. Write down why for each decision.

## Pipeline

1. Orient
2. Form hypothesis
3. Design experiment
4. Run explore
5. Evaluate
6. Validate
7. Promote or reject
8. Write knowledge

## Stage Definitions

### Orient

- read current project knowledge
- inspect active runs
- inspect current best
- confirm metric and threshold logic

### Form Hypothesis

Every experiment proposal should state:

- mechanism: what change is being made
- prediction: what metric movement is expected
- reason: why this should work here
- risk: what could invalidate the idea

### Design Experiment

Every experiment must define:

- parent base
- stage
- step budget
- comparison baseline
- success threshold
- rollback condition

### Run Explore

> **HARD RULE: No experiment without a baseline at the same step count.** If no baseline exists at the step count you are about to use, train the unmodified base first and record its metric. This applies to all step counts — standard or custom.

- use cheap explore runs to eliminate weak ideas fast
- keep the control baseline in the same stage whenever possible
- compare within the same stage and budget

### Evaluate

> **You decide, not a script.** Look at each result relative to the baseline at the same step count. Categorize:
> - **Much worse than baseline** (e.g. >2x the gap) → eliminate. The mechanism is broken or harmful.
> - **Somewhat worse** → examine why. Could it recover at longer training? If no reason to believe so, eliminate.
> - **Near baseline** (within noise) → neutral. Advance only if the mechanism has theoretical reason to shine at scale.
> - **Better than baseline** → promising. Strong candidate for validate stage.
> Write your reasoning for each decision. "Rejected because metric was X vs baseline Y" is not enough — explain whether the mechanism itself is worth revisiting.

- determine pass/fail from your own review of results against same-step-count baseline
- separate signal from initialization noise
- record quantitative and qualitative findings
- rank experiments by promise, not just by metric — mechanism quality matters

### Validate

- rerun promising ideas at the next stage or on the latest base
- require confirmation before base promotion

### Promote Or Reject

> **Scaling up = spending compute.** Before promoting an experiment to the next stage, ask: given everything in the current batch, is this the single best use of the GPU for the next N hours? If you have multiple candidates, pick the best one. You are not obligated to advance anything — if nothing looks promising, generate new ideas instead.

- promote only if the run is valid for the current base and stage policy
- reject explicitly and capture why
- when multiple candidates compete for the next stage, rank them and advance only the best
- document opportunity cost reasoning: "chose X over Y because..."

### Write Knowledge

- update wins if the lesson is reusable
- update failures if the lesson closes off a path
- update architecture or training docs if the insight changes future search

## Standard Output Of A Research Cycle

- what was checked
- what finished
- what was promoted
- what was rejected
- what was learned
- what is running now
- what the next batch should test
