# Goals

Each subdirectory is a **1-year research goal** set by the human.

## Structure

```
goals/
  <goal-slug>/
    MISSION.md           # Human-written objective (AI cannot modify)
    goal.json            # Optional machine-readable goal metadata
    queue.json           # Optional goal-scoped dispatch queue
    plans/
      year.md            # Annual roadmap (reviewed quarterly)
      q<N>_<YYYY>.md     # Quarter plans (reviewed monthly)
      <YYYY>_<MM>.md     # Month plans (reviewed weekly)
      <YYYY>_w<WW>.md    # Week plans (reviewed daily)
    campaigns/
      c<NN>_<name>.md    # Research campaigns within this goal
    progress.md          # Metric timeline with dates
    resources.md         # GPU and budget allocation
    reports/             # Generated goal reports
```

## Rules

1. **Human creates goals.** AI cannot create, modify, or close a goal's MISSION.md.
2. **AI creates everything else.** Plans, campaigns, progress, resources — all AI-managed.
3. **Goals are isolated.** Each goal has its own plans, campaigns, resource allocation, and optional queue/report metadata.
4. **Goals share infrastructure.** Lab rules (`lab/`), scripts (`scripts/`), and knowledge (`knowledge/`) are shared.
5. **One goal active per GPU at a time.** Don't multiplex goals on the same GPU in the same wave.

## Active Goals

See [`ACTIVE.md`](/root/research/autoresearch/goals/ACTIVE.md) — the live index of active goals (human-maintained).

The system supports any number of concurrent goals. Each is fully self-contained. Add a goal by creating its directory + `MISSION.md` + an entry in `ACTIVE.md`.

## Planning Hierarchy

See `lab/13_PLANNING_HIERARCHY.md` for the full cascade rules (year → quarter → month → week → wave).

## Creating a New Goal

1. Human creates `goals/<slug>/MISSION.md` with objective, scope, constraints
2. AI reads the mission and generates `plans/year.md`
3. AI cascades: year → quarter → month → week
4. AI creates first campaign and begins execution

## Time-Boxed Research Goals

For short research sprints, the goal metadata must distinguish:

- `started_at`: when planning/setup began
- `training_window_seconds`: total runtime budget for experiments
- `training_window_anchor`: how the runtime budget starts
  - `first_dispatch`: budget starts on the first successful training dispatch
  - `goal_started_at`: budget starts at `started_at`
- `training_started_at`: auto-stamped on first dispatch when `training_window_anchor=first_dispatch`
- `training_deadline_at`: auto-derived from `training_started_at + training_window_seconds`
- `report_due_at`: optional explicit report time; otherwise it may be derived from the training deadline

If a human says "research in 5 minutes", the correct contract is not "5 minutes from when the agent began coding". It is:
- planning/setup can happen first
- the experiment runtime budget starts at first dispatch
- all validation, quantization, compression, export, and collection tails count against that runtime budget
- the queue and preflight logic must be based on that runtime budget, not on optimism
