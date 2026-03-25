#!/bin/bash
# Run parameter-golf on a single GPU (e.g., RTX 3090)
# Uses reduced batch size and shorter iterations for rapid iteration
# Override: RUN_ID, ITERATIONS, NUM_LAYERS, MODEL_DIM, etc.

set -e

# Defaults for single-GPU testing
export ITERATIONS=${ITERATIONS:-500}
export TRAIN_BATCH_TOKENS=${TRAIN_BATCH_TOKENS:-65536}  # 64 seqs * 1024 tokens
export VAL_LOSS_EVERY=${VAL_LOSS_EVERY:-100}
export TRAIN_LOG_EVERY=${TRAIN_LOG_EVERY:-50}
export MAX_WALLCLOCK_SECONDS=${MAX_WALLCLOCK_SECONDS:-600}
export RUN_ID=${RUN_ID:-"single_gpu_$(date +%Y%m%d_%H%M%S)"}

echo "=== Parameter Golf — Single GPU Run ==="
echo "RUN_ID: $RUN_ID"
echo "ITERATIONS: $ITERATIONS"
echo "BATCH_TOKENS: $TRAIN_BATCH_TOKENS"
echo "NUM_LAYERS: ${NUM_LAYERS:-9}"
echo "MODEL_DIM: ${MODEL_DIM:-512}"
echo "========================================"

cd /root/parameter-golf
python3 train_gpt.py
