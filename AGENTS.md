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

You should:

- create missing lab folders and starter files
- translate the user's mission into durable plans and experiment records
- keep important state in repo files
- run the research loop according to `LAB.md` and `OPERATING_MODEL.md`
- follow `PRODUCT_SPEC.md` when the goal is the first concrete product workflow

## First Session Behavior

If the lab folders do not exist yet:

1. Read `FOLDER_BLUEPRINT.md`.
2. Create the missing folders and starter files in the target repo.
3. Use `TEMPLATES.md` to materialize the first mission, plans, and project config.
4. Ask only for critical missing facts that cannot be inferred safely:
   - research objective
   - metric and direction
   - training or evaluation entrypoint
   - completion or result signal
   - compute constraints

If the folders already exist:

1. Read `state/NOW.md` if present.
2. Read the active goal mission and current plans.
3. Reconcile state against project and experiment records.
4. Continue from the latest durable state.

## Recovery Rule

When context is missing, rebuild it from files in this order:

1. mission
2. year, quarter, month, and week plans
3. project config
4. experiment records
5. knowledge files
6. `state/NOW.md`

If those records do not exist yet, create them from `FOLDER_BLUEPRINT.md` and `TEMPLATES.md`.

## Working Rule

Do not rely on hidden memory when durable files should be updated.
