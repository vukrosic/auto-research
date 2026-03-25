#!/usr/bin/env bash
# Check if an experiment is still running on its GPU.
# Usage: scripts/check_experiment.sh <experiment_name>
# Outputs: running | done | failed
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTORESEARCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/gpu_config.sh"

NAME="${1:?Usage: scripts/check_experiment.sh <experiment_name>}"
SNAPSHOT_DIR="$AUTORESEARCH_DIR/experiments/snapshots/$NAME"

if [ ! -f "$SNAPSHOT_DIR/gpu" ]; then
    echo "ERROR: No GPU assigned for experiment '$NAME'"
    exit 1
fi

GPU=$(cat "$SNAPSHOT_DIR/gpu")
REMOTE_DIR=$(gpu_var "$GPU" REMOTE_DIR)

# Check if training process is still running
if gpu_ssh "$GPU" "ps aux | grep 'RUN_ID=${NAME}' | grep -v grep" &>/dev/null; then
    echo "running"
    # Show progress
    gpu_ssh "$GPU" "tail -5 /tmp/autoresearch_${NAME}.log 2>/dev/null || tail -5 ${REMOTE_DIR}/logs/${NAME}.txt 2>/dev/null" || true
    exit 0
fi

# Training is not running — check if it completed or crashed
if gpu_ssh "$GPU" "test -f ${REMOTE_DIR}/results/${NAME}/summary.json" &>/dev/null; then
    echo "done"
elif gpu_ssh "$GPU" "grep -q 'val_bpb' ${REMOTE_DIR}/logs/${NAME}.txt 2>/dev/null"; then
    echo "done"
else
    echo "failed"
    echo "--- Last 10 lines of log ---"
    gpu_ssh "$GPU" "tail -10 /tmp/autoresearch_${NAME}.log 2>/dev/null || tail -10 ${REMOTE_DIR}/logs/${NAME}.txt 2>/dev/null" || echo "(no log found)"
fi
