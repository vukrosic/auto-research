#!/usr/bin/env bash
# Check if an experiment is still running on its GPU.
# Canonical usage: scripts/check_experiment.sh <project_name> <experiment_name>
# Legacy one-project shorthand: scripts/check_experiment.sh <experiment_name>
# Outputs: running | done | failed
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTORESEARCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/gpu_config.sh"

if [ $# -ge 2 ] && project_exists "$AUTORESEARCH_DIR" "$1"; then
    PROJECT="$1"
    NAME="${2:?Usage: scripts/check_experiment.sh <project_name> <experiment_name>}"
else
    NAME="${1:?Usage: scripts/check_experiment.sh <project_name> <experiment_name>}"
    PROJECT="$(snapshot_project_by_name "$AUTORESEARCH_DIR" "$NAME")"
fi

PROJECT_JSON="$(project_config_path "$AUTORESEARCH_DIR" "$PROJECT")"
if [ ! -f "$PROJECT_JSON" ]; then
    echo "ERROR: No project config at $PROJECT_JSON"
    exit 1
fi

HOOK="$(project_hook_path "$PROJECT_JSON" check "$AUTORESEARCH_DIR" || true)"
if [ -n "$HOOK" ]; then
    if [ ! -x "$HOOK" ]; then
        echo "ERROR: Check hook is not executable: $HOOK"
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
REMOTE_LOG="/tmp/autoresearch_${NAME}.log"
REMOTE_PID=""
if [ -f "$SNAPSHOT_DIR/remote_pid" ]; then
    REMOTE_PID="$(cat "$SNAPSHOT_DIR/remote_pid")"
fi

# Read project-specific settings
LOG_PATH=$(python3 -c "
import json
p = json.load(open('$PROJECT_JSON'))
print(p.get('log_path', 'logs/{name}.txt').replace('{name}', '$NAME'))
")
COMPLETION_INDICATOR=$(python3 -c "
import json
p = json.load(open('$PROJECT_JSON'))
ci = p.get('completion_indicator', '')
print(ci.replace('{name}', '$NAME') if ci else '')
")
METRIC=$(project_field "$PROJECT_JSON" metric "val_bpb")

# Read primary metric regex from project config
METRIC_REGEX=$(python3 -c "
import json
p = json.load(open('$PROJECT_JSON'))
mp = p.get('metric_parse', {})
primary = mp.get(p.get('metric', 'val_bpb'), {})
print(primary.get('log_regex', r'\b' + p.get('metric', 'val_bpb') + r'[:=]\s*[0-9]'))
")
METRIC_REGEX_B64="$(printf '%s' "$METRIC_REGEX" | base64 -w0)"
REMOTE_METRIC_CHECK=$(cat <<EOF
python3 - <<'PY'
import base64
import pathlib
import re
import sys

pattern = re.compile(base64.b64decode("${METRIC_REGEX_B64}").decode("utf-8"))
for raw_path in (r"${REMOTE_DIR}/${LOG_PATH}", r"${REMOTE_LOG}"):
    path = pathlib.Path(raw_path)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    if pattern.search(text):
        sys.exit(0)
sys.exit(1)
PY
EOF
)

# 1. Check if training process is still running (check this FIRST)
if [ -n "$REMOTE_PID" ] && gpu_ssh "$GPU" "test -d /proc/${REMOTE_PID}" &>/dev/null; then
    echo "running"
    # Show progress
    gpu_ssh "$GPU" "tail -5 ${REMOTE_LOG} 2>/dev/null || tail -5 ${REMOTE_DIR}/${LOG_PATH} 2>/dev/null" || true
    exit 0
fi

# 2. Process is dead — check for fatal errors
if gpu_ssh "$GPU" "grep -Eq 'OutOfMemoryError|CUDA out of memory|Traceback \(most recent call last\)|RuntimeError:' ${REMOTE_LOG} ${REMOTE_DIR}/${LOG_PATH} 2>/dev/null" &>/dev/null; then
    echo "failed"
    echo "--- Fatal error detected in log ---"
    gpu_ssh "$GPU" "tail -20 ${REMOTE_LOG} 2>/dev/null || tail -20 ${REMOTE_DIR}/${LOG_PATH} 2>/dev/null" || true
    exit 0
fi

# 3. No fatal error — check if it completed successfully
if [ -n "$COMPLETION_INDICATOR" ] && gpu_ssh "$GPU" "test -f ${REMOTE_DIR}/${COMPLETION_INDICATOR}" &>/dev/null; then
    echo "done"
elif gpu_ssh "$GPU" "$REMOTE_METRIC_CHECK" &>/dev/null; then
    echo "done"
else
    echo "failed"
    echo "--- Last 10 lines of log ---"
    gpu_ssh "$GPU" "tail -10 ${REMOTE_LOG} 2>/dev/null || tail -10 ${REMOTE_DIR}/${LOG_PATH} 2>/dev/null" || echo "(no log found)"
fi
