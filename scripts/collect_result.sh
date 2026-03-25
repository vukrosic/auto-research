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
    # Extract last val_bpb
    VAL_BPB=$(grep 'val_bpb' "$LOG" | tail -1 | grep -oP 'val_bpb[:\s=]+\K[0-9.]+' || echo "null")
    # Extract post-quant if available
    QUANT_BPB=$(grep 'final_int8_zlib_roundtrip_exact' "$LOG" | tail -1 | grep -oP '[0-9]+\.[0-9]+' || echo "null")
    # Extract steps completed
    STEPS=$(grep -oP 'step[:\s=]+\K[0-9]+' "$LOG" | tail -1 || echo "0")
    # Log tail
    LOG_TAIL=$(tail -20 "$LOG")

    python3 -c "
import json
result = {
    'val_bpb': $VAL_BPB if '$VAL_BPB' != 'null' else None,
    'val_bpb_quant': $QUANT_BPB if '$QUANT_BPB' != 'null' else None,
    'steps_completed': int('${STEPS}') if '${STEPS}' else 0,
    'gpu': '$GPU',
    'log_tail': '''$(tail -20 "$LOG" | sed "s/'/\\\\'/g")'''
}
with open('$SNAPSHOT_DIR/result.json', 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
"
    echo "done" > "$SNAPSHOT_DIR/status"
    echo "=== Result written to $SNAPSHOT_DIR/result.json ==="
else
    echo "ERROR: No training log found"
    echo "failed" > "$SNAPSHOT_DIR/status"
fi
