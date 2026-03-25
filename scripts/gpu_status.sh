#!/usr/bin/env bash
# Check status of all GPUs: connectivity, running processes, GPU utilization.
# Also checks across all projects for running experiments.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AUTORESEARCH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/gpu_config.sh"

for gpu in $ALL_GPUS; do
    echo "=== $gpu ==="

    # Check connectivity
    if ! gpu_ssh "$gpu" "echo ok" &>/dev/null; then
        echo "  STATUS: OFFLINE (cannot connect)"
        echo ""
        continue
    fi

    echo "  STATUS: ONLINE"

    # GPU utilization
    util=$(gpu_ssh "$gpu" "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits 2>/dev/null" || echo "?,?,?,?")
    echo "  GPU: ${util}"

    # Collect process patterns from all project configs
    PATTERNS=$(python3 -c "
import json, glob
patterns = set()
for f in glob.glob('$AUTORESEARCH_DIR/projects/*.json'):
    p = json.load(open(f))
    pp = p.get('process_pattern', '')
    if pp:
        patterns.add(pp)
if not patterns:
    patterns.add('python3')
print('|'.join(patterns))
" 2>/dev/null || echo "python3")

    # Check for running training using project-specific patterns
    training=$(gpu_ssh "$gpu" "ps aux | grep -E '$PATTERNS' | grep -v grep | head -1" 2>/dev/null || echo "")
    if [ -n "$training" ]; then
        echo "  TRAINING: running"
    else
        echo "  TRAINING: idle"
    fi

    # Show which experiment is assigned to this GPU (from local state)
    for proj_dir in "$AUTORESEARCH_DIR"/experiments/*/; do
        [ -d "$proj_dir/snapshots" ] || continue
        proj_name=$(basename "$proj_dir")
        for snap_dir in "$proj_dir"/snapshots/*/; do
            [ -d "$snap_dir" ] || continue
            snap_status=$(cat "$snap_dir/status" 2>/dev/null || true)
            snap_gpu=$(cat "$snap_dir/gpu" 2>/dev/null || true)
            if [ "$snap_status" = "running" ] && [ "$snap_gpu" = "$gpu" ]; then
                echo "  EXPERIMENT: $(basename "$snap_dir") (project: $proj_name)"
            fi
        done
    done

    echo ""
done
