#!/usr/bin/env bash
# Dispatch an experiment to a GPU.
# Canonical usage: scripts/dispatch.sh <project_name> <experiment_name> <gpu_name> [steps]
# Legacy one-project shorthand: scripts/dispatch.sh <experiment_name> <gpu_name> [steps]
#
# 1. Rsyncs snapshot code to GPU
# 2. Starts training via nohup
# 3. Sets status=running
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTORESEARCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/gpu_config.sh"

if [ $# -ge 3 ] && project_exists "$AUTORESEARCH_DIR" "$1"; then
    PROJECT="$1"
    NAME="${2:?Usage: scripts/dispatch.sh <project_name> <experiment_name> <gpu_name> [steps]}"
    GPU="${3:?Usage: scripts/dispatch.sh <project_name> <experiment_name> <gpu_name> [steps]}"
    STEPS_OVERRIDE="${4:-}"
else
    NAME="${1:?Usage: scripts/dispatch.sh <project_name> <experiment_name> <gpu_name> [steps]}"
    GPU="${2:?Usage: scripts/dispatch.sh <project_name> <experiment_name> <gpu_name> [steps]}"
    PROJECT="$(snapshot_project_by_name "$AUTORESEARCH_DIR" "$NAME")"
    STEPS_OVERRIDE="${3:-}"
fi

PROJECT_JSON="$(project_config_path "$AUTORESEARCH_DIR" "$PROJECT")"
if [ ! -f "$PROJECT_JSON" ]; then
    echo "ERROR: No project config at $PROJECT_JSON"
    exit 1
fi

if ! python3 "$SCRIPT_DIR/preflight_experiment.py" "$PROJECT" "$NAME" --gpu "$GPU" --write --sync-expected; then
    echo "ERROR: Preflight failed for '$NAME'"
    exit 1
fi

HOOK="$(project_hook_path "$PROJECT_JSON" dispatch "$AUTORESEARCH_DIR" || true)"
if [ -n "$HOOK" ]; then
    if [ ! -x "$HOOK" ]; then
        echo "ERROR: Dispatch hook is not executable: $HOOK"
        exit 1
    fi
    if [ -n "$STEPS_OVERRIDE" ]; then
        exec "$HOOK" "$PROJECT" "$NAME" "$GPU" "$STEPS_OVERRIDE"
    else
        exec "$HOOK" "$PROJECT" "$NAME" "$GPU"
    fi
fi

PROJECT_EXPERIMENTS="$AUTORESEARCH_DIR/experiments/$PROJECT"
SNAPSHOT_DIR="$PROJECT_EXPERIMENTS/snapshots/$NAME"
STATUS_FILE="$SNAPSHOT_DIR/status"

if [ ! -d "$SNAPSHOT_DIR/code" ]; then
    echo "ERROR: Experiment '$NAME' not found at $SNAPSHOT_DIR/code/"
    exit 1
fi

if [ -f "$STATUS_FILE" ] && [ "$(cat "$STATUS_FILE")" = "running" ]; then
    echo "ERROR: Experiment '$NAME' is already marked running"
    exit 1
fi

# Check if another experiment is already running on this GPU (across ALL projects)
for proj_dir in "$AUTORESEARCH_DIR"/experiments/*/; do
    [ -d "$proj_dir/snapshots" ] || continue
    for other_dir in "$proj_dir"/snapshots/*/; do
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
done

# Read steps from meta.json if not provided
if [ -n "$STEPS_OVERRIDE" ]; then
    STEPS="$STEPS_OVERRIDE"
elif [ -f "$SNAPSHOT_DIR/meta.json" ]; then
    STEPS=$(python3 -c "import json; print(json.load(open('$SNAPSHOT_DIR/meta.json'))['steps'])")
else
    echo "ERROR: No steps specified and no meta.json found"
    exit 1
fi

# Get remote dir and run command from project config
REMOTE_DIR=$(project_remote_dir "$PROJECT_JSON" "$GPU")
RUN_COMMAND=$(project_field "$PROJECT_JSON" run_command)
PROCESS_PATTERN=$(project_field "$PROJECT_JSON" process_pattern)
REMOTE_LOG="/tmp/autoresearch_${NAME}.log"
REMOTE_RUNTIME_JSON="/tmp/autoresearch_${NAME}.runtime.json"
REMOTE_WRAPPER_PID="/tmp/autoresearch_${NAME}.wrapper.pid"
REMOTE_WRAPPER_PATH="${REMOTE_DIR}/.autoresearch_wrapper_${NAME}.sh"

# Read env overrides from meta.json
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
STALE_PIDS=$(gpu_ssh "$GPU" "pgrep -f '$PROCESS_PATTERN' 2>/dev/null" || true)
if [ -n "$STALE_PIDS" ]; then
    echo "WARNING: Killing stale training processes on $GPU: $STALE_PIDS"
    gpu_ssh "$GPU" "pkill -f '$PROCESS_PATTERN' 2>/dev/null" || true
    sleep 2
fi

# 1. Rsync code to GPU
echo "Syncing code..."
gpu_rsync_to "$GPU" "$SNAPSHOT_DIR/code/" "$REMOTE_DIR/"

# 2. Build the run command from project config template
EXPANDED_CMD=$(echo "$RUN_COMMAND" | sed "s/{name}/$NAME/g; s/{steps}/$STEPS/g")

WRAPPER_LOCAL="$(mktemp)"
cleanup_wrapper() {
    rm -f "$WRAPPER_LOCAL"
}
trap cleanup_wrapper EXIT

python3 - "$NAME" "$REMOTE_ENV" "$EXPANDED_CMD" > "$WRAPPER_LOCAL" <<'PY'
import shlex
import sys

name, remote_env, expanded_cmd = sys.argv[1:4]
runtime_path = f"/tmp/autoresearch_{name}.runtime.json"
wrapper_pid_path = f"/tmp/autoresearch_{name}.wrapper.pid"
command = expanded_cmd if not remote_env else f"env {remote_env} {expanded_cmd}"

print("#!/usr/bin/env bash")
print("set -euo pipefail")
print(f"echo $$ > {shlex.quote(wrapper_pid_path)}")
print('started_at="$(date -u +\"%Y-%m-%dT%H:%M:%SZ\")"')
print('started_epoch="$(date -u +%s)"')
print("exit_code=0")
print("set +e")
print(command)
print("exit_code=$?")
print("set -e")
print('finished_at="$(date -u +\"%Y-%m-%dT%H:%M:%SZ\")"')
print('finished_epoch="$(date -u +%s)"')
print('runtime_seconds=$((finished_epoch - started_epoch))')
print(
    "python3 - "
    + shlex.quote(runtime_path)
    + ' "$started_at" "$finished_at" "$started_epoch" "$finished_epoch" "$runtime_seconds" "$exit_code" <<\'PY\''
)
print("import json")
print("import sys")
print("")
print("runtime_path, started_at, finished_at, started_epoch, finished_epoch, runtime_seconds, exit_code = sys.argv[1:8]")
print("payload = {")
print('    "started_at": started_at,')
print('    "finished_at": finished_at,')
print('    "started_epoch": int(started_epoch),')
print('    "finished_epoch": int(finished_epoch),')
print('    "runtime_seconds": int(runtime_seconds),')
print('    "exit_code": int(exit_code),')
print("}")
print("with open(runtime_path, 'w', encoding='utf-8') as handle:")
print("    handle.write(json.dumps(payload, indent=2) + '\\n')")
print("PY")
print('exit "$exit_code"')
PY
chmod +x "$WRAPPER_LOCAL"

# 3. Start training via nohup
echo "Starting training: $EXPANDED_CMD"
echo "Preparing runtime wrapper..."
gpu_ssh "$GPU" "rm -f $(printf '%q' "$REMOTE_LOG") $(printf '%q' "$REMOTE_RUNTIME_JSON") $(printf '%q' "$REMOTE_WRAPPER_PID")" >/dev/null 2>&1 || true
gpu_rsync_to "$GPU" "$WRAPPER_LOCAL" "$REMOTE_WRAPPER_PATH"
REMOTE_PID=$(gpu_ssh "$GPU" "cd $(printf '%q' "$REMOTE_DIR") && chmod +x $(printf '%q' "$REMOTE_WRAPPER_PATH") && nohup bash $(printf '%q' "$REMOTE_WRAPPER_PATH") > $(printf '%q' "$REMOTE_LOG") 2>&1 & echo \$!")

# 4. Update status
echo "running" > "$SNAPSHOT_DIR/status"
echo "$GPU" > "$SNAPSHOT_DIR/gpu"
printf '%s\n' "$REMOTE_PID" > "$SNAPSHOT_DIR/remote_pid"
DISPATCHED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
printf '%s\n' "$DISPATCHED_AT" > "$SNAPSHOT_DIR/dispatched_at"

GOAL_NAME="$(python3 -c "
import json
from pathlib import Path
meta = json.load(open('$SNAPSHOT_DIR/meta.json'))
print(meta.get('goal', ''))
")"
if [ -n "$GOAL_NAME" ] && [ -f "$AUTORESEARCH_DIR/goals/$GOAL_NAME/goal.json" ]; then
    python3 "$SCRIPT_DIR/goal_timing.py" start "$AUTORESEARCH_DIR/goals/$GOAL_NAME/goal.json" "$DISPATCHED_AT" >/dev/null || true
fi

echo "=== Dispatched. Check with: scripts/check_experiment.sh $PROJECT $NAME ==="
