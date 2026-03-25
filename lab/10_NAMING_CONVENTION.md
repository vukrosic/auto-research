# Experiment Naming Convention

Policy version: 1.0
Effective: 2026-03-24
Last updated: 2026-03-24

## Format

```
<stage>_<topic>_<mechanism>_<shortid>
```

## Examples

- `explore_moe_width_7ac2`
- `validate_bn128_untied_f31d`
- `full_residual_gate_91bf`
- `explore_lr_warmup_a4e1`

## Rules

- Lowercase only
- Underscores only (no hyphens, no spaces)
- Stage must be one of: `explore`, `validate`, `full`
- Topic should be one or two words identifying the area (e.g., `moe`, `lr`, `bn128`, `residual`)
- Mechanism should be one or two words identifying the specific change
- Short ID is 4 hex characters, globally unique within the project
- Total name should be short enough for filenames and remote log directories

## Generating The Short ID

Use the first 4 characters of a random hex string. Check for collisions against existing snapshot directory names before creating.

## Why This Convention

- Stage in the name makes glob patterns like `explore_*` and `validate_*` useful
- Topic and mechanism make the name human-readable without opening `meta.json`
- Short ID prevents collisions when the same mechanism is tested twice
- Consistent format prevents tooling from breaking on irregular names
