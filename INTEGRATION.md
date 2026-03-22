# Auto-Research ↔ Parameter-Golf Integration Plan

## Overview

`parameter-golf` is the research engine. `auto-research` is the platform shell. Users interact with the platform; the platform dispatches work to the engine running on GPU machines.

---

## Architecture

```
[User Browser]
     │  HTTP (cookie auth)
     ▼
[auto-research FastAPI]  ─── SQLite DB (users, experiments, GPUs, competitions)
     │  SSH via sshpass
     ▼
[GPU Machine]
  /root/parameter-golf/
  ├── train_gpt.py          ← actual training script
  ├── infra/run_experiment.sh  ← invoked per experiment
  └── results/explore|validate|full/  ← output files
```

---

## What Is For Users

| Feature | How It Works |
|---------|-------------|
| **AI Research Chat** | User asks questions → `POST /chat/` → Novita API (mimo-v2-flash) with research context prompt |
| **Submit Experiment** | User fills form (name, stage, config overrides) → `POST /experiments/` → queued in DB |
| **View Results** | User sees val_bpb table → pulled from DB (populated by result collection from GPUs) |
| **Competitions** | User sees active competitions, submits experiments to compete, views leaderboard |
| **Profile** | View tier, usage (explore/validate/full used vs limit), API key |
| **Pricing** | Shows 3 tiers (Starter/Researcher/Pro), links to Skool community |

Users never touch the GPU fleet directly. They submit work; it runs asynchronously.

---

## What Is For Admin (Me)

| Feature | How It Works |
|---------|-------------|
| **GPU Fleet** | Add GPUs by pasting SSH command, test connectivity, run terminal commands, monitor utilization |
| **Admin Dashboard** | MRR estimate, user counts by tier, experiment stats, open support tickets |
| **User Management** | Create users after Skool payment, change tiers, reset usage, disable accounts |
| **Competition Management** | Create competitions with sponsor/prize, set metric and max steps |

---

## Current Integration Gap: Experiment Dispatch

Right now experiments are queued in the DB but **not dispatched to GPUs automatically**. Here's the plan to close this gap:

### Phase 1 — Manual Dispatch (Now)

Admin uses `/fleet/{id}/run-experiment` to manually run a queued experiment on a specific GPU.

The GPU machine must have `parameter-golf` cloned at `/root/parameter-golf` with data downloaded.

### Phase 2 — Scheduler (Next)

Add a background task to `auto-research` that:
1. Polls DB every 30s for queued experiments
2. Finds idle GPUs
3. SSHes to GPU and runs: `cd /root/parameter-golf && <OVERRIDES> bash infra/run_experiment.sh <name> <steps>`
4. Updates experiment status to `running`, stores GPU assignment

```python
# engine/scheduler.py (to be built)
async def dispatch_loop():
    while True:
        queued = db.query(Experiment).filter(status='queued').order_by(priority)
        idle_gpus = db.query(GPU).filter(status='idle')
        for exp, gpu in zip(queued, idle_gpus):
            ssh_exec(gpu, build_command(exp))
            exp.status = 'running'; exp.gpu_name = gpu.name
        await asyncio.sleep(30)
```

### Phase 3 — Result Collection

After experiment completes on GPU, results land in `/root/parameter-golf/results/explore/<name>.txt`.

The result file format (from existing `train_gpt.py`):
```
val_bpb: 1.2198
steps: 500
...
```

Collection flow:
1. Polling job SSHes to GPU, runs `cat /root/parameter-golf/results/<stage>/<name>.txt`
2. Parses `val_bpb` value
3. Updates `Experiment.val_bpb`, `Experiment.status = 'completed'` in DB

**OR** the GPU `infra/run_experiment.sh` could `curl` the platform API with results on completion (webhook approach — cleaner).

---

## Config Overrides Mapping

User submits overrides like:
```
NUM_LAYERS=14
MLP_MULT=4
MATRIX_LR=0.06
```

Platform converts to shell env vars prepended to the training command:
```bash
NUM_LAYERS=14 MLP_MULT=4 MATRIX_LR=0.06 bash infra/run_experiment.sh my_exp_500 500
```

Full list of supported overrides (from `parameter-golf` train_gpt.py):
`MATRIX_LR`, `SCALAR_LR`, `EMBED_LR`, `NUM_LAYERS`, `MODEL_DIM`, `NUM_HEADS`, `NUM_KV_HEADS`, `MLP_MULT`, `WARMDOWN_ITERS`, `WARMUP_STEPS`, `LOGIT_SOFTCAP`, `QK_GAIN_INIT`, `ROPE_BASE`, `MUON_MOMENTUM`, `GRAD_CLIP_NORM`, `TIED_EMBED_LR`, `TIED_EMBED_INIT_STD`

---

## Stage → Steps Mapping

| Stage | Steps | Time (L40S) | Tier Required |
|-------|------:|-------------|---------------|
| explore | 500 | ~28 min | All tiers |
| validate | 2000–4000 | ~1.8–3.7 hr | Researcher+ |
| full | 13780 | ~12.7 hr | Pro+ |

---

## AI Chat Context Enhancement (Future)

Today: chat has no user context — just static system prompt.

Plan: Before calling LLM, inject user's recent experiments + results:
```python
# In chat.py, fetch user's data before LLM call:
recent_exps = db.query(Experiment).filter(user_id=user.id).order_by(created_at.desc()).limit(5)
context_block = format_experiments_as_context(recent_exps)
# Inject into system prompt
```

This makes the AI actually useful — it can say "Your last explore run got 1.2341 bpb, here's what to try next."

---

## Skool → Platform User Provisioning

Currently: manual (admin creates user via panel after Skool payment).

Future (webhooks.py stub):
1. Skool sends webhook on new member join
2. Platform receives `POST /webhooks/skool`
3. Auto-creates user with correct tier
4. Sends email with login credentials

---

## Deployment

For production, the platform needs to be on a machine that:
- Has `sshpass` installed
- Has SSH access to the GPU machines (same proxy host)
- Is accessible from the internet (Railway, Hetzner, or Novita)

The `parameter-golf` repo on GPUs stays independent — it just needs to be cloned and have data downloaded (use `/setup` skill).
