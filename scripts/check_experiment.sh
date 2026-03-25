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
REMOTE_LOG="/tmp/autoresearch_${NAME}.log"
REMOTE_PID=""
if [ -f "$SNAPSHOT_DIR/remote_pid" ]; then
    REMOTE_PID="$(cat "$SNAPSHOT_DIR/remote_pid")"
fi

# 1. Check if training process is still running (check this FIRST)
if [ -n "$REMOTE_PID" ] && gpu_ssh "$GPU" "test -d /proc/${REMOTE_PID}" &>/dev/null; then
    echo "running"
    # Show progress
    gpu_ssh "$GPU" "tail -5 ${REMOTE_LOG} 2>/dev/null || tail -5 ${REMOTE_DIR}/logs/${NAME}.txt 2>/dev/null" || true
    exit 0
fi

# 2. Process is dead — check for fatal errors
if gpu_ssh "$GPU" "grep -Eq 'OutOfMemoryError|CUDA out of memory|Traceback \\(most recent call last\\)|RuntimeError:' ${REMOTE_LOG} ${REMOTE_DIR}/logs/${NAME}.txt 2>/dev/null" &>/dev/null; then
    echo "failed"
    echo "--- Fatal error detected in log ---"
    gpu_ssh "$GPU" "tail -20 ${REMOTE_LOG} 2>/dev/null || tail -20 ${REMOTE_DIR}/logs/${NAME}.txt 2>/dev/null" || true
    exit 0
fi

# 3. No fatal error — check if it completed successfully
if gpu_ssh "$GPU" "test -f ${REMOTE_DIR}/results/${NAME}/summary.json" &>/dev/null; then
    echo "done"
elif gpu_ssh "$GPU" "grep -Eq '\\bval_bpb[:=]\\s*[0-9]' ${REMOTE_DIR}/logs/${NAME}.txt ${REMOTE_LOG} 2>/dev/null"; then
    echo "done"
else
    echo "failed"
    echo "--- Last 10 lines of log ---"
    gpu_ssh "$GPU" "tail -10 ${REMOTE_LOG} 2>/dev/null || tail -10 ${REMOTE_DIR}/logs/${NAME}.txt 2>/dev/null" || echo "(no log found)"
fi
