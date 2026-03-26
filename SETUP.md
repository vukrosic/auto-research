# Autoresearch — First-Time Setup

**Read this file when setting up autoresearch for the first time.** Walk through each section with the user, ask the questions marked with `ASK:`, and configure accordingly.

---

## Prerequisites

Before starting, confirm:
- [ ] SSH access to at least one GPU machine (with `sshpass` and `rsync` installed locally)
- [ ] A target research repo (the codebase you want to run experiments on)
- [ ] Claude Code (or compatible AI agent) as the operator

---

## Step 1: GPU Credentials

Copy the example config and fill in real values:

```bash
cp scripts/gpu_config.example.sh scripts/gpu_config.sh
```

Edit `scripts/gpu_config.sh` with your GPU host, port, user, and password. This file is gitignored and must never be committed.

> **ASK:** What GPU(s) do you have access to? I need: hostname, SSH port, username, and password for each.

---

## Step 2: Create a Project Config

Create `projects/<name>.json` for your research repo. See `RESEARCH.md` for the full schema.

> **ASK:** What repo do you want to research on? I need:
> - Repo path (local)
> - Primary metric name and direction (lower/higher is better)
> - Target metric value (the goal to beat)
> - How to run training (command, log format, result location)

---

## Step 3: Initialize the Base

```bash
scripts/init_base.sh <project_name>
```

This copies the repo into `experiments/<project>/base/` as the starting point for all experiments.

---

## Step 4: Experiment Storage Policy

Experiments (snapshots, results, logs) accumulate in `experiments/` and can grow large.

> **ASK:** Do you want to commit experiments to git?
>
> - **No (recommended)** — Experiments are local-only. They contain large code copies, logs, and binary artifacts. Gitignoring them keeps the repo clean and fast. You can always back them up separately.
> - **Yes (not recommended)** — Useful if you want full experiment history in version control, but the repo will grow quickly. Consider using Git LFS or a separate branch.

Based on the answer, configure `.gitignore`:

**If No (recommended):**
Experiments directory ships empty with a README. All runtime data stays local.
```
# Already configured — experiments/<project>/ contents are gitignored
# Only experiments/README.md and experiments/.gitignore are tracked
```

**If Yes:**
Remove the experiments exclusion from `.gitignore`. Consider adding size limits or using a dedicated branch.

---

## Step 5: State and Logs

The `state/`, `logs/`, and `reports/` directories contain runtime output regenerated each session.

These are **gitignored by default**. They are derived from experiment snapshots and should not be committed. If you want to preserve session reports, copy them elsewhere.

---

## Step 6: Knowledge Files

`knowledge/<project>/` stores accumulated research findings (what worked, what failed, architecture insights).

These **are tracked in git** — they are the durable research output of the system and valuable to share.

---

## Step 7: Goals and Plans

Goals in `goals/` define what you're trying to achieve. Plans cascade from year to week level.

> **ASK:** What is your research goal? I'll create `goals/<slug>/MISSION.md` with your objective.

---

## Step 8: Verify Setup

Run these checks:

```bash
# Test GPU connectivity
scripts/gpu_status.sh

# Verify base is initialized
ls experiments/<project>/base/

# Verify project config
cat projects/<project>.json
```

---

## Step 9: Start Researching

Read `AGENTS.md` for the full agent onboarding, then follow the research cycle in `RESEARCH.md`.

---

## Configuration Summary

| What | Where | Tracked in git? |
|------|-------|-----------------|
| GPU credentials | `scripts/gpu_config.sh` | No (gitignored) |
| Project config | `projects/<name>.json` | Yes |
| Experiment base | `experiments/<project>/base/` | No (gitignored) |
| Experiment snapshots | `experiments/<project>/snapshots/` | No (gitignored) |
| Knowledge | `knowledge/<project>/` | Yes |
| Goals & missions | `goals/<slug>/` | Yes |
| Plans | `goals/<slug>/plans/` | Yes |
| State files | `state/` | No (gitignored) |
| Lab policies | `lab/` | Yes |
| Scripts | `scripts/` | Yes (except gpu_config.sh) |
