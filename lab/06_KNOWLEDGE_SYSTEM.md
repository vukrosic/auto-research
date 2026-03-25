# Knowledge System

Policy version: 1.0
Effective: 2026-03-24
Last updated: 2026-03-24

## Purpose

The knowledge system is the lab's long-term memory.

Its job is to reduce repeated mistakes and make good ideas compound.

## Knowledge Layers

### Project Knowledge

Stored under `knowledge/<project>/`.

Recommended files:

- `architecture.md`
- `training.md`
- `failures.md`
- `wins.md`
- `open_questions.md`

### Repo-Level Knowledge

Stored in project repos when the knowledge is tightly coupled to code, such as `experiments/base/KNOWLEDGE.md`.

### Lab Policy Knowledge

Stored under `lab/` and used across all projects.

## Writing Rules

- write claims as durable lessons, not diary entries
- attach numbers whenever possible
- distinguish observed result from interpretation
- mark uncertain conclusions as tentative
- delete or rewrite claims that no longer survive better evidence

## Recommended Entry Format

For any important learning, capture:

- claim
- evidence
- confidence
- implication for future runs

## Example

Claim: untied factorized embeddings help at this parameter budget.

Evidence: `bn128 untied` improved BPB by `0.031` in a validated comparison.

Confidence: medium.

Implication: include untied factored embeddings in future architecture combinations; avoid tied variants unless testing a new mechanism.

## Anti-Patterns

- dumping raw logs into knowledge docs
- recording conclusions without metrics
- mixing temporary run notes with stable lessons
- keeping contradictory claims without resolving them
