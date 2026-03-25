# Goals

Each subdirectory is a **1-year research goal** set by the human.

## Structure

```
goals/
  <goal-slug>/
    MISSION.md           # Human-written objective (AI cannot modify)
    plans/
      year.md            # Annual roadmap (reviewed quarterly)
      q<N>_<YYYY>.md     # Quarter plans (reviewed monthly)
      <YYYY>_<MM>.md     # Month plans (reviewed weekly)
      <YYYY>_w<WW>.md    # Week plans (reviewed daily)
    campaigns/
      c<NN>_<name>.md    # Research campaigns within this goal
    progress.md          # Metric timeline with dates
    resources.md         # GPU and budget allocation
```

## Rules

1. **Human creates goals.** AI cannot create, modify, or close a goal's MISSION.md.
2. **AI creates everything else.** Plans, campaigns, progress, resources — all AI-managed.
3. **Goals are isolated.** Each goal has its own plans, campaigns, and resource allocation.
4. **Goals share infrastructure.** Lab rules (`lab/`), scripts (`scripts/`), and knowledge (`knowledge/`) are shared.
5. **One goal active per GPU at a time.** Don't multiplex goals on the same GPU in the same wave.

## Active Goals

| Goal | Mission | Current Best | Target | Status |
|------|---------|-------------|--------|--------|
| surpass_transformer_2026 | Beat transformer baseline on parameter-golf | 1.3564 BPB | < 1.2244 BPB | Active |

## Planning Hierarchy

See `lab/13_PLANNING_HIERARCHY.md` for the full cascade rules (year → quarter → month → week → wave).

## Creating a New Goal

1. Human creates `goals/<slug>/MISSION.md` with objective, scope, constraints
2. AI reads the mission and generates `plans/year.md`
3. AI cascades: year → quarter → month → week
4. AI creates first campaign and begins execution
