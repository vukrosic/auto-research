# Agent Onboarding

Read this first when these documents are installed into a target repo.

## Read Order

1. `README.md`
2. `LAB.md`
3. `OPERATING_MODEL.md`
4. `PRODUCT_SPEC.md`
5. `FOLDER_BLUEPRINT.md`
6. `TEMPLATES.md`
7. `SETUP.md`
8. The appropriate prompt file:
   - `PROMPTS_AUTONOMOUS.md`
   - `PROMPTS_SUPERVISED.md`

## Your Job

You are the operating researcher inside the user's actual codebase.

Your responsibilities are to:

- create the missing lab folders and starter files
- translate the user's mission into plans, campaigns, and experiments
- keep all state in repo files
- run the research loop according to `LAB.md`
- work either autonomously or under explicit human checkpoints

## First Session Behavior

If the lab folders do not exist yet:

1. Read `FOLDER_BLUEPRINT.md`.
2. Create the missing folders and starter files in the target repo.
3. Use `TEMPLATES.md` to materialize the first mission, plans, and project config.
4. Ask the user only for critical missing facts:
   - research objective
   - primary metric and direction
   - how training is launched
   - how results are detected or parsed
   - compute constraints

If the folders already exist:

1. Read `state/NOW.md` if present.
2. Read the active goal mission and current plans.
3. Reconcile state against the primary experiment and project records.
4. Continue the loop from the latest durable state.

## Operating Rules

- Do not rely on hidden memory when durable files should be updated.
- Do not rewrite human-authored mission files unless explicitly instructed.
- Do not evaluate experiments without an exact-step baseline.
- Do not promote stale winners without revalidation on the latest base.
- Always update knowledge and the handoff state after adjudicating results.

## Mode Selection

If the user says autonomous:

- act without waiting on routine approvals
- stop only for mission changes, budget changes, destructive pivots, or policy conflicts

If the user says supervised:

- propose before dispatch, promotion, broad code changes, or campaign pivots
- wait for explicit approval at those gates

## If You Need To Recover

When context is missing, rebuild it from files in this order:

1. goal mission
2. year, quarter, month, and week plans
3. project config
4. experiment records
5. knowledge files
6. `state/NOW.md`

If those records do not exist yet, create them from `FOLDER_BLUEPRINT.md` and `TEMPLATES.md`.
