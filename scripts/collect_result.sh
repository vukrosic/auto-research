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

# Parse metrics from log using project config
LOG="$SNAPSHOT_DIR/results/train.log"
if [ ! -f "$LOG" ] && [ -f "$SNAPSHOT_DIR/results/nohup.log" ]; then
    LOG="$SNAPSHOT_DIR/results/nohup.log"
fi
if [ -f "$LOG" ]; then
    PARSE_OUTPUT=$(python3 -c "
import json, re, sys, datetime
from pathlib import Path

log_path = Path('$LOG')
project = json.load(open('$PROJECT_JSON'))
metric_parse = project.get('metric_parse', {})
step_parse = project.get('step_parse', {})
primary_metric = project.get('metric', 'val_bpb')
secondary_metrics = project.get('secondary_metrics', [])
all_metrics = [primary_metric] + secondary_metrics

text = log_path.read_text(encoding='utf-8', errors='replace')
lines = text.splitlines()

# Try summary.json first
summary_path_str = '$SUMMARY_JSON_PATH'
summary_local = Path('$SNAPSHOT_DIR/results/summary.json')
summary = {}
if summary_local.exists():
    try:
        summary = json.loads(summary_local.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        pass

parsed_metrics = {}
for metric_name in all_metrics:
    mconf = metric_parse.get(metric_name, {})
    value = None

    # Try summary.json key path first
    sjk = mconf.get('summary_json_key', '')
    if sjk and isinstance(summary, dict):
        obj = summary
        for part in sjk.split('.'):
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = None
                break
        if obj is not None:
            try:
                value = float(obj)
            except (ValueError, TypeError):
                pass

    # Fall back to log regex
    if value is None:
        regex = mconf.get('log_regex')
        if regex:
            for line in reversed(lines):
                m = re.search(regex, line)
                if m:
                    value = float(m.group(1))
                    break

    if value is not None:
        parsed_metrics[metric_name] = value

# Parse steps completed
steps_completed = 0
# Try summary.json
sjk = step_parse.get('summary_json_key', '')
if sjk and isinstance(summary, dict):
    obj = summary
    for part in sjk.split('.'):
        if isinstance(obj, dict):
            obj = obj.get(part)
        else:
            obj = None
            break
    if obj is not None:
        try:
            steps_completed = int(obj)
        except (ValueError, TypeError):
            pass

# Fall back to log regex
if steps_completed == 0:
    regex = step_parse.get('log_regex', r'\bstep[:=]\s*([0-9]+)')
    if regex:
        for line in reversed(lines):
            m = re.search(regex, line)
            if m:
                steps_completed = int(m.group(1))
                break

if steps_completed == 0:
    fallback = step_parse.get('log_regex_fallback', '')
    if fallback:
        for line in reversed(lines):
            m = re.search(fallback, line)
            if m:
                steps_completed = int(m.group(1))
                break

# Compute duration
dispatched_at_path = Path('$SNAPSHOT_DIR/dispatched_at')
collected_at = datetime.datetime.utcnow()
collected_at_str = collected_at.strftime('%Y-%m-%dT%H:%M:%SZ')
duration_seconds = None
dispatched_at_str = None
if dispatched_at_path.exists():
    dispatched_at_str = dispatched_at_path.read_text().strip()
    try:
        dispatched_dt = datetime.datetime.strptime(dispatched_at_str, '%Y-%m-%dT%H:%M:%SZ')
        duration_seconds = int((collected_at - dispatched_dt).total_seconds())
    except Exception:
        pass

meta_path = Path('$SNAPSHOT_DIR/meta.json')
expected_seconds = None
if meta_path.exists():
    try:
        meta = json.loads(meta_path.read_text())
        expected_seconds = meta.get('expected_duration_seconds')
    except Exception:
        pass

result = {
    'steps_completed': steps_completed,
    'gpu': '$GPU',
    'project': '$PROJECT',
    'log_source': str(log_path.name),
    'dispatched_at': dispatched_at_str,
    'collected_at': collected_at_str,
    'duration_seconds': duration_seconds,
    'expected_duration_seconds': expected_seconds,
    'log_tail': '\n'.join(lines[-20:]),
}
# Add all parsed metrics as top-level keys
result.update(parsed_metrics)

with open('$SNAPSHOT_DIR/result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print(json.dumps({k: v for k, v in result.items() if k != 'log_tail'}, indent=2))
has_metric = primary_metric in parsed_metrics
print('HAS_METRIC=' + str(has_metric), file=sys.stderr)
" 2>&1) || true
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
