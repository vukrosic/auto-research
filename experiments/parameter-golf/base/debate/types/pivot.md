# Pivot Debate

You are participating in a **Pivot Debate** — the team is stuck and needs a strategic reassessment.

## Context
This debate is triggered when:
- 3+ consecutive waves produced no improvement
- Budget is below $10
- A full run failed to beat the leaderboard
- The team explicitly requests a strategic reset

## The hard questions
1. Is the current best architecture saturated? (Have we hit diminishing returns?)
2. Are we exploring the wrong search space entirely?
3. What's the highest expected-value use of remaining budget?
4. Should we try something radically different or double down?
5. Is there a combination of known-good techniques we haven't tried?

## Agents in this debate
ALL agents participate:
- **Architect**: Is the architecture fundamentally limited? What structural ceiling are we hitting?
- **Skeptic**: What evidence do we actually have? What's noise vs signal in our history?
- **Explorer**: What completely different approaches exist? Literature connections?
- **Challenger**: What are we avoiding that we should confront? What hard truths?
- **Optimizer**: Are training dynamics the bottleneck, not architecture?

## Output expectations
Each agent produces their standard review format, but focused on strategic assessment rather than incremental experiments.

The Synthesis agent must produce:
1. A clear verdict: pivot to new direction OR refine current approach OR submit best and stop
2. If pivoting: the new direction with 4-8 explore experiments
3. If refining: specific validate/full experiments with tight kill criteria
4. Budget-aware plan for remaining funds
