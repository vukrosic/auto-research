# Parameter Golf — AI Research Automation

## What This Is

A competitive ML research repo for the [OpenAI Parameter Golf Challenge](https://github.com/openai/parameter-golf): train the best 16MB language model in <10 min on 8xH100s, scored by bits-per-byte (val_bpb, lower = better).

The repo doubles as an **automated AI research platform** — Claude Code skills (`/fleet`, `/deploy`, `/status`, etc.) orchestrate a fleet of remote GPUs via SSH for continuous experimentation.

## Quick Setup (New Machine)

```bash
git clone <repo_url> && cd parameter-golf
pip install -r requirements.txt
python3 data/cached_challenge_fineweb.py --variant sp1024
```

Or use the `/setup` skill which does all of this plus smoke test.

## Project Structure

```
train_gpt.py                # THE training script (competition artifact)
train_gpt_mlx.py            # Apple Silicon variant
requirements.txt             # Python dependencies
KNOWLEDGE.md                 # Persistent research memory (proven facts, failed approaches)
│
├── data/                    # Dataset download scripts + tokenizers
├── records/                 # Official leaderboard submissions
├── utils/                   # Plotting, param checking
│
├── infra/                   # GPU orchestration & experiment runners
│   ├── run_experiment.sh    # Run single experiment with env var overrides
│   ├── run_queue.sh         # Run queue file of experiments sequentially
│   ├── gpu_creds.sh         # SSH credentials (GITIGNORED)
│   ├── gpu_scheduler.py     # Daemon: watches queues/active.txt, assigns to idle GPUs
│   ├── watch_all_gpus.sh    # Fleet monitoring (utilization, temp, cost, progress)
│   ├── gpu_sync_cron.sh     # 2-hourly git sync across all GPUs
│   └── export_experiment_artifacts.py
│
├── research/                # All research content
│   ├── ideas/               # Architecture ideas (Tier 1-3)
│   ├── papers/              # Literature reviews
│   ├── findings/            # Experiment analysis documents
│   └── figures/             # Plots and visualizations
│
├── screens/                 # Tiered screen configs (one .py file per topic)
│   └── archive/             # Completed screens
│
├── queues/                  # Experiment queue management
│   ├── active.txt           # THE current queue (what gets run next)
│   └── archive/             # Completed/old queue files
│
├── results/                 # Experiment results (staged by pipeline phase)
│   ├── explore/             # 500-step screening (cheap, high volume)
│   ├── validate/            # 2000-5000 step validation (confirm winners)
│   ├── full/                # 13000+ step full runs (pre-submission)
│   └── misc/                # One-offs, probes, smoke tests
│
├── .claude/skills/          # Claude Code skills for GPU orchestration
└── logs/                    # Training logs (gitignored)
```

## GPU Fleet Architecture

GPUs are managed via SSH through a proxy host. Credentials live in `infra/gpu_creds.sh` (gitignored) with this pattern:
```bash
HOST="proxy.host.example"
GPU_<NAME>_PORT=<port>
GPU_<NAME>_PASS="<password>"
```

Skills auto-discover GPUs by parsing `gpu_creds.sh` via `.claude/skills/fleet/scripts/discover_gpus.sh`.

### Fleet Operations (Skills)

| Skill | Purpose |
|-------|---------|
| `/setup` | Set up a fresh machine (deps, data, smoke test) |
| `/fleet` | Show all GPU status (utilization, temp, experiment, cost) |
| `/deploy` | Send experiments to GPUs (queue file or single) |
| `/status` | Detailed training progress (step, loss, ETA) |
| `/collect` | Pull results from all GPUs immediately |
| `/compare` | Rank experiments by val_bpb, diff configs |
| `/cost` | Budget report ($40 limit, burn rate, per-GPU) |
| `/kill-exp` | Stop running experiments |
| `/add-gpu` | Register a new GPU instance |
| `/wave` | **Research loop orchestrator** — status, plan, approve, results, pivot |
| `/post` | Draft X/Twitter posts from experiment results |
| `/research` | Legacy research pipeline (prefer `/wave`) |

## Running Experiments

### Step 0: Tiered screen (local, free — always do this first)

Before spending any GPU time, screen ideas locally in seconds:

```bash
# 1. Create a screen config (copy template, fill in CONFIGS list)
cp screens/template.py screens/<topic>.py

# 2. Run the screen
python3 infra/tiered_screen.py --screen screens/<topic>.py [--ladder quick|standard|thorough]

# 3. Read the report
cat results/tiered_screen_<topic>_<date>.md
```

Only candidates that beat the baseline across **both stages** advance to a GPU queue.
Ladder presets: `quick` (1→2 steps, seconds), `standard` (3→6 steps, minutes), `thorough` (10→20 steps).

### Single experiment (GPU)
```bash
infra/run_experiment.sh <name> <steps>
# With overrides:
MATRIX_LR=0.08 NUM_LAYERS=12 infra/run_experiment.sh my_test 200
```

### Queue of experiments
```bash
# Queue file format: <name> <steps> [ENV=val ...]
bash infra/run_queue.sh queues/active.txt
```

### Key env vars for train_gpt.py
`MATRIX_LR`, `SCALAR_LR`, `EMBED_LR`, `NUM_LAYERS`, `MODEL_DIM`, `NUM_HEADS`, `NUM_KV_HEADS`, `MLP_MULT`, `WARMDOWN_ITERS`, `WARMUP_STEPS`, `LOGIT_SOFTCAP`, `QK_GAIN_INIT`, `ROPE_BASE`, `MUON_MOMENTUM`, `GRAD_CLIP_NORM`, `TIED_EMBED_LR`, `TIED_EMBED_INIT_STD`

## Research Pipeline

See `research/PIPELINE.md` for the full pipeline definition. The loop:

```
/wave           → Check status, get suggested next action
/wave plan      → Run debate (direction/scale/pivot) → generate wave plan
/wave approve   → Lock plan, activate queue
/deploy         → Send to GPUs
/wave results   → Collect, compare, gate check, draft X post
```

Three debate types select different agent combinations:
- **Direction** (Architect + Explorer + Skeptic): New ideas to explore
- **Scale** (Architect + Challenger + Optimizer): Validate/scale winners
- **Pivot** (all 5 agents): Strategic reassessment when stuck

| Stage | Steps | Time (reference single-GPU) | Purpose | Advance if |
|-------|------:|-------------|---------|------------|
| Explore | 500 | ~28 min | Screen many ideas fast | >0.01 BPB improvement |
| Validate-light | 2000 | ~1.8 hr | Quick confirmation | >0.005 BPB on 2+ seeds |
| Validate-full | 4000 | ~3.7 hr | Strong confirmation | >0.005 BPB on 2+ seeds |
| Full | 13780 | ~12.7 hr | Pre-submission | Beats 1.2244 BPB |

Results are automatically sorted into `results/explore/`, `results/validate/`, `results/full/` based on step count.

## Conventions

- **val_bpb** is the only metric that matters for the competition
- **KNOWLEDGE.md** — Read this first. Contains proven facts, failed approaches, open questions
- **FORBIDDEN**: LR tuning alone is not research. Focus on architecture/mechanism changes (see `infra/FORBIDDEN.md`)
- Experiment names use snake_case: `act_leaky05_gradfloor_2000`
- Queue files go in `queues/`, one active queue at a time
- Work directly on `main`; submit PRs upstream from there
- Budget: $40 total across all GPUs, tracked via `/cost` skill

## Data

Download with: `python3 data/cached_challenge_fineweb.py --variant sp1024`
- Default: full val split + 80 train shards (8B tokens)
- Smaller: add `--train-shards 1` for local smoke tests
- Data lands in `data/datasets/fineweb10B_sp1024/` and `data/tokenizers/`
