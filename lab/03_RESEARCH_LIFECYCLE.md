# Research Lifecycle

## Pipeline

1. Orient
2. Form hypothesis
3. Design experiment
4. Run screen
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

### Run Screen

- use cheap screening to eliminate weak ideas fast
- keep the control baseline in the same screen whenever possible
- compare within the same stage and budget

### Evaluate

- determine pass/fail from pre-written criteria
- separate signal from initialization noise
- record quantitative and qualitative findings

### Validate

- rerun promising ideas at the next stage or on the latest base
- require confirmation before base promotion

### Promote Or Reject

- promote only if the run is valid for the current base and stage policy
- reject explicitly and capture why

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
