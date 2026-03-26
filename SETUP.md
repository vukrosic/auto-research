# Setup

Use this file when installing the kit into a real project repo.

## Preconditions

You need:

- a target codebase where experiments will actually run
- an AI coding agent working inside that repo
- a clear metric with a direction
- a way to launch training or evaluation
- a place where results can be read from logs, JSON, or artifacts

## What To Tell The AI Up Front

Provide these facts early:

- the research objective
- the active repo or subproject being studied
- the primary metric and whether lower or higher is better
- the training or evaluation entrypoint
- how completion is detected
- the compute environment and budget
- whether the AI is operating autonomously or under supervision

## Installation Flow

1. Copy these markdown files into the root of the target repo.
2. Start the AI in that repo.
3. Have it read:
   - `AGENTS.md`
   - `LAB.md`
   - `OPERATING_MODEL.md`
   - `FOLDER_BLUEPRINT.md`
   - `TEMPLATES.md`
4. Use one of the prompt files:
   - `PROMPTS_AUTONOMOUS.md`
   - `PROMPTS_SUPERVISED.md`
5. Let the AI create the working folders and starter files described in `FOLDER_BLUEPRINT.md`.

## Recommended Bootstrap Questions

If the AI cannot infer these safely, it should ask:

1. What goal should this lab optimize for?
2. What metric determines a win?
3. How is a run started?
4. What artifact or log proves completion?
5. What machines, GPUs, or budgets are available?
6. Which decisions require approval?

## Expected First Output In The Target Repo

On a clean install, the AI should create:

- at least one goal mission
- one project config
- starter knowledge files
- a first year plan and current week plan
- a current handoff note
- the experiment folder skeleton

## Secret Handling

Do not store credentials in these template docs.

When the target repo needs machine credentials, API keys, or SSH details, the AI should place them in local-only files that are not committed.

## Recommended Git Policy In The Target Repo

- track policy, goals, plans, knowledge, and reports
- decide deliberately whether to track experiment artifacts
- do not commit credentials
- treat derived dashboards as disposable if they can be regenerated
