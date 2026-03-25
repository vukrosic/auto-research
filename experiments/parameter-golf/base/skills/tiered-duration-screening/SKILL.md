---
name: tiered-screen
description: Screen architecture variants with a fast step-ladder. Eliminate losers early, scale only survivors. Writes a markdown report with per-stage tables.
---

# Tiered Screen

## What This Does

Runs many architecture variants cheaply in a single process (no per-run startup cost), promotes winners to longer runs, drops losers early. Writes `results/tiered_screen_<topic>_<date>.md` with three tables.

**This is the required first step before any GPU experiment.**

## How to Run

```bash
# 1. Create a screen config
cp screens/template.py screens/<topic>.py
# Edit CONFIGS list — first entry must be baseline with overrides={}

# 2. Run
python3 infra/tiered_screen.py --screen screens/<topic>.py --ladder quick

# 3. Read report
cat results/tiered_screen_<topic>_<date>.md
```

Ladder options:

| Preset | Stage 1 | Stage 2 | Candidates | Promote |
|---|---:|---:|---:|---:|
| `quick` | 1 step | 2 steps | any | top 2 |
| `standard` | 3 steps | 6 steps | any | top 3 |
| `thorough` | 10 steps | 20 steps | any | top 5 |

## Screen Config Format

`screens/<topic>.py` must define a `CONFIGS` list:

```python
WHY = "One sentence: why these candidates."  # optional, shown in report header

CONFIGS = [
    ("baseline",    "Control — no changes.",                    {}),
    ("my_variant",  "What changes and what hypothesis it tests.", {"mlp_act": "swiglu"}),
]
```

- First entry is always the baseline (`overrides={}`)
- `desc` is one sentence explaining what the change tests
- `overrides` keys must match `FULL` dict in `infra/tiered_screen.py`
- Finished screen files go in `screens/archive/`

## Promotion Rule

Sort by `delta_loss = candidate_loss - baseline_loss` (lower is better).
Promote only candidates that beat the baseline. If a candidate led at stage 1 but flipped at stage 2, drop it — that's initialization noise, not signal.

## Report Output

Always written to `results/tiered_screen_<topic>_<date>.md`. Contains:
- Header: model, ladder, why these candidates
- Stage 1 table with decision column
- Stage 2 table with decision column
- "What happened" conclusion: who survived, who flipped, next action

## What Claude Should Do

1. If user has candidates in mind: write `screens/<topic>.py` with them, run the screen.
2. If user wants Claude to pick: choose from KNOWLEDGE.md proven facts + prior screen finalists. Prefer changes with clear architectural motivation over LR tuning.
3. After the run: read the report, summarize finalists in plain language, recommend whether to promote to a 500-step explore queue or run another screen with a different direction.
4. Move finished screen file to `screens/archive/<topic>.py`.
