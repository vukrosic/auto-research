#!/usr/bin/env bash
# Check status of all GPUs: connectivity, running processes, GPU utilization.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
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
    echo "  GPU: ${util}% util, ${util##*,}°C"

    # Check for running training
    training=$(gpu_ssh "$gpu" "ps aux | grep 'train_gpt.py' | grep -v grep | head -1" 2>/dev/null || echo "")
    if [ -n "$training" ]; then
        echo "  TRAINING: running"
        # Try to get experiment name from RUN_ID env
        run_id=$(gpu_ssh "$gpu" "ps aux | grep train_gpt.py | grep -v grep | head -1 | sed 's/.*RUN_ID=\([^ ]*\).*/\1/'" 2>/dev/null || echo "unknown")
        echo "  EXPERIMENT: $run_id"
    else
        echo "  TRAINING: idle"
    fi

    echo ""
done
