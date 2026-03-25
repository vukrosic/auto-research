# Universalizing `autoresearch` Without Rewriting Repos

## Short Answer

Yes, `autoresearch` can be made universal with little to no required changes to target repos.

The right approach is:

1. Keep `autoresearch` as the control plane.
2. Move repo-specific behavior behind per-project adapters.
3. Keep upstream repos mostly untouched.
4. Migrate additively so the current parameter-golf flow keeps working.

## What Needs To Change

### 1. Stop Assuming There Is Only One Project

Current problem:

- `scripts/autonomous_lab.py` uses global paths like `experiments/base`, `experiments/snapshots`, and `experiments/current_best.json`.
- It also picks the first file in `projects/*.json` as the active project.

Required change:

- Introduce explicit `goal -> project` selection.
- Namespace experiment state by project.

Recommended structure:

```text
experiments/
  parameter-golf/
    base/
    snapshots/
    current_best.json
    base_id.txt
  vjepa2/
    base/
    snapshots/
    current_best.json
    base_id.txt

knowledge/
  parameter-golf/
  vjepa2/
```

### 2. Replace Hardcoded Training Assumptions With Project Adapters

Current problem:

- `dispatch.sh` assumes `infra/run_experiment.sh`.
- `check_experiment.sh` and `gpu_status.sh` assume `train_gpt.py`.
- `collect_result.sh` assumes `val_bpb` and a parameter-golf-style log layout.
- `calibrate_baselines.sh` assumes the same run interface.

Required change:

- Introduce an adapter contract per project.

Suggested adapter responsibilities:

- `init_base`
- `create_snapshot`
- `dispatch`
- `check`
- `collect`
- `calibrate`
- `parse_result`
- `estimate_duration`

Suggested locations:

```text
scripts/
  adapters/
    parameter_golf/
      adapter.py
    vjepa2/
      adapter.py
  lib/
    project_runtime.py
```

### 3. Generalize Metrics and Promotion Logic

Current problem:

- Adjudication assumes a lower-is-better BPB metric and reads `val_bpb` or `val_bpb_quant`.

Required change:

- Project config must define:
  - primary metric key
  - metric direction: `min` or `max`
  - optional promoted metric key
  - stage thresholds

Suggested project manifest fields:

```json
{
  "name": "vjepa2",
  "repo_path": "/root/research/vjepa2",
  "metric": {
    "key": "avg_loss_last_30_mean",
    "direction": "min"
  },
  "stages": {
    "explore": {"steps": 300, "threshold": 0.01},
    "validate": {"steps": 900, "threshold": 0.005}
  },
  "adapter": "vjepa2"
}
```

### 4. Separate Goal Metadata From Human Mission Text

Current problem:

- The system currently relies on `MISSION.md` for human intent, but machine-readable goal/project linkage is weak.

Required change:

- Keep `MISSION.md` human-owned.
- Add an AI-managed machine file per goal, for example:

```text
goals/<goal>/goal.json
```

Suggested fields:

```json
{
  "project": "vjepa2",
  "metric_key": "avg_loss_last_30_mean",
  "metric_direction": "min"
}
```

This avoids parsing free-form markdown to determine which repo a goal uses.

### 5. Keep Repo Integration Thin

Preferred default:

- No repo changes required.
- Adapters in `autoresearch` call the repo's existing entrypoints.

Allowed repo changes only if unavoidable:

1. Add a thin launch wrapper.
2. Add a machine-readable `summary.json` output.
3. Add a smoke-test mode or small-step override.
4. Add a stable output directory contract.

Avoid changing model code purely for orchestration.

## Will This Break The Current Training?

## Short Answer

Not if the migration is done additively.

## Important Detail

An already running remote training process will not stop just because local orchestration scripts change.

The real risk is breaking the management path for the next actions:

- checking status
- collecting results
- dispatching the next queued run
- reading old snapshot locations

## Safe Migration Rules

1. Do not remove or rename the current parameter-golf paths while its queue is active.
2. Do not change the old shell interface first. Wrap it.
3. Make the new universal runtime opt-in at first.
4. Keep a compatibility adapter for parameter-golf that preserves today's behavior.
5. Do not migrate existing snapshots until the current wave and queue are drained.

## Unsafe Changes Right Now

These would risk the current flow if done immediately:

- moving `experiments/base` to a new location without compatibility
- changing `dispatch.sh`, `check_experiment.sh`, or `collect_result.sh` in-place without preserving old behavior
- changing status/result schemas before old snapshots are collected

## Universal Design With Minimal Repo Changes

## Control Plane vs Execution Plane

Use this split:

- `autoresearch` = planning, queueing, promotion, bookkeeping, GPU orchestration
- repo adapter = how to run this specific codebase
- target repo = mostly unchanged research code

## Adapter Contract

Each adapter should expose a stable interface to the control plane:

```text
prepare_base(project, repo_path, dst)
create_snapshot(project, src_base, dst_snapshot, meta)
dispatch(project, snapshot, gpu)
check(project, snapshot, gpu)
collect(project, snapshot, gpu)
calibrate(project, gpu, stage)
```

The control plane should not know whether the repo uses:

- `infra/run_experiment.sh`
- `python -m app.main`
- `torchrun`
- `submitit`
- custom log files
- custom metrics

That belongs in the adapter only.

## Zero-Change Path For Most Repos

For many repos, the adapter can live entirely in `autoresearch` and just call the repo's existing commands.

Examples:

- Parameter-golf adapter wraps `infra/run_experiment.sh`
- V-JEPA2 adapter wraps `python run_experiments_v2.py ...` or `python -m app.main ...`

## Minimal Repo Changes If Needed

If a repo is difficult to automate cleanly, prefer tiny repo-local changes like:

1. `scripts/run_smoke.sh`
2. `scripts/export_result.py`
3. consistent `results/<run>/summary.json`

These are acceptable because they improve machine operability without changing the research code itself.

## Recommended Migration Plan

### Phase 0: Freeze Current Parameter-Golf Layout

Goal:

- Keep the current system stable while building the universal path.

Actions:

1. Treat the current parameter-golf flow as legacy-but-live.
2. Do not move existing snapshots or base directories.
3. Do not break current shell commands.

### Phase 1: Add a Universal Runtime Layer

Goal:

- Introduce project selection and adapters without changing current behavior.

Files to add:

- `scripts/lib/project_runtime.py`
- `scripts/adapters/parameter_golf/adapter.py`
- `scripts/adapters/vjepa2/adapter.py`

Files to change:

- `scripts/autonomous_lab.py`

Changes:

1. Load a specific project explicitly.
2. Resolve project-scoped experiment paths.
3. Route dispatch/check/collect/calibrate through the selected adapter.

### Phase 2: Keep Old Shell Commands As Compatibility Wrappers

Goal:

- Preserve the current user and automation entrypoints.

Files to change:

- `scripts/dispatch.sh`
- `scripts/check_experiment.sh`
- `scripts/collect_result.sh`
- `scripts/calibrate_baselines.sh`
- `scripts/init_base.sh`

Changes:

- These scripts become thin wrappers around the runtime layer.
- Default behavior remains parameter-golf unless `--project` is provided.

Example:

```bash
bash scripts/dispatch.sh --project parameter-golf explore_6e_d352 novita-rtx3090
bash scripts/dispatch.sh --project vjepa2 explore_deeper_predictor novita-rtx3090
```

### Phase 3: Namespace State By Project

Goal:

- Remove the global singleton assumption.

Files to change:

- `scripts/autonomous_lab.py`
- state generators
- any code reading `experiments/current_best.json`

Changes:

- move to `experiments/<project>/...`
- optionally generate `state/<project>/...` plus shared summary views

### Phase 4: Add Machine-Readable Goal Metadata

Goal:

- Make goal selection and project binding explicit.

Files to add:

- `goals/<goal>/goal.json`

Changes:

- control plane resolves active goal, then project, then adapter

### Phase 5: Onboard New Projects One At A Time

Goal:

- Keep onboarding cheap and predictable.

For each new repo:

1. create `projects/<name>.json`
2. add adapter
3. run smoke test
4. confirm result parsing
5. only then create live research waves

## Concrete File-Level Suggestions

### Change First

- `/root/research/autoresearch/scripts/autonomous_lab.py`
- `/root/research/autoresearch/scripts/dispatch.sh`
- `/root/research/autoresearch/scripts/check_experiment.sh`
- `/root/research/autoresearch/scripts/collect_result.sh`
- `/root/research/autoresearch/scripts/calibrate_baselines.sh`
- `/root/research/autoresearch/scripts/init_base.sh`

### Add

- `/root/research/autoresearch/scripts/lib/project_runtime.py`
- `/root/research/autoresearch/scripts/adapters/parameter_golf/adapter.py`
- `/root/research/autoresearch/scripts/adapters/vjepa2/adapter.py`
- `/root/research/autoresearch/projects/vjepa2.json`
- `goals/<goal>/goal.json`

### Migrate Later

- `/root/research/autoresearch/experiments/base`
- `/root/research/autoresearch/experiments/snapshots`
- `/root/research/autoresearch/experiments/current_best.json`

These should only be migrated after compatibility wrappers exist.

## My Recommendation

The best sequence is:

1. build the universal adapter layer first
2. preserve parameter-golf as adapter #1
3. keep current commands as wrappers
4. onboard `vjepa2` as adapter #2
5. only then start a JEPA research campaign

This gives you a system that is:

- reusable across repos
- mostly non-invasive to research codebases
- safe for the current parameter-golf setup
- extensible without another rewrite later

## Practical Rule Of Thumb

If a new repo requires more than:

- one project manifest
- one adapter
- optional tiny wrapper scripts

then the lab is still too repo-specific and needs more work in `autoresearch`, not in the repo.
