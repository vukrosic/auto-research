#!/usr/bin/env bash
# Collect results from a completed experiment on its GPU.
# Canonical usage: scripts/collect_result.sh <project_name> <experiment_name>
# Legacy one-project shorthand: scripts/collect_result.sh <experiment_name>
# Pulls logs and results back, parses metrics into result.json
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTORESEARCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/gpu_config.sh"

if [ $# -ge 2 ] && project_exists "$AUTORESEARCH_DIR" "$1"; then
    PROJECT="$1"
    NAME="${2:?Usage: scripts/collect_result.sh <project_name> <experiment_name>}"
else
    NAME="${1:?Usage: scripts/collect_result.sh <project_name> <experiment_name>}"
    PROJECT="$(snapshot_project_by_name "$AUTORESEARCH_DIR" "$NAME")"
fi

PROJECT_JSON="$(project_config_path "$AUTORESEARCH_DIR" "$PROJECT")"
if [ ! -f "$PROJECT_JSON" ]; then
    echo "ERROR: No project config at $PROJECT_JSON"
    exit 1
fi

HOOK="$(project_hook_path "$PROJECT_JSON" collect "$AUTORESEARCH_DIR" || true)"
if [ -n "$HOOK" ]; then
    if [ ! -x "$HOOK" ]; then
        echo "ERROR: Collect hook is not executable: $HOOK"
        exit 1
    fi
    exec "$HOOK" "$PROJECT" "$NAME"
fi

PROJECT_EXPERIMENTS="$AUTORESEARCH_DIR/experiments/$PROJECT"
SNAPSHOT_DIR="$PROJECT_EXPERIMENTS/snapshots/$NAME"

if [ ! -f "$SNAPSHOT_DIR/gpu" ]; then
    echo "ERROR: No GPU assigned for experiment '$NAME'"
    exit 1
fi

GPU=$(cat "$SNAPSHOT_DIR/gpu")
REMOTE_DIR=$(project_remote_dir "$PROJECT_JSON" "$GPU")

# Read project-specific paths
LOG_PATH=$(python3 -c "
import json
p = json.load(open('$PROJECT_JSON'))
print(p.get('log_path', 'logs/{name}.txt').replace('{name}', '$NAME'))
")
RESULT_DIR_TEMPLATE=$(python3 -c "
import json
p = json.load(open('$PROJECT_JSON'))
print(p.get('result_dir', 'results/{name}/').replace('{name}', '$NAME'))
")
SUMMARY_JSON_PATH=$(python3 -c "
import json
p = json.load(open('$PROJECT_JSON'))
sjp = p.get('summary_json_path', '')
print(sjp.replace('{name}', '$NAME') if sjp else '')
")

echo "=== Collecting results: $NAME from $GPU (project: $PROJECT) ==="

# Pull results directory
mkdir -p "$SNAPSHOT_DIR/results"
gpu_rsync_from "$GPU" "${REMOTE_DIR}/${RESULT_DIR_TEMPLATE}" "$SNAPSHOT_DIR/results/" 2>/dev/null || true

# Pull log
gpu_rsync_from "$GPU" "${REMOTE_DIR}/${LOG_PATH}" "$SNAPSHOT_DIR/results/train.log" 2>/dev/null || true
# Also try the nohup log
gpu_rsync_from "$GPU" "/tmp/autoresearch_${NAME}.log" "$SNAPSHOT_DIR/results/nohup.log" 2>/dev/null || true
# Pull runtime metadata if the dispatch wrapper produced it
gpu_rsync_from "$GPU" "/tmp/autoresearch_${NAME}.runtime.json" "$SNAPSHOT_DIR/results/runtime.json" 2>/dev/null || true

# Parse metrics from log using project config
LOG="$SNAPSHOT_DIR/results/train.log"
if [ ! -f "$LOG" ] && [ -f "$SNAPSHOT_DIR/results/nohup.log" ]; then
    LOG="$SNAPSHOT_DIR/results/nohup.log"
fi
if [ -f "$LOG" ]; then
    PARSE_OUTPUT=$(python3 "$SCRIPT_DIR/build_result.py" "$SNAPSHOT_DIR" "$PROJECT_JSON" "$GPU" "$LOG" 2>&1) || true
    echo "$PARSE_OUTPUT"
    if echo "$PARSE_OUTPUT" | grep -q "HAS_METRIC=True"; then
        echo "done" > "$SNAPSHOT_DIR/status"
    else
        echo "failed" > "$SNAPSHOT_DIR/status"
        echo "WARNING: No primary metric found in log — marking as failed"
    fi
    rm -f "$SNAPSHOT_DIR/remote_pid"
    echo "=== Result written to $SNAPSHOT_DIR/result.json ==="
    # Append to central timing log
    python3 "$SCRIPT_DIR/update_timing_log.py" "$NAME" "$SNAPSHOT_DIR/result.json" "$SNAPSHOT_DIR/meta.json" 2>/dev/null || true
else
    echo "ERROR: No training log found"
    echo "failed" > "$SNAPSHOT_DIR/status"
    rm -f "$SNAPSHOT_DIR/remote_pid"
fi
