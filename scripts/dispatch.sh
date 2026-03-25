#!/usr/bin/env bash
# Dispatch an experiment to a GPU.
# Usage: scripts/dispatch.sh <experiment_name> <gpu_name> [steps]
#
# 1. Rsyncs snapshot code to GPU
# 2. Starts training via nohup
# 3. Sets status=running
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTORESEARCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/gpu_config.sh"

NAME="${1:?Usage: scripts/dispatch.sh <experiment_name> <gpu_name> [steps]}"
GPU="${2:?Usage: scripts/dispatch.sh <experiment_name> <gpu_name> [steps]}"
SNAPSHOT_DIR="$AUTORESEARCH_DIR/experiments/snapshots/$NAME"

if [ ! -d "$SNAPSHOT_DIR/code" ]; then
    echo "ERROR: Experiment '$NAME' not found at $SNAPSHOT_DIR/code/"
    exit 1
fi

# Read steps from meta.json if not provided
if [ -n "${3:-}" ]; then
    STEPS="$3"
elif [ -f "$SNAPSHOT_DIR/meta.json" ]; then
    STEPS=$(python3 -c "import json; print(json.load(open('$SNAPSHOT_DIR/meta.json'))['steps'])")
else
    echo "ERROR: No steps specified and no meta.json found"
    exit 1
fi

REMOTE_DIR=$(gpu_var "$GPU" REMOTE_DIR)

echo "=== Dispatching: $NAME → $GPU ($STEPS steps) ==="

# 1. Rsync code to GPU
echo "Syncing code..."
gpu_rsync_to "$GPU" "$SNAPSHOT_DIR/code/" "$REMOTE_DIR/"

# 2. Start training via nohup
echo "Starting training..."
gpu_ssh "$GPU" "cd $REMOTE_DIR && nohup bash infra/run_experiment.sh '$NAME' '$STEPS' > /tmp/autoresearch_${NAME}.log 2>&1 & echo \$!"

# 3. Update status
echo "running" > "$SNAPSHOT_DIR/status"
echo "$GPU" > "$SNAPSHOT_DIR/gpu"

echo "=== Dispatched. Check with: scripts/check_experiment.sh $NAME ==="
