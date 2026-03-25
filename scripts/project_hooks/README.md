# Project Hooks

Project hooks are optional per-project overrides for lifecycle steps that the generic
runtime cannot express cleanly through `projects/<name>.json` alone.

If a hook is configured, the generic script delegates to it with canonical arguments:

- `dispatch`: `<project> <experiment> <gpu> [steps]`
- `check`: `<project> <experiment>`
- `collect`: `<project> <experiment>`
- `new_experiment`: `<project> <experiment>`
- `init_base`: `<project> [repo_path]`
- `promote`: `<project> <experiment>`
- `calibrate`: `<project> <gpu> [stage]`

Configure them in project JSON like:

```json
{
  "hooks": {
    "collect": "scripts/project_hooks/my_project/collect.sh"
  }
}
```

Hook paths may be absolute or relative to the autoresearch root.

Guideline:

- prefer the generic config-only path first
- add hooks only for the steps that truly need custom behavior
- keep hooks thin and project-specific
