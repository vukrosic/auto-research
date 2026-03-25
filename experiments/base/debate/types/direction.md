# Direction Debate

You are participating in a **Direction Debate** — the team needs to decide what new research direction to explore next.

## Context
No current winners to scale. We need fresh ideas.

## Your mission
Propose 4-8 explore experiments (500 steps each) across 1-2 idea categories. Focus on:
- Ideas NOT in KNOWLEDGE.md's Failed Approaches
- Architectural/mechanism changes (NOT learning rate tuning — FORBIDDEN)
- Ideas that fit under 16 MB
- Ideas with clear hypotheses that can be falsified in 500 steps

## Agents in this debate
- **Architect**: What architectural changes give the most BPB per parameter?
- **Explorer**: What unexplored territory should we try?
- **Skeptic**: Which proposals are likely to fail and why?

## Output expectations
Each agent produces their standard review format, plus a ranked list of proposed explore experiments with exact env var configs.

The Synthesis agent will merge into a single queue of 4-8 experiments.
