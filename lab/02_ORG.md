# Org Structure

## Functional Roles

Even if one person runs the system, the lab should think in roles.

### Research Director

- chooses project priorities
- sets success criteria
- approves changes to lab policy
- decides when a project changes strategy

### Principal Investigator

- defines hypotheses worth testing
- interprets results
- updates research direction from evidence

### Research Engineer

- implements model, training, data, and eval changes
- keeps experiments reproducible
- writes clear experiment metadata

### Compute Operator

- tracks GPU availability and utilization
- dispatches jobs
- detects failed or stalled runs

### Knowledge Manager

- updates wins, failures, architecture, and training notes
- ensures claims in docs match actual results
- keeps the state of the lab legible

## Current Mapping

In the current system, Claude Code may act as:

- researcher
- engineer
- operator
- analyst

The human acts as:

- lab director
- final policy owner
- escalation point when the system is ambiguous or unsafe

## Decision Rights

- Lab policy: human-owned
- Project strategy: human-owned, Claude-informed
- Experiment generation: Claude-owned within policy
- Dispatch and collection: Claude-owned
- Promotion to base: should be policy-driven and mechanically enforced

## Failure Mode To Avoid

Do not let a single agent switch silently between "idea generator" and "promotion authority" without explicit written rules.
