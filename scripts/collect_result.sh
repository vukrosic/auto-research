#!/usr/bin/env bash
# Collect results from a completed experiment on its GPU.
# Usage: scripts/collect_result.sh <experiment_name>
# Pulls logs and results back, parses val_bpb into result.json
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTORESEARCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/gpu_config.sh"

NAME="${1:?Usage: scripts/collect_result.sh <experiment_name>}"
SNAPSHOT_DIR="$AUTORESEARCH_DIR/experiments/snapshots/$NAME"

if [ ! -f "$SNAPSHOT_DIR/gpu" ]; then
    echo "ERROR: No GPU assigned for experiment '$NAME'"
    exit 1
fi

GPU=$(cat "$SNAPSHOT_DIR/gpu")
REMOTE_DIR=$(gpu_var "$GPU" REMOTE_DIR)

echo "=== Collecting results: $NAME from $GPU ==="

# Pull results directory
mkdir -p "$SNAPSHOT_DIR/results"
gpu_rsync_from "$GPU" "${REMOTE_DIR}/results/${NAME}/" "$SNAPSHOT_DIR/results/" 2>/dev/null || true

# Pull log
gpu_rsync_from "$GPU" "${REMOTE_DIR}/logs/${NAME}.txt" "$SNAPSHOT_DIR/results/train.log" 2>/dev/null || true
# Also try the nohup log
gpu_rsync_from "$GPU" "/tmp/autoresearch_${NAME}.log" "$SNAPSHOT_DIR/results/nohup.log" 2>/dev/null || true

# Parse metrics from log
LOG="$SNAPSHOT_DIR/results/train.log"
if [ -f "$LOG" ]; then
    PARSE_OUTPUT=$(python3 -c "
import json, re, sys
from pathlib import Path

log_path = Path('$LOG')
summary_path = Path('$SNAPSHOT_DIR/results/summary.json')
text = log_path.read_text(encoding='utf-8', errors='replace')
lines = text.splitlines()

val_bpb = None
val_quant = None
steps_completed = 0

if summary_path.exists():
    try:
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        summary = {}
    if isinstance(summary, dict):
        last_eval = summary.get('last_eval') or {}
        final_quant = summary.get('final_quant_eval') or {}
        val_bpb = last_eval.get('val_bpb')
        val_quant = final_quant.get('val_bpb')
        steps_completed = int(last_eval.get('step') or last_eval.get('max_steps') or 0)

if val_bpb is None:
    for line in reversed(lines):
        m = re.search(r'\\bval_bpb[:=]\\s*([0-9]+(?:\\.[0-9]+)?)\\b', line)
        if m:
            val_bpb = float(m.group(1))
            break

if val_quant is None:
    for line in reversed(lines):
        m = re.search(r'final_int8_zlib_roundtrip_exact[^0-9]*([0-9]+(?:\\.[0-9]+)?)', line)
        if m:
            val_quant = float(m.group(1))
            break

if steps_completed == 0:
    for line in reversed(lines):
        m = re.search(r'\\bstep[:=]\\s*([0-9]+)', line)
        if m:
            steps_completed = int(m.group(1))
            break
    if steps_completed == 0:
        for line in reversed(lines):
            m = re.search(r'warmup_step:(\\d+)/(\\d+)', line)
            if m:
                steps_completed = int(m.group(1))
                break

import datetime
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
    'val_bpb': val_bpb,
    'val_bpb_quant': val_quant,
    'steps_completed': steps_completed,
    'gpu': '$GPU',
    'dispatched_at': dispatched_at_str,
    'collected_at': collected_at_str,
    'duration_seconds': duration_seconds,
    'expected_duration_seconds': expected_seconds,
    'log_tail': '\\n'.join(lines[-20:]),
}
with open('$SNAPSHOT_DIR/result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print(json.dumps({k: v for k, v in result.items() if k != 'log_tail'}, indent=2))
has_metric = val_bpb is not None or val_quant is not None
print('HAS_METRIC=' + str(has_metric), file=sys.stderr)
" 2>&1) || true
    echo "$PARSE_OUTPUT"
    if echo "$PARSE_OUTPUT" | grep -q "HAS_METRIC=True"; then
        echo "done" > "$SNAPSHOT_DIR/status"
    else
        echo "failed" > "$SNAPSHOT_DIR/status"
        echo "WARNING: No val_bpb metric found in log — marking as failed"
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
