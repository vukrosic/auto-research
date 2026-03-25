#!/usr/bin/env bash
# Register a GPU in the local fallback registry and sync it to auto-research if available.
# Usage: bash infra/register_gpu.sh <name> <port> <password> [rate] [gpu_type]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

NAME="${1:?Usage: register_gpu.sh <name> <port> <password> [rate] [gpu_type]}"
PORT="${2:?Usage: register_gpu.sh <name> <port> <password> [rate] [gpu_type]}"
PASS="${3:?Usage: register_gpu.sh <name> <port> <password> [rate] [gpu_type]}"
RATE="${4:-}"
GPU_TYPE="${5:-}"

ARGS=("$NAME" "$PORT" "$PASS")
if [ -n "$RATE" ]; then
    ARGS+=("--rate" "$RATE")
fi
if [ -n "$GPU_TYPE" ]; then
    ARGS+=("--gpu-type" "$GPU_TYPE")
fi

python3 "$REPO_ROOT/infra/gpu_inventory.py" register "${ARGS[@]}"
