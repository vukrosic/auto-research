#!/usr/bin/env bash
# Usage: infra/run_experiment.sh <experiment_name> <max_steps> [extra_env...]
#
# Runs train_gpt.py with standardized settings for 1-GPU development.
# Results go to results/<experiment_name>/ and logs/<experiment_name>.txt
#
# Examples:
#   infra/run_experiment.sh baseline_check 200
#   MATRIX_LR=0.08 infra/run_experiment.sh lr_test 500
#   NUM_LAYERS=12 MODEL_DIM=448 infra/run_experiment.sh arch_12x448 200

set -euo pipefail
cd "$(dirname "$0")/.."

NAME="${1:?Usage: infra/run_experiment.sh <name> <max_steps>}"
MAX_STEPS="${2:?Usage: infra/run_experiment.sh <name> <max_steps>}"

# Auto-detect GPU and estimate wall-clock seconds per step.
# Override with GPU_TIMING_PER_STEP env var for unlisted GPUs.
if [ -z "${GPU_TIMING_PER_STEP:-}" ]; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 | xargs || echo "")
    case "$GPU_NAME" in
        *3090*)  GPU_TIMING_PER_STEP=4.2 ;;
        *L40*)   GPU_TIMING_PER_STEP=3.4 ;;
        *5090*)  GPU_TIMING_PER_STEP=2.8 ;;
        *A100*)  GPU_TIMING_PER_STEP=2.5 ;;
        *H100*)  GPU_TIMING_PER_STEP=2.0 ;;
        *)       GPU_TIMING_PER_STEP=3.4 ;;
    esac
    echo "Detected GPU: ${GPU_NAME:-unknown} -> ${GPU_TIMING_PER_STEP}s/step"
fi

# Choose safer single-GPU defaults on smaller cards unless the experiment overrides them.
if [ -z "${TRAIN_BATCH_TOKENS:-}" ]; then
    case "$GPU_NAME" in
        *3090*) TRAIN_BATCH_TOKENS=65536 ;;
        *L40*)  TRAIN_BATCH_TOKENS=131072 ;;
        *)      TRAIN_BATCH_TOKENS=524288 ;;
    esac
fi
if [ -z "${VAL_BATCH_SIZE:-}" ]; then
    case "$GPU_NAME" in
        *3090*) VAL_BATCH_SIZE=65536 ;;
        *L40*)  VAL_BATCH_SIZE=131072 ;;
        *)      VAL_BATCH_SIZE=524288 ;;
    esac
fi
export TRAIN_BATCH_TOKENS VAL_BATCH_SIZE
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

# Add 15% buffer for validation + overhead
WALLCLOCK=$(python3 -c "import math; print(math.ceil($MAX_STEPS * $GPU_TIMING_PER_STEP * 1.15))")

# Standardized settings for reproducible comparisons.
# Allow queue entries to pre-set a shorter wallclock or iteration budget for fast probes.
export RUN_ID="${NAME}"
export ITERATIONS="${ITERATIONS:-$MAX_STEPS}"
export MAX_WALLCLOCK_SECONDS="${MAX_WALLCLOCK_SECONDS:-$WALLCLOCK}"
export VAL_LOSS_EVERY="${VAL_LOSS_EVERY:-50}"
export TRAIN_LOG_EVERY="${TRAIN_LOG_EVERY:-10}"
export SEED="${SEED:-1337}"

# Print experiment config
echo "============================================"
echo "Experiment: ${NAME}"
echo "Max steps:  ${MAX_STEPS}"
echo "Wallclock:  ${WALLCLOCK}s (~$(python3 -c "print(f'{$WALLCLOCK/60:.1f}')")min)"
echo "============================================"
echo "Env overrides:"
for var in MATRIX_LR SCALAR_LR EMBED_LR NUM_LAYERS MODEL_DIM NUM_HEADS NUM_KV_HEADS \
           MLP_MULT WARMDOWN_ITERS WARMUP_STEPS LOGIT_SOFTCAP QK_GAIN_INIT ROPE_BASE \
           MUON_MOMENTUM MUON_BACKEND_STEPS GRAD_CLIP_NORM TIED_EMBED_LR TIED_EMBED_INIT_STD \
           TRAIN_BATCH_TOKENS VAL_BATCH_SIZE VAL_LOSS_EVERY TRAIN_LOG_EVERY PYTORCH_CUDA_ALLOC_CONF; do
    if [ -n "${!var+x}" ]; then
        echo "  ${var}=${!var}"
    fi
done
echo "============================================"

mkdir -p results/"${NAME}" logs

# Run training
python3 train_gpt.py 2>&1 | tee logs/"${NAME}.txt"

# Copy the log into results dir for self-contained experiment records
if [ -f "logs/${NAME}.txt" ]; then
    cp "logs/${NAME}.txt" "results/${NAME}/train.log"
fi

# Export commit-friendly artifacts for git tracking.
python3 infra/export_experiment_artifacts.py \
    --run-id "${NAME}" \
    --log-path "logs/${NAME}.txt" \
    --output-dir "results/${NAME}"

# Extract final metrics
echo ""
echo "=== Results ==="
if grep -q "val_bpb" "logs/${NAME}.txt"; then
    echo "Final val_bpb:"
    grep "val_bpb" "logs/${NAME}.txt" | tail -1
fi
if grep -q "final_int8_zlib_roundtrip" "logs/${NAME}.txt"; then
    echo "Post-quant val_bpb:"
    grep "final_int8_zlib_roundtrip_exact" "logs/${NAME}.txt" | tail -1
fi
echo "==============="
