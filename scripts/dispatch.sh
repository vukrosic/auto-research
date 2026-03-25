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
STATUS_FILE="$SNAPSHOT_DIR/status"

if [ ! -d "$SNAPSHOT_DIR/code" ]; then
    echo "ERROR: Experiment '$NAME' not found at $SNAPSHOT_DIR/code/"
    exit 1
fi

if [ -f "$STATUS_FILE" ] && [ "$(cat "$STATUS_FILE")" = "running" ]; then
    echo "ERROR: Experiment '$NAME' is already marked running"
    exit 1
fi

# Check if another experiment is already running on this GPU
for other_dir in "$AUTORESEARCH_DIR"/experiments/snapshots/*/; do
    [ -d "$other_dir" ] || continue
    other_name=$(basename "$other_dir")
    [ "$other_name" = "$NAME" ] && continue
    other_status=$(cat "$other_dir/status" 2>/dev/null || true)
    other_gpu=$(cat "$other_dir/gpu" 2>/dev/null || true)
    if [ "$other_status" = "running" ] && [ "$other_gpu" = "$GPU" ]; then
        echo "ERROR: GPU '$GPU' is already running experiment '$other_name'"
        exit 1
    fi
done

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
REMOTE_ENV=""
if [ -f "$SNAPSHOT_DIR/meta.json" ]; then
    REMOTE_ENV=$(python3 -c "
import json, shlex
meta = json.load(open('$SNAPSHOT_DIR/meta.json'))
env = meta.get('env_overrides') or {}
parts = []
for key, value in env.items():
    parts.append(f'{key}=' + shlex.quote(str(value)))
print(' '.join(parts))
")
fi

echo "=== Dispatching: $NAME → $GPU ($STEPS steps) ==="

# 0. Kill any stale training processes on the GPU
STALE_PIDS=$(gpu_ssh "$GPU" "pgrep -f 'train_gpt.py' 2>/dev/null" || true)
if [ -n "$STALE_PIDS" ]; then
    echo "WARNING: Killing stale training processes on $GPU: $STALE_PIDS"
    gpu_ssh "$GPU" "pkill -f 'train_gpt.py' 2>/dev/null" || true
    sleep 2
fi

# 1. Rsync code to GPU
echo "Syncing code..."
gpu_rsync_to "$GPU" "$SNAPSHOT_DIR/code/" "$REMOTE_DIR/"

# 2. Start training via nohup
echo "Starting training..."
REMOTE_PID=$(gpu_ssh "$GPU" "cd $REMOTE_DIR && nohup bash -lc 'echo \$\$ > /tmp/autoresearch_${NAME}.wrapper.pid; exec env ${REMOTE_ENV} bash infra/run_experiment.sh \"$NAME\" \"$STEPS\"' > /tmp/autoresearch_${NAME}.log 2>&1 & echo \$!")

# 3. Update status
echo "running" > "$SNAPSHOT_DIR/status"
echo "$GPU" > "$SNAPSHOT_DIR/gpu"
printf '%s\n' "$REMOTE_PID" > "$SNAPSHOT_DIR/remote_pid"

echo "=== Dispatched. Check with: scripts/check_experiment.sh $NAME ==="
