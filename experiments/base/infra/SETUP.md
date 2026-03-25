# Lab Setup

## Development Hardware

- **1x reference single-GPU benchmark machine** (48GB VRAM class)
- All experiments run single-GPU with grad_accum=8 (automatic)
- Step dynamics identical to 8xH100 (same effective batch)

## Running an Experiment

Every experiment is a single invocation of `train_gpt.py` (or a fork) with env vars.
Use `infra/run_experiment.sh` for standardized runs:

```bash
# Quick sanity check (50 steps, ~2.5 min on the reference benchmark machine)
infra/run_experiment.sh my_test_name 50

# Medium run (200 steps, ~11 min)
infra/run_experiment.sh my_test_name 200

# Full 600s 8xH100 equivalent (13780 steps ≈ 12.7 hours)
infra/run_experiment.sh my_test_name 13780

# With custom env overrides
MATRIX_LR=0.08 NUM_LAYERS=12 MODEL_DIM=448 infra/run_experiment.sh my_arch_test 200
```

Each run exports commit-friendly artifacts:

- `results/<run_id>/summary.json`
- `results/<run_id>/metadata.json`
- `results/<run_id>/train.log` (raw log, git-ignored)

## Git Hook Guardrail

Enable the pre-commit size guard once per clone:

```bash
infra/install_git_hooks.sh
```

This blocks staged files larger than 20MB by default. Override if needed:

```bash
MAX_FILE_MB=50 git commit -m "..."
```

## Experiment Duration Guide

On the reference single-GPU benchmark machine at ~3.33s/step:

| Steps | Wall-clock | Equivalent 8xH100 time | Use for |
|-------|-----------|------------------------|---------|
| 15 | ~50s | ~0.65s | Smoke test only |
| 50 | ~2.8 min | ~2.2s | Quick architecture sanity |
| 200 | ~11 min | ~8.7s | LR/schedule comparison |
| 500 | ~28 min | ~22s | Medium convergence check |
| 1000 | ~55 min | ~43s | Solid convergence signal |
| 3000 | ~2.8 hr | ~2.2 min | Strong signal |
| 5000 | ~4.6 hr | ~3.6 min | Near-final validation |
| 13780 | ~12.7 hr | 600s (full run) | Final pre-submission |

## What to Measure

Every experiment log contains:
- `train_loss` at each logged step
- `val_loss` and `val_bpb` at validation intervals
- `step_avg` (ms/step, useful for throughput calibration)

For submission candidates, the script also produces:
- `final_model.int8.ptz` — the compressed artifact
- `final_int8_zlib_roundtrip val_bpb` — the actual submission score

## Choosing Step Counts for Experiments

The key insight: **you don't need to run all 13,780 steps to compare configs**.

Loss curves are monotonic and largely parallel during mid-training. If config A beats
config B at step 500, it will almost certainly beat it at step 13,780 (barring schedule
interactions). Use this:

1. **Screening** (50-200 steps): Compare 5-10 configs. Keep top 3.
2. **Validation** (500-1000 steps): Compare top 3. Confirm ranking holds.
3. **Final** (3000-5000 steps): Run best 1-2 configs. Check for late divergence.
4. **Pre-submission** (13780 steps): Run the winner once. Verify BPB target.

## Step-Based Scheduling for 8xH100

The warmdown schedule is time-based by default (uses wall-clock remaining).
For 8xH100 at ~43ms/step over 600s:

- Total steps: ~13,780
- warmdown_iters=1200 → warmdown starts at step ~12,580
- warmdown_iters=2400 → warmdown starts at step ~11,380

The time-based schedule auto-adapts, so this transfers correctly as long as
MAX_WALLCLOCK_SECONDS=600 is set on the H100 run. No manual step calibration needed.

## Multi-GPU Fleet Workflow

Remote GPUs are disposable compute — no git setup needed on them. The workflow is:

1. **Deploy code** to a new GPU via tarball (see GPU Setup below)
2. **Copy an approved or archived queue payload into `queues/active.txt`** and start the scheduler
3. **Pull results** back to this machine via SCP

### Starting a GPU

```bash
# Pack and send the repo
tar czf /tmp/pg.tar.gz -C /root parameter-golf/
sshpass -p "$PASS" scp -P $PORT /tmp/pg.tar.gz root@$HOST:/tmp/
sshpass -p "$PASS" ssh -p $PORT root@$HOST 'cd /root && tar xzf /tmp/pg.tar.gz'

# Copy the right queue and start the scheduler
sshpass -p "$PASS" ssh -p $PORT root@$HOST \
  'cp parameter-golf/queues/archive/queue_arch1_weightsharing.txt parameter-golf/queues/active.txt \
   && cd parameter-golf && nohup python3 infra/gpu_scheduler.py > /tmp/scheduler.log 2>&1 &'
```

### Monitoring

```bash
# Live table of all GPUs (training progress, GPU stats, git status)
watch -c -n 30 bash infra/watch_all_gpus.sh
```

### Pulling Results

Results are saved on each GPU at `/root/results/<run_id>/`. Pull them back:

```bash
# Pull everything new from all GPUs (skips already-pulled runs)
bash infra/pull_results.sh

# Pull from specific GPUs only
bash infra/pull_results.sh ARCH1 ARCH2
```

### Auto-Pull Loop

Keep results syncing automatically in the background:

```bash
# Start (pulls every 2 min)
nohup bash infra/auto_pull.sh 2 > /tmp/auto_pull.log 2>&1 &

# Check it's working
tail -f /tmp/auto_pull.log

# Stop
pkill -f auto_pull.sh
```

### Adding a New GPU

1. Add credentials to `infra/gpu_creds.sh`:
   ```bash
   GPU_ARCH5_PORT=12345
   GPU_ARCH5_PASS="yourpassword"
   ```
2. It auto-appears in `watch_all_gpus.sh` and `pull_results.sh` — no other changes needed.

### Why Not Git on Remote GPUs?

- Results don't need git history — they're just JSON + logs
- Auto-commit loops break silently (82 stale unpushed commits on older GPUs proved this)
- SCP is stateless, always works, no auth setup needed on remotes

## Interpreting Results

**val_bpb is the only metric that matters for the challenge.**

- val_loss is in nats (natural log). val_bpb converts to bits-per-byte.
- train_loss tracks optimization but can diverge from val due to overfitting.
- The quant gap (pre-quant BPB minus post-quant BPB) is ~0.03 BPB for the baseline.
  Anything that reduces this gap is free performance.
